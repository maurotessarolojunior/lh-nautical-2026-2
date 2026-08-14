#!/usr/bin/env python3
"""Gera os seis extratos analiticos do dashboard final (Looker Studio) a
partir dos CSVs brutos, reproduzindo em pandas as mesmas regras ja testadas
e aprovadas nas Q1, Q4, Q5, Q6 e Q7 - sem alterar nenhum arquivo em
Submissao/ e sem depender do PostgreSQL estar de pe.

Decisao arquitetural: os extratos ficam em
data/processed/marts/dashboard/ (dados prontos para consumo), separados de
dashboard/ (codigo, documentacao e produto visual). Nao ha camada
stage/intermediate porque data/raw ja preserva a origem, o PostgreSQL das
Q2/Q3 ja materializa uma camada de ingestao tipada para as analises SQL, e
as transformacoes deste script sao pequenas e reproduzem diretamente as
regras ja validadas - so o produto final consumido pelo Looker Studio
precisa ser materializado em CSV.
"""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
PASTA_CSVS = RAIZ_REPOSITORIO / "data" / "raw" / "1-lh_nautical_csv"
PASTA_SAIDA = RAIZ_REPOSITORIO / "data" / "processed" / "marts" / "dashboard"

DIAS_PT = {
    1: "Segunda-feira",
    2: "Terça-feira",
    3: "Quarta-feira",
    4: "Quinta-feira",
    5: "Sexta-feira",
    6: "Sábado",
    7: "Domingo",
}

NOME_PRODUTO_Q6 = "Bússola de Bordo 702"
INICIO_TESTE_Q6 = pd.Timestamp("2026-01-01")
FIM_TESTE_Q6 = pd.Timestamp("2026-03-01")

NOME_PRODUTO_Q7 = "Motor de Popa 1949"


def carregar_dados() -> tuple[pd.DataFrame, ...]:
    orders = pd.read_csv(PASTA_CSVS / "orders.csv", parse_dates=["placed_at"])
    order_items = pd.read_csv(PASTA_CSVS / "order_items.csv")
    product_variants = pd.read_csv(PASTA_CSVS / "product_variants.csv")
    products = pd.read_csv(PASTA_CSVS / "products.csv")
    categories = pd.read_csv(PASTA_CSVS / "categories.csv")
    customers = pd.read_csv(PASTA_CSVS / "customers.csv")
    return orders, order_items, product_variants, products, categories, customers


def construir_itens_com_categoria(
    orders: pd.DataFrame,
    order_items: pd.DataFrame,
    product_variants: pd.DataFrame,
    products: pd.DataFrame,
) -> pd.DataFrame:
    """Mesma cadeia da Q4 (orders -> order_items -> product_variants ->
    products), uma linha por item de pedido com customer_id e category_id -
    granularidade de item, reaproveitada tanto para diversidade quanto para
    quantidade por categoria."""
    pedidos = orders[["id", "customer_id"]].rename(columns={"id": "order_id"})
    variantes = product_variants[["id", "product_id"]].rename(columns={"id": "product_variant_id"})
    produtos = products[["id", "category_id"]].rename(columns={"id": "product_id"})
    itens = order_items[["order_id", "product_variant_id", "quantity"]]

    return itens.merge(pedidos, on="order_id").merge(variantes, on="product_variant_id").merge(
        produtos, on="product_id"
    )


def gerar_pedidos_dashboard(orders: pd.DataFrame) -> pd.DataFrame:
    """Extrato 1: uma linha por pedido, sem join com order_items - juntar
    itens aqui repetiria pedido e inflaria valor_pedido."""
    extrato = orders[["id", "placed_at", "channel", "status", "customer_id", "total"]].copy()
    extrato["data_pedido"] = extrato["placed_at"].dt.date
    extrato["ano_mes"] = extrato["placed_at"].dt.to_period("M").dt.to_timestamp().dt.date
    extrato["ano"] = extrato["placed_at"].dt.year
    extrato = extrato.rename(columns={"id": "order_id", "total": "valor_pedido"})
    return extrato[
        ["order_id", "data_pedido", "ano_mes", "ano", "channel", "status", "customer_id", "valor_pedido"]
    ]


def gerar_clientes_fieis(
    orders: pd.DataFrame, itens_com_categoria: pd.DataFrame, customers: pd.DataFrame
) -> pd.DataFrame:
    """Extrato 2: Top 10 da Q4 - faturamento/frequencia/ticket so a partir
    de orders (nunca pos-join com itens), diversidade de categoria numa
    consulta separada, mesmo filtro (diversidade >= 13) e desempate
    (ticket desc, customer_id asc)."""
    metricas = orders.groupby("customer_id").agg(faturamento_total=("total", "sum"), frequencia=("id", "count"))
    metricas["ticket_medio"] = metricas["faturamento_total"] / metricas["frequencia"]

    diversidade = itens_com_categoria.groupby("customer_id")["category_id"].nunique()
    metricas = metricas.join(diversidade.rename("diversidade_categorias"), how="inner")

    top10 = metricas[metricas["diversidade_categorias"] >= 13].reset_index()
    top10 = top10.sort_values(["ticket_medio", "customer_id"], ascending=[False, True]).head(10)
    top10 = top10.reset_index(drop=True)
    top10["posicao"] = top10.index + 1

    nomes = customers[["id", "legal_name"]].rename(columns={"id": "customer_id", "legal_name": "cliente"})
    top10 = top10.merge(nomes, on="customer_id")
    top10["faturamento_total"] = top10["faturamento_total"].round(2)
    top10["ticket_medio"] = top10["ticket_medio"].round(2)

    return top10[
        ["customer_id", "cliente", "faturamento_total", "frequencia", "ticket_medio", "diversidade_categorias", "posicao"]
    ]


def gerar_categorias_clientes_fieis(
    itens_com_categoria: pd.DataFrame, clientes_fieis: pd.DataFrame, categories: pd.DataFrame
) -> pd.DataFrame:
    """Extrato 3: soma de quantity (nunca contagem de linha) por categoria,
    restrita aos clientes do Top 10 - a CTE top_10 filtra antes do JOIN
    final, exatamente como no 4.1.sql."""
    itens_top10 = itens_com_categoria[itens_com_categoria["customer_id"].isin(clientes_fieis["customer_id"])]
    agregado = itens_top10.groupby("category_id")["quantity"].sum().rename("quantidade_itens").reset_index()

    nomes = categories[["id", "name"]].rename(columns={"id": "category_id", "name": "categoria"})
    agregado = agregado.merge(nomes, on="category_id")
    agregado = agregado.sort_values(["quantidade_itens", "category_id"], ascending=[False, True])
    agregado = agregado.reset_index(drop=True)
    agregado["posicao"] = agregado.index + 1

    return agregado[["category_id", "categoria", "quantidade_itens", "posicao"]]


def gerar_vendas_dia_semana(orders: pd.DataFrame) -> pd.DataFrame:
    """Extrato 4: mesmo calendario completo da Q5 (MIN/MAX de placed_at,
    sem lacuna), canal pos somado por dia antes do join, COALESCE(0) antes
    da media - dias sem venda entram no calculo, nao desaparecem."""
    data_inicial = orders["placed_at"].dt.normalize().min()
    data_final = orders["placed_at"].dt.normalize().max()
    calendario = pd.DataFrame({"data": pd.date_range(data_inicial, data_final, freq="D")})
    calendario["numero_dia_semana"] = calendario["data"].dt.dayofweek + 1  # ISODOW: segunda=1..domingo=7
    calendario["dia_semana"] = calendario["numero_dia_semana"].map(DIAS_PT)

    vendas_pos = orders[orders["channel"] == "pos"].copy()
    vendas_pos["data"] = vendas_pos["placed_at"].dt.normalize()
    vendas_diarias = vendas_pos.groupby("data")["total"].sum().rename("venda_diaria")

    calendario = calendario.merge(vendas_diarias, left_on="data", right_index=True, how="left")
    calendario["venda_diaria"] = calendario["venda_diaria"].fillna(0)

    resumo = (
        calendario.groupby(["numero_dia_semana", "dia_semana"])
        .agg(
            dias_calendario=("venda_diaria", "count"),
            dias_sem_venda=("venda_diaria", lambda s: int((s == 0).sum())),
            valor_total=("venda_diaria", "sum"),
            media_vendas=("venda_diaria", "mean"),
        )
        .reset_index()
        .sort_values("numero_dia_semana")
        .reset_index(drop=True)
    )
    resumo = resumo.rename(columns={"numero_dia_semana": "ordem_dia"})
    resumo["media_vendas"] = resumo["media_vendas"].round(2)
    resumo["valor_total"] = resumo["valor_total"].round(2)

    pior_dia = resumo.loc[resumo["media_vendas"].idxmin(), "dia_semana"]
    resumo["destaque"] = resumo["dia_semana"].apply(lambda d: "Pior média" if d == pior_dia else "Demais dias")

    return resumo[["ordem_dia", "dia_semana", "media_vendas", "dias_calendario", "dias_sem_venda", "valor_total", "destaque"]]


def gerar_previsao_demanda(
    products: pd.DataFrame, product_variants: pd.DataFrame, order_items: pd.DataFrame, orders: pd.DataFrame
) -> pd.DataFrame:
    """Extrato 5: mesma cadeia e mesmo baseline walk-forward da Q6 (dois
    product_id do nome duplicado, meses sem venda preenchidos com zero,
    previsao so com meses estritamente anteriores)."""
    produtos_alvo = products.loc[products["name"] == NOME_PRODUTO_Q6, ["id"]].rename(columns={"id": "product_id"})
    ids_produtos = sorted(produtos_alvo["product_id"].tolist())
    assert ids_produtos == [74, 240], f"product_id do produto Q6 divergente: {ids_produtos}"

    variantes = product_variants[["id", "product_id"]].rename(columns={"id": "product_variant_id"})
    ids_variantes = sorted(variantes.loc[variantes["product_id"].isin(produtos_alvo["product_id"]), "product_variant_id"])
    assert ids_variantes == [147, 148, 486], f"product_variant_id do produto Q6 divergente: {ids_variantes}"

    itens = order_items[["order_id", "product_variant_id", "quantity"]]
    pedidos = orders[["id", "placed_at"]].rename(columns={"id": "order_id"})

    unificado = produtos_alvo.merge(variantes, on="product_id").merge(itens, on="product_variant_id").merge(
        pedidos, on="order_id"
    )
    unificado["month"] = unificado["placed_at"].dt.to_period("M").dt.to_timestamp()
    unificado = unificado[unificado["month"] <= FIM_TESTE_Q6]

    vendas_mensais = unificado.groupby("month", as_index=False)["quantity"].sum()
    todos_os_meses = pd.date_range(vendas_mensais["month"].min(), FIM_TESTE_Q6, freq="MS")
    vendas_mensais = (
        vendas_mensais.set_index("month").reindex(todos_os_meses, fill_value=0).rename_axis("month").reset_index()
    )

    teste = vendas_mensais.loc[vendas_mensais["month"].between(INICIO_TESTE_Q6, FIM_TESTE_Q6)].reset_index(drop=True)
    assert len(teste) == 3, f"esperado 3 meses de teste, encontrado {len(teste)}"
    meses_esperados = [pd.Timestamp("2026-01-01"), pd.Timestamp("2026-02-01"), pd.Timestamp("2026-03-01")]
    assert list(teste["month"]) == meses_esperados, f"meses de teste divergentes: {list(teste['month'])}"

    previsoes = []
    for mes_previsto in teste["month"]:
        tres_meses_anteriores = vendas_mensais.loc[vendas_mensais["month"] < mes_previsto].tail(3)
        previsoes.append(tres_meses_anteriores["quantity"].mean())
    teste["previsto"] = previsoes
    assert teste["previsto"].notnull().all(), "previsao nula encontrada em previsao_demanda"
    teste["erro_absoluto"] = (teste["quantity"] - teste["previsto"]).abs()

    extrato = teste.rename(columns={"month": "mes", "quantity": "real"})
    extrato["mes"] = extrato["mes"].dt.date
    return extrato[["mes", "real", "previsto", "erro_absoluto"]]


def gerar_recomendacoes(
    orders: pd.DataFrame, order_items: pd.DataFrame, product_variants: pd.DataFrame, products: pd.DataFrame
) -> pd.DataFrame:
    """Extrato 6: mesma matriz binaria e mesmo cosseno (sklearn) da Q7 -
    exclusao do alvo pelo product_id, nunca por similaridade == 1."""
    pedidos = orders[["id", "customer_id"]].rename(columns={"id": "order_id"})
    itens = order_items[["order_id", "product_variant_id"]]
    variantes = product_variants[["id", "product_id"]].rename(columns={"id": "product_variant_id"})

    unificado = itens.merge(pedidos, on="order_id").merge(variantes, on="product_variant_id")
    interacoes = unificado[["customer_id", "product_id"]].drop_duplicates()
    matriz = pd.crosstab(interacoes["customer_id"], interacoes["product_id"])
    matriz = (matriz > 0).astype(int)

    alvo = products[products["name"] == NOME_PRODUTO_Q7]
    assert len(alvo) == 1, f"esperado 1 produto para '{NOME_PRODUTO_Q7}', encontrado {len(alvo)}"
    produto_alvo_id = int(alvo.iloc[0]["id"])
    assert produto_alvo_id == 180, f"product_id do produto Q7 divergente: {produto_alvo_id}"
    assert produto_alvo_id in matriz.columns, "product_id alvo ausente na matriz binaria"

    similaridade = cosine_similarity(matriz.T)
    similaridade = pd.DataFrame(similaridade, index=matriz.columns, columns=matriz.columns)

    ranking = (
        similaridade[produto_alvo_id]
        .drop(index=produto_alvo_id)
        .rename("similaridade")
        .reset_index()
        .rename(columns={"index": "product_id"})
    )
    ranking = ranking.sort_values(["similaridade", "product_id"], ascending=[False, True]).head(5)
    ranking = ranking.reset_index(drop=True)
    ranking["posicao"] = ranking.index + 1

    nomes = products[["id", "name"]].rename(columns={"id": "product_id", "name": "produto"})
    ranking = ranking.merge(nomes, on="product_id")

    return ranking[["posicao", "product_id", "produto", "similaridade"]]


def validar(
    pedidos: pd.DataFrame,
    clientes: pd.DataFrame,
    categorias: pd.DataFrame,
    dia_semana: pd.DataFrame,
    previsao: pd.DataFrame,
    recomendacoes: pd.DataFrame,
) -> None:
    # Ausencia de nulo em qualquer coluna exportada, para todos os extratos.
    extratos = {
        "pedidos_dashboard": pedidos,
        "clientes_fieis": clientes,
        "categorias_clientes_fieis": categorias,
        "vendas_dia_semana": dia_semana,
        "previsao_demanda": previsao,
        "recomendacoes": recomendacoes,
    }
    for nome, extrato in extratos.items():
        assert extrato.notna().all().all(), f"{nome}: nulo encontrado em coluna exportada"

    assert len(pedidos) == 48998, f"pedidos_dashboard: {len(pedidos)} linhas, esperado 48998"
    assert pedidos["order_id"].is_unique, "order_id duplicado em pedidos_dashboard"
    assert pedidos["order_id"].nunique() == 48998, "order_id com duplicidade"
    assert pedidos["customer_id"].nunique() == 2000, "customer_id distintos != 2000"
    assert str(pedidos["data_pedido"].min()) == "2020-01-01", "data minima divergente"
    assert str(pedidos["data_pedido"].max()) == "2026-12-31", "data maxima divergente"
    assert math.isclose(
        pedidos["valor_pedido"].sum(), 1_406_487_201.80, rel_tol=0.0, abs_tol=0.01
    ), "soma de valor_pedido divergente"
    assert math.isclose(
        pedidos["valor_pedido"].mean(), 28704.99, rel_tol=0.0, abs_tol=0.01
    ), "media de valor_pedido divergente"

    assert len(clientes) == 10, "clientes_fieis: esperado 10 linhas"
    assert clientes["customer_id"].is_unique, "customer_id duplicado em clientes_fieis"
    assert list(clientes["posicao"]) == list(range(1, 11)), "posicao nao sequencial em clientes_fieis"
    assert int(clientes.iloc[0]["customer_id"]) == 22, "1o colocado divergente"
    assert math.isclose(
        clientes.iloc[0]["ticket_medio"], 41839.94, rel_tol=0.0, abs_tol=0.01
    ), "ticket do 1o colocado divergente"
    assert (clientes["diversidade_categorias"] == 14).all(), "diversidade fora do esperado"

    assert len(categorias) == 14, f"categorias_clientes_fieis: {len(categorias)} linhas, esperado 14"
    assert categorias["category_id"].is_unique, "category_id duplicado em categorias_clientes_fieis"
    assert list(categorias["posicao"]) == list(range(1, 15)), "posicao nao sequencial em categorias_clientes_fieis"
    assert categorias.iloc[0]["categoria"] == "Hélices", "categoria lider divergente"
    assert int(categorias.iloc[0]["quantidade_itens"]) == 492, "quantidade da categoria lider divergente"

    assert len(dia_semana) == 7, "vendas_dia_semana: esperado 7 linhas"
    assert dia_semana["ordem_dia"].is_unique, "ordem_dia duplicado em vendas_dia_semana"
    assert int(dia_semana["dias_calendario"].sum()) == 2557, "dias de calendario divergente"
    assert int(dia_semana["dias_sem_venda"].sum()) == 78, "dias sem venda divergente"
    assert math.isclose(
        dia_semana["valor_total"].sum(), 419_273_315.30, rel_tol=0.0, abs_tol=0.01
    ), "valor_total divergente"
    pior = dia_semana.loc[dia_semana["media_vendas"].idxmin()]
    assert pior["dia_semana"] == "Quinta-feira", "pior dia divergente"
    assert math.isclose(pior["media_vendas"], 157154.32, rel_tol=0.0, abs_tol=0.01), "media do pior dia divergente"

    assert len(previsao) == 3, "previsao_demanda: esperado 3 linhas"
    assert previsao["mes"].is_unique, "mes duplicado em previsao_demanda"
    soma_prevista = previsao["previsto"].sum()
    assert math.isclose(soma_prevista, 148.6667, rel_tol=0.0, abs_tol=0.01), "soma prevista divergente"
    assert round(soma_prevista) == 149, "Q6.2 divergente"
    mae = previsao["erro_absoluto"].mean()
    assert math.isclose(mae, 19.4444, rel_tol=0.0, abs_tol=0.01), "MAE divergente"

    assert len(recomendacoes) == 5, "recomendacoes: esperado 5 linhas"
    assert recomendacoes["product_id"].is_unique, "product_id duplicado em recomendacoes"
    assert list(recomendacoes["posicao"]) == list(range(1, 6)), "posicao nao sequencial em recomendacoes"
    assert 180 not in recomendacoes["product_id"].values, "produto-alvo presente no ranking"
    assert recomendacoes.iloc[0]["produto"] == "Motor de Popa 5331", "1o colocado divergente"
    assert math.isclose(
        recomendacoes.iloc[0]["similaridade"], 0.256553, rel_tol=0.0, abs_tol=0.0001
    ), "similaridade do 1o divergente"


def main() -> None:
    orders, order_items, product_variants, products, categories, customers = carregar_dados()
    itens_com_categoria = construir_itens_com_categoria(orders, order_items, product_variants, products)

    pedidos = gerar_pedidos_dashboard(orders)
    clientes = gerar_clientes_fieis(orders, itens_com_categoria, customers)
    categorias = gerar_categorias_clientes_fieis(itens_com_categoria, clientes, categories)
    dia_semana = gerar_vendas_dia_semana(orders)
    previsao = gerar_previsao_demanda(products, product_variants, order_items, orders)
    recomendacoes = gerar_recomendacoes(orders, order_items, product_variants, products)

    validar(pedidos, clientes, categorias, dia_semana, previsao, recomendacoes)

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)
    pedidos.to_csv(PASTA_SAIDA / "pedidos_dashboard.csv", index=False)
    clientes.to_csv(PASTA_SAIDA / "clientes_fieis.csv", index=False)
    categorias.to_csv(PASTA_SAIDA / "categorias_clientes_fieis.csv", index=False)
    dia_semana.to_csv(PASTA_SAIDA / "vendas_dia_semana.csv", index=False)
    previsao.to_csv(PASTA_SAIDA / "previsao_demanda.csv", index=False)
    recomendacoes.to_csv(PASTA_SAIDA / "recomendacoes.csv", index=False)

    print("6 extratos gerados")
    print(f"{len(pedidos):,}".replace(",", ".") + " pedidos preservados")
    print("Q4, Q5, Q6 e Q7 conferidos")
    print("dados prontos para o Looker Studio")


if __name__ == "__main__":
    main()
