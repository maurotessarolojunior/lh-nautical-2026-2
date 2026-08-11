# LH Nautical 2026.2

## Visão geral

Resolução do desafio Lighthouse 2026.2 (LH Nautical): um varejo náutico fictício, com dados brutos exportados em 24 arquivos CSV. O trabalho cobre desde a inferência do schema relacional até a carga em PostgreSQL e a análise de vendas e clientes.

## Fluxo do projeto

```text
CSV bruto (24 arquivos)
        │
        ▼
inferência do schema (Q2, Python padrão)
        │
        ▼
criação das tabelas + carga (Q3, PostgreSQL)
        │
        ▼
análises (Q1, Q4, Q5) — SQL direto no banco carregado
```

## Estrutura do repositório

```text
.
├── data/raw/1-lh_nautical_csv/   # os 24 CSVs originais do desafio
├── notebooks/
│   └── lh_nautical.ipynb         # raciocínio completo, questão por questão
├── Submissão/
│   ├── Q1/                       # EDA da tabela orders
│   ├── Q2/                       # inferência de schema (infer_schema.py, schema.sql)
│   ├── Q3/                       # carregamento (load_data.py)
│   ├── Q4/                       # análise de clientes
│   └── Q5/                       # dimensão de calendário
├── requirements.txt
└── README.md
```

## Como executar

### Pré-requisitos

- PostgreSQL em execução;
- banco de destino vazio;
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

### 4. Executar o notebook

```bash
jupyter notebook notebooks/lh_nautical.ipynb
```

Reiniciar o kernel e executar todas as células em ordem — o notebook consulta o banco já carregado pelos passos 2 e 3.

## Questões e principais resultados

| Questão | Entrega | Resultado-chave |
|---|---|---|
| Q1 — EDA | `Submissão/Q1/1.1.sql`, `1.2.md`, `1.3.md` | 48.998 linhas, 13 colunas, `total` médio R$ 28.704,99 |
| Q2 — Schema | `Submissão/Q2/infer_schema.py`, `schema.sql` | 24 tabelas geradas; identificadores (CPF, chave de NF-e, CEP) preservados como texto |
| Q3 — Carregamento | `Submissão/Q3/load_data.py`, `3.2.md` | 433.424 linhas carregadas, 0 divergência por tabela, resposta `251864` |
| Q4 — Análise de clientes | `Submissão/Q4/4.1.sql`, `4.2.md` | Top 10 clientes por ticket médio; categoria líder Hélices (492 itens) |
| Q5 — Dimensão de calendário | `Submissão/Q5/5.1.sql`, `5.2.md` | Pior dia de vendas físicas: Quinta-feira (R$ 157.154,32) |

## Decisões técnicas

- **SQL direto no PostgreSQL.** Depois que a Q2 gera o schema e a Q3 carrega os dados, as consultas de Q1, Q4 e Q5 usam a mesma base PostgreSQL, sem ferramenta intermediária.
- **Q2 usa só biblioteca padrão do Python** (exigência do enunciado): varredura completa dos 24 CSVs — nunca amostra — e uma lista curta de exceções semânticas para colunas que parecem número mas são identificadores (CPF, chave de nota fiscal, código de barras), preservando zeros à esquerda que um tipo numérico perderia silenciosamente.
- **Q3 carrega com `COPY FROM STDIN` dentro de uma transação única:** qualquer falha desfaz a carga inteira, evitando um banco parcialmente carregado. O script recusa rodar se o destino já tiver dados, para não duplicar numa segunda execução.
- **Q4 e Q5 separam a granularidade de cada cálculo antes de juntar tabelas** — evita inflar soma ou contagem quando uma linha se relaciona com várias outras (um pedido com vários itens, por exemplo).

## Tecnologias utilizadas

| Tecnologia | Função |
|---|---|
| Python 3 | linguagem principal |
| PostgreSQL | banco de destino do schema e da carga |
| psycopg2 | conexão e carga (`COPY FROM STDIN`) com o PostgreSQL |
| pandas | inspeção inicial dos CSVs (Q1) |
| Jupyter Notebook | relatório executável com o raciocínio de cada questão |

## Premissas e limitações

- Os dados são fictícios, gerados para o desafio, com registros até 2026-12-31 — incluindo datas posteriores à data de execução da análise.
- O schema da Q2 é uma camada de ingestão bruta: sem `PRIMARY KEY`, `FOREIGN KEY` ou `NOT NULL`. O objetivo é carregar os dados exatamente como estão, sem rejeitar nenhuma linha por causa de uma regra de integridade ainda não validada.
- As consultas de Q4 e Q5 seguem a definição literal de cada enunciado, sem acrescentar filtro de status de pedido além do que foi pedido.

## Autor

**Mauro Tessarolo Junior**
GitHub: [@maurotessarolojunior](https://github.com/maurotessarolojunior)
