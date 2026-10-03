# Tarefa 02 — Produtos "repetidos" que sao variantes SKU do fornecedor

Esta tarefa trata produtos distintos que parecem repetidos. Se a queixa for que
cores ou tamanhos não aparecem em um anúncio, não aplique este playbook: use o
precedente de variações ausentes em
`../references/known-case-solutions.md` e mantenha o caso como investigação até
confirmar a grade ao vivo na Shopee.

Automatiza a resposta pra tickets onde a aluna reclama "produtos duplicados / iguais / repetidos" na Wave da loja, quando na verdade sao SKUs distintos do mesmo modelo base (cores/lavagens/composicoes diferentes) que o fornecedor cataloga separadamente.

Este NAO e bug do sistema. E o padrao de venda do fornecedor. A skill responde com contexto pro atendimento explicar pra aluna.

Referencia canonical:
- Casos que deram origem: cliente de exemplo + cliente de exemplo (2026-07-06)
- Fornecedor recorrente: **Herbron Confeccoes LTDA** — cataloga cada cor de vestido, cada lavagem de calca, cada combinacao de kit como `external_id` distinto

---

## Quando executar

Carrega quando `tarefas/00-analise-geral.md` classifica um ticket como `categoria:produtos-variantes-fornecedor` durante o sweep.

Regex de deteccao (title/desc):

```
/produtos?\s*(iguais|repetid[oa]s|duplicad[oa]s|mesm[oa]s)|produto[s]?\s*sao\s*iguais|(\d+)\s*produtos?\s*(iguais|repetid[oa]s)|3\s*(iguais|repetid[oa]s)/i
```

Tambem pode ser invocada direto:

```bash
/gleap --category=produtos-variantes-fornecedor --ticket-id=X
```

---

## Pre-requisitos (HARD GATES)

1. Preflight da skill passou (Gleap MCP + Supabase + owner ID + `contexto/lp-arquitetura.md` carregado)
2. Ticket alvo tem `type=BUG` e `status=OPEN` (ou `INPROGRESS`, se owner ja moveu manualmente)
3. Contato Gleap tem `session.companyId` (store_id) — se vazio, tag `skill:aguardando-owner`
4. **Screenshot obrigatorio (KAKA-6):** se `screenshotUrl` presente, baixar + ler antes de decidir

---

## Modos de execucao

| Modo | Comportamento |
|---|---|
| `scan` / `--dry-run` (default) | Query DB + preview da nota. NAO escreve no Gleap. |
| `--apply` | Query DB + envia nota interna + move status pra TOTEST + assigna Caio. |

---

## Passo 1 — Query dos produtos da store

Obter todos os `store_products` publicados/gerados da loja e cruzar com o fornecedor. Foco no wave que a aluna cita (Wave 1 na maioria dos casos).

```sql
SELECT
  sp.id AS sp_id,
  sp.wave_number,
  sp.shopee_item_id,
  sp.final_title,
  p.title AS product_title,
  p.external_id AS supplier_sku,
  p.supplier_id,
  s.name AS supplier_name
FROM store_products sp
LEFT JOIN products p ON p.id = sp.product_id
LEFT JOIN suppliers s ON s.id = p.supplier_id
WHERE sp.store_id = $STORE_ID
ORDER BY sp.wave_number, sp.id;
```

Registrar no preview:
- Total de SPs por Wave
- Total de `supplier_sku` distintos (se == total SPs → confirma variantes distintas)
- Nome do fornecedor (identifica Herbron)

---

## Passo 2 — Decisao (variante fornecedor vs bug real)

### 2a. Confirmar variantes distintas

Se **todos os `external_id` sao distintos** entre os SPs reclamados → NAO e bug. Skill segue pra Passo 3 (nota + TOTEST).

Sinal forte adicional: `product_title` compartilha o modelo base (ex: "Vestido Midi Com Manga e Fendas Laterais") variando so o sufixo cor/lavagem.

### 2b. Bug real (`external_id` duplicado)

Se **dois ou mais SPs tem o MESMO `external_id`** → EH bug real. Dispatch pra `tarefas/97-fix.md` como novo FIX ou linkar em bug existente. Skill NAO move status.

### 2c. Screenshot mostra outro problema (KAKA-6)

Se screenshot revelou queixa alem de "produtos repetidos" (ex: pedido de refund, insatisfacao ampla) → skill NAO trata como categoria isolada. Tag `skill:aguardando-owner`, nota interna listando o que apareceu no print, aguarda owner categorizar (regra da KAKA-6, ticket de exemplo case).

---

## Passo 3 — Template de nota interna

Nota interna EM LINGUAGEM SIMPLES pro atendente (regra do owner 2026-07-06: nao usar termos tecnicos como "SKU", "external_id", "backfill" — Support nao entende ingles tecnico).

Template canonico:

```
Nota interna — atendimento

Nao sao produtos repetidos. Aqui vai o contexto pra explicar pra aluna:

Os {N} produtos da Wave {W} dela sao:
1. {product_title 1}
2. {product_title 2}
...
{N}. {product_title N}

O fornecedor ({supplier_name}) trata cada {cor/lavagem/combinacao} como um
produto separado no catalogo — cada um tem codigo proprio, imagem propria,
estoque proprio. Por isso aparecem como anuncios distintos na loja da aluna,
mesmo quando o modelo base e parecido.

Isso NAO e bug de duplicacao. E o padrao de venda desse fornecedor.

Como responder:
Explicar que sao produtos diferentes ({cor/lavagem/kit} distintas), cada um
com estoque separado no fornecedor. Se a aluna quiser trocar algum, pode
substituir por outro produto no ajuste de catalogo depois. Nao precisa refazer
publicacao.
```

Substituicoes:
- `{N}`: quantidade de SPs
- `{W}`: numero da wave (geralmente 1)
- `{cor/lavagem/combinacao}`: pegar do sufixo do `product_title` ou `external_id`. Se produtos sao vestidos/calcas com cores → "cor" ou "lavagem". Se sao kits com 3 pecas → "combinacao de cores no kit".
- `{supplier_name}`: nome do fornecedor. Herbron eh o mais comum, mas skill nao hardcoda.

**Idioma:** PT-BR. Sem asteriscos markdown alem dos titulos (`**`) que Support ja renderiza.

**MCP call:**

```
send_message({ ticketId: <objectId>, isNote: true, text: <nota renderizada> })
```

Manter o prefixo `Nota interna — atendimento` no corpo e confirmar `type: "NOTE"` na resposta ou em uma releitura antes de continuar o lote.

---

## Passo 4 — Transicionar pra TOTEST + assignee Caio

```
update_ticket({ ticketId: <objectId>, status: toTestStatusKey })
assign_ticket({ ticketId: <objectId>, processingUser: '<gleap-id>' })
```

Resolver `toTestStatusKey` no preflight. A atribuicao ao Caio e uma chamada separada e vem por ultimo; o time atual permanece inalterado.

---

## Edge cases

| Cenario | Comportamento |
|---|---|
| Aluna reclama de 2 SPs mas ha 3+ com mesmo external_id → bug real | Dispatch `97-fix.md` (nao aplicar template desta task) |
| Screenshot revelou refund pedido | Tag `skill:aguardando-owner` + nota lista o que apareceu no print (KAKA-6 rule) |
| Store nao tem produto no Supabase (aluna publicou por fora?) | Tag `skill:aguardando-owner`, nota "store_id nao tem SPs — verificar" |
| Fornecedor NAO e Herbron mas padrao bate | Aplicar template normalmente — regra vale pra qualquer fornecedor multi-variante |
| Aluna quer TROCAR produto (nao so entender) | Template ja cobre no ultimo paragrafo. Support da instrucao no ajuste de catalogo |
| Ticket ja em INPROGRESS | Skill segue direto pro Passo 3 (skip Passo 1 transicao) |
| Ticket ja em TOTEST | Skip skill — owner ja moveu manualmente |

---

## Recovery

Idempotente: `send_message` cria nova nota (nao substitui), `update_ticket` re-aplicar status TOTEST no mesmo ticket nao muda nada. Owner pode re-invocar `--ticket-id=X` sem side effects.

Se `execute_sql` falhar (Supabase indisponivel): tag `skill:aguardando-owner` + nota "Falha ao consultar produtos da store — Supabase MCP indisponivel", ticket segue OPEN. Skill NAO chuta a resposta.

---

## Limites de risco

- ❌ NUNCA responder a aluna diretamente (`isNote:false`)
- ❌ NUNCA aplicar template se `external_id` duplicado detectado (isso e bug real, precisa fix)
- ❌ NUNCA usar termos tecnicos na nota ("SKU", "external_id", "wave_batch_run") — Support nao entende
- ❌ NUNCA mover pra DONE (Support decide encerrar apos responder aluna)

---

## Tempo estimado

Query + template + updates Gleap: ~5-10s por ticket.

---

## Referencias

- Casos que originaram: cliente de exemplo + cliente de exemplo (2026-07-06)
- Fornecedor recorrente: Herbron Confeccoes LTDA (mas regra vale pra qualquer multi-variante)
- SKILL.md pai: `../SKILL.md`
- Task de sweep: `../tarefas/00-analise-geral.md`
- Regra KAKA-6 (screenshots): `../SKILL.md` secao "Analise de screenshots"
- Regra KAKA-7 (assignee Caio): `../SKILL.md` tabela Decisoes cravadas
