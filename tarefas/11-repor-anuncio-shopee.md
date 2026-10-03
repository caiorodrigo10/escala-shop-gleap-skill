# Tarefa 11 — Repor anúncio removido com produto whitelisted

Executa a reposição unitária de um anúncio confirmado como `SHOPEE_DELETE` ou
`BANNED`, ou de um `SELLER_DELETE` que passe integralmente pelo gate contextual,
usando outro produto já existente no Supabase e com whitelist ativa para o
mesmo fornecedor. O produto removido nunca é republicado.

> Estado: `active` desde 2026-09-02, após cinco canários reais concluídos e
> verificados. Toda execução continua exigindo preview e GO explícito do owner.

## Entradas obrigatórias

- ObjectId e número humano do ticket Gleap;
- `stores.id`;
- `store_products.id` do anúncio removido;
- status remoto confirmado ao vivo para o item exato;
- fornecedor canônico sem divergência.

Para `SELLER_DELETE`, exigir adicionalmente ticket `BUG`, relato da cliente de
que o anúncio/produto sumiu ou foi removido, exatamente um `SELLER_DELETE` ao
vivo na loja e GO explícito do owner. O estado sozinho nunca basta.

Não aceitar apenas o título do ticket, o status local ou todos os produtos da
loja como identificação do item removido.

## Preflight

1. Carregar `../references/tool-contract.md` e validar o catálogo.
2. Reobter o ticket e todas as mídias; inspecionar evidência visual obrigatória.
3. Sondar o item na Shopee. Aceitar diretamente `SHOPEE_DELETE` ou `BANNED`.
   Para `SELLER_DELETE`, contar todos os itens nesse estado ao vivo na loja e
   exigir o gate contextual completo; zero, mais de um ou contexto incompleto
   vira `needs_review`.
4. Confirmar `store_products.product_id -> products.supplier_id` e fornecedor
   canônico da loja. Divergência ou ambiguidade vira `needs_review`.
5. Confirmar política vigente do fornecedor e whitelist ativa do candidato.
6. Confirmar que o candidato é outro produto, não foi usado na loja, tem estoque
   e não está em quarentena.
7. Resolver ao vivo a key da lane `To Test` e confirmar capacidade de nota
   interna. Não assumir `TOTEST` sem consultar o board.
8. Somente quando 3–6 estiverem comprovados, adicionar o sinal composto
   `derived:shopee-replacement-ready`; o catálogo não infere esse sinal por texto.

## Paridade obrigatória com publicação por wave

A reposição prepara o substituto com o mesmo padrão do pipeline de wave:

- `custom_title` e `custom_description` têm precedência sobre os campos brutos;
- título usa `buildTitle` e descrição usa `buildDescription` com o mesmo par de
  templates fixado na loja;
- a imagem IA usa `generateProductImage`, com a imagem original do fornecedor
  como fonte;
- a publicação envia primeiro a imagem IA ativa e depois as imagens do
  fornecedor, mantendo preço, atributos, marca, logística e variantes pelos
  mesmos resolvers canônicos.

Se qualquer um desses artefatos não estiver pronto, o fluxo falha fechado e não
publica com título, descrição ou imagem improvisados.

## Preview obrigatório

```bash
INTERNAL_API_SECRET='<carregado-no-ambiente>' \
node skills-shared/gleap/commands/replace-shopee-listing.mjs preview \
  --ticket-id '<ObjectId-ou-numero>' \
  --store-id '<stores.id>' \
  --removed-store-product-id '<store_products.id>' \
  --base-url 'http://localhost:3000'
```

O preview consulta o endpoint com `dryRun=true` e mostra ticket, loja, produto
removido, candidato, fornecedor e efeitos previstos. Ele não publica, não aplica
desconto e não altera o ticket. Nunca mostrar o segredo no preview ou report.

Antes do `apply`, apresentar exatamente:

- ticket/ObjectId, loja e produto removido;
- fornecedor e candidato whitelisted selecionado;
- criação de um novo anúncio e inclusão no desconto padrão;
- texto exato da nota interna;
- mudança para a lane `To Test` resolvida ao vivo;
- confirmação de que não haverá mensagem à aluna nem transição para `Done`.

## Apply

Durante `validated`, somente após GO explícito para o canário apresentado. Depois
da promoção para `active`, uma política persistente vigente para o fornecedor
exato pode autorizar a execução sem GO por ticket:

```bash
SHOPEE_REPLACEMENT_BASE_URL='<origem-https-oficial-configurada>' \
INTERNAL_API_SECRET='<carregado-no-ambiente>' \
node skills-shared/gleap/commands/replace-shopee-listing.mjs apply \
  --ticket-id '<ObjectId-ou-numero>' \
  --store-id '<stores.id>' \
  --removed-store-product-id '<store_products.id>' \
  --owner-go
```

Quando o alvo for o único `SELLER_DELETE` contextual do ticket, acrescentar:

```bash
  --seller-delete-bug-context --customer-reported-removal
```

Essas flags apenas transportam o contexto aprovado. O endpoint reconta o estado
ao vivo e continua bloqueando caso não exista exatamente um `SELLER_DELETE`.

No modo autônomo já promovido, substituir `--owner-go` por
`--policy-authorized`. O endpoint precisa validar a política persistida; a flag
não contorna política ausente, expirada ou desativada.

`apply` não aceita `--base-url`: usa somente a origem HTTPS oficial configurada
em `SHOPEE_REPLACEMENT_BASE_URL`. Preview aceita apenas loopback. O CLI rejeita
credenciais na URL e redirects antes de expor o segredo a uma requisição.

O endpoint é responsável por política, reserva, publicação, desconto,
idempotência e read-back. Se retornar `needs_review`, não trocar silenciosamente
o candidato, não alterar o ticket e não tentar o write novamente sem reler o run.

## Encerramento no Gleap

Somente quando o endpoint retornar `completed` e o anúncio/desconto estiverem
confirmados:

1. montar a nota a partir dos IDs efetivamente retornados;
2. apresentar o texto exato no preview de writes Gleap;
3. com o GO do canário ou a política persistente válida para esses writes, usar
   `send_message({ ticketId: objectId, text, isNote: true })`;
4. reler a nota;
5. usar `update_ticket` com a key de `To Test` resolvida ao vivo;
6. reler o ticket;
7. atribuir somente se previsto, em chamada separada e por último.

Template mínimo:

```text
[interno] Reposição Shopee concluída e verificada.
Item removido: {removed_store_product_id} / Shopee {removed_shopee_item_id}.
Produto substituto whitelisted: {product_id}; fornecedor: {supplier_id}.
Novo anúncio Shopee: {replacement_shopee_item_id}.
Campanha de desconto padrão: confirmada.
Run auditável: {run_id}.
```

Nunca enviar esse texto como mensagem pública. Nunca mover para `Done`.

## Falhas e retomada

- `preview`: nenhum write externo; registrar blockers.
- falha antes da publicação: seguir o lease/run retornado, sem criar outro ticket.
- run `published`: retomar desconto/verificação; nunca chamar publicação de novo.
- resposta incerta, whitelist desativada, estoque inválido, OAuth ou fornecedor
  divergente: `needs_review`, sem writes Gleap.
- antes de retry, reler o estado atual; nunca repetir write não idempotente às cegas.

## Verificação final

- run `completed`;
- novo `shopee_item_id` relido e diferente do removido;
- produto e fornecedor correspondem à whitelist;
- desconto padrão relido;
- nota interna e lane `To Test` relidas;
- nenhuma mensagem pública e nenhum status `Done`.
- título, descrição e ordem das imagens seguem o contrato canônico da wave.
