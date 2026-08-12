#!/usr/bin/env python3
"""Questao 7 - Sistema de recomendacao: matriz binaria cliente x produto e
similaridade de cosseno (sklearn) para recomendar o produto mais comprado
pelos mesmos clientes que compraram "Motor de Popa 1949".

A matriz ignora quantidade e numero de pedidos - cada celula e 1 se o
cliente comprou o produto ao menos uma vez, 0 caso contrario. Todos os
pedidos entram (paid, confirmed, cancelled, draft): o enunciado nao define
filtro de status, e inventar um mudaria o ranking sem base no que foi pedido.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
PASTA_CSVS = RAIZ_REPOSITORIO / "data" / "raw" / "1-lh_nautical_csv"

NOME_PRODUTO_ALVO = "Motor de Popa 1949"
TOP_N = 5


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    orders = pd.read_csv(PASTA_CSVS / "orders.csv").rename(columns={"id": "order_id"})[
        ["order_id", "customer_id"]
    ]
    order_items = pd.read_csv(PASTA_CSVS / "order_items.csv")[["order_id", "product_variant_id"]]
    product_variants = pd.read_csv(PASTA_CSVS / "product_variants.csv").rename(
        columns={"id": "product_variant_id"}
    )[["product_variant_id", "product_id"]]
    products = pd.read_csv(PASTA_CSVS / "products.csv").rename(columns={"id": "product_id"})[
        ["product_id", "name"]
    ]
    return orders, order_items, product_variants, products


def construir_matriz_binaria(
    orders: pd.DataFrame, order_items: pd.DataFrame, product_variants: pd.DataFrame
) -> pd.DataFrame:
    unificado = order_items.merge(orders, on="order_id").merge(product_variants, on="product_variant_id")
    print(f"linhas apos os merges: {len(unificado)}")
    assert unificado["customer_id"].isnull().sum() == 0, "customer_id nulo apos merge"
    assert unificado["product_id"].isnull().sum() == 0, "product_id nulo apos merge"

    # Um par unico cliente-produto por linha: se o cliente comprou 1 ou N
    # vezes, o valor continua sendo 1 - drop_duplicates torna isso explicito.
    interacoes = unificado[["customer_id", "product_id"]].drop_duplicates()
    print(f"pares unicos cliente-produto: {len(interacoes)}")

    matriz = pd.crosstab(interacoes["customer_id"], interacoes["product_id"])
    matriz = (matriz > 0).astype(int)
    print(f"formato da matriz: {matriz.shape}")
    print(f"valores unicos na matriz: {sorted(int(v) for v in pd.unique(matriz.values.ravel()))}")
    return matriz


def calcular_similaridade(matriz: pd.DataFrame) -> pd.DataFrame:
    # .T: sem a transposicao o sklearn compararia clientes, nao produtos.
    similaridade = cosine_similarity(matriz.T)
    return pd.DataFrame(similaridade, index=matriz.columns, columns=matriz.columns)


def montar_ranking(similaridade: pd.DataFrame, produto_alvo_id: int, produtos: pd.DataFrame) -> pd.DataFrame:
    # Exclusao pelo product_id, nunca comparando a similaridade a 1 - o
    # cosseno do produto consigo mesmo pode nao ser exatamente 1.0 por
    # ponto flutuante.
    ranking = (
        similaridade[produto_alvo_id]
        .drop(index=produto_alvo_id)
        .rename("similarity")
        .reset_index()
        .rename(columns={"index": "product_id"})
    )
    ranking = ranking.sort_values(["similarity", "product_id"], ascending=[False, True]).head(TOP_N)
    return ranking.merge(produtos, on="product_id")[["product_id", "name", "similarity"]]


def main() -> None:
    orders, order_items, product_variants, products = carregar_dados()

    alvo = products[products["name"] == NOME_PRODUTO_ALVO]
    if len(alvo) != 1:
        raise SystemExit(f"esperado 1 produto para '{NOME_PRODUTO_ALVO}', encontrado {len(alvo)}")
    produto_alvo_id = int(alvo.iloc[0]["product_id"])
    print(f"product_id alvo: {produto_alvo_id}")

    matriz = construir_matriz_binaria(orders, order_items, product_variants)
    print(f"compradores do alvo: {int(matriz[produto_alvo_id].sum())}")

    similaridade = calcular_similaridade(matriz)
    print(f"formato da matriz de similaridade: {similaridade.shape}")
    print(
        "similaridade do alvo consigo mesmo (antes da exclusao): "
        f"{similaridade.loc[produto_alvo_id, produto_alvo_id]:.10f}"
    )

    ranking = montar_ranking(similaridade, produto_alvo_id, products)

    print(f"\ntop {TOP_N} produtos mais similares a '{NOME_PRODUTO_ALVO}':")
    for _, linha in ranking.iterrows():
        print(f"  {linha['product_id']:>4} | {linha['name']:<25} | {linha['similarity']:.6f}")

    print(f"\nQ7.2 (produto mais similar): {ranking.iloc[0]['name']}")


if __name__ == "__main__":
    main()
