# Dashboard — LH Nautical 2026.2

Material complementar obrigatório do desafio: um painel para a diretoria fictícia da LH Nautical, sintetizando os resultados já validados nas Q1 e Q4–Q7. **Status: concluído** — painel construído no Looker Studio e PDF final exportado. Esta pasta contém o código que prepara os dados, a documentação e o produto visual. Os dados em si (os 6 CSVs consumidos pelo painel) não ficam aqui — ver "Onde estão os dados" abaixo.

## Onde estão os dados

```text
data/raw/1-lh_nautical_csv/                                    → CSVs originais do desafio (24 arquivos)
data/processed/marts/dashboard/                                → 6 extratos analíticos, consumidos pelo painel
Submissão/Q8-Dashboard/gerar_dados.py                          → script que gera os extratos a partir dos CSVs brutos
Submissão/Q8-Dashboard/README.md                               → este arquivo
Submissão/Q8-Dashboard/LH_Nautical_2026_2_Dashboard.pdf        → PDF final do painel, exportado do Looker Studio
Submissão/Q8-Dashboard/LH_Nautical_2026_2_Apresentacao.pdf     → apresentação, versão de 8 slides
Submissão/Q8-Dashboard/LH_Nautical_2026_2_Apresentacao_v2.pdf  → apresentação, versão de 10 slides
```

Essa separação é uma decisão consciente de organização, não uma arquitetura adicionada para parecer mais sofisticada: `data/processed/marts/dashboard/` guarda dados prontos para consumo; `Submissão/Q8-Dashboard/` guarda código, documentação e o produto visual — inclusive depois do painel pronto, o PDF fica em `Submissão/Q8-Dashboard/`, não junto dos CSVs. Não existe camada `stage`/`intermediate` porque não há necessidade real dela neste desafio — ver "Linhagem dos dados" abaixo.

## Painel no Looker Studio

PDF final: [`LH_Nautical_2026_2_Dashboard.pdf`](LH_Nautical_2026_2_Dashboard.pdf) (3 páginas, formato 16:9).

1. **Visão geral de vendas** — cartões de valor total registrado, pedidos, clientes e ticket médio; evolução mensal do valor registrado; valor por canal; pedidos por status.
2. **Clientes e operação física** — Top 10 clientes fiéis por ticket médio, categorias mais consumidas por esse grupo, e média de vendas físicas por dia da semana (dias sem venda incluídos no cálculo, Quinta-feira destacada como pior média).
3. **Previsão e recomendação** — previsão trimestral e MAE da Q6 (real vs. previsto por mês), e o ranking dos 5 produtos mais similares ao item de referência da Q7.

O painel consome diretamente os seis CSVs materializados em `data/processed/marts/dashboard/` — nenhum visual foi construído a partir de uma consulta refeita dentro do Looker Studio.

### Por que cada CSV é uma fonte de dados independente no Looker Studio

Os seis marts têm granularidades e schemas diferentes entre si (um pedido, um cliente do Top 10, uma categoria, um dia da semana, um mês, um produto recomendado — ver "Dicionário dos extratos" abaixo). Por isso cada CSV foi importado como um conjunto de dados próprio no Looker Studio, não unificado num só. A opção "Adicionar arquivo" dentro de um conjunto de dados já existente serve para acrescentar mais arquivos **compatíveis com o mesmo schema e o mesmo grão** (por exemplo, um novo lote de `pedidos_dashboard.csv` de um mês seguinte) — não para juntar marts diferentes num único conjunto, o que misturaria granularidades incompatíveis num mesmo conjunto de campos.

## Linhagem dos dados (de onde cada número vem)

O desafio tem, hoje, **três caminhos reproduzíveis** a partir de `data/raw`, todos partindo da mesma origem, mas sem depender fisicamente um do outro:

```text
data/raw/1-lh_nautical_csv/
├── Submissão/Q2 + Q3 → PostgreSQL tipado → SQL das Q1, Q4 e Q5
├── Submissão/Q6 + Q7 → pandas/scikit-learn → respostas e notebook
└── Submissão/Q8-Dashboard/gerar_dados.py → data/processed/marts/dashboard/*.csv → Looker Studio
```

`Submissão/Q8-Dashboard/gerar_dados.py` **lê os CSVs brutos diretamente** — não lê do PostgreSQL nem chama os scripts de `Submissão/`. Ele reproduz em pandas as mesmas regras de negócio já testadas e aprovadas na Q1 e nas Q4–Q7 (mesmas chaves de junção, mesmos filtros, mesma granularidade, mesmo desempate, mesmo baseline walk-forward da Q6, mesma matriz binária e cosseno da Q7), para que o dashboard não dependa do banco estar de pé nem da execução prévia dos scripts das submissões. Por isso o script valida cada extrato contra os valores já aprovados antes de gravar qualquer CSV — se algo divergir, ele falha com uma mensagem clara em vez de gravar um número errado silenciosamente.

Não há `stage`/`intermediate` porque, neste desafio, essas camadas não teriam função real: `data/raw` já preserva a origem sem tratamento; a Q3 já materializa uma camada de ingestão tipada e fiel à origem no PostgreSQL; e as transformações necessárias ao dashboard são pequenas o bastante para viver inteiras, de forma legível, dentro de `gerar_dados.py`. Uma evolução futura com uma ferramenta como dbt Core poderia unificar os três caminhos sobre o PostgreSQL — isso é um estudo pós-entrega, fora do escopo desta implementação.

## Como regenerar os extratos

A partir da raiz do repositório:

```bash
source .venv/bin/activate
python Submissão/Q8-Dashboard/gerar_dados.py
```

O script lê `data/raw/1-lh_nautical_csv/`, recalcula os seis extratos, valida cada um contra os resultados já aprovados e grava (sobrescrevendo) os arquivos em `data/processed/marts/dashboard/`. Execução determinística: rodar mais de uma vez produz arquivos byte a byte idênticos, sem duplicar linhas.

## Dicionário dos extratos

### `pedidos_dashboard.csv` — uma linha por pedido

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `order_id` | inteiro | `orders.id` |
| `data_pedido` | data (ISO) | data de `orders.placed_at` |
| `ano_mes` | data (ISO, dia 1) | primeiro dia do mês de `placed_at` |
| `ano` | inteiro | ano de `placed_at` |
| `channel` | texto | `orders.channel` |
| `status` | texto | `orders.status` |
| `customer_id` | inteiro | `orders.customer_id` |
| `valor_pedido` | decimal | `orders.total` |

Não há junção com `order_items` — evita repetir pedido e inflar `valor_pedido`. Todos os status de pedido estão incluídos (premissa do desafio, sem filtro inventado); por isso o painel deve rotular os totais como "registrado", não como receita reconhecida.

### `clientes_fieis.csv` — uma linha por cliente do Top 10 (Q4)

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `customer_id` | inteiro | `orders.customer_id` |
| `cliente` | texto | `customers.legal_name` (nome fictício) |
| `faturamento_total` | decimal | soma de `orders.total` do cliente |
| `frequencia` | inteiro | quantidade de pedidos do cliente |
| `ticket_medio` | decimal | `faturamento_total / frequencia` |
| `diversidade_categorias` | inteiro | categorias distintas compradas (via `order_items → product_variants → products`) |
| `posicao` | inteiro | 1 a 10, por `ticket_medio` desc., desempate por `customer_id` asc. |

Filtro: `diversidade_categorias >= 13`. Faturamento/frequência vêm só de `orders`, nunca depois de um `JOIN` com itens.

### `categorias_clientes_fieis.csv` — uma linha por categoria comprada pelo Top 10

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `category_id` | inteiro | `categories.id` |
| `categoria` | texto | `categories.name` |
| `quantidade_itens` | inteiro | soma de `order_items.quantity` (nunca contagem de linha), restrita aos clientes do Top 10 |
| `posicao` | inteiro | 1 a 14, por `quantidade_itens` desc. |

### `vendas_dia_semana.csv` — uma linha por dia da semana (7)

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `ordem_dia` | inteiro | segunda = 1 ... domingo = 7 |
| `dia_semana` | texto | rótulo em português |
| `media_vendas` | decimal | média de `orders.total` (canal `pos`) por dia, incluindo dias sem venda como zero |
| `dias_calendario` | inteiro | quantidade de ocorrências do dia da semana no período |
| `dias_sem_venda` | inteiro | dias com venda física igual a zero |
| `valor_total` | decimal | soma das vendas físicas do dia da semana |
| `destaque` | texto | `"Pior média"` para o dia de menor `media_vendas`, `"Demais dias"` para os outros — calculado pelo código, nunca escrito manualmente |

Calendário completo entre o mínimo e o máximo de `placed_at` (sem lacuna) construído antes da média — dias sem venda física entram como zero, não desaparecem do cálculo.

### `previsao_demanda.csv` — uma linha por mês do 1º trimestre/2026 (3)

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `mes` | data (ISO, dia 1) | mês previsto |
| `real` | inteiro | unidades vendidas do produto "Bússola de Bordo 702" no mês |
| `previsto` | decimal | média móvel walk-forward dos 3 meses anteriores (sem arredondar) |
| `erro_absoluto` | decimal | `\|real - previsto\|` |

Mesmo baseline da Q6.1: previsão de cada mês usa só meses com data estritamente anterior a ele.

### `recomendacoes.csv` — uma linha por produto do Top 5 (Q7)

| Coluna | Tipo | Origem/cálculo |
|---|---|---|
| `posicao` | inteiro | 1 a 5, por `similaridade` desc. |
| `product_id` | inteiro | `products.id` |
| `produto` | texto | `products.name` |
| `similaridade` | decimal | cosseno entre o vetor de compradores do produto e o do "Motor de Popa 1949" |

O `product_id = 180` (produto de referência) nunca aparece no ranking — excluído pelo próprio identificador, não por comparação de similaridade.

## O que não está nos extratos

Nenhuma coluna de CPF/CNPJ, e-mail, telefone, endereço, credencial ou caminho absoluto de máquina. `clientes_fieis.csv` traz `customer_id` junto do nome fictício para evitar ambiguidade entre clientes.

## Validações executadas pelo script

Antes de gravar qualquer CSV, `gerar_dados.py` confere, com `assert` e `math.isclose(..., rel_tol=0.0, abs_tol=...)` — tolerância só absoluta (centésimos para valores monetários, `0,0001` para similaridade), nunca relativa, para que uma diferença de poucos centavos num total de R$ 1,4 bilhão não passe despercebida:

**Comuns a todos os extratos:** ausência de nulo em qualquer coluna exportada.

- `pedidos_dashboard.csv`: 48.998 linhas, `order_id` único, 2.000 clientes distintos, período 2020-01-01 a 2026-12-31, soma R$ 1.406.487.201,80, média R$ 28.704,99;
- `clientes_fieis.csv`: 10 linhas, `customer_id` único, `posicao` sequencial 1–10, 1º colocado `customer_id = 22` com ticket R$ 41.839,94, diversidade 14 em todas as linhas;
- `categorias_clientes_fieis.csv`: exatamente 14 linhas, `category_id` único, `posicao` sequencial 1–14, 1ª categoria "Hélices" com 492 itens;
- `vendas_dia_semana.csv`: 7 linhas, `ordem_dia` único, 2.557 dias de calendário no total, 78 dias sem venda física, soma R$ 419.273.315,30, pior média na Quinta-feira (R$ 157.154,32);
- `previsao_demanda.csv`: 3 linhas, `mes` único, meses exatamente 2026-01-01/02-01/03-01, nenhuma previsão nula, soma prevista 148,6667 (arredondada 149), MAE 19,4444;
- `recomendacoes.csv`: 5 linhas, `product_id` único, `posicao` sequencial 1–5, produto-alvo (`product_id = 180`) ausente, 1º colocado "Motor de Popa 5331" com similaridade 0,256553.

**Proteções específicas antes dos merges (Q6 e Q7):**

- Q6: `product_id` do nome "Bússola de Bordo 702" precisa ser exatamente `[74, 240]`, e os `product_variant_id` relacionados exatamente `[147, 148, 486]` — falha com mensagem clara antes de qualquer merge se divergir.
- Q7: o nome "Motor de Popa 1949" precisa corresponder a exatamente um produto (nunca `.iloc[0]` sem checar cardinalidade); o `product_id` encontrado precisa ser `180` e precisa existir nas colunas da matriz binária antes de calcular a similaridade.
