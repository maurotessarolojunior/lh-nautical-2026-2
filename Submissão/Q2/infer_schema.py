#!/usr/bin/env python3
"""Questao 2 - Schema: infere o schema PostgreSQL de cada CSV e gera schema.sql.

Uso:
    python infer_schema.py [--input-dir lh_nautical_csv] [--output schema.sql]

Regras obrigatorias respeitadas: so biblioteca padrao (csv, os, re, decimal,
datetime, argparse, pathlib - nada de pandas/dask/polars); destino Postgres.

------------------------------------------------------------------------
COMO A INFERENCIA FUNCIONA (leia isto antes de mexer no codigo)
------------------------------------------------------------------------
Por coluna, o tipo e decidido em duas etapas, nesta ordem de prioridade:

  1. Override semantico explicito (SEMANTIC_TEXT_OVERRIDES abaixo): uma
     lista nomeada por "tabela.coluna" para colunas que sao identificadores/
     codigos/documentos, nao grandezas matematicas (cpf, tax_id, telefone,
     chave de NF-e, CEP, SKU, numero de pedido/compra/devolucao, EAN, NCM).
     Essas colunas viram TEXT mesmo que os valores observados pareçam
     inteiros - CPF, chave de NF-e e CEP podem ser só dígitos sem
     representar uma quantidade sobre a qual soma/média faz sentido.

  2. Inferencia por varredura completa (100% das linhas, nunca amostra)
     para todas as colunas nao cobertas pelo passo 1, na ordem:
     vazio -> booleano -> inteiro -> decimal -> data -> timestamp -> texto.
     Cada nivel so "sobrevive" se TODOS os valores nao vazios da coluna
     baterem com o criterio - um unico valor fora do padrao já reclassifica
     a coluna inteira para o proximo nivel mais permissivo.

Duas guardas de integridade valem tanto para inteiro quanto para decimal
(nao so para inteiro, que seria o erro mais comum):

  - Zero a esquerda ("01234567890"): qualquer coluna numerica do Postgres
    (INTEGER, BIGINT, NUMERIC) normaliza o valor e perde o zero a esquerda
    na leitura de volta - isso e corrupcao silenciosa de dado, nao so um
    problema de INTEGER. Por isso a checagem de zero a esquerda bloqueia
    tanto o caminho inteiro quanto o caminho decimal.
  - Estouro de BIGINT (> ~9.2e18): so bloqueia o caminho inteiro. NUMERIC
    do Postgres aceita muito mais digitos que isso, entao um numero de 44
    digitos sem zero a esquerda (como parte de fiscal_invoices.nfe_access_key)
    ainda cairia em NUMERIC(44,0) por pura inferencia de valor - tecnicamente
    nao quebraria a carga, mas seria um tipo enganoso (chave de NF-e nao e
    uma grandeza). E exatamente por isso que o override semantico do passo 1
    continua necessario mesmo depois dessas duas guardas: elas evitam quebra
    de carga e corrupcao, mas nao substituem o julgamento de que aquilo e
    um identificador, nao um numero.

Nota honesta sobre o limite da inferencia por valor: em employees.cpf, os
15 CPFs desta tabela nao tem nenhum zero a esquerda na amostra atual - a
guarda acima nao teria motivo para agir, e por inferencia pura a coluna
viraria BIGINT sem erro aparente. Isso seria coincidencia da amostra, nao
garantia. O override semantico existe para nao depender dessa sorte.

Nenhuma PRIMARY KEY, FOREIGN KEY ou NOT NULL e gerada. Este schema.sql
representa uma camada de ingestao bruta (landing): o objetivo e nao
rejeitar nenhuma linha real na carga da Q3, que carrega sem tratamento.
Chaves e obrigatoriedades candidatas ficam documentadas em comentario por
tabela, para promover a constraint depois, se e quando a integridade entre
as 24 tabelas for validada - isso nao e um passo garantido do desafio.
"""

from __future__ import annotations

import argparse
import csv
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

BIGINT_MIN = -9_223_372_036_854_775_808
BIGINT_MAX = 9_223_372_036_854_775_807

INT_RE = re.compile(r"^-?\d+$")
DECIMAL_RE = re.compile(r"^-?\d+\.\d+$")
LEADING_ZERO_RE = re.compile(r"^-?0\d")  # "0123" ou "-0123": zero seguido de outro digito
BOOL_VALUES = {"TRUE", "FALSE"}
DATE_LEN = 10
TIMESTAMP_LEN = 19

# ---------------------------------------------------------------------
# Passo 1: overrides semanticos explicitos por "tabela.coluna".
#
# Cada entrada e uma coluna que, por avaliacao de dominio, e um
# identificador/codigo/documento - nao uma grandeza matematica - mesmo
# quando o valor observado e puramente numerico. Onde o override coincide
# com o que a inferencia por valor ja decidiria sozinha (ex.: order_number,
# que ja tem prefixo "SO-"), a entrada fica mesmo assim: o objetivo e
# documentar a intencao, nao so cobrir o caso que a amostra atual mostrou.
# ---------------------------------------------------------------------
SEMANTIC_TEXT_OVERRIDES: dict[str, str] = {
    "customers.tax_id": "CPF/CNPJ - documento, nao quantidade (ja seria pego pela guarda de zero a esquerda; mantido explicito)",
    "customers.phone": "telefone - identificador de contato, nao quantidade",
    "customers.state_registration": "inscricao estadual - pode ser 'ISENTO'; ja e texto por evidencia, mantido explicito",
    "employees.cpf": "CPF - documento; amostra atual (15 linhas) nao tem zero a esquerda por coincidencia, nao por garantia",
    "suppliers.phone": "telefone - identificador de contato, nao quantidade",
    "suppliers.tax_id": "documento fiscal do fornecedor (formato varia por pais); ja e texto por evidencia, mantido explicito",
    "fiscal_invoices.nfe_access_key": "chave de acesso da NF-e (44 digitos) - identificador, nao quantidade",
    "fiscal_invoices.nfe_number": "numero da NF-e - identificador; ja e texto por evidencia (prefixo NFE), mantido explicito",
    "addresses.postal_code": "CEP - identificador geografico; ja e texto por evidencia (formato com hifen), mantido explicito",
    "locations.postal_code": "CEP - identificador geografico; ja e texto por evidencia (formato com hifen), mantido explicito",
    "addresses.number": "numero do endereco - pode conter 'S/N' ou complemento no futuro; nao e usado em operacao aritmetica",
    "product_variants.barcode_ean": "codigo de barras EAN - identificador, nao quantidade",
    "product_variants.sku": "SKU - identificador; ja e texto por evidencia, mantido explicito",
    "product_suppliers.supplier_sku": "SKU do fornecedor - identificador; ja e texto por evidencia, mantido explicito",
    "products.ncm_code": "codigo NCM (classificacao fiscal de mercadoria) - identificador de categoria, nao quantidade",
    "orders.order_number": "numero do pedido - identificador; ja e texto por evidencia (prefixo SO-), mantido explicito",
    "purchase_orders.po_number": "numero da ordem de compra - identificador; ja e texto por evidencia (prefixo PO-), mantido explicito",
    "returns.return_number": "numero da devolucao - identificador; ja e texto por evidencia (prefixo RT-), mantido explicito",
}


class ColumnInference:
    """Acumula evidencia de uma coluna, uma linha por vez (varredura completa)."""

    def __init__(self) -> None:
        self.total = 0
        self.empty = 0
        self.is_bool = True
        self.is_int = True
        self.int_range_ok = True
        self.is_decimal = True
        self.is_date = True
        self.is_timestamp = True
        self.max_int_digits = 0
        self.max_scale = 0

    def observe(self, value: str) -> None:
        self.total += 1
        if value == "":
            self.empty += 1
            return

        if value not in BOOL_VALUES:
            self.is_bool = False

        has_leading_zero = bool(LEADING_ZERO_RE.match(value))
        if has_leading_zero:
            # zero a esquerda: nenhum tipo numerico do Postgres preserva isso
            self.is_int = False
            self.is_decimal = False
        else:
            looks_int = bool(INT_RE.match(value))
            looks_decimal = bool(DECIMAL_RE.match(value))

            # Inteiro so sobrevive se TODO valor bater com INT_RE (um valor
            # com ponto decimal, ex. "1234.56", derruba is_int mesmo que
            # "pareça numerico" no sentido amplo - e exatamente o bug que
            # um "elif" mal desenhado aqui deixou passar na primeira versao
            # deste script (sale_price/cost_price saiam como BIGINT).
            if looks_int:
                int_value = int(value)
                if not (BIGINT_MIN <= int_value <= BIGINT_MAX):
                    self.is_int = False
            else:
                self.is_int = False

            if looks_int or looks_decimal:
                self._update_decimal_shape(value)
            else:
                self.is_decimal = False

        if self.is_date and not self._is_valid_date(value):
            self.is_date = False
        if self.is_timestamp and not self._is_valid_timestamp(value):
            self.is_timestamp = False

    def _update_decimal_shape(self, value: str) -> None:
        try:
            digits, exponent = Decimal(value).as_tuple()[1:]
        except InvalidOperation:
            self.is_decimal = False
            return
        scale = max(0, -exponent)
        int_digits = max(1, len(digits) - scale)
        self.max_scale = max(self.max_scale, scale)
        self.max_int_digits = max(self.max_int_digits, int_digits)

    @staticmethod
    def _is_valid_date(value: str) -> bool:
        if len(value) != DATE_LEN:
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_valid_timestamp(value: str) -> bool:
        if len(value) != TIMESTAMP_LEN:
            return False
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False

    def decide(self) -> tuple[str, str]:
        """Retorna (tipo_sql, motivo) considerando so os valores nao vazios."""
        non_empty = self.total - self.empty
        if non_empty == 0:
            return "TEXT", "coluna 100% vazia - sem evidencia, fallback documentado"
        if self.is_bool:
            return "BOOLEAN", "100% dos valores sao TRUE/FALSE"
        if self.is_int:
            return "BIGINT", "100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT"
        if self.is_decimal:
            precision = self.max_int_digits + self.max_scale
            return (
                f"NUMERIC({precision},{self.max_scale})",
                f"100% numerico decimal, sem zero a esquerda (maior forma observada: {self.max_int_digits} "
                f"digito(s) inteiro(s) + {self.max_scale} decimal(is))",
            )
        if self.is_date:
            return "DATE", "100% no formato YYYY-MM-DD"
        if self.is_timestamp:
            return "TIMESTAMP", "100% no formato YYYY-MM-DD HH:MM:SS"
        return "TEXT", "valores mistos ou fora dos formatos acima"


def quote_ident(name: str) -> str:
    """Aspas duplas defensivas em qualquer identificador (tabela ou coluna)."""
    return '"' + name.replace('"', '""') + '"'


def infer_table_schema(csv_path: Path) -> list[tuple[str, str, str]]:
    """Varre um CSV inteiro e retorna [(coluna, tipo_sql, motivo), ...]."""
    table_name = csv_path.stem
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        inferences = [ColumnInference() for _ in header]
        for line_number, row in enumerate(reader, start=2):
            if len(row) != len(header):
                raise ValueError(
                    f"{csv_path.name}, linha {line_number}: {len(row)} campos, "
                    f"esperado {len(header)} (cabecalho: {header})"
                )
            for value, inference in zip(row, inferences):
                inference.observe(value)

    columns: list[tuple[str, str, str]] = []
    for column_name, inference in zip(header, inferences):
        override_key = f"{table_name}.{column_name}"
        if override_key in SEMANTIC_TEXT_OVERRIDES:
            columns.append(("TEXT", SEMANTIC_TEXT_OVERRIDES[override_key], column_name))
        else:
            sql_type, reason = inference.decide()
            columns.append((sql_type, reason, column_name))
    # devolve na ordem (coluna, tipo, motivo) para leitura mais natural no chamador
    return [(col, sql_type, reason) for sql_type, reason, col in columns]


def generate_create_table(table_name: str, columns: list[tuple[str, str, str]]) -> str:
    # A virgula que separa colunas tem que vir ANTES do comentario "-- motivo",
    # nunca depois: "--" comenta ate o fim da linha, entao uma virgula colocada
    # depois dela vira texto do comentario, nao um separador de verdade - o
    # parser do Postgres perde a virgula e da erro de sintaxe na coluna seguinte.
    lines = [f"CREATE TABLE {quote_ident(table_name)} ("]
    last_index = len(columns) - 1
    for i, (column_name, sql_type, reason) in enumerate(columns):
        separator = "," if i < last_index else ""
        lines.append(f"    {quote_ident(column_name)} {sql_type}{separator} -- {reason}")
    lines.append(");")
    return "\n".join(lines)


def build_schema_sql(input_dir: Path) -> str:
    csv_paths = sorted(input_dir.glob("*.csv"))
    if not csv_paths:
        raise SystemExit(f"nenhum CSV encontrado em {input_dir}")

    header = f"""-- schema.sql gerado automaticamente por infer_schema.py
-- Fonte: {len(csv_paths)} arquivos CSV em {input_dir}
-- Destino: PostgreSQL. Camada de ingestao bruta (landing) - sem PRIMARY KEY,
-- FOREIGN KEY ou NOT NULL: o objetivo e nao rejeitar nenhuma linha real na
-- carga da Q3. Cada coluna traz um comentario com o motivo da tipagem
-- (override semantico explicito ou evidencia da varredura completa do CSV).
-- Ver o cabecalho deste script para o raciocinio completo da inferencia.
"""
    tables_sql = []
    for csv_path in csv_paths:
        table_name = csv_path.stem
        columns = infer_table_schema(csv_path)
        tables_sql.append(generate_create_table(table_name, columns))
    return header + "\n\n" + "\n\n".join(tables_sql) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("lh_nautical_csv"),
        help="diretorio com os 24 CSVs de origem (default: ./lh_nautical_csv)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("schema.sql"),
        help="arquivo .sql de saida (default: ./schema.sql)",
    )
    args = parser.parse_args()

    schema_sql = build_schema_sql(args.input_dir)
    args.output.write_text(schema_sql, encoding="utf-8")
    print(f"schema.sql gerado em {args.output} a partir de {args.input_dir}")


if __name__ == "__main__":
    main()
