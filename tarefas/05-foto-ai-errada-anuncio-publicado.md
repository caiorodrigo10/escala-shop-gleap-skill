# Tarefa 05 — Foto AI errada em anuncio ja publicado (Shopee)

Automatiza a correcao de foto slot 1 (imagem AI) em anuncios ja publicados na Shopee quando a aluna reclama que a imagem NAO representa o produto real (ex: modelo errado, categoria errada, salto errado, cor errada).

Diferente de outros bugs, este NAO e "produto errado no anuncio" — o texto/categoria/preco estao certos. So a IMAGEM slot 1 gerada pela IA saiu diferente do produto real do fornecedor.

Referencia canonical:
- Caso que originou: cliente de exemplo 2026-07-06 — CHINELO SLIDE NUVEM TRATORADO FEMININO. Aluna reclamou "foto errada". IA gerou sandalia salto alto tratorado (interpretou "altura extra" no texto do fornecedor como salto), quando produto real e slide EVA plano tratorado tipo Yeezy Slide.
- Fix aplicado: regen fal-ai (nova seed) → upload Shopee media_space → update_item slot 1 → DB sync
- Precedente adicional `ticket de exemplo`: imagens atuais fiéis não foram trocadas; algumas
  candidatas do mesmo produto eram piores. Ver
  `../references/known-case-solutions.md`.

---

## Quando executar

Carrega quando `tarefas/00-analise-geral.md` classifica um ticket como `categoria:foto-ai-errada-anuncio-publicado`.

Regex de deteccao (title/desc):

```
/foto\s*(errad[oa]|feia|estranha|nao\s*(bate|combina))|imagem\s*(errad[oa]|feia|estranha)|anuncio\s*com\s*(foto|imagem)|produto\s*(diferente|nao\s*e)\s*(o\s*)?(mesmo|igual)|(alterar|corrigir|trocar|mudar)\s*(a\s*)?foto|foto\s*(do\s*)?anuncio/i
```

Trigger complementar: link Shopee no corpo/attachment do ticket (`shopee.com.br/product/{itemId}` ou `shopee.com.br/{slug}-i.{shopId}.{itemId}`).

Tambem pode ser invocada direto:

```bash
/gleap --category=foto-ai-errada-anuncio-publicado --ticket-id=X
```

---

## Pre-requisitos (HARD GATES)

1. Preflight da skill passou (Gleap MCP + Supabase + owner ID + `contexto/lp-arquitetura.md` carregado)
2. Ticket alvo tem `type=BUG` e `status IN ('OPEN','INPROGRESS')`
3. **Screenshot obrigatorio (KAKA-6):** print da aluna mostrando o anuncio errado + link Shopee. Se nao tiver print E nao tiver link, tag `skill:aguardando-owner` — sem visual dos 2 lados nao da pra decidir.
4. Contato Gleap tem `session.companyId` (store_id)
5. Custo fal-ai autorizado por batch — skill NUNCA regenera sem GO owner explicito (regen custa $0.04/img)

---

## Modos de execucao

| Modo | Comportamento |
|---|---|
| `scan` / `--dry-run` (default) | Investigar SPs + baixar imagens + preview do problema. NAO regenera. NAO altera Shopee. |
| `--apply` (owner explicito) | Regen + preview local + owner aprova + push Shopee via `update_item` slot 1 |

**Restricao critica:** modo `--apply` requer GO owner em 2 momentos:
1. Antes do regen (custo fal-ai)
2. Depois do regen, antes do push Shopee (imagem esta boa?)

---

## Passo 1 — Identificar o SP afetado

### 1a. Extrair shopee_item_id do link Shopee

Padrao URL Shopee BR:
```
https://shopee.com.br/{slug-produto}-i.{shopId}.{itemId}
```

Regex captura: `/i\.(\d+)\.(\d+)/` — group 1 = shopId, group 2 = itemId.

Se aluna nao mandou link, pedir ao Support pra pedir link antes de continuar. Sem link OU screenshot com identificador claro, skill nao consegue localizar o SP.

### 1b. Query DB pra achar SP

```sql
SELECT
  sp.id AS sp_id,
  sp.wave_number,
  sp.shopee_item_id,
  sp.final_title,
  sp.ai_image_run_ids[1] AS active_run_id,
  array_length(sp.ai_image_run_ids, 1) AS ai_runs_count,
  sp.supplier_image_urls,
  p.title AS product_title,
  p.external_id AS supplier_sku,
  p.original_image_urls AS supplier_images,
  s.name AS supplier_name
FROM store_products sp
LEFT JOIN products p ON p.id = sp.product_id
LEFT JOIN suppliers s ON s.id = p.supplier_id
WHERE sp.shopee_item_id = $ITEM_ID
  AND sp.store_id = $STORE_ID;
```

Se aluna mandou 2+ links, iterar por cada `shopee_item_id`.

---

## Passo 2 — Baixar as 3 imagens pra comparar (KAKA-6)

Baixar em paralelo:

```bash
# 1. Screenshot da aluna (o print original que ela mandou)
curl -s -o /tmp/ticket-{bugId}-print.jpg "{ticket.screenshotUrl}"

# 2. Imagem do fornecedor (primeira do array)
curl -s -o /tmp/ticket-{bugId}-supplier.jpg "{products.original_image_urls[0]}"

# 3. Imagem AI gerada (a que foi publicada — vem de generation_runs.result_url)
curl -s -o /tmp/ticket-{bugId}-ai.jpg "{generation_runs.result_url}"
```

Ler as 3 via `view_image` no Codex ou ferramenta visual equivalente no Hermes. Comparar:
- **Fornecedor** = verdade absoluta do produto
- **AI** = o que foi publicado (errado)
- **Print aluna** = confirma que ela viu esse AI errado

Se AI e fornecedor sao similares (ambos batem), aluna talvez esteja errada — tag `skill:aguardando-owner` pra owner revisar.

Se AI diverge do fornecedor: seguir Passo 3.

---

## Passo 3 — Diagnostico da causa (opcional mas util)

Ler o `resolved_prompt` do generation_run pra identificar o que confundiu o modelo:

```sql
SELECT resolved_prompt, model_id FROM generation_runs WHERE id = $ACTIVE_RUN_ID;
```

Padroes conhecidos que confundem Flux Kontext (adicionar aqui conforme aparecem):

| Padrao no prompt/texto fornecedor | Como IA interpreta erroneamente |
|---|---|
| "altura extra" + "tratorada" | Salto alto bloco tratorado |
| "estiloso" + "moderno" + calcado feminino | Adiciona salto/detalhes de moda |
| (adicionar novos casos aqui) | |

Isso ajuda a decidir se regen simples (nova seed) vai resolver, ou se precisa editar prompt.

### Reaproveitar imagem do mesmo produto em outra loja

Antes de pagar uma nova geracao, procurar `store_products` de outras lojas com o
**mesmo `product_id`** e `generation_runs.result_url` pronto. O titulo parecido ou
o mesmo fornecedor nao bastam: o `product_id` exato e o gate de identidade do
produto.

Comparar visualmente, lado a lado:

1. primeira imagem do fornecedor (verdade do produto);
2. imagem atual do anuncio alvo;
3. cada candidata do mesmo `product_id`.

Decisao:

- imagem atual fiel e sem o defeito relatado: nao trocar por trocar; confirmar o
  slot 1 ao vivo na Shopee e encaminhar para validacao;
- candidata fiel e claramente melhor que a atual: pode ser reaproveitada sem
  custo fal.ai, depois de preview e GO do owner;
- candidata perdeu aplique, estampa, cor, formato, quantidade de itens ou criou
  artefato: rejeitar, mesmo quando a composicao parece mais limpa;
- nenhuma candidata segura: voltar ao fluxo de regeneracao com custo e dois GOs.

O reaproveitamento nao autoriza apontar o alvo para um run pertencente a outra
store nem editar o historico da loja de origem. A imagem deve entrar no alvo por
um mecanismo auditavel que preserve o historico do `store_product`; se o runner
canonico nao suportar isso, parar no preview em vez de improvisar SQL ou push.

---

## Passo 4 — Regen preview (SO owner GO)

**Owner autoriza custo fal-ai ($0.04/img).** Skill roda pipeline padrao **sem** push pra Shopee.

Usar a CLI canonica de produto individual. Primeiro, preview local:

```bash
node .claude/skills/lp-regen-image/commands/regen-image.mjs \
  --store-product-id <SP_ID> \
  --dry-run
```

Depois do primeiro GO, executar sem `--dry-run`, usando `INTERNAL_API_SECRET` no ambiente e a `base-url` correta. Nao colocar o segredo na conversa ou no report.

**Comportamento pos-regen:**
- Nova imagem: baixar via curl pra `/tmp/regen-{ticketBugId}-{shortRunId}.jpg`
- Ler via `view_image`/equivalente
- Comparar visual com fornecedor
- Reportar ao owner:
  - "GO push pra Shopee" → seguir Passo 5
  - "Tentar 2a seed" → repetir Passo 4 (novo regen)
  - "Editar prompt" → out-of-scope skill (owner ajusta prompt template)

**Importante:** `regenerateImage` ja swap no DB (`is_active` toggle) mesmo antes do push. Se rejeitar visual, precisa rodar novo regen — o antigo NAO volta ativo automaticamente.

---

## Passo 5 — Push Shopee (SO com 2o GO owner)

Usar o runner generico, primeiro em dry-run:

```bash
pnpm exec tsx scripts/push-shopee-product-image.ts \
  --store-product-id=<SP_ID>
```

Ele mostra o `generation_run` ativo e o `shopee_item_id`. Depois de inspecionar exatamente essa imagem e receber o segundo GO:

```bash
pnpm exec tsx scripts/push-shopee-product-image.ts \
  --store-product-id=<SP_ID> \
  --generation-run-id=<RUN_ATIVO_APROVADO> \
  --confirm-store-product-id=<SP_ID> \
  --confirm-item-id=<SHOPEE_ITEM_ID> \
  --execute
```

O runner recusa um run que deixou de ser o ativo, preserva os slots 2..N e verifica o slot 1 depois do `update_item`.

Latencia total: ~15-30s por SP (Shopee media upload + update_item).

---

## Passo 6 — Template de nota interna Gleap

```
Nota interna — atendimento

O {product_title} (o do link enviado pela aluna) foi corrigido: nova foto
substituida na Shopee, agora mostra {descricao curta do produto real} corretamente
(nao mais {descricao do erro anterior}).

Link do anuncio pra confirmar: https://shopee.com.br/product/{itemId}

**O que rolou tecnicamente:** {diagnostico simplificado - ex: "o texto do fornecedor
mencionava 'altura extra' junto de 'tratorado', e a IA interpretou como salto alto.
Gerei nova imagem e saiu fiel ao produto real."}

**Sobre outros produtos:** {SE aluna mencionou "mais produtos com erro" — pedir lista}.

**Como responder:**
Confirmar que a foto do {produto} foi ajustada. {SE aluna mencionou outros: Pedir que
liste quais outros anuncios estao com foto ruim se quiser que corrijamos.}
```

Substituicoes:
- `{product_title}`, `{itemId}` — da query
- `{descricao curta produto real}`, `{descricao erro anterior}` — diagnostico visual
- Trechos opcionais dependem se aluna mencionou "mais produtos" no ticket

**Linguagem simples (regra owner 2026-07-06):** nao usar termos "generation_run", "seed", "prompt", "swap". "IA gerou imagem nova" e suficiente.

---

## Passo 7 — Transicionar TOTEST + assignee Caio

```
update_ticket({ ticketId: <objectId>, status: toTestStatusKey })
assign_ticket({ ticketId: <objectId>, processingUser: '<gleap-id>' })
```

Resolver `toTestStatusKey` no preflight e atribuir por ultimo.

Support recebe nota + confirma visualmente na Shopee → responde aluna.

---

## Edge cases

| Cenario | Comportamento |
|---|---|
| Aluna nao mandou link nem print | Tag `skill:aguardando-owner`, nota "precisa link Shopee do anuncio pra corrigir" |
| Aluna mandou print mas sem link Shopee | Tentar identificar SP por title matching no DB. Se ambiguo, aguardando-owner. |
| Print da aluna mostra imagem DIFERENTE do que esta no DB (Shopee atualizada recente) | Aluna talvez esteja vendo cache antigo. Confirmar via `get_item_base_info` + comparar image_id_list. |
| 2 links no ticket (2 SPs) | Processar sequencial, um por vez. Nota interna lista os 2 status. |
| "Temos mais produtos com erro" (aluna nao lista) | Nota interna pede lista. NAO fazer sweep automatico de todos SPs — custo fal-ai imprevisivel. |
| Aluna quer voltar pra foto do fornecedor (sem IA) | Fora de escopo. Owner decide caso a caso. |
| Regen sucessivo (3+ vezes) gera mesmo tipo de erro | Prompt precisa edicao. Escalar owner. Tag `skill:aguardando-owner` + nota diagnostica. |
| SP nao publicado (shopee_item_id=null) | Skill NAO trata. `update_item` so funciona em publicados. Dispatch pra regen wave normal (out-of-scope skill Gleap). |
| Item excluido pela Shopee (product.error_busi) | Skill NAO consegue corrigir — item nao pode ser editado. Nota "item banido Shopee, precisa apelacao aluna" + aguardando-owner. |
| Token Shopee expirado durante a verificacao | Nao inferir o estado live pelo DB e nao fazer push. Orientar reconexao da loja, manter o ticket pendente e repetir `get_item_base_info` depois da reconexao. |

---

## Recovery

`regenerateImage` swap no DB e atomico via RPC `regen_image_atomic_swap` (mig 149). Race entre 2 operadores no MESMO SP: segundo bloqueia via `pg_advisory_xact_lock`.

Se push Shopee falhar apos regen OK (rede/token/rate limit):
- Nova imagem ja esta no fal.media (URL persiste)
- DB ja marcou novo run ativo
- Re-invocar `_regen-*-push.ts` com mesma URL — safe

Se push OK mas nota Gleap falhou:
- Item live na Shopee ja atualizado
- Re-invocar `send_message` — safe (nova nota, nao substitui)

Idempotencia: rodar 2x o pipeline gera 2 novas imagens (paga 2x). Skill NUNCA re-executa Passo 4 sem novo GO owner.

---

## Limites de risco

- ❌ NUNCA regenerar sem GO owner explicito (custo fal-ai)
- ❌ NUNCA fazer push Shopee sem 2o GO owner (imagem pode continuar ruim)
- ❌ NUNCA regenerar em batch todos SPs de uma aluna sem lista explicita
- ❌ NUNCA remover slots 2..N do image_id_list (mantem 8+ slots do fornecedor intactos)
- ❌ NUNCA responder a aluna diretamente
- ❌ NUNCA usar termos tecnicos na nota ("seed", "prompt", "generation_run")

---

## Tempo estimado

- Investigacao (queries + downloads + reads): ~30s
- Regen fal-ai: ~15-20s
- Push Shopee (upload + update_item): ~5-10s
- Total por SP corrigido: ~1-2 min + 2 GOs owner

---

## Referencias

- Caso que originou: cliente de exemplo — 2026-07-06
- CLI de regeneracao: `.claude/skills/lp-regen-image/commands/regen-image.mjs`
- Runner de push Shopee: `scripts/push-shopee-product-image.ts`
- Helper de regeneracao: `shared/lib/publication/regenerateImage.ts`
- Helper server-only: `shared/lib/publication/regenerateImage.ts` (Story 16.3, RPC atomic swap mig 149)
- Fal payload: `shared/lib/falPayload.ts` — Flux Pro Kontext img2img (usa `image_url` do fornecedor)
- Shopee API: `shared/lib/shopee/products.ts:updateItem`, `shared/lib/shopee/media.ts:uploadImageByUrl`
- SKILL.md pai: `../SKILL.md`
- Task de sweep: `../tarefas/00-analise-geral.md`
- Regra KAKA-6 (screenshots): `../SKILL.md` secao "Analise de screenshots"
- Regra KAKA-7 (assignee Caio): `../SKILL.md` tabela Decisoes cravadas
