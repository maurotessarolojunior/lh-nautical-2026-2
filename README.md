# LH Nautical 2026.2

## Visão geral

Resolução do desafio Lighthouse 2026.2 (LH Nautical): um varejo náutico fictício, com dados brutos exportados em 24 arquivos CSV. O trabalho cobre desde a inferência do schema relacional e a carga em PostgreSQL até a análise de vendas e clientes, a previsão de demanda, um sistema de recomendação de produtos e a preparação dos dados para o dashboard final.

## Fluxo do projeto

```text
data/raw
├── Q2/Q3 → PostgreSQL tipado → análises SQL (Q1, Q4 e Q5)
├── Q6/Q7 → pandas e scikit-learn → previsão e recomendação
└── gerar_dados.py → marts em CSV → Looker Studio → PDF
```

Os três caminhos partem da mesma origem (`data/raw/1-lh_nautical_csv/`) e reutilizam as mesmas regras de negócio já validadas, mas não dependem fisicamente um do outro — nenhum lê a saída do outro. O dashboard está concluído: os seis extratos foram gerados e validados por `Submissão/Q8-Dashboard/gerar_dados.py`, o painel foi construído no Looker Studio a partir deles, e o PDF final está em [`Submissão/Q8-Dashboard/LH_Nautical_2026_2_Dashboard.pdf`](Submissão/Q8-Dashboard/LH_Nautical_2026_2_Dashboard.pdf).

## Estrutura do repositório

```text
.
├── data/
│   ├── raw/1-lh_nautical_csv/       # os 24 CSVs originais do desafio
│   └── processed/marts/dashboard/   # 6 extratos analíticos para o Looker Studio
├── notebooks/
│   └── lh_nautical_mauro.ipynb      # raciocínio completo, questão por questão
├── Submissão/
│   ├── Q1/                          # EDA da tabela orders
│   ├── Q2/                          # inferência de schema (infer_schema.py, schema.sql)
│   ├── Q3/                          # carregamento (load_data.py)
│   ├── Q4/                          # análise de clientes
│   ├── Q5/                          # dimensão de calendário
│   ├── Q6/                          # previsão de demanda (baseline walk-forward)
│   ├── Q7/                          # sistema de recomendação
│   └── Q8-Dashboard/                # gerar_dados.py, README.md e PDF final do painel
├── requirements.txt
└── README.md
```

## Como executar

### Pré-requisitos

- PostgreSQL em execução — necessário para aplicar o schema da Q2, executar a carga da Q3, rodar as análises SQL de Q1/Q4/Q5 e executar o notebook completo;
- banco de destino vazio — exigência da carga da Q3 (o script recusa rodar se o destino já tiver dados); não é necessário para Q6, Q7 nem para o gerador do dashboard, que leem os CSVs brutos diretamente;
- variáveis `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER` e `PGPASSWORD` configuradas no ambiente.

### 1. Preparar o ambiente

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

O acesso ao PostgreSQL usa as variáveis de ambiente listadas acima, lidas automaticamente por `psycopg2` — nenhuma credencial fica no código.

### 2. Gerar o schema — Q2

```bash
python Submissão/Q2/infer_schema.py
```

Lê os 24 CSVs em `data/raw/1-lh_nautical_csv/` e gera `Submissão/Q2/schema.sql` (DDL do PostgreSQL), usando só biblioteca padrão do Python.

### 3. Criar as tabelas e carregar os dados — Q3

```bash
psql -f Submissão/Q2/schema.sql
python Submissão/Q3/load_data.py
```

O primeiro comando cria as 24 tabelas a partir do schema gerado; o segundo carrega os CSVs com `COPY FROM STDIN`, dentro de uma única transação.

### 4. Executar a Q6 e a Q7

```bash
python Submissão/Q6/6.1.py
python Submissão/Q7/7.1.py
```

Diferente de Q1/Q4/Q5, essas duas questões **não dependem do PostgreSQL** — leem os CSVs brutos diretamente com pandas.

### 5. Preparar os dados do dashboard

```bash
python Submissão/Q8-Dashboard/gerar_dados.py
```

Também lê os CSVs brutos diretamente (sem PostgreSQL), reproduz as regras já validadas da Q1 e das Q4–Q7, e grava os seis extratos em `data/processed/marts/dashboard/` — prontos para importar no Looker Studio.

### 6. Executar o notebook

```bash
jupyter notebook notebooks/lh_nautical_mauro.ipynb
```

Reiniciar o kernel e executar todas as células em ordem. As seções de Q1, Q4 e Q5 consultam o PostgreSQL já carregado pelos passos 2 e 3; as seções de Q6 e Q7 leem os CSVs brutos diretamente, como os scripts correspondentes.

## Questões e principais resultados

| Questão | Entrega | Resultado-chave |
|---|---|---|
| Q1 — EDA | `Submissão/Q1/1.1.sql`, `1.2.md`, `1.3.md` | 48.998 linhas, 13 colunas, `total` médio R$ 28.704,99 |
| Q2 — Schema | `Submissão/Q2/infer_schema.py`, `schema.sql` | 24 tabelas geradas; identificadores (CPF, chave de NF-e, CEP) preservados como texto |
| Q3 — Carregamento | `Submissão/Q3/load_data.py`, `3.2.md` | 433.424 linhas carregadas, 0 divergência por tabela, resposta `251864` |
| Q4 — Análise de clientes | `Submissão/Q4/4.1.sql`, `4.2.md` | Top 10 clientes por ticket médio; categoria líder Hélices (492 itens) |
| Q5 — Dimensão de calendário | `Submissão/Q5/5.1.sql`, `5.2.md` | Pior dia de vendas físicas: Quinta-feira (R$ 157.154,32) |
| Q6 — Previsão de demanda | `Submissão/Q6/6.1.py`, `6.2.md`, `6.3.md` | Baseline de média móvel de 3 meses, avaliado walk-forward; soma prevista arredondada = `149`; MAE ≈ `19,4444` |
| Q7 — Sistema de recomendação | `Submissão/Q7/7.1.py`, `7.2.md`, `7.3.md` | Produto mais similar a "Motor de Popa 1949": "Motor de Popa 5331" |

## Dashboard

Painel construído no Looker Studio a partir dos seis extratos de `data/processed/marts/dashboard/` (gerados e validados por `Submissão/Q8-Dashboard/gerar_dados.py` — dicionário completo em `Submissão/Q8-Dashboard/README.md`). PDF final: [`Submissão/Q8-Dashboard/LH_Nautical_2026_2_Dashboard.pdf`](Submissão/Q8-Dashboard/LH_Nautical_2026_2_Dashboard.pdf).

Três páginas:

1. **Visão geral de vendas** — tamanho da operação (valor total, pedidos, clientes, ticket médio), evolução mensal, comparação por canal e distribuição por status de pedido.
2. **Clientes e operação física** — Top 10 clientes fiéis por ticket médio, categorias mais consumidas por esse grupo, e a média de vendas físicas por dia da semana (com os dias sem venda incluídos no cálculo).
3. **Previsão e recomendação** — demanda real vs. prevista pelo baseline da Q6 (com o MAE), e o ranking de produtos mais similares ao item de referência da Q7.

## Decisões técnicas

- **SQL direto no PostgreSQL.** Depois que a Q2 gera o schema e a Q3 carrega os dados, as consultas de Q1, Q4 e Q5 usam a mesma base PostgreSQL, sem ferramenta intermediária.
- **Q2 usa só biblioteca padrão do Python** (exigência do enunciado): varredura completa dos 24 CSVs — nunca amostra — e uma lista curta de exceções semânticas para colunas que parecem número mas são identificadores (CPF, chave de nota fiscal, código de barras), preservando zeros à esquerda que um tipo numérico perderia silenciosamente.
- **Q3 carrega com `COPY FROM STDIN` dentro de uma transação única:** qualquer falha desfaz a carga inteira, evitando um banco parcialmente carregado. O script recusa rodar se o destino já tiver dados, para não duplicar numa segunda execução.
- **Q4 e Q5 separam a granularidade de cada cálculo antes de juntar tabelas** — evita inflar soma ou contagem quando uma linha se relaciona com várias outras (um pedido com vários itens, por exemplo).
- **Q6 usa o baseline obrigatório do enunciado** (média móvel de 3 meses) com avaliação temporal walk-forward: cada previsão usa só meses com data estritamente anterior a ela, sem embaralhar treino e teste.
- **Q7 usa uma matriz binária cliente × produto e a similaridade de cosseno do scikit-learn** (`cosine_similarity`), sem implementar a fórmula manualmente — a exclusão do produto de referência do ranking é feita pelo `product_id`, nunca por comparação de valor de similaridade.
- **Nenhum filtro de status de pedido foi inventado em Q4, Q5, Q6, Q7 ou no dashboard.** O enunciado não define quais status (`paid`, `confirmed`, `cancelled`, `draft`) devem entrar em cada análise, e criar um filtro não solicitado mudaria os resultados sem base no que foi pedido.
- **O dashboard final tem um caminho de dados separado do PostgreSQL, não um só.** `Submissão/Q8-Dashboard/gerar_dados.py` lê os CSVs brutos diretamente e materializa seis extratos analíticos em `data/processed/marts/dashboard/`, reproduzindo em pandas as mesmas regras já validadas na Q1 e nas Q4–Q7 — sem depender do banco estar de pé para gerar o material do Looker Studio. Não há camada `stage`/`intermediate`: `data/raw` já preserva a origem, a Q3 já materializa uma ingestão tipada no PostgreSQL, e as transformações do dashboard são pequenas o bastante para viver, legíveis, dentro de um único script.
- **`data/processed/marts/dashboard/` e `Submissão/Q8-Dashboard/` continuam com responsabilidades separadas mesmo com o painel concluído.** O primeiro guarda os seis CSVs prontos para consumo; o segundo guarda o gerador, a documentação (`Submissão/Q8-Dashboard/README.md`, com o dicionário completo dos extratos) e o produto visual (o PDF final exportado do Looker Studio).

## Tecnologias utilizadas

| Tecnologia | Função |
|---|---|
| Python 3 | linguagem principal |
| PostgreSQL | destino do schema e da carga (Q2/Q3) e base das análises SQL (Q1/Q4/Q5) |
| psycopg2 | conexão e carga (`COPY FROM STDIN`) com o PostgreSQL |
| pandas | preparação e análise de dados (Q1, Q6, Q7, dashboard) |
| scikit-learn | similaridade de cosseno entre produtos (Q7) |
| matplotlib | gráfico de vendas reais vs. previstas (Q6) |
| Jupyter Notebook | relatório executável com o raciocínio de cada questão |
| Looker Studio | construção do painel visual (3 páginas) a partir dos seis marts, exportado em PDF |

## Premissas e limitações

- Os dados são fictícios, gerados para o desafio, com registros até 2026-12-31 — incluindo datas posteriores à data de execução da análise.
- O schema da Q2 é uma camada de ingestão bruta: sem `PRIMARY KEY`, `FOREIGN KEY` ou `NOT NULL`. O objetivo é carregar os dados exatamente como estão, sem rejeitar nenhuma linha por causa de uma regra de integridade ainda não validada.
- As consultas e scripts de Q4 a Q7 (e a preparação do dashboard) seguem a definição literal de cada enunciado, sem acrescentar filtro de status de pedido além do que foi pedido.
- O baseline da Q6 (média móvel de 3 meses) reage com atraso e não representa tendência, sazonalidade nem mudanças bruscas de demanda — por isso subestimou os três meses de teste.
- A similaridade da Q7 mede sobreposição relativa entre grupos de compradores, não compra no mesmo pedido nem relação de causalidade entre produtos.

## Autor

**Mauro Tessarolo Junior**
GitHub: [@maurotessarolojunior](https://github.com/maurotessarolojunior)
