-- schema.sql gerado automaticamente por infer_schema.py
-- Fonte: 24 arquivos CSV em ../../Workspace/data/raw/1-lh_nautical_csv
-- Destino: PostgreSQL. Camada de ingestao bruta (landing) - sem PRIMARY KEY,
-- FOREIGN KEY ou NOT NULL: o objetivo e nao rejeitar nenhuma linha real na
-- carga da Q3. Cada coluna traz um comentario com o motivo da tipagem
-- (override semantico explicito ou evidencia da varredura completa do CSV).
-- Ver o cabecalho deste script para o raciocinio completo da inferencia.


CREATE TABLE "addresses" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "customer_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "address_type" TEXT, -- valores mistos ou fora dos formatos acima
    "postal_code" TEXT, -- CEP - identificador geografico; ja e texto por evidencia (formato com hifen), mantido explicito
    "street" TEXT, -- valores mistos ou fora dos formatos acima
    "number" TEXT, -- numero do endereco - pode conter 'S/N' ou complemento no futuro; nao e usado em operacao aritmetica
    "complement" TEXT, -- valores mistos ou fora dos formatos acima
    "district" TEXT, -- valores mistos ou fora dos formatos acima
    "city" TEXT, -- valores mistos ou fora dos formatos acima
    "state" TEXT, -- valores mistos ou fora dos formatos acima
    "country" TEXT, -- valores mistos ou fora dos formatos acima
    "is_primary" BOOLEAN -- 100% dos valores sao TRUE/FALSE
);

CREATE TABLE "attributes" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "name" TEXT, -- valores mistos ou fora dos formatos acima
    "data_type" TEXT -- valores mistos ou fora dos formatos acima
);

CREATE TABLE "brands" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "name" TEXT, -- valores mistos ou fora dos formatos acima
    "country" TEXT, -- valores mistos ou fora dos formatos acima
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "categories" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "name" TEXT, -- valores mistos ou fora dos formatos acima
    "slug" TEXT, -- valores mistos ou fora dos formatos acima
    "parent_category_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "customers" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "person_type" TEXT, -- valores mistos ou fora dos formatos acima
    "legal_name" TEXT, -- valores mistos ou fora dos formatos acima
    "trade_name" TEXT, -- valores mistos ou fora dos formatos acima
    "tax_id" TEXT, -- CPF/CNPJ - documento, nao quantidade (ja seria pego pela guarda de zero a esquerda; mantido explicito)
    "state_registration" TEXT, -- inscricao estadual - pode ser 'ISENTO'; ja e texto por evidencia, mantido explicito
    "email" TEXT, -- valores mistos ou fora dos formatos acima
    "phone" TEXT, -- telefone - identificador de contato, nao quantidade
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "employees" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "full_name" TEXT, -- valores mistos ou fora dos formatos acima
    "cpf" TEXT, -- CPF - documento; amostra atual (15 linhas) nao tem zero a esquerda por coincidencia, nao por garantia
    "email" TEXT, -- valores mistos ou fora dos formatos acima
    "role" TEXT, -- valores mistos ou fora dos formatos acima
    "primary_location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "hire_date" DATE, -- 100% no formato YYYY-MM-DD
    "termination_date" DATE, -- 100% no formato YYYY-MM-DD
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "fiscal_invoices" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "nfe_number" TEXT, -- numero da NF-e - identificador; ja e texto por evidencia (prefixo NFE), mantido explicito
    "nfe_access_key" TEXT, -- chave de acesso da NF-e (44 digitos) - identificador, nao quantidade
    "series" TEXT, -- valores mistos ou fora dos formatos acima
    "issued_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "status" TEXT, -- valores mistos ou fora dos formatos acima
    "total_amount" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "xml_storage_uri" TEXT, -- valores mistos ou fora dos formatos acima
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "goods_receipt_items" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "goods_receipt_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "purchase_order_item_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "quantity_received" NUMERIC(5,3) -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 3 decimal(is))
);

CREATE TABLE "goods_receipts" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "purchase_order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "received_by_employee_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "received_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "notes" TEXT, -- valores mistos ou fora dos formatos acima
    "created_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "locations" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "name" TEXT, -- valores mistos ou fora dos formatos acima
    "location_type" TEXT, -- valores mistos ou fora dos formatos acima
    "postal_code" TEXT, -- CEP - identificador geografico; ja e texto por evidencia (formato com hifen), mantido explicito
    "street" TEXT, -- valores mistos ou fora dos formatos acima
    "number" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "complement" TEXT, -- valores mistos ou fora dos formatos acima
    "district" TEXT, -- valores mistos ou fora dos formatos acima
    "city" TEXT, -- valores mistos ou fora dos formatos acima
    "state" TEXT, -- valores mistos ou fora dos formatos acima
    "country" TEXT, -- valores mistos ou fora dos formatos acima
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "order_items" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "quantity" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "unit_price" NUMERIC(6,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
    "icms_rate" NUMERIC(4,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 2 decimal(is))
    "ipi_rate" NUMERIC(4,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 2 decimal(is))
    "line_total" NUMERIC(7,2) -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 5 digito(s) inteiro(s) + 2 decimal(is))
);

CREATE TABLE "orders" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "order_number" TEXT, -- numero do pedido - identificador; ja e texto por evidencia (prefixo SO-), mantido explicito
    "channel" TEXT, -- valores mistos ou fora dos formatos acima
    "customer_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "salesperson_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "status" TEXT, -- valores mistos ou fora dos formatos acima
    "subtotal" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "discount_amount" NUMERIC(7,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 5 digito(s) inteiro(s) + 2 decimal(is))
    "total" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "placed_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "payments" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "method" TEXT, -- valores mistos ou fora dos formatos acima
    "installments" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "amount" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "status" TEXT, -- valores mistos ou fora dos formatos acima
    "paid_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "product_suppliers" (
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "supplier_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "supplier_sku" TEXT, -- SKU do fornecedor - identificador; ja e texto por evidencia, mantido explicito
    "last_quoted_cost" NUMERIC(6,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
    "lead_time_days" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "is_preferred" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "product_variants" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "product_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "sku" TEXT, -- SKU - identificador; ja e texto por evidencia, mantido explicito
    "barcode_ean" TEXT, -- codigo de barras EAN - identificador, nao quantidade
    "sale_price" NUMERIC(6,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
    "cost_price" NUMERIC(6,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
    "weight_kg" NUMERIC(5,3), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 3 decimal(is))
    "icms_rate" NUMERIC(4,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 2 decimal(is))
    "ipi_rate" NUMERIC(4,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 2 decimal(is))
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "products" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "name" TEXT, -- valores mistos ou fora dos formatos acima
    "description" TEXT, -- valores mistos ou fora dos formatos acima
    "brand_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "category_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "ncm_code" TEXT, -- codigo NCM (classificacao fiscal de mercadoria) - identificador de categoria, nao quantidade
    "unit_of_measure" TEXT, -- valores mistos ou fora dos formatos acima
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "purchase_order_items" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "purchase_order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "quantity_ordered" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "unit_cost" NUMERIC(6,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
    "line_total" NUMERIC(8,2) -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
);

CREATE TABLE "purchase_orders" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "po_number" TEXT, -- numero da ordem de compra - identificador; ja e texto por evidencia (prefixo PO-), mantido explicito
    "supplier_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "buyer_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "destination_location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "status" TEXT, -- valores mistos ou fora dos formatos acima
    "currency" TEXT, -- valores mistos ou fora dos formatos acima
    "subtotal" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "total" NUMERIC(8,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 6 digito(s) inteiro(s) + 2 decimal(is))
    "placed_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "expected_delivery_at" DATE, -- 100% no formato YYYY-MM-DD
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "return_items" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "return_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "order_item_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "quantity" NUMERIC(5,3), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 3 decimal(is))
    "action" TEXT, -- valores mistos ou fora dos formatos acima
    "exchange_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "unit_refund_amount" NUMERIC(6,2) -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 4 digito(s) inteiro(s) + 2 decimal(is))
);

CREATE TABLE "returns" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "return_number" TEXT, -- numero da devolucao - identificador; ja e texto por evidencia (prefixo RT-), mantido explicito
    "order_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "customer_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "received_at_location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "status" TEXT, -- valores mistos ou fora dos formatos acima
    "reason" TEXT, -- valores mistos ou fora dos formatos acima
    "total_refund_amount" NUMERIC(7,2), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 5 digito(s) inteiro(s) + 2 decimal(is))
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "stock_levels" (
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "quantity_on_hand" NUMERIC(5,3), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 2 digito(s) inteiro(s) + 3 decimal(is))
    "reorder_point" TEXT, -- coluna 100% vazia - sem evidencia, fallback documentado
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "stock_movements" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "location_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "movement_type" TEXT, -- valores mistos ou fora dos formatos acima
    "quantity" NUMERIC(6,3), -- 100% numerico decimal, sem zero a esquerda (maior forma observada: 3 digito(s) inteiro(s) + 3 decimal(is))
    "reference_table" TEXT, -- valores mistos ou fora dos formatos acima
    "reference_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "employee_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "notes" TEXT, -- valores mistos ou fora dos formatos acima
    "occurred_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "created_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "suppliers" (
    "id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "legal_name" TEXT, -- valores mistos ou fora dos formatos acima
    "trade_name" TEXT, -- valores mistos ou fora dos formatos acima
    "country" TEXT, -- valores mistos ou fora dos formatos acima
    "tax_id" TEXT, -- documento fiscal do fornecedor (formato varia por pais); ja e texto por evidencia, mantido explicito
    "tax_id_type" TEXT, -- valores mistos ou fora dos formatos acima
    "email" TEXT, -- valores mistos ou fora dos formatos acima
    "phone" TEXT, -- telefone - identificador de contato, nao quantidade
    "contact_name" TEXT, -- valores mistos ou fora dos formatos acima
    "is_active" BOOLEAN, -- 100% dos valores sao TRUE/FALSE
    "created_at" TIMESTAMP, -- 100% no formato YYYY-MM-DD HH:MM:SS
    "updated_at" TIMESTAMP -- 100% no formato YYYY-MM-DD HH:MM:SS
);

CREATE TABLE "variant_attribute_values" (
    "product_variant_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "attribute_id" BIGINT, -- 100% inteiro, sem zero a esquerda, dentro da faixa de BIGINT
    "value" TEXT -- valores mistos ou fora dos formatos acima
);
