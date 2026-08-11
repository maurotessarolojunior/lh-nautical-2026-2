#!/usr/bin/env python3
"""Questao 3 - Carregamento: carrega os 24 CSVs no PostgreSQL respeitando o
schema criado na Q2, sem nenhum tratamento (sem remover nulo, sem corrigir
caractere especial, sem normalizar nada).

Uso:
    python load_data.py --input-dir lh_nautical_csv
    python load_data.py --input-dir lh_nautical_csv --schema-file schema.sql
    python load_data.py --input-dir lh_nautical_csv --truncate-before-load

Credenciais nunca vao no codigo nem em argumento de linha de comando: vem
das variaveis de ambiente padrao do PostgreSQL (PGHOST, PGPORT, PGDATABASE,
PGUSER, PGPASSWORD), lidas automaticamente pelo psycopg2/libpq.

------------------------------------------------------------------------
DECISOES DE DESENHO (raciocinio completo em ../../Anotações/comentarios.md)
------------------------------------------------------------------------

COPY FROM STDIN, nao INSERT linha a linha nem COPY FROM '/caminho/no/servidor'.
O arquivo e transmitido pelo cliente Python direto pro protocolo COPY do
Postgres, em modo binario ('rb'), sem reconstruir cada linha em Python -
isso preserva aspas, virgula interna, acento, zero a esquerda em coluna
TEXT e quebra de linha valida dentro de campo delimitado, exatamente como
estao no CSV. COPY FROM '/caminho.csv' leria o filesystem do SERVIDOR
Postgres, nao o do cliente - errado para esta entrega.

Colunas do COPY sao declaradas explicitamente (COPY "tabela" (col1, col2,
...) FROM STDIN), na ordem do cabecalho do CSV - nunca dependendo
silenciosamente da ordem fisica das colunas na tabela.

Identificadores (nome de tabela/coluna) sempre via psycopg2.sql.Identifier,
nunca por f-string/concatenacao - e o nome da tabela so e usado depois de
validado contra o schema de destino (nunca aceito cru vindo do nome do
arquivo).

Todas as 24 tabelas carregam dentro de uma unica transacao: falha em
qualquer uma faz ROLLBACK de tudo, nao deixa banco parcialmente carregado.
So da COMMIT depois de reconciliar as 24 contagens (CSV vs Postgres) E as
checagens de fidelidade (documentos preservados, nulos esperados,
consistencia numerica) - qualquer divergencia aborta a carga inteira.

Sem PRIMARY KEY/UNIQUE no schema da Q2 (camada bruta, de proposito), rodar
o loader duas vezes duplicaria tudo silenciosamente. Por isso, por padrao
o script aborta se qualquer tabela de destino ja tiver linha - checagem
feita ANTES de qualquer COPY, pras 24 tabelas de uma vez, nao descoberta
tabela por tabela no meio da carga. --truncate-before-load muda esse
comportamento, mas precisa ser pedido explicitamente na linha de comando.

Nenhum "except Exception: pass". Qualquer falha imprime arquivo, tabela,
etapa e a mensagem original do driver, confirma o rollback e termina com
codigo de saida diferente de zero.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

COPY_OPTIONS = "FORMAT CSV, HEADER TRUE, ENCODING 'UTF8', NULL ''"

# Checagens de fidelidade pos-carga: mesmos invariantes ja confirmados na
# Q1 (DuckDB) e na Q2 (validacao manual contra Postgres). Servem de
# segunda linha de defesa - se algum deles não bater, a carga aborta,
# mesmo que a contagem de linhas por tabela tenha fechado certo.
EXPECTED_FIDELITY = {
    "tax_id_leading_zero": 223,       # customers.tax_id que comecam com '0'
    "cpf_length": 11,                 # employees.cpf: todo valor tem 11 chars
    "nfe_key_length": 44,             # fiscal_invoices.nfe_access_key: 44 chars
    "nfe_key_leading_zero": 3440,     # fiscal_invoices.nfe_access_key com '0' na frente
    "fiscal_series_value": "001",     # fiscal_invoices.series: valor unico
    "salesperson_nulls": 24131,       # orders.salesperson_id nulo
    "reorder_point_nulls": 6054,      # stock_levels.reorder_point nulo
}


def discover_csv_files(input_dir: Path) -> list[Path]:
    csv_paths = sorted(input_dir.glob("*.csv"))
    if not csv_paths:
        raise SystemExit(f"nenhum CSV encontrado em {input_dir}")
    return csv_paths


def read_csv_header(csv_path: Path) -> list[str]:
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        header = next(csv.reader(f))
    if not header or any(name == "" for name in header):
        raise ValueError(f"{csv_path.name}: cabecalho ausente ou com coluna sem nome")
    return header


def count_csv_records(csv_path: Path) -> int:
    """Conta linhas logicas via csv.reader (nao wc -l): um campo delimitado
    pode conter quebra de linha valida, que wc -l contaria errado."""
    with csv_path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)  # cabecalho
        return sum(1 for _ in reader)


def validate_target_table(cur, table_name: str, csv_header: list[str]) -> None:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = current_schema() AND table_name = %s
        """,
        (table_name,),
    )
    table_columns = {row[0] for row in cur.fetchall()}
    if not table_columns:
        raise ValueError(f"tabela \"{table_name}\" nao existe no schema de destino")

    csv_columns = set(csv_header)
    missing_in_table = csv_columns - table_columns
    missing_in_csv = table_columns - csv_columns
    if missing_in_table or missing_in_csv:
        raise ValueError(
            f"tabela \"{table_name}\": cabecalho do CSV nao bate com as colunas da tabela "
            f"(no CSV mas nao na tabela: {sorted(missing_in_table) or '-'}; "
            f"na tabela mas nao no CSV: {sorted(missing_in_csv) or '-'})"
        )


def ensure_destinations_empty(cur, table_names: list[str], truncate_before_load: bool) -> None:
    """Checa as 24 tabelas ANTES de qualquer COPY - falha rapido e por
    inteiro, em vez de descobrir tabela suja no meio da carga."""
    non_empty = []
    for table_name in table_names:
        cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
        (count,) = cur.fetchone()
        if count > 0:
            non_empty.append((table_name, count))

    if not non_empty:
        return

    if not truncate_before_load:
        detalhe = ", ".join(f"{t} ({c} linhas)" for t, c in non_empty)
        raise ValueError(
            f"destino nao esta vazio, carga abortada pra nao duplicar dado silenciosamente: {detalhe}. "
            "Rode com --truncate-before-load se isso for intencional."
        )

    for table_name, _ in non_empty:
        cur.execute(sql.SQL("TRUNCATE TABLE {}").format(sql.Identifier(table_name)))
        print(f"  [{table_name}] truncado (--truncate-before-load)")


def copy_csv_to_table(cur, csv_path: Path, table_name: str, header: list[str]) -> int:
    copy_sql = sql.SQL("COPY {table} ({cols}) FROM STDIN WITH ({options})").format(
        table=sql.Identifier(table_name),
        cols=sql.SQL(", ").join(sql.Identifier(col) for col in header),
        options=sql.SQL(COPY_OPTIONS),
    )
    with csv_path.open("rb") as f:
        cur.copy_expert(copy_sql, f)
    return cur.rowcount


def count_database_records(cur, table_name: str) -> int:
    cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table_name)))
    (count,) = cur.fetchone()
    return count


def validate_fidelity(cur) -> list[tuple[str, bool, str]]:
    """Confere invariantes ja conhecidos dos dados (Q1/Q2) dentro do banco
    recem-carregado. Nao e limpeza - e prova de que a ingestao preservou
    exatamente o que ja sabiamos estar no CSV."""
    results = []

    cur.execute("SELECT COUNT(*) FROM customers WHERE tax_id LIKE '0%%'")
    (v,) = cur.fetchone()
    results.append((
        "customers.tax_id com zero a esquerda",
        v == EXPECTED_FIDELITY["tax_id_leading_zero"],
        f"esperado {EXPECTED_FIDELITY['tax_id_leading_zero']}, achou {v}",
    ))

    cur.execute("SELECT MIN(LENGTH(cpf)), MAX(LENGTH(cpf)) FROM employees")
    min_len, max_len = cur.fetchone()
    results.append((
        "employees.cpf sempre com 11 caracteres",
        min_len == max_len == EXPECTED_FIDELITY["cpf_length"],
        f"esperado {EXPECTED_FIDELITY['cpf_length']}, achou min={min_len} max={max_len}",
    ))

    cur.execute("SELECT MIN(LENGTH(nfe_access_key)), MAX(LENGTH(nfe_access_key)) FROM fiscal_invoices")
    min_len, max_len = cur.fetchone()
    results.append((
        "fiscal_invoices.nfe_access_key sempre com 44 caracteres",
        min_len == max_len == EXPECTED_FIDELITY["nfe_key_length"],
        f"esperado {EXPECTED_FIDELITY['nfe_key_length']}, achou min={min_len} max={max_len}",
    ))

    cur.execute("SELECT COUNT(*) FROM fiscal_invoices WHERE nfe_access_key LIKE '0%%'")
    (v,) = cur.fetchone()
    results.append((
        "fiscal_invoices.nfe_access_key com zero a esquerda",
        v == EXPECTED_FIDELITY["nfe_key_leading_zero"],
        f"esperado {EXPECTED_FIDELITY['nfe_key_leading_zero']}, achou {v}",
    ))

    cur.execute("SELECT DISTINCT series FROM fiscal_invoices")
    values = {row[0] for row in cur.fetchall()}
    results.append((
        "fiscal_invoices.series preservada",
        values == {EXPECTED_FIDELITY["fiscal_series_value"]},
        f"esperado {{'{EXPECTED_FIDELITY['fiscal_series_value']}'}}, achou {values}",
    ))

    cur.execute("SELECT COUNT(*) FROM orders WHERE salesperson_id IS NULL")
    (v,) = cur.fetchone()
    results.append((
        "orders.salesperson_id nulos preservados",
        v == EXPECTED_FIDELITY["salesperson_nulls"],
        f"esperado {EXPECTED_FIDELITY['salesperson_nulls']}, achou {v}",
    ))

    cur.execute("SELECT COUNT(*) FROM stock_levels WHERE reorder_point IS NULL")
    (v,) = cur.fetchone()
    results.append((
        "stock_levels.reorder_point nulos preservados",
        v == EXPECTED_FIDELITY["reorder_point_nulls"],
        f"esperado {EXPECTED_FIDELITY['reorder_point_nulls']}, achou {v}",
    ))

    cur.execute(
        "SELECT COUNT(*) FROM orders WHERE ABS(total - (subtotal - discount_amount)) > 0.01"
    )
    (v,) = cur.fetchone()
    results.append((
        "orders: subtotal - discount_amount = total",
        v == 0,
        f"esperado 0 divergencias, achou {v}",
    ))

    return results


def reconcile_counts(cur, csv_counts: dict[str, int]) -> tuple[bool, list[tuple[str, int, int, int, str]]]:
    rows = []
    all_ok = True
    for table_name in sorted(csv_counts):
        csv_count = csv_counts[table_name]
        db_count = count_database_records(cur, table_name)
        diff = db_count - csv_count
        status = "OK" if diff == 0 else "DIVERGENTE"
        if diff != 0:
            all_ok = False
        rows.append((table_name, csv_count, db_count, diff, status))
    return all_ok, rows


def print_reconciliation(rows: list[tuple[str, int, int, int, str]]) -> None:
    print(f"\n{'tabela':28s} {'csv':>10s} {'postgres':>10s} {'diff':>6s}  status")
    total_csv = total_db = 0
    for table_name, csv_count, db_count, diff, status in rows:
        print(f"{table_name:28s} {csv_count:10d} {db_count:10d} {diff:6d}  {status}")
        total_csv += csv_count
        total_db += db_count
    print("-" * 70)
    print(f"{'TOTAL':28s} {total_csv:10d} {total_db:10d} {total_db - total_csv:6d}")


def apply_schema_file(conn, schema_path: Path) -> None:
    """Aplica o schema.sql explicitamente - so acontece se --schema-file
    for passado, nunca escondido dentro do loader por padrao."""
    print(f"Aplicando schema de {schema_path} ...")
    with conn.cursor() as cur, schema_path.open(encoding="utf-8") as f:
        cur.execute(f.read())
    conn.commit()
    print("Schema aplicado.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--input-dir", type=Path, default=Path("lh_nautical_csv"),
        help="diretorio com os 24 CSVs de origem (default: ./lh_nautical_csv)",
    )
    parser.add_argument(
        "--schema-file", type=Path, default=None,
        help="se passado, aplica este schema.sql antes de carregar (etapa explicita, opcional)",
    )
    parser.add_argument(
        "--truncate-before-load", action="store_true",
        help="trunca tabelas nao-vazias antes de carregar, em vez de abortar (precisa ser pedido explicitamente)",
    )
    args = parser.parse_args()

    csv_paths = discover_csv_files(args.input_dir)
    table_names = [p.stem for p in csv_paths]
    print(f"{len(csv_paths)} CSVs encontrados em {args.input_dir}")

    try:
        # psycopg2.connect() sem argumentos le PGHOST/PGPORT/PGDATABASE/
        # PGUSER/PGPASSWORD do ambiente (comportamento padrao do libpq) -
        # nenhuma credencial fica no codigo nem em argumento de CLI.
        conn = psycopg2.connect()
    except psycopg2.OperationalError as exc:
        print(f"ERRO ao conectar no PostgreSQL: {exc}", file=sys.stderr)
        return 1

    try:
        if args.schema_file:
            apply_schema_file(conn, args.schema_file)

        conn.autocommit = False
        with conn.cursor() as cur:
            csv_counts: dict[str, int] = {}
            headers: dict[str, list[str]] = {}

            print("\nValidando tabelas e cabecalhos antes de qualquer carga...")
            for csv_path, table_name in zip(csv_paths, table_names):
                header = read_csv_header(csv_path)
                validate_target_table(cur, table_name, header)
                headers[table_name] = header
                csv_counts[table_name] = count_csv_records(csv_path)
                print(f"  [{table_name}] OK — {csv_counts[table_name]} linhas no CSV")

            print("\nChecando se o destino esta vazio...")
            ensure_destinations_empty(cur, table_names, args.truncate_before_load)

            print("\nCarregando via COPY FROM STDIN...")
            for csv_path, table_name in zip(csv_paths, table_names):
                loaded = copy_csv_to_table(cur, csv_path, table_name, headers[table_name])
                expected = csv_counts[table_name]
                if loaded != expected:
                    raise ValueError(
                        f"tabela \"{table_name}\": COPY carregou {loaded} linhas, "
                        f"esperado {expected} (arquivo {csv_path.name})"
                    )
                print(f"  [{table_name}] {loaded} linhas carregadas")

            print("\nReconciliando contagens (CSV vs. PostgreSQL)...")
            counts_ok, rows = reconcile_counts(cur, csv_counts)
            print_reconciliation(rows)

            print("\nValidando fidelidade (documentos, nulos, consistencia numerica)...")
            fidelity_results = validate_fidelity(cur)
            fidelity_ok = True
            for description, ok, detail in fidelity_results:
                status = "OK" if ok else "FALHOU"
                print(f"  [{status}] {description} — {detail}")
                if not ok:
                    fidelity_ok = False

            if not (counts_ok and fidelity_ok):
                conn.rollback()
                print("\nROLLBACK — reconciliacao ou fidelidade falhou, nenhuma linha ficou gravada.", file=sys.stderr)
                return 1

            conn.commit()
            print("\nCOMMIT — carga concluida, 24 tabelas reconciliadas, fidelidade confirmada.")

            total = sum(c for t, c in csv_counts.items() if t in {"customers", "orders", "order_items", "payments"})
            print(f"\nQ3.2 (customers + orders + order_items + payments): {total}")
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
