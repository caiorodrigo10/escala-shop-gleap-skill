# Tarefa 01 — Acesso Nao Provisionado

Automatiza o procedimento de provisionar acesso Loja Pronta Fase 0 pra alunas cujo ticket Gleap pede "Liberacao do site da loja", usando o helper reutilizavel `provisionLpAccess`.

---

## Quando executar

Carrega quando `tarefas/00-analise-geral.md` classifica um ticket como `categoria:acesso-nao-provisionado` durante o sweep. Regex de deteccao (title):

```
/liberar\s*acesso|liberacao\s*(do\s*)?site\s*da\s*loja/i
```

Fallback desc: mesmo padrao aplicado a `ticket.description` se title nao bateu.

Tambem pode ser invocada direto:

```bash
/gleap --category=acesso-nao-provisionado --ticket-id=X
```

Antes da cascata Hotmart, avaliar `acesso-solicitado-pelo-support`. Quando o
ticket foi criado manualmente por Support e pede explicitamente Loja Pronta, a
solicitacao do Support substitui a compra como fonte de autorizacao; seguir
`tarefas/12-acesso-solicitado-pelo-support.md`. Nao rotear como
`nao-e-aluna-lp` apenas porque a compra nao foi localizada.

Nesse caso pula sweep (`00-*.md`) e carrega esta tarefa isoladamente pro ticket X.

---

## Pre-requisitos (HARD GATES)

1. Preflight da skill passou (Gleap MCP + Supabase + owner ID + `contexto/lp-arquitetura.md` carregado) — ver `SKILL.md`
2. Ticket alvo tem `type=BUG` e `status=OPEN`
3. Contato Gleap tem `session.email` OU `session.phone` — se ambos vazios, skip pra owner ask direto (Passo 2d)
4. Helper KAKA-1 disponivel: `shared/lib/lojapronta/provision/provision-lp-access.ts` (server-only)

Se qualquer gate falhar: tag `skill:aguardando-owner`, nota interna com motivo, ticket segue OPEN. Nao provisiona.

---

## Modos de execucao

| Modo | Comportamento |
|---|---|
| `scan` / `--dry-run` (default) | Mostra preview de provisao + updates Gleap. NAO chama helper. NAO escreve no Gleap. |
| `--apply` | Executa provisao real via `provisionLpAccess` + updates Gleap MCP. |

A tarefa suporta investigacao em `scan` e execucao real somente em `apply`, depois do preview e GO explicito do owner.

Restricao: mesmo com `--apply`, a senha temporaria vem da constante `LOJA_PRONTA_DEFAULT_TEMPORARY_PASSWORD` em `shared/lib/auth/temporary-password.ts`; nunca a registre no ticket ou report. Magic link NUNCA e enviado sem uma aprovacao separada e explicita. A comunicacao prevista aqui ocorre somente pelo GHL Workflow 1 do helper.

---

## Passo 1 — Transicionar OPEN → INPROGRESS

Skill sinaliza que comecou a processar o ticket.

**MCP call:**
```
update_ticket({ ticketId: <objectId>, status: inProgressStatusKey })
```

`inProgressStatusKey` deve ser a key da lane In progress resolvida no preflight; atualmente e `INPROGRESS`. Escritas usam o ObjectId de 24 caracteres retornado por `get_ticket`.

Se falhar: abort tarefa pra este ticket, tag `skill:aguardando-owner`, log erro.

Modo dry-run: registrar no preview mas nao chamar `update_ticket`.

---

## Passo 2 — Identificar aluna (cascade)

Ordem sequencial. Para no primeiro passo que produz match valido.

### 2a. Extrair contato do ticket

Skill obtem via MCP Gleap (`get_ticket(ticketId)`):
- `contact.email` (session.email)
- `contact.phone` (session.phone) — normalizar E.164 se possivel (`+55XXXXXXXXXXX`)
- `contact.name` (session.name)

Fallback: regex email/phone no `title + description` do ticket se `contact.*` vazio.

### 2b. Passo 1 — Match por email em `hotmart_purchases`

Executa via MCP Supabase (`execute_sql` project `<supabase-project-ref>`):

```sql
SELECT transaction_id, buyer_email, buyer_phone, buyer_name,
       product_id, status, approved_at, created_at,
       user_id, store_id
FROM hotmart_purchases
WHERE lower(buyer_email) = lower($1)
  AND product_id IN (<IDs derivados de HOTMART_PRODUCT_IDS_LP ou do fallback em shared/lib/hotmart/product-gates.ts>)
  AND status IN ('complete', 'approved')
  AND refund_effectivated_at IS NULL
  AND chargeback_at IS NULL
ORDER BY approved_at DESC
LIMIT 1;
```

Interpretacao:
- **Match >= 1 row:** cascade encerra aqui. Tag `skill:match-email`. Provisiona **sem GO owner adicional** (email match = confianca alta).
- **0 rows:** segue pra Passo 2c.

Se query retorna row mas `product_id` **nao** esta em IDs LP: rota `nao-e-aluna-lp` (Passo 2e).

### 2c. Passo 2 — Fallback por telefone

So executa se Passo 2b retornou 0 rows E `contact.phone` presente:

```sql
SELECT transaction_id, buyer_email, buyer_phone, buyer_name,
       product_id, status, approved_at, created_at,
       user_id, store_id
FROM hotmart_purchases
WHERE buyer_phone = $1
  AND product_id IN (<IDs LP>)
  AND status IN ('complete', 'approved')
  AND refund_effectivated_at IS NULL
  AND chargeback_at IS NULL
ORDER BY approved_at DESC
LIMIT 1;
```

Interpretacao:
- **Match >= 1 row:** tag `skill:match-phone`. **Skill PEDE confirmacao owner per-ticket** antes de provisionar (email divergente entre Gleap contact vs Hotmart buyer_email = possivel troca de contato, precisa validacao humana).
- **0 rows:** segue pra Passo 2d.

### 2d. Passo 3 — Owner ask (sem match)

Skill imprime dados do ticket e pergunta:

```
Ticket #{bugId} — {title}
  Contato Gleap: {email} / {phone}
  Cascade: email lookup 0 rows, phone lookup 0 rows

Quer criar acesso mesmo assim usando o email do Gleap?
  [1] SIM — provisiona com email={email} e transactionId sintetico
      (opcao arriscada: sem confirmar compra Hotmart)
  [2] NAO — tag skill:nao-e-aluna-lp + route Support
  [3] Pular por agora — tag skill:tbd (carry-forward)
```

Se owner escolhe [1]: skill precisa de um `transactionId` valido. Como nao ha `hotmart_purchases` correspondente:
- Skill pergunta owner: *"Voce tem o transaction_id da Hotmart? (se nao, digite `skip`)"*
- Se owner fornece: usa esse valor.
- Se `skip`: tag `skill:aguardando-owner` + nota interna pedindo owner buscar transaction na Hotmart Sales API antes de rerodar (helper KAKA-1 exige `transactionId` valido no input — ver `provision-lp-access.ts` linhas 176-190).

Se owner escolhe [2] ou [3]: aplicar routing correspondente e encerrar tarefa pra este ticket.

> **Exceção Reclame Aqui / reversão / chargeback (política owner 2026-07-30):** se o
> contexto do ticket é reversão de reembolso, Reclame Aqui ou chargeback (não é MSL no
> lugar errado), NÃO parkear em Support por "sem compra". A política é provisionar
> **standalone** (cria loja no email do Gleap, sem `transactionId`) — carregar
> `tarefas/06-refund-reclame-chargeback.md` e seguir o fluxo de lá (GO owner → grant
> standalone → LP Fase 1). Precedente: cliente de exemplo.

### 2e. Route `nao-e-aluna-lp`

Aplicado quando cascade encontrou row mas `product_id` NAO esta em IDs LP (ex: aluna MSL abriu ticket no lugar errado):

**MCP calls:**
```
add_ticket_tags({ ticketId: <objectId>, tags: ['skill:nao-e-aluna-lp', 'skill:analisado'] })
send_message({ ticketId: <objectId>, text: '[interno] [skill:gleap] Cross-check LP falhou. buyer_email={email} tem compra Hotmart mas product_id={pid} nao esta na lista LP. Provavelmente MSL ou outro produto. Route para Support identificar o produto correto.', isNote: true })
assign_ticket({ ticketId: <objectId>, processingTeam: '<gleap-id>' })
```

Skill NAO provisiona. Ticket segue INPROGRESS assigned a Support (nao volta pra OPEN — skill ja executou parte da analise; Support continua daqui).

Encerra tarefa pra este ticket.

---

## Passo 3 — Cutoff 2026-05-19 (flag informacional)

Se cascade produziu match (Passo 2b ou 2c) e `hotmart_purchases.approved_at < '2026-05-19T00:00:00-03:00'` (BRT):
- Skill NAO bloqueia. Mantem a provisao no preview; executa somente depois do GO aplicavel ao ticket e as acoes apresentadas.
- Sinaliza no preview: `[cutoff pre-2026-05-19: compra anterior ao pipeline automatico — outra equipe deveria ter entregue manual]`
- Nota interna do Passo 6 registra o flag pra rastreabilidade

Se `approved_at >= 2026-05-19`: sem flag adicional, provisiona.

---

## Passo 4 — Preparar `rawPayload` (se necessario)

Helper KAKA-1 (`provisionLpAccess`) exige `rawPayload` **somente se** `hotmart_purchases` ainda nao existe pra esse `transactionId` (linha 222-226 do helper). No fluxo normal esta tarefa, cascade Passo 2 ja confirmou que existe (senao teria caido em owner ask).

Estrategia:
1. Se `hotmart_purchases` existe (99% dos casos KAKA-3): passa `rawPayload=undefined`, helper pula RPC `apply_purchase_event`.
2. Se cascade caiu em owner ask [1] com `transactionId` fornecido mas SEM row em `hotmart_purchases`: skill precisa buscar `raw_payload`:

```sql
SELECT raw_payload
FROM hotmart_webhook_log
WHERE hotmart_transaction_id = $1
  AND event IN ('PURCHASE_APPROVED', 'PURCHASE_COMPLETE')
ORDER BY created_at DESC
LIMIT 1;
```

Se retorna row: passa `raw_payload` como `rawPayload` (helper valida shape via `HotmartRawPayload`).
Se nao retorna: skill imprime `raw_payload_ausente` e pede ao owner que recupere a transacao/payload por uma fonte autorizada antes de tentar novamente. Nao improvise um script de grant. Ticket segue OPEN com tag `skill:aguardando-owner` somente depois do GO de escrita.

---

## Passo 5 — Provisionar via helper KAKA-1

**Import canonical:**
```typescript
import { provisionLpAccess } from '@/shared/lib/lojapronta/provision/provision-lp-access'
```

**Chamada:**
```typescript
const result = await provisionLpAccess({
  email: contact.email,                       // do Gleap session.email
  transactionId: purchase.transaction_id,     // do cascade Passo 2
  displayName: contact.name ?? purchase.buyer_name,
  rawPayload: undefined,                      // Passo 4 decidiu
  opts: {
    skipGhlDispatch: false,                   // dispara GHL Workflow 1 (LP_FASE_1)
    skipApplyPurchaseEvent: false,
  }
})
// result: { email, transactionId, userId, storeId, alreadyExists, error? }
```

**Comportamento esperado:**
- Sucesso normal: `result.alreadyExists=false`, helper criou user+profile+store+journey + disparou `maybeEmitLpFase1` (GHL envia email pra aluna com senha `<senha-temporaria-configurada>`).
- Idempotencia: `result.alreadyExists=true` significa que TUDO ja existia antes. Skill NAO re-provisiona. Segue pro Passo 6 com nota "Acesso ja existia — nenhuma provisao necessaria."
- Exception: helper lanca `ProvisionError` com `step` identificando onde falhou. Skill captura, NAO progride pra TOTEST — ver Passo 7 (tratamento de falha).

Nota GHL: se `lp_workflow_fase_1_enabled=false` em `lp_settings`, helper NAO dispara mesmo com `skipGhlDispatch: false` (dual gate DB+opts). Registrar isso na nota interna do Passo 6 se detectado (query `lp_settings` opcional pra confirmar).

Modo dry-run: NAO chama `provisionLpAccess`. Preview mostra os parametros que passaria.

---

## Passo 6 — Acao Gleap pos-provisao (sucesso)

Sequencia estrita:

### 6a. Aplicar tags

```
add_ticket_tags({
  ticketId: <objectId>,
  tags: [
    'categoria:acesso-nao-provisionado',
    'skill:analisado',
    'skill:match-email' ou 'skill:match-phone' ou 'skill:owner-forced'
  ]
})
```

Convencao: skill NUNCA sobrescreve tags humanas. So adiciona via `add_ticket_tags`. Ver `SKILL.md`.

### 6b. Nota interna

**Formato canonical:**
```
[interno] [skill:gleap] Provisionamento concluido.

Aluna: {email}
Transaction: {transaction_id}
User ID: {userId}
Store ID: {storeId}
Store name: {store.name ou '(sem nome — briefing pendente)'}
GHL Workflow 1: disparado (helper interno)
Cutoff pre-2026-05-19: {sim/nao}
Cascade: {email|phone|owner-forced}
Already existed: {sim/nao}
```

Variante quando `alreadyExists=true`:
```
[interno] [skill:gleap] Acesso ja existia. Nenhuma acao de provisionamento necessaria.

Aluna: {email}
User ID: {userId}  (ja existente)
Store ID: {storeId}  (ja existente)
GHL Workflow 1: nao disparado (nao ha novo usuario — helper pula por design)
Cutoff pre-2026-05-19: {sim/nao}
```

**MCP call:**
```
send_message({ ticketId: <objectId>, text: <texto acima>, isNote: true })
```

O prefixo `[interno]` permanece como defesa adicional. Depois da chamada, releia o ticket quando a resposta da ferramenta nao confirmar `type: "NOTE"`; se houver divergencia, pare as mensagens restantes e registre o incidente.

### 6c. Transicionar INPROGRESS → TOTEST

```
update_ticket({ ticketId: <objectId>, status: toTestStatusKey })
assign_ticket({ ticketId: <objectId>, processingTeam: '<gleap-id>' })
```

As chamadas sao sempre separadas e a atribuicao vem por ultimo. `toTestStatusKey` e resolvida no preflight; atualmente e `TOTEST`. Releia o ticket e confirme status/time como pos-condicao.

---

## Passo 7 — Tratamento de falha (provisao)

Se `provisionLpAccess` lancou exception (`ProvisionError` com step):

### 7a. NAO avancar status

Ticket **permanece em INPROGRESS** (nao volta pra OPEN — skill ja moveu). Nao vai pra TOTEST.

### 7b. Aplicar tags

```
add_ticket_tags({
  ticketId: <objectId>,
  tags: ['categoria:acesso-nao-provisionado', 'skill:analisado', 'skill:aguardando-owner', 'skill:falha-provisao']
})
```

### 7c. Nota interna com erro

```
[interno] [skill:gleap] FALHA no provisionamento.

Aluna: {email}
Transaction: {transactionId}
Step que falhou: {error.step}
Erro: {error.message}

Cascade: {email|phone|owner-forced}
Cutoff pre-2026-05-19: {sim/nao}

Acao necessaria: owner investigar e reintentar manual ou rerodar `/gleap apply --category=acesso-nao-provisionado --ticket-id={id}`.
```

**MCP:**
```
send_message({ ticketId: <objectId>, text: <acima>, isNote: true })
```

Ticket fica assinado ao owner (nao passa pra Support), pra Caio decidir proximo passo.

Modo dry-run: nem chega aqui (helper nao foi chamado).

---

## Preview esperado (dry-run e apply)

Formato exato do output por ticket processado:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎫 Ticket #{bugId} — "{title}"
   Aluna: {email} ({name})
   Contato: {phone}

   🔍 Cascade:
     [Passo 2b] Email lookup em hotmart_purchases LP: {✅ HP1234... product 7243982 approved 2026-06-15 / ❌ 0 rows}
     [Passo 2c] Phone lookup: {✅ HP1234... / ❌ 0 rows / [skip — email ja bateu]}
     [Passo 2d] Owner ask: {sim / nao / [skip — cascade encerrou]}

   {Se match confirmado:}
   📦 Provisao planejada:
     Transaction: HP1234...
     Produto: {product_id} ({7243982=LP P2 R$697})
     Aprovada em: 2026-06-15T14:32:00-03:00
     Cutoff pre-2026-05-19: nao
     rawPayload necessario: nao (hotmart_purchases ja existe)

   🔄 Acoes Gleap planejadas:
     Status: OPEN → INPROGRESS → TOTEST
     Tags: +categoria:acesso-nao-provisionado, +skill:analisado, +skill:match-email
     Assignee TOTEST: 💪 Support team (<gleap-id>)
     Nota interna: [preview do texto do 6b]

   {Se dry-run:}
   🚦 [DRY-RUN] Nenhuma acao executada. Nem helper nem Gleap MCP tocados.

   {Se apply e sucesso:}
   ✅ Aplicado.
      userId = <uuid>
      storeId = <uuid>
      alreadyExists = false
      GHL Workflow 1 disparado.
      Gleap: INPROGRESS → TOTEST + Support assignee + nota interna postada.

   {Se apply e falha:}
   ❌ Falha no provisionamento.
      Step: apply_purchase_event
      Erro: rawPayload buyer email mismatch: "cliente@exemplo.com" != "outro@exemplo.com"
      Ticket permanece INPROGRESS + tag skill:falha-provisao + nota interna com erro.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Batch mode (multiplos tickets)

Quando `00-*.md` agrupa N tickets `categoria:acesso-nao-provisionado` e owner deu GO em batch:

Skill agrupa por cascade result:
- **Todos match-email:** helper batch `provisionLpAccessBatch(items)` — sequencial internamente (helper linha 499), evita rate limit `auth.admin`
- **Match-phone:** pergunta owner **1x por ticket** (nao batch — cada um pode ser aluna diferente com contato divergente)
- **Sem match (owner ask):** pergunta owner **1x por ticket**

Report final agregado por `runs/*.md` (KAKA-5, ainda pendente). Em KAKA-3, skill imprime resumo `N ok / N skipped / N failed` no fim do batch usando `result.summary`.

---

## Output pro report (dados agregados)

Retornar por ticket ao chamador (`00-*.md` ou report KAKA-5):

```
{
  ticketId: '<bugId>',
  status: 'ok' | 'skipped' | 'error' | 'nao-e-aluna-lp' | 'dry-run',
  action: 'provisioned' | 'already-existed' | 'route-support' | 'owner-ask',
  transactionId: '<HP...>' | null,
  userId: '<uuid>' | null,
  storeId: '<uuid>' | null,
  cascadeResult: 'match-email' | 'match-phone' | 'owner-forced' | 'no-match',
  cutoffFlag: boolean,
  errorStep: string | null,
  errorMessage: string | null,
}
```

---

## Edge cases

| Cenario | Comportamento |
|---|---|
| Email duplicado no ticket Gleap (contact tem 2 emails) | Usa `session.email` primario. Registra ambos na nota interna pra auditoria. |
| Aluna com `refund_effectivated_at` ou `chargeback_at` populados | Query WHERE ja filtra — nao aparece no cascade. Cai em Passo 2d (owner ask). |
| `hotmart_purchases.status='refunded'` mas `refund_effectivated_at IS NULL` | Query WHERE filtra por status IN ('complete','approved') — nao aparece. Rota owner ask. |
| Aluna ja provisionada (`alreadyExists=true`) | Skill NAO re-provisiona. Ainda aplica tags + TOTEST + Support assignee + nota "Acesso ja existia." |
| `session.email` do Gleap difere do `buyer_email` no Hotmart | Skill flagga na nota interna. Se cascade foi por phone (Passo 2c), pede confirmacao owner antes. Se por email direto (Passo 2b), esse cenario nao ocorre por design. |
| Sem `raw_payload` em `hotmart_webhook_log` (owner ask [1] com transactionId novo) | Helper KAKA-1 lanca `apply_purchase_event` error. Ticket tag `skill:falha-provisao` + owner buscar Hotmart Sales API. |
| `product_id` retornado nao esta na lista LP | Rota `nao-e-aluna-lp` (Passo 2e). Support decide destino. |
| `lp_workflow_fase_1_enabled=false` em `lp_settings` | Helper NAO dispara GHL. Skill registra na nota: `"GHL Workflow 1 NAO disparado (lp_workflow_fase_1_enabled=false em lp_settings)"`. Provisao ainda ocorre — aluna precisara ser notificada manual. |
| Owner passou `--apply` mas preflight falhou depois | Nunca deveria acontecer (preflight roda antes). Se acontecer: abort tarefa, ticket segue OPEN + tag `skill:aguardando-owner`. |
| MCP Gleap timeout no `update_ticket` do Passo 1 | Skill abort tarefa pra este ticket. Ticket **nao foi movido** (OPEN mantido). Log warn. Owner retry manual. |
| MCP Gleap timeout no `send_message` (nota interna Passo 6b) | Provisao ja ocorreu (nao rollback). Skill loga warn e tenta 1 retry. Se falhar de novo: registrar em report final + owner posta nota manual. |
| Ticket ja tem tag humana `categoria:X` conflitante | Skill ADICIONA sua tag (nao remove) + registra warn no preview. Convencao SKILL.md. |
| Owner passou `--dry-run --apply` (contradicao) | Prioriza `--dry-run` (mais seguro). Warn no preview. |

---

## Recovery

Idempotente:
- Re-rodar `/gleap apply --category=acesso-nao-provisionado --ticket-id=X` na mesma aluna: helper retorna `alreadyExists=true`, skill segue pra Passo 6 (tags + TOTEST + nota "ja existia").
- Se batch parcial falhou (N tickets processados, M nao): tickets pendentes ficam OPEN + tag `skill:tbd`. Proxima run pega.
- O estado transacional de uma execucao interrompida nao e presumido entre runs. Catalogo e fila persistem o conhecimento; idempotencia do helper e `add_ticket_tags` cobrem re-execucao. Antes de retry de qualquer write, releia o ticket.

---

## Observability (apply mode)

Eventos previstos (implementacao real fica em KAKA-3 quando helper for chamado):
- `lp_gleap.acesso_provisao_started` — { ticketId, cascadeResult }
- `lp_gleap.acesso_provisao_completed` — { ticketId, userId, storeId, alreadyExists, cutoffFlag }
- `lp_gleap.acesso_provisao_failed` — { ticketId, step, errorMessage }
- `lp_gleap.acesso_route_nao_lp` — { ticketId, productId }

Log tambem via `shared/lib/log` no proprio helper KAKA-1 (`provision_lp_*` events ja emitidos).

Modo dry-run: nenhum evento emitido.

---

## Limites de risco

- ❌ **Nunca** enviar mensagem publica pra aluna via Gleap (`isNote:false` explicito). Skill so posta nota interna.
- ❌ **Nunca** enviar magic link. Aluna recebe senha padrao (`<senha-temporaria-configurada>`) via GHL Workflow 1 (helper interno).
- ❌ **Nunca** provisionar sem `transactionId` valido. Owner ask [1] sem transactionId = skip.
- ❌ **Nunca** mover ticket pra DONE. Skill so vai ate TOTEST — Support ou owner finalizam.
- ❌ **Nunca** sobrescrever tags humanas. So `add_ticket_tags`.
- ❌ **Nunca** re-provisionar se `alreadyExists=true`. Helper garante idempotencia; skill respeita.
- ❌ **Nunca** provisionar aluna com `product_id` fora de LP. Rota `nao-e-aluna-lp`.

---

## Tempo estimado

Por ticket em apply mode:
- Cascade Passo 2b + 2c: ~500ms (2 queries Supabase MCP)
- `provisionLpAccess` helper: ~2-4s (Supabase auth + inserts + GHL dispatch)
- 3 MCP Gleap calls (update_ticket status, send_message, update_ticket TOTEST): ~1-2s
- **Total: ~4-7s por ticket**

Batch de 10 tickets com match-email: ~40-70s (helper sequencial pra evitar rate limit `auth.admin`).

---

## Referencias

- SKILL.md pai: `../SKILL.md`
- Tarefa sweep (dispatcher): `../tarefas/00-analise-geral.md`
- Contexto LP: `../contexto/lp-arquitetura.md`
- Contrato de ferramentas: `../references/tool-contract.md`
- Helper de provisao: `/projects/escala-shop/shared/lib/lojapronta/provision/provision-lp-access.ts`
- IDs Hotmart LP: `/projects/escala-shop/shared/lib/hotmart/product-gates.ts`
