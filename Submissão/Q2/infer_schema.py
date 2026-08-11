#!/usr/bin/env python3
"""Questao 2 - Schema: le os CSVs de PASTA_CSVS e gera um schema.sql (DDL
PostgreSQL), um CREATE TABLE por arquivo. So biblioteca padrao (csv, re,
datetime, pathlib) - nada de pandas/dask/polars.

Por coluna, o tipo e decidido em ordem: override semantico explicito (lista
abaixo, para identificadores/documentos que parecem numero mas nao sao) ->
varredura de 100% das linhas (nunca amostra) testando, nessa ordem, vazio ->
booleano -> inteiro -> decimal -> data -> timestamp -> texto. Um unico valor
fora do padrao já reclassifica a coluna inteira para o proximo nivel mais
permissivo. Zero a esquerda ("01234567890") bloqueia tanto o caminho inteiro
quanto o decimal, porque qualquer tipo numerico do Postgres perderia esse
zero silenciosamente na leitura de volta.

Sem PRIMARY KEY, FOREIGN KEY ou NOT NULL: este schema.sql e uma camada de
ingestao bruta, o objetivo e nao rejeitar nenhuma linha real na carga da Q3.

O motivo de cada override semantico esta comentado ao lado da propria
entrada, em OVERRIDES_TEXTO abaixo.
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


def novo_estado() -> dict:
    return {
        "total": 0,
        "vazios": 0,
        "bool": True,
        "inteiro": True,
        "decimal": True,
        "data": True,
        "timestamp": True,
    }


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


def observar(estado: dict, valor: str) -> None:
    """Atualiza o estado da coluna com um valor por vez (varredura em fluxo,
    sem acumular os valores da coluna inteira em memória)."""
    estado["total"] += 1
    if valor == "":
        estado["vazios"] += 1
        return

    if valor not in VALORES_BOOL:
        estado["bool"] = False

    if RE_ZERO_A_ESQUERDA.match(valor):
        estado["inteiro"] = False
        estado["decimal"] = False
    else:
        parece_inteiro = bool(RE_INTEIRO.match(valor))
        parece_decimal = bool(RE_DECIMAL.match(valor))

        if parece_inteiro:
            if not (BIGINT_MIN <= int(valor) <= BIGINT_MAX):
                estado["inteiro"] = False
        else:
            estado["inteiro"] = False

        if not (parece_inteiro or parece_decimal):
            estado["decimal"] = False

    if estado["data"] and not eh_data(valor):
        estado["data"] = False
    if estado["timestamp"] and not eh_timestamp(valor):
        estado["timestamp"] = False


def decidir_tipo(estado: dict) -> str:
    if estado["total"] - estado["vazios"] == 0:
        return "TEXT"  # coluna 100% vazia, sem evidência
    if estado["bool"]:
        return "BOOLEAN"
    if estado["inteiro"]:
        return "BIGINT"
    if estado["decimal"]:
        return "NUMERIC"
    if estado["data"]:
        return "DATE"
    if estado["timestamp"]:
        return "TIMESTAMP"
    return "TEXT"


def ler_csv_e_inferir(caminho: Path) -> list[tuple[str, str]]:
    """Varre um CSV inteiro e retorna [(coluna, tipo_sql), ...]."""
    nome_tabela = caminho.stem
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        leitor = csv.reader(f)
        cabecalho = next(leitor)
        estados = [novo_estado() for _ in cabecalho]
        for numero_linha, linha in enumerate(leitor, start=2):
            if len(linha) != len(cabecalho):
                raise ValueError(
                    f"{caminho.name}, linha {numero_linha}: {len(linha)} campos, "
                    f"esperado {len(cabecalho)}"
                )
            for valor, estado in zip(linha, estados):
                observar(estado, valor)

    colunas = []
    for nome_coluna, estado in zip(cabecalho, estados):
        override = OVERRIDES_TEXTO.get(f"{nome_tabela}.{nome_coluna}")
        tipo = "TEXT" if override else decidir_tipo(estado)
        colunas.append((nome_coluna, tipo))
    return colunas


def gerar_create_table(nome_tabela: str, colunas: list[tuple[str, str]]) -> str:
    linhas = [f'CREATE TABLE "{nome_tabela}" (']
    ultimo = len(colunas) - 1
    for i, (nome_coluna, tipo) in enumerate(colunas):
        virgula = "," if i < ultimo else ""
        linhas.append(f'    "{nome_coluna}" {tipo}{virgula}')
    linhas.append(");")
    return "\n".join(linhas)


def main() -> None:
    caminhos_csv = sorted(PASTA_CSVS.glob("*.csv"))
    if not caminhos_csv:
        raise SystemExit(f"nenhum CSV encontrado em {PASTA_CSVS}")

    blocos = []
    for caminho in caminhos_csv:
        colunas = ler_csv_e_inferir(caminho)
        blocos.append(gerar_create_table(caminho.stem, colunas))

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
