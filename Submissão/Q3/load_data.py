#!/usr/bin/env python3
"""Questao 3 - Carregamento: carrega os 24 CSVs no PostgreSQL respeitando o
schema criado na Q2 (schema.sql ja aplicado antes de rodar este script), sem
nenhum tratamento - sem remover nulo, sem corrigir caractere especial.

Credenciais vem das variaveis de ambiente padrao do PostgreSQL (PGHOST,
PGPORT, PGDATABASE, PGUSER, PGPASSWORD), lidas automaticamente pelo
psycopg2/libpq - nunca no codigo.

COPY FROM STDIN, nao INSERT nem COPY FROM caminho no servidor: o arquivo e
transmitido do cliente Python direto pro protocolo COPY do Postgres, sem
reconstruir linha nenhuma - preserva aspas, virgula interna, acento e zero a
esquerda em coluna TEXT exatamente como estao no CSV. Colunas declaradas
explicitamente na ordem do cabecalho do CSV, nunca dependendo da ordem
fisica da tabela. Identificadores via psycopg2.sql.Identifier, nunca
f-string.

As 24 tabelas carregam numa unica transacao: COMMIT so depois de reconciliar
a contagem de cada tabela (CSV vs. Postgres); qualquer divergencia ou falha
faz ROLLBACK de tudo, nao deixa banco parcialmente carregado.

Sem PRIMARY KEY/UNIQUE no schema da Q2 (camada bruta, de proposito), rodar
duas vezes duplicaria os dados silenciosamente - por isso o script aborta se
encontrar uma tabela de destino que ja tem linha. Recarregar e um passo
consciente: recriar o banco (ou as tabelas) antes de rodar de novo.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
PASTA_CSVS = RAIZ_REPOSITORIO / "data" / "raw" / "1-lh_nautical_csv"

OPCOES_COPY = "FORMAT CSV, HEADER TRUE, ENCODING 'UTF8', NULL ''"
TABELAS_Q3_2 = ["customers", "orders", "order_items", "payments"]


def listar_csvs() -> list[Path]:
    caminhos = sorted(PASTA_CSVS.glob("*.csv"))
    if len(caminhos) != 24:
        raise SystemExit(f"esperados 24 CSVs em {PASTA_CSVS}, encontrados {len(caminhos)}")
    return caminhos


def ler_cabecalho(caminho: Path) -> list[str]:
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        return next(csv.reader(f))


def contar_linhas_csv(caminho: Path) -> int:
    with caminho.open(newline="", encoding="utf-8-sig") as f:
        leitor = csv.reader(f)
        next(leitor)  # cabeçalho
        return sum(1 for _ in leitor)


def contar_linhas_banco(cur, tabela: str) -> int:
    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(tabela)))
    return cur.fetchone()[0]


def verificar_destino_vazio(cur, tabelas: list[str]) -> None:
    ocupadas = [t for t in tabelas if contar_linhas_banco(cur, t) > 0]
    if ocupadas:
        raise ValueError(
            f"destino não está vazio, carga abortada pra não duplicar: {', '.join(ocupadas)}. "
            "Recrie o banco (ou as tabelas) antes de rodar de novo."
        )


def carregar_csv(cur, caminho: Path, tabela: str, cabecalho: list[str]) -> None:
    copy_sql = sql.SQL("COPY {tabela} ({colunas}) FROM STDIN WITH ({opcoes})").format(
        tabela=sql.Identifier(tabela),
        colunas=sql.SQL(", ").join(sql.Identifier(c) for c in cabecalho),
        opcoes=sql.SQL(OPCOES_COPY),
    )
    with caminho.open("rb") as f:
        cur.copy_expert(copy_sql, f)


def main() -> int:
    try:
        conn = psycopg2.connect()
    except psycopg2.OperationalError as exc:
        print(f"ERRO ao conectar no PostgreSQL: {exc}", file=sys.stderr)
        return 1

    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            caminhos = listar_csvs()
            tabelas = [c.stem for c in caminhos]
            print(f"{len(caminhos)} CSVs encontrados em {PASTA_CSVS}")

            verificar_destino_vazio(cur, tabelas)

            print("Carregando via COPY FROM STDIN...")
            contagens_csv = {}
            for caminho, tabela in zip(caminhos, tabelas):
                cabecalho = ler_cabecalho(caminho)
                contagens_csv[tabela] = contar_linhas_csv(caminho)
                carregar_csv(cur, caminho, tabela, cabecalho)
                print(f"  [{tabela}] carregado")

            print("\nReconciliando CSV vs. PostgreSQL, tabela por tabela...")
            divergente = False
            for tabela in tabelas:
                esperado = contagens_csv[tabela]
                no_banco = contar_linhas_banco(cur, tabela)
                status = "OK" if no_banco == esperado else "DIVERGENTE"
                divergente = divergente or status != "OK"
                print(f"  {tabela:28s} csv={esperado:7d}  postgres={no_banco:7d}  {status}")

            if divergente:
                conn.rollback()
                print("\nROLLBACK — divergência encontrada, nenhuma linha ficou gravada.", file=sys.stderr)
                return 1

            total = sum(contar_linhas_banco(cur, t) for t in TABELAS_Q3_2)

            conn.commit()
            print(f"\nCOMMIT — {len(tabelas)} tabelas carregadas e reconciliadas.")
            print(f"Q3.2 (customers + orders + order_items + payments): {total}")
            return 0

    except Exception as exc:
        conn.rollback()
        print(f"\nERRO — {type(exc).__name__}: {exc}", file=sys.stderr)
        print("ROLLBACK confirmado — nenhuma tabela ficou parcialmente carregada.", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
