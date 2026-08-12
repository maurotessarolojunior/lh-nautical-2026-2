#!/usr/bin/env python3
"""Questao 6 - Previsao de demanda: baseline de media movel de 3 meses,
avaliado mes a mes (walk-forward), para o produto "Bussola de Bordo 702".

O nome aparece em dois registros distintos de products.csv (product_id 74 e
240, marcas/categorias diferentes) - os dois entram na analise, com as tres
variantes relacionadas, porque o enunciado identifica o produto pelo nome,
nao por um product_id especifico.

Treino: pedidos ate 31/12/2025 (o mes inteiro de dezembro, nao so o dia 1 -
"2025-12-01" e apenas o rotulo que representa o mes inteiro na serie mensal).
Teste: janeiro a marco de 2026. Cada previsao usa so meses com data
estritamente anterior a ela (walk-forward): fevereiro pode usar janeiro real,
e marco pode usar janeiro e fevereiro reais, porque a avaliacao simula uma
atualizacao mensal apos o fechamento do mes anterior. O proprio mes previsto
e qualquer mes posterior a marco/2026 nunca entram numa previsao.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
PASTA_CSVS = RAIZ_REPOSITORIO / "data" / "raw" / "1-lh_nautical_csv"

NOME_PRODUTO = "Bússola de Bordo 702"
FIM_TREINO = pd.Timestamp("2025-12-01")
INICIO_TESTE = pd.Timestamp("2026-01-01")
FIM_TESTE = pd.Timestamp("2026-03-01")


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    products = pd.read_csv(PASTA_CSVS / "products.csv")
    product_variants = pd.read_csv(PASTA_CSVS / "product_variants.csv")
    order_items = pd.read_csv(PASTA_CSVS / "order_items.csv")
    orders = pd.read_csv(PASTA_CSVS / "orders.csv", parse_dates=["placed_at"])
    return products, product_variants, order_items, orders


def construir_dataset_unificado(
    products: pd.DataFrame,
    product_variants: pd.DataFrame,
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
) -> pd.DataFrame:
    # Filtro pelo nome exato (com acento) - mantem os dois product_id
    # encontrados. Nao usar .iloc[0] nem fixar product_id manualmente: isso
    # descartaria parte das vendas do produto pedido.
    produtos_alvo = products.loc[products["name"] == NOME_PRODUTO, ["id", "name"]].rename(
        columns={"id": "product_id"}
    )
    print(f"product_id encontrados para '{NOME_PRODUTO}': {sorted(produtos_alvo['product_id'])}")

    variantes = product_variants.loc[:, ["id", "product_id"]].rename(columns={"id": "product_variant_id"})
    itens = order_items.loc[:, ["order_id", "product_variant_id", "quantity"]]
    pedidos = orders.loc[:, ["id", "placed_at"]].rename(columns={"id": "order_id"})

    unificado = pd.merge(produtos_alvo, variantes, on="product_id", how="inner")
    print(f"product_variant_id relacionados: {sorted(unificado['product_variant_id'])}")

    unificado = pd.merge(unificado, itens, on="product_variant_id", how="inner")
    unificado = pd.merge(unificado, pedidos, on="order_id", how="inner")

    print(
        f"dataset unificado: {unificado.shape[0]} linhas, "
        f"{unificado['order_id'].nunique()} pedidos distintos"
    )
    return unificado


def agregar_serie_mensal(unificado: pd.DataFrame) -> pd.DataFrame:
    unificado = unificado.copy()
    unificado["month"] = unificado["placed_at"].dt.to_period("M").dt.to_timestamp()

    # Nada depois de marco/2026 entra na analise - a base tem pedidos ate
    # dezembro/2026, mas o teste termina no primeiro trimestre.
    unificado = unificado[unificado["month"] <= FIM_TESTE]

    vendas_mensais = unificado.groupby("month", as_index=False)["quantity"].sum()

    # Completa meses sem venda com zero - senao tail(3)/rolling(3) pularia
    # meses ausentes e a janela deixaria de representar 3 meses consecutivos
    # do calendario (mesmo principio da dimensao de calendario da Q5).
    todos_os_meses = pd.date_range(vendas_mensais["month"].min(), FIM_TESTE, freq="MS")
    vendas_mensais = (
        vendas_mensais.set_index("month")
        .reindex(todos_os_meses, fill_value=0)
        .rename_axis("month")
        .reset_index()
    )
    return vendas_mensais


def prever_walk_forward(vendas_mensais: pd.DataFrame, meses_teste: pd.Series) -> list[float]:
    previsoes = []
    for mes_previsto in meses_teste:
        tres_meses_anteriores = vendas_mensais.loc[vendas_mensais["month"] < mes_previsto].tail(3)
        previsoes.append(tres_meses_anteriores["quantity"].mean())
    return previsoes


def main() -> None:
    products, product_variants, order_items, orders = carregar_dados()
    unificado = construir_dataset_unificado(products, product_variants, order_items, orders)
    vendas_mensais = agregar_serie_mensal(unificado)

    treino = vendas_mensais.loc[vendas_mensais["month"] <= FIM_TREINO]
    print(
        f"treino: {treino['month'].min().date()} a {treino['month'].max().date()} "
        f"({len(treino)} meses)"
    )

    teste = vendas_mensais.loc[vendas_mensais["month"].between(INICIO_TESTE, FIM_TESTE)].reset_index(
        drop=True
    )
    assert len(teste) == 3, f"esperado 3 meses de teste, encontrado {len(teste)}"

    teste["forecast"] = prever_walk_forward(vendas_mensais, teste["month"])
    teste["absolute_error"] = (teste["quantity"] - teste["forecast"]).abs()

    mae = teste["absolute_error"].mean()
    total_previsto = teste["forecast"].sum()
    total_previsto_arredondado = round(total_previsto)

    print("\nprevisao walk-forward (mes | real | previsao | erro absoluto):")
    for _, linha in teste.iterrows():
        print(
            f"  {linha['month'].date()} | {linha['quantity']:.0f} | "
            f"{linha['forecast']:.4f} | {linha['absolute_error']:.4f}"
        )

    print(f"\nMAE: {mae:.4f}")
    print(f"soma das previsoes (sem arredondar): {total_previsto:.4f}")
    print(f"Q6.2 (soma arredondada): {total_previsto_arredondado}")


if __name__ == "__main__":
    main()
