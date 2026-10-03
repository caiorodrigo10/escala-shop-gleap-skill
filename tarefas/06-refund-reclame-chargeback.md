# Tarefa 06 — Refund / Reclame Aqui / Chargeback (liberação de acesso)

Trata tickets de **reversão de reembolso, Reclame Aqui e chargeback** onde a aluna
pede "liberar o site da loja" mas **NÃO existe compra Hotmart LP no histórico** (nem
conta no banco).

> **Política cravada (owner Caio, 2026-07-30):** nesses casos, a **ausência de compra
> no histórico Hotmart NÃO significa não fazer nada**. Cria-se a loja em cima do email
> do ticket e libera-se o acesso (provisão standalone, sem base Hotmart). O contexto
> Reclame Aqui / reversão é justamente o de alguém que reverteu o refund / está
> retirando a reclamação — é aluna legítima, entra na esteira normal.

Isto **sobrepõe** a rota genérica `nao-e-aluna-lp` (que só parkeia em Support) e o
Passo 2d de `01-acesso-nao-provisionado.md` (que exige `transactionId`). Aqui NÃO se
exige `transactionId` — usa-se o pattern de grant standalone.

Caso de referência: **cliente de exemplo** (`cliente@exemplo.com`) — 2026-07-30.

---

## Quando executar

Carrega quando o ticket bate categoria `refund-reclame-chargeback`:
- Tags humanas `Reversão de Reembolso` / `Reclame Aqui` / `Acompanhamento` no ticket
- Título/desc com `/reclame\s*aqui|revers[ãa]o\s*(de\s*)?(reembolso|refund)|chargeback|liberar?\s*(o\s*)?site.*(loja)?/i`
- Ou landing vindo de `nao-e-aluna-lp` **quando o contexto é reversão/Reclame Aqui/chargeback** (não é MSL-no-lugar-errado)

Manual: `/gleap --category=refund-reclame-chargeback --ticket-id=X`

---

## Pré-requisitos (HARD GATES)

1. Preflight da skill passou (Gleap MCP + Supabase + owner ID + `contexto/lp-arquitetura.md`)
2. Ticket `type=BUG`, status `IN ('OPEN','INPROGRESS','TOTEST')`
3. **Análise de screenshots obrigatória (KAKA-6)** — se há `screenshotUrl`/attachments, baixar + Read antes de decidir
4. **GO owner explícito** — categoria sensível; skill NUNCA provisiona aqui sem aprovação per-ticket do owner (é write em prod + dispara comunicação GHL à aluna)

---

## Passo 1 — Confirmar estado no banco

```sql
-- Existe conta/loja com o email do ticket?
SELECT u.id AS user_id, u.email, s.id AS store_id
FROM auth.users u
LEFT JOIN stores s ON s.owner_user_id = u.id
WHERE lower(u.email) = lower($1);   -- email do Gleap

-- Existe compra Hotmart (qualquer status) sob esse email?
SELECT transaction_id, product_id, status, buyer_email, buyer_name
FROM hotmart_purchases
WHERE lower(buyer_email) = lower($1);
```

Interpretação:
- **Já existe conta** → NÃO reprovisiona. Vira caso de reset/investigação (rota reset-senha ou nota interna). Encerra.
- **Compra LP ativa existe** → não é este fluxo; usar `01-acesso-nao-provisionado.md` (cascade normal).
- **Sem conta + sem compra LP** (ou só MSL / só refund) → segue Passo 2 (provisão standalone com GO owner).

---

## Passo 2 — Owner GO

Skill imprime e pergunta:

```
Ticket #{bugId} — {title}
  Contato Gleap: {email} / {name}
  Banco: sem conta, sem compra LP no histórico Hotmart
  Contexto: Reclame Aqui / reversão de reembolso / chargeback

Política: criar a loja em cima do email do ticket e liberar acesso (standalone, sem Hotmart)?
  [1] SIM — provisiona standalone + dispara LP Fase 1
  [2] NÃO — tag skill:aguardando-owner + nota interna (decisão manual)
  [3] Pular por agora — tag skill:tbd (carry-forward)
```

Só `[1]` dispara o Passo 3.

---

## Passo 3 — Provisão standalone (`--apply`)

Usa o runner generico `scripts/grant-lp-standalone.ts` (NÃO `provisionLpAccess`, que exige `transactionId` e pode chamar `apply_purchase_event`).

1. Dry-run obrigatorio:
   ```bash
   pnpm exec tsx scripts/grant-lp-standalone.ts \
     --email='<email-do-ticket>' \
     --display-name='<nome-do-contato>' \
     --reason='Reclame Aqui/reversao — ticket <id>'
   ```
2. Apresentar o alvo e as acoes; aguardar GO per-ticket.
3. Apply com confirmacoes redundantes:
   ```bash
   pnpm exec tsx scripts/grant-lp-standalone.ts \
     --email='<email-do-ticket>' \
     --display-name='<nome-do-contato>' \
     --reason='Reclame Aqui/reversao — ticket <id>' \
     --approval-ticket=<ObjectId-ou-bugId> \
     --confirm-email='<email-do-ticket>' \
     --owner-approved \
     --execute
   ```
4. O runner:
   - `auth.admin.createUser` (email_confirm=true, senha `<senha-temporaria-configurada>`, `must_change_password=true`)
   - INSERT `profiles` role=aluna
   - INSERT `stores` (name='', niche default) → `hotmart_transaction_id = NULL`
   - UPDATE `journey_state` → `pos_compra` (guard `WHERE current_phase='1.1_perfil'`)
   - `emitLpWorkflowDispatch(LP_FASE_1)` — boas-vindas GHL
5. **Confirmar via SQL** que user/store/journey/outbox existem antes de fechar.

Gotchas do pattern standalone:
- PostHog flush pode dar 401 — fire-and-forget, ignorar.
- Trigger bootstrap cria journey em `1.1_perfil` — o UPDATE pra `pos_compra` é idempotente.
- Falha antes de concluir o core dispara rollback apenas dos IDs criados naquela execucao; falha do GHL depois do core preserva a conta e retorna status parcial.

---

## Passo 4 — Fechar no Gleap

> **IMPORTANTE:** endpoints de escrita do Gleap MCP (`update_ticket`, `add_ticket_tags`,
> `send_message`) exigem o **ObjectId** do ticket (`ticket.id`, ex `6a610ed5...`), **não**
> o `bugId` numérico. Passar o número dá 400 (`Invalid ID format`) ou 403.

```
send_message({
  ticketId: <objectId>,
  isNote: true,
  text: '[interno] Acesso liberado. Owner autorizou criar a loja no email do ticket mesmo sem compra Hotmart (Reclame Aqui / reversao). Fase pos-compra criada e LP Fase 1 disparada. Follow-up: acompanhar a reversao separadamente. Nao incluir senha ou token nesta nota.'
})
add_ticket_tags({
  ticketId: <objectId>,
  tags: ['categoria:refund-reclame-chargeback', 'skill:analisado', 'skill:acesso-liberado']
})
update_ticket({ ticketId: <objectId>, status: toTestStatusKey })
assign_ticket({
  ticketId: <objectId>,
  processingTeam: '<gleap-id>',
  processingUser: '<gleap-id>'
})
```

Resolver `toTestStatusKey` no preflight e manter a atribuicao por ultimo.

Move pra **TOTEST** (Support monitora chegada da aluna + acompanha a reversão do
Reclame Aqui à parte). NÃO mover pra DONE autonomamente.

---

## NÃO fazer

- ❌ Provisionar sem GO owner per-ticket (categoria sensível)
- ❌ Enviar mensagem à aluna via Gleap (só nota interna) — comunicação é via GHL LP Fase 1
- ❌ Exigir `transactionId` (é standalone — o pattern bypassa isso de propósito)
- ❌ Reprovisionar se já existe conta com o email
- ❌ Passar `bugId` numérico nos endpoints de escrita do Gleap MCP (usar `ticket.id`)
