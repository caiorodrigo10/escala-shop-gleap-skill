# Tarefa 04 — Refunded Cleanup

Automatiza o encerramento de tickets de alunas que **ja pediram refund**. Ticket geralmente foi aberto ANTES do refund; owner NAO responde mais (aluna nao esta mais na plataforma); skill fecha ticket + deleta produtos publicados na Shopee.

Motivacao: sem cleanup, tickets ficam eternos em OPEN/INPROGRESS + produtos ficam vivos na Shopee vinculados a shop_id que a aluna nem tem acesso.

Referencia canonical:
- Casos que originaram (2026-07-06): Soraia (bug#XXXX) + Marina (bug#XXXX)

---

## Quando executar

Carrega quando ticket carrega tag ou signal de refund:
- Skill detecta `session.customData.has_refund = true` no Gleap → categoria `refunded-cleanup`
- Owner passa manual: `/gleap --category=refunded-cleanup --ticket-id=X`

Regex fallback (title/desc) — sinal fraco, usar so pra flag no preview:

```
/refund|reembols[oa]|estornad[oa]|cancelad[oa]/i
```

**Importante:** deteccao PRIMARIA e a flag `has_refund` no customData do Gleap (populada pelo webhook Hotmart). Regex e fallback pra tickets com contexto textual claro.

---

## Pre-requisitos (HARD GATES)

1. Preflight da skill passou (Gleap MCP + Supabase + owner ID + `contexto/lp-arquitetura.md` carregado)
2. Ticket alvo tem `type=BUG` e `status IN ('OPEN','INPROGRESS','TOTEST')`
3. Contato Gleap tem `session.companyId` (store_id) OU `session.email`
4. **Confirmacao dupla via `hotmart_purchases`:** query DB pra confirmar refund efetivo (`refund_effectivated_at IS NOT NULL` OR `chargeback_at IS NOT NULL`). Skill NAO confia so na flag `has_refund` do Gleap — pode estar dessincronizado.

---

## Modos de execucao

| Modo | Comportamento |
|---|---|
| `scan` / `--dry-run` (default) | Query DB + preview. NAO deleta nada da Shopee. NAO altera Gleap. |
| `--apply` | Query DB + delete Shopee items + nota interna Gleap + move status pra DONE + assigna Caio. **ACAO DESTRUTIVA — deletes definitivos na Shopee.** |

**Restricao critica:** modo `--apply` requer GO owner explicito no preview antes da acao. Skill nunca deleta produtos Shopee autonomamente.

Exceção observada (`ticket de exemplo`): se o owner determinar explicitamente que, naquele
ticket, não precisa excluir anúncios, limite a execução ao encerramento aprovado
no Gleap. Não rode o cleanup Shopee e não generalize a decisão para outros
refunds. Ver `../references/known-case-solutions.md`.

---

## Passo 1 — Confirmar refund efetivo via Supabase

```sql
SELECT
  transaction_id,
  buyer_email,
  product_id,
  status,
  approved_at,
  refund_requested_at,
  refund_effectivated_at,
  chargeback_at
FROM hotmart_purchases
WHERE (lower(buyer_email) = lower($TICKET_EMAIL) OR buyer_phone = $TICKET_PHONE)
  AND product_id IN (<IDs derivados de HOTMART_PRODUCT_IDS_LP ou do fallback em shared/lib/hotmart/product-gates.ts>)
ORDER BY approved_at DESC;
```

**Interpretacao:**

| Estado | Acao |
|---|---|
| `refund_effectivated_at IS NOT NULL` | Refund confirmado → segue Passo 2 |
| `chargeback_at IS NOT NULL` | Chargeback confirmado → segue Passo 2 (tratar como refund) |
| So `refund_requested_at` sem effectivated | Refund pediu mas ainda nao efetivou → tag `skill:aguardando-owner`, NAO deleta |
| Nada → aluna nao refundou | Skill classificou errado — dispatch pra fluxo normal |

---

## Passo 2 — Timeline: ticket antes ou depois do refund?

Comparar `ticket.createdAt` com `refund_effectivated_at`:

- **Ticket ANTES do refund:** aluna abriu quando estava ativa, entao pediu refund depois. Owner NAO responde mais. Skill fecha DONE.
- **Ticket DEPOIS do refund:** raro — aluna volta pedindo algo pos-refund. Skill NAO fecha; tag `skill:aguardando-owner` — owner decide.

Registrar no preview.

---

## Passo 3 — Listar produtos Shopee publicados

```sql
SELECT
  sp.id AS sp_id,
  sp.wave_number,
  sp.shopee_item_id,
  sp.final_title,
  sp.publish_status
FROM store_products sp
WHERE sp.store_id = $STORE_ID
  AND sp.shopee_item_id IS NOT NULL
ORDER BY sp.wave_number, sp.id;
```

Registrar no preview: quantos SPs, quais Waves, quais shopee_item_ids.

**Se nenhum `shopee_item_id`:** aluna nao publicou nada na Shopee — pular Passo 4 (nada a deletar).

---

## Passo 4 — Delete Shopee items (SO em `--apply` + GO owner)

Usar o runner generico, que repete a validacao de refund no banco e opera em dry-run por padrao:

```bash
pnpm exec tsx scripts/delete-shopee-items-refunded.ts --store-id=<uuid>
```

Depois do preview e de um GO explicito para a store e a lista mostradas:

```bash
pnpm exec tsx scripts/delete-shopee-items-refunded.ts \
  --store-id=<uuid> \
  --all-items \
  --confirm-store-id=<mesmo-uuid> \
  --confirm-count=<N-do-preview> \
  --confirm-refund=REFUND_CONFIRMED \
  --execute
```

O script usa `POST /api/v2/product/delete_item`, verifica cada resultado e recusa executar se houver compra LP ativa na mesma store. A acao continua irreversivel.

**Se aluna refundou mas produtos ainda ativos:** skill exibe lista + espera GO owner. NAO executa auto.

Para escopo parcial, troque `--all-items` por um ou mais `--item-id=<id>` e ajuste `--confirm-count`.

---

## Passo 5 — Template de nota interna Gleap

```
Nota interna — atendimento

Aluna refundou a compra da Loja Pronta em {refund_effectivated_at}.

Timeline do ticket:
- Ticket aberto em: {ticket.createdAt}
- Refund efetivado em: {refund_effectivated_at}
- Ticket foi criado {ANTES/DEPOIS} do refund

Acao tomada:
{Ticket antes do refund}: Encerrando o ticket. Aluna nao esta mais na plataforma
e nao vai responder. Produtos publicados na Shopee ({N} items) foram deletados
via API pra nao ficarem vivos vinculados a uma loja sem dona.

{Ticket depois do refund}: Nao encerrei automatico — precisa decisao do Caio
porque aluna reabriu contato pos-refund.

Como responder:
{Ticket antes}: sem resposta pra aluna. Pode marcar Done.
{Ticket depois}: aguardar Caio orientar.
```

Substituicoes: skill preenche marcadores baseado no fluxo (antes/depois).

---

## Passo 6 — Transicionar status + assignee Caio

### 6a. Ticket antes do refund + delete Shopee OK

```
update_ticket({ ticketId: <objectId>, status: doneStatusKey })
assign_ticket({ ticketId: <objectId>, processingUser: '<gleap-id>' })
```

### 6b. Ticket depois do refund

```
update_ticket({ ticketId: <objectId>, status: inProgressStatusKey })
assign_ticket({ ticketId: <objectId>, processingUser: '<gleap-id>' })
```

Fica INPROGRESS com Caio pra decisao.

### 6c. Refund solicitado mas nao efetivado

```
update_ticket({ ticketId: <objectId>, status: inProgressStatusKey })
assign_ticket({ ticketId: <objectId>, processingUser: '<gleap-id>' })
```

Resolver todas as status keys no preflight e manter `assign_ticket` por ultimo.

Tag `skill:aguardando-owner` — Support ou skill re-checa depois.

---

## Edge cases

| Cenario | Comportamento |
|---|---|
| Aluna refundou mas volta como cliente novo (nova compra) | Skill trata como caso separado — nao aplica cleanup. Ticket seguem fluxo normal por categoria |
| Refund parcial (produto extra devolvido, mas LP ativa) | Skill NAO deleta shopee. Tag `skill:aguardando-owner`. Refund parcial e edge case raro |
| Ticket com screenshot de recibo Hotmart refund | Confirma pattern — segue fluxo normal Passo 1-6 |
| Store sem `shop_id` Shopee (aluna nao conectou) | Passo 4 vazio (nada a deletar). So fecha ticket DONE. |
| Shopee API retorna erro "item nao existe" no delete | Idempotente — significa que ja foi deletado antes. Registrar warn `[already_deleted]` e prosseguir. |
| Multiplas compras da aluna (LP + P1 MSL) | Filtrar so LP no query (product_id IN IDs LP) |

---

## Recovery

Delete Shopee eh **DESTRUTIVO E IRREVERSIVEL** na Shopee. Se skill errou o alvo:
- Aluna NAO tem como recuperar produtos (Shopee nao restaura delete)
- Owner precisa republicar via wave runner (skill `lp-orchestrate`)

Por isso GO owner e OBRIGATORIO no preview antes de qualquer delete.

Se `send_message` falhar mas delete Shopee ja rodou: skill loga warn, ticket segue OPEN, owner re-invoca `--ticket-id=X` pra terminar update Gleap. Delete nao repete (idempotente).

---

## Limites de risco

- ❌ NUNCA deletar Shopee items sem GO owner explicito no preview
- ❌ NUNCA marcar DONE se ticket foi criado DEPOIS do refund efetivado
- ❌ NUNCA responder a aluna diretamente (aluna nao esta mais na plataforma)
- ❌ NUNCA rodar em modo `--dry-run` com script de delete (mesmo dry-run nao chama script)
- ❌ NUNCA assumir refund confirmado so pelo flag Gleap — sempre confirmar via `hotmart_purchases`

---

## Tempo estimado

Query + delete Shopee (~2-3s por item) + updates Gleap: **~30-90s por ticket** dependendo de quantos SPs deletar.

---

## Referencias

- Casos que originaram (2026-07-06): Soraia + Marina
- Runner seguro: `scripts/delete-shopee-items-refunded.ts`
- SKILL.md pai: `../SKILL.md`
- Task de sweep: `../tarefas/00-analise-geral.md`
- Regra KAKA-6 (screenshots): `../SKILL.md` secao "Analise de screenshots"
- Regra KAKA-7 (assignee Caio): `../SKILL.md` tabela Decisoes cravadas
- IDs Hotmart LP: `/projects/escala-shop/shared/lib/hotmart/product-gates.ts`
