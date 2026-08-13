#!/usr/bin/env python3
"""Questao 2 - Schema: le os CSVs de PASTA_CSVS e gera um schema.sql (DDL
PostgreSQL), um CREATE TABLE por arquivo. So biblioteca padrao (csv, re,
datetime, pathlib) - nada de pandas/dask/polars.

Fluxo linear, um passo de cada vez:
1. ler o CSV inteiro (sem amostragem);
2. organizar os valores de cada coluna numa lista;
3. inferir o tipo de cada coluna (funcao unica, regras testadas em ordem
   com all() - o primeiro caso em que TODOS os valores da coluna passam
   no teste "vence");
4. gerar o CREATE TABLE da tabela;
5. gravar tudo em schema.sql.

Zero a esquerda ("01234567890") bloqueia BIGINT e NUMERIC, porque qualquer
tipo numerico do Postgres perderia esse zero silenciosamente na leitura de
volta. Identificadores que parecem numero mas sao documento/codigo (CPF,
chave de NF-e, etc.) tem um override explicito para TEXT, comentado ao lado
de cada entrada em OVERRIDES_TEXTO.

Sem PRIMARY KEY, FOREIGN KEY ou NOT NULL: este schema.sql e uma camada de
ingestao bruta, o objetivo e nao rejeitar nenhuma linha real na carga da Q3.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from pathlib import Path

PASTA_SCRIPT = Path(__file__).resolve().parent
RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]

PASTA_CSVS = RAIZ_REPOSITORIO / "data" / "raw" / "1-lh_nautical_csv"
ARQUIVO_SAIDA = PASTA_SCRIPT / "schema.sql"

BIGINT_MIN = -9_223_372_036_854_775_808
BIGINT_MAX = 9_223_372_036_854_775_807

RE_INTEIRO = re.compile(r"^-?\d+$")
RE_DECIMAL = re.compile(r"^-?\d+\.\d+$")
RE_ZERO_A_ESQUERDA = re.compile(r"^-?0\d")  # zero seguido de outro digito
VALORES_BOOL = {"TRUE", "FALSE"}
TAM_DATA = 10
TAM_TIMESTAMP = 19

# Overrides semânticos: identificadores puramente numéricos cujo tipo TEXT
# não é garantido só pela inferência por valor - dois grupos:
#   (a) mudariam para BIGINT hoje mesmo, sem o override: cpf, ncm_code,
#       addresses.number, locations.number (0% zero à esquerda no lote atual);
#   (b) já são TEXT hoje por causa da guarda de zero à esquerda, mas isso
#       depende do lote: tax_id, nfe_access_key, series, barcode_ean têm zero
#       à esquerda em PARTE dos registros - se o próximo lote não tiver
#       nenhum, a guarda não teria motivo para agir. Chave = "tabela.coluna".
OVERRIDES_TEXTO = {
    "customers.tax_id": "CPF/CNPJ - tem zero à esquerda só em parte dos registros deste lote",
    "employees.cpf": "CPF - 0% zero à esquerda neste lote; sem override viraria BIGINT",
    "products.ncm_code": "código fiscal de 8 dígitos - 0% zero à esquerda; sem override viraria BIGINT",
    "fiscal_invoices.nfe_access_key": "chave de NF-e (44 dígitos) - tem zero à esquerda só em parte dos registros",
    "fiscal_invoices.series": "série da NF-e - hoje só '001', zero à esquerda não é garantia estrutural",
    "product_variants.barcode_ean": "EAN - tem zero à esquerda só em parte dos registros (85 de 852)",
    "addresses.number": "número do endereço - 0% zero à esquerda hoje; sem override viraria BIGINT",
    "locations.number": "número do endereço - mesmo caso de addresses.number",
}


# --- Passo 3: predicados usados pela inferência (um por tipo candidato) ----


def tem_zero_a_esquerda(valor: str) -> bool:
    return bool(RE_ZERO_A_ESQUERDA.match(valor))


def eh_inteiro_seguro(valor: str) -> bool:
    """Inteiro sem zero à esquerda e dentro do limite do BIGINT."""
    if tem_zero_a_esquerda(valor) or not RE_INTEIRO.match(valor):
        return False
    return BIGINT_MIN <= int(valor) <= BIGINT_MAX


def eh_numerico(valor: str) -> bool:
    """Inteiro ou decimal, sem zero à esquerda (mesmo motivo do BIGINT)."""
    if tem_zero_a_esquerda(valor):
        return False
    return bool(RE_INTEIRO.match(valor) or RE_DECIMAL.match(valor))


def eh_data(valor: str) -> bool:
    if len(valor) != TAM_DATA:
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def eh_timestamp(valor: str) -> bool:
    if len(valor) != TAM_TIMESTAMP:
        return False
    try:
        datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
        return True
    except ValueError:
        return False


def inferir_tipo(valores: list[str]) -> str:
    """Testa os candidatos em ordem, do mais restrito ao mais permissivo.
    O primeiro tipo em que TODOS os valores da coluna passam no teste
    (all()) é o escolhido; se nenhum servir, a coluna vira TEXT."""
    preenchidos = [v for v in valores if v != ""]

    if not preenchidos:
        return "TEXT"  # coluna 100% vazia, sem evidência pra decidir
    if all(v in VALORES_BOOL for v in preenchidos):
        return "BOOLEAN"
    if all(eh_inteiro_seguro(v) for v in preenchidos):
        return "BIGINT"
    if all(eh_numerico(v) for v in preenchidos):
        return "NUMERIC"
    if all(eh_data(v) for v in preenchidos):
        return "DATE"
    if all(eh_timestamp(v) for v in preenchidos):
        return "TIMESTAMP"
    return "TEXT"


def tipo_da_coluna(nome_tabela: str, nome_coluna: str, valores: list[str]) -> str:
    """Override semântico primeiro; só chama a inferência se a coluna não
    estiver na lista de identificadores que precisam ficar como TEXT."""
    if f"{nome_tabela}.{nome_coluna}" in OVERRIDES_TEXTO:
        return "TEXT"
    return inferir_tipo(valores)


# --- Passos 1 e 2: ler o CSV inteiro e organizar os valores por coluna -----


def ler_valores_por_coluna(caminho: Path) -> tuple[list[str], list[list[str]]]:
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        valores_por_coluna: list[list[str]] = [[] for _ in cabecalho]

        for numero_linha, linha in enumerate(leitor, start=2):
            if len(linha) != len(cabecalho):
                raise ValueError(
                    f"{caminho.name}, linha {numero_linha}: {len(linha)} campos, "
                    f"esperado {len(cabecalho)}"
                )
            for valores_da_coluna, valor in zip(valores_por_coluna, linha):
                valores_da_coluna.append(valor)

    return cabecalho, valores_por_coluna


# --- Passo 4: montar o CREATE TABLE a partir dos tipos já decididos -------


def gerar_create_table(nome_tabela: str, colunas: list[tuple[str, str]]) -> str:
    linhas = [f'CREATE TABLE "{nome_tabela}" (']
    ultimo = len(colunas) - 1
    for i, (nome_coluna, tipo) in enumerate(colunas):
        virgula = "," if i < ultimo else ""
        linhas.append(f'    "{nome_coluna}" {tipo}{virgula}')
    linhas.append(");")
    return "\n".join(linhas)


def processar_csv(caminho: Path) -> str:
    """Une os passos 1 a 4 para um único CSV: lê, organiza por coluna,
    infere o tipo de cada uma e devolve o CREATE TABLE pronto."""
    nome_tabela = caminho.stem
    cabecalho, valores_por_coluna = ler_valores_por_coluna(caminho)

    colunas = [
        (nome_coluna, tipo_da_coluna(nome_tabela, nome_coluna, valores))
        for nome_coluna, valores in zip(cabecalho, valores_por_coluna)
    ]
    return gerar_create_table(nome_tabela, colunas)


# --- Passo 5: rodar para todos os CSVs e gravar o schema.sql --------------


def main() -> None:
    caminhos_csv = sorted(PASTA_CSVS.glob("*.csv"))
    if not caminhos_csv:
        raise SystemExit(f"nenhum CSV encontrado em {PASTA_CSVS}")

    blocos = [processar_csv(caminho) for caminho in caminhos_csv]

    cabecalho_arquivo = (
        f"-- schema.sql gerado por infer_schema.py a partir de {len(caminhos_csv)} CSVs em data/raw/1-lh_nautical_csv\n"
        "-- Camada de ingestão bruta (landing): sem PRIMARY KEY/FOREIGN KEY/NOT NULL,\n"
        "-- para não rejeitar nenhuma linha real na carga da Q3.\n"
        "-- Overrides semânticos (identificador tratado como TEXT mesmo parecendo número)\n"
        "-- e o raciocínio completo da inferência: ver infer_schema.py.\n"
    )
    ARQUIVO_SAIDA.write_text(cabecalho_arquivo + "\n" + "\n\n".join(blocos) + "\n", encoding="utf-8")
    print(f"{len(caminhos_csv)} tabelas geradas em {ARQUIVO_SAIDA}")


if __name__ == "__main__":
    main()
