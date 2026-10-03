# Contexto LP — referencia rapida para a skill Gleap

Resumo operacional versionado que a skill carrega no preflight. As fontes de verdade continuam sendo o codigo e o banco consultado ao vivo; quando houver divergencia, pare antes de escrever e reporte-a.

---

## Supabase project

- **Project ref:** `<supabase-project-ref>`
- **Region:** sa-east-1
- **MCP tool/capacidade:** `execute_sql` (queries); `apply_migration` nao e usado pela skill operacional

---

## Tabelas-chave e colunas relevantes

### `auth.users` (schema `auth`)

Colunas usadas pela skill:

| Coluna | Uso |
|---|---|
| `id` (uuid) | Referencia em profiles.user_id, stores.owner_user_id |
| `email` (text) | Match case-insensitive com ticket Gleap sender |
| `raw_user_meta_data` (jsonb) | display_name, phone eventualmente |
| `created_at` | Idade da conta |

### `profiles`

| Coluna | Tipo | Uso |
|---|---|---|
| `user_id` | uuid PK | FK auth.users.id |
| `role` | enum | `aluna` = LP; `support`, `fornecedor`, `admin` fora do escopo Gleap |
| `must_change_password` | boolean | true = senha temporaria ativa |
| `temporary_password_set_at` | timestamptz | quando helper KAKA-1 setou |
| `hotmart_transaction_id` | text | Fallback quando aluna nao tem store ainda |
| `display_name` | text | Nome usado em UI + mensagens GHL |

### `stores`

| Coluna | Tipo | Uso |
|---|---|---|
| `id` | uuid PK | Referenciada em journey_state, store_products, phase_unlocks |
| `owner_user_id` | uuid | FK auth.users.id |
| `hotmart_transaction_id` | text | Vinculo canonical com Hotmart |
| `name` | text | Nome da loja |
| `niche_slug` | text | Default `DEFAULT_EMPTY_NICHE` quando helper KAKA-1 provisiona |
| `logo_url` | text | Populada pelo briefing fal.ai |

### `journey_state`

| Coluna | Tipo | Uso |
|---|---|---|
| `store_id` | uuid PK | FK stores.id |
| `current_phase` | enum JourneyPhase | Ver secao Phases abaixo |
| `shopee_kyc_status` | text | `not_started`, `pending`, `approved`, `rejected` |
| `shopee_oauth_completed_at` | timestamptz | Requisito pra publicar |
| `phase_before_abandonment` | JourneyPhase | Resolucao pra transient states |
| `wave_1_published_at` / `wave_2_published_at` / `wave_3_published_at` | timestamptz | Marcos de publicacao |

### `hotmart_purchases`

| Coluna | Tipo | Uso |
|---|---|---|
| `id` | uuid PK | — |
| `hotmart_transaction_id` | text | Vinculo canonical |
| `buyer_email` | text | Match ticket Gleap sender (lowercase compare) |
| `buyer_phone` | text | Match phone normalizado |
| `product_id` | text | IDs LP definidos por `HOTMART_PRODUCT_IDS_LP`, com fallback em `shared/lib/hotmart/product-gates.ts` |
| `status` | enum | `complete`, `approved` = LP ativo; `refunded`, `chargeback` = nao |
| `user_id` / `store_id` | uuid | Nulls ate helper KAKA-1 vincular |
| `source` | enum | `webhook`, `backfill_api` |

### `hotmart_webhook_log`

Fonte do `raw_payload` que o helper KAKA-1 exige pra chamar `apply_purchase_event`.

| Coluna | Uso |
|---|---|
| `hotmart_transaction_id` | Match com ticket |
| `event` | `PURCHASE_APPROVED`, `PURCHASE_COMPLETE` = valido pra provisao |
| `raw_payload` (jsonb) | Passado direto ao helper KAKA-1 via `rawPayload` |

---

## Queries canonicas

### Achar aluna por email

```sql
SELECT au.id, au.email, p.role, s.id AS store_id, s.name,
       js.current_phase, js.shopee_kyc_status
FROM auth.users au
LEFT JOIN profiles p ON p.user_id = au.id
LEFT JOIN stores s ON s.owner_user_id = au.id
LEFT JOIN journey_state js ON js.store_id = s.id
WHERE lower(au.email) = lower($1);
```

### Achar compra Hotmart por email OR telefone (produto LP)

```sql
SELECT * FROM hotmart_purchases
WHERE (lower(buyer_email) = lower($1) OR buyer_phone = $2)
  AND product_id IN ('7243352', '7243982', '4072309', '5398362', '7745766', '6102550')
  AND status IN ('complete', 'approved');
-- Antes de executar, derive a lista vigente de HOTMART_PRODUCT_IDS_LP ou do
-- fallback LP_PRODUCT_IDS_DEFAULT em shared/lib/hotmart/product-gates.ts.
```

### Detectar duplicados de produtos numa store

```sql
SELECT sp.final_title, COUNT(*) AS duplicates
FROM store_products sp
WHERE sp.store_id = $1
GROUP BY sp.final_title
HAVING COUNT(*) > 1;
```

---

## Phases da jornada Loja Pronta

Enum `JourneyPhase` canonico em `/projects/escala-shop/shared/lib/lojapronta/phase-routes.ts`.

Mapeamento resumido (ver `shared/lib/lojapronta/phase-lock.ts:PHASE_TO_BOUNDARY` pra tabela completa):

| Fase | Phases | Boundary |
|---|---|---|
| FASE 0 | `pos_compra` | FASE_1 |
| FASE 1 (chat) | `1.1_perfil`, `1.2_briefing_logo`, `1.3_video_pri` | FASE_1 |
| FASE 2 preview | `2.1_aguardando_assets` | FASE_1 (holding) |
| FASE 2 real | `2.2_assets_entregues`, `2.3_logo_selecionado`, `2.4_descricao_selecionada`, `pendente_shopee_kyc`, `2.5_shopee_conectada`, `2.6_browsing_catalogo`, `2.7_produtos_iniciais_selecionados` | FASE_2 |
| FASE 3 | `3.1_aguardando_publicacao`, `3.1.1_logo_publicada_shopee`, `3.1.2_descricao_publicada_shopee`, `3.1.3_endereco_atualizado_shopee`, `aguardando_aprovacao_imagens`, `3.2_publicando_wave_1`, `3.3_loja_publicada`, `wave_2_pending`, `wave_2_published`, `wave_3_pending`, `wave_3_published` | FASE_2 |
| Terminais | `finalizada`, `refunded` | FASE_2 |
| Transientes | `abandonada`, `reativada` | FASE_1 (resolucao via `phase_before_abandonment`) |

Phase inicial pos-provisao (helper KAKA-1): **`pos_compra`**.

O trigger de auto-promote da migracao 120 move FASE_1 → FASE_2 quando a phase entra no bucket FASE_2. Confirme a migracao e o estado atual antes de depender desse comportamento.

---

## IDs Hotmart LP

**Fallback versionado atual** (para a query canonica):
```
'7243352', '7243982', '4072309', '5398362', '7745766', '6102550'
```

**IMPORTANTE:** multiplos IDs coexistem. Antes de filtrar, leia `HOTMART_PRODUCT_IDS_LP` no ambiente autorizado; se ela estiver ausente ou vazia, use o fallback de `shared/lib/hotmart/product-gates.ts`. Nunca assuma um unico ID nem mantenha uma lista paralela sem conferir a fonte.

Produto principal: **P2 Loja Pronta R$697** (curso LP). P1 = MSL R$297 (fora de escopo skill).

---

## Sistema de provisao (KAKA-1)

**Helper canonico:** `/projects/escala-shop/shared/lib/lojapronta/provision/provision-lp-access.ts`

Assinatura:
```typescript
import { provisionLpAccess } from '@/shared/lib/lojapronta/provision/provision-lp-access'

const result = await provisionLpAccess({
  email: 'cliente@exemplo.com',
  transactionId: 'HP2993188696',
  displayName: 'Nome da Aluna',
  rawPayload: <hotmart_webhook_log.raw_payload>, // opcional se hotmart_purchases ja existe
  opts: {
    skipGhlDispatch: false,        // default false — dispara LP_FASE_1
    skipApplyPurchaseEvent: false, // default false
  }
})
// → { email, transactionId, userId, storeId, alreadyExists, error? }
```

Fluxo interno:
1. RPC `apply_purchase_event` (se `rawPayload` presente + skip false)
2. `auth.admin.createUser` (skip se ja existe)
3. Insert `profiles` (role=aluna, must_change_password=true, temporary_password_set_at=now)
4. Insert `stores` (niche_slug=DEFAULT_EMPTY_NICHE)
5. Insert `journey_state` (current_phase='pos_compra')
6. Link `hotmart_purchases.user_id/store_id`
7. Chamar `maybeEmitLpFase1({ storeId, transactionId })` (skippable)

Idempotencia total: rodar 2x mesmo input NAO duplica nada.

**Batch:** `provisionLpAccessBatch(items: Array<Input>)` retorna `{ results, summary }`.

---

## GHL LP_FASE_1 dispatch

**Helper canonico:** `/projects/escala-shop/shared/lib/lojapronta/lp-workflows/maybe-emit-fase-1.ts`

Chamado internamente por `provisionLpAccess` (a menos que `opts.skipGhlDispatch=true`).

Nao invocar diretamente da skill — sempre passar por `provisionLpAccess`.

O historico indica modo automatico ativo desde 2026-06-16. Isso nao e garantia de estado atual: confira as flags relevantes em `lp_settings` antes de uma provisao real.

---

## Constantes-chave

| Constante | Valor | Origem |
|---|---|---|
| `LOJA_PRONTA_DEFAULT_TEMPORARY_PASSWORD` | `'<senha-temporaria-configurada>'` | `shared/lib/auth/temporary-password.ts` |
| `DEFAULT_EMPTY_NICHE` | (import `shared/lib/onboarding/niches`) | Niche placeholder pra provisao inicial |
| `PIPELINE_CUTOFF_ISO` | `2026-05-19` (BRT) | Compras anteriores foram entregues manual |

---

## Cutoff manual delivery — 2026-05-19 BRT

**Regra operacional versionada:** compras Hotmart aprovadas **antes** de 2026-05-19 BRT foram entregues manualmente pelo owner e nao passaram pelo pipeline automatico atual.

**Implicacao pra skill:**
- Ticket Gleap pedindo acesso e compra `< 2026-05-19` → provavelmente foi entregue manual, mas se aluna abriu ticket = algo furou. **Provisionar mesmo assim** via helper KAKA-1 (idempotente — se ja existe, `alreadyExists=true` e nao duplica).
- Flag no output do preview: `[cutoff pre-2026-05-19]` como aviso pro owner.

---

## Fontes versionadas obrigatorias

| Fonte | Uso |
|---|---|
| `shared/lib/hotmart/product-gates.ts` | Gate e fallback vigente dos IDs Hotmart LP |
| `skills-shared/gleap/references/tool-contract.md` | Contrato atual de Gleap/Supabase, status, ObjectIds e notas internas |
| `shared/lib/lojapronta/provision/provision-lp-access.ts` | Implementacao de provisao e idempotencia |
| `shared/lib/lojapronta/lp-workflows/maybe-emit-fase-1.ts` | Disparo do workflow LP Fase 1 |
| `shared/lib/lojapronta/phase-routes.ts` | Enum e rotas das fases |
| `supabase/migrations/` | Estado versionado de triggers, constraints e funcoes SQL |
