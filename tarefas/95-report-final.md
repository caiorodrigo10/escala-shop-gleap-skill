# Tarefa 95 — Report final

Cria um registro append-only de cada run da `/gleap`. O report explica o que foi observado e executado; a memoria operacional permanece em `catalog.json` e `learning/queue.json`.

## Quando executar

Ao fim de `scan`, `teach`, `apply`, `fix` ou `bug-fixed`, inclusive quando:

- nao ha tickets;
- o owner cancela depois do preview;
- uma run termina parcialmente;
- somente arquivos locais foram alterados.

Nao gerar quando o processo termina antes de qualquer leitura/classificacao e nao existe estado util. Falha de escrita do report e soft failure: imprimir o conteudo no canal atual.

## Path

`docs/gleap-runs/run-YYYY-MM-DD-HHmm.md`, usando `America/Sao_Paulo` e o horario de inicio da run.

- Nunca sobrescrever.
- Em colisao, usar `-2`, `-3`, etc.
- Criar o diretorio se necessario.
- Nunca editar ou apagar reports antigos automaticamente.

## Entrada

Aceitar campos ausentes com defaults seguros:

```text
runId, mode, invocation, startedAt, endedAt, outcome
tickets[]
classifications[]
queueChanges[]
playbookResults[]
canaryResults[]
knowledgeChanges[]
fixChanges[]
githubIssueCandidates[]
ownerCorrections[]
externalWrites[]
warnings[]
failures[]
toolsUsed[]
```

Cada classificacao deve preservar:

- ticket/bug ID;
- categoria primaria e secundarias;
- estado da categoria (`draft`, `validated`, `active`, `deprecated`);
- confianca do match;
- evidencias e blockers resumidos;
- acao/resultados, quando houver.

## Metricas calculadas

Calcular sem esconder zeros:

- `totalTickets`;
- `knownCount`: primaria `active` com match high e gates completos;
- `candidateCount`: draft/validated/blocked/medium/low;
- `unknownCount`;
- `coverageRate = knownCount / totalTickets * 100`;
- `unknownRate = unknownCount / totalTickets * 100`;
- fila criada, atualizada e reaberta;
- drafts criados;
- canarios executados, bem-sucedidos e falhos;
- categorias promovidas/deprecadas;
- correcoes do owner/falsos positivos;
- sucesso, skip e falha por playbook;
- FIXes criados, ligados, implantados, verificados e fechados;
- issues GitHub de FIX vinculadas, candidatas prontas e aguardando esclarecimento;
- writes externos tentados e confirmados.

Quando `totalTickets=0`, taxas sao `0%`, nao `NaN`.

## Template canonico

```markdown
# Run Gleap — Escala Shop — {timestamp BRT}

**Run ID:** `{runId}`
**Modo:** `{mode}`
**Resultado:** `{success|partial|cancelled|failed}`
**Duracao:** `{mm:ss}`
**Invocacao:** `{invocation}`

## Resumo

| Metrica | Valor |
|---|---:|
| Tickets analisados | {totalTickets} |
| Conhecidos e executaveis | {knownCount} |
| Candidatos/bloqueados | {candidateCount} |
| Desconhecidos | {unknownCount} |
| Cobertura do catalogo | {coverageRate}% |
| Unknown rate | {unknownRate}% |
| Writes externos confirmados | {externalWritesConfirmed} |
| Warnings | {warningsCount} |
| Falhas | {failuresCount} |

## Classificacao

| Ticket | Primaria | Secundarias | Estado | Match | Evidencia/blocker | Resultado |
|---|---|---|---|---|---|---|
| #{bugId} | {primary} | {secondary} | {knowledgeStatus} | {confidence} | {summary} | {result} |

## Aprendizado

| Metrica | Valor |
|---|---:|
| Itens novos na fila | {queueCreated} |
| Itens atualizados | {queueUpdated} |
| Itens reabertos | {queueReopened} |
| Drafts criados | {draftsCreated} |
| Canarios sucesso/falha | {canarySuccess}/{canaryFailure} |
| Promovidos para active | {promotions} |
| Correcoes do owner | {ownerCorrections} |

### Mudancas de conhecimento
- `{artifact}`: `{before} -> {after}` — {reason}

## Execucao de playbooks

| Categoria | Ticket | Writes | Verificacao | Resultado |
|---|---|---|---|---|
| {slug} | #{bugId} | {summary} | {verification} | {ok|skipped|error} |

## FIXes
- **{BUG-id}** — estado `{before} -> {after}` — {tickets} — `{documentPath}`

## Issues GitHub de FIX
- **{BUG-id ou ticketIds}** — `{linked|prepared|needs-clarification}` — prioridade `{P0|P1|P2|pending}` — {issueUrl ou motivo/perguntas}

## Writes externos
- {system} — {operation} — {target} — {confirmed|failed|not-authorized}

## Warnings e falhas
- WARNING: {message}
- FAILURE: {step} — {message}

## Proximos passos
- {teach, canary, promote, apply, investigar ou implementar FIX}

## Metadata tecnico
- Catalog version: `{skillVersion}`
- Tools/capacidades: {toolsUsed}
- Inicio/fim: {startedAt} / {endedAt}
- External write mode: {none|owner-approved}

---
*Gerado pela skill `/gleap`; report append-only.*
```

Omitir tabelas vazias somente quando substituir por uma frase explicita como `Nenhum write externo foi realizado.`

## Regras por modo

### `scan`

- Declarar: `Nenhuma escrita externa foi executada.`
- Informar separadamente que report e fila local podem ter sido atualizados.
- Nao listar hipoteses como playbooks criados.
- Para cada FIX de codigo confirmado, registrar a issue GitHub vinculada ou o candidato preparado; nunca declarar candidato como issue criada.
- Todos os totais, taxas e tabelas sao exclusivamente de tickets `BUG`; `BOT` e excluido antes do calculo e nao pode aparecer como ticket analisado, candidato ou desconhecido.

### `teach`

- Mostrar mudancas em fila, catalogo e tarefas.
- Distinguir draft, canario e promocao.
- Se houve canario, registrar o GO, writes e verificacao sem expor segredo.

### `apply`

- Reportar somente writes realmente confirmados.
- Acao apenas proposta fica `not-authorized` ou `skipped`, nunca `ok`.
- Preservar falha parcial por ticket.

### `fix`

- Mostrar slug, estado, documento, backlog e tickets vinculados/pendentes.
- Mostrar issue GitHub vinculada ou preview pendente, prioridade e motivo; escrita nao autorizada fica `not-authorized`.
- Um FIX local criado sem write Gleap continua sendo sucesso local.

### `bug-fixed`

- Mostrar estado de deploy/verificacao, opcao escolhida pelo owner e resultado de cada ticket.
- Nao declarar `closed` se ficou em `TOTEST` aguardando validacao; usar `verified` ou `deployed` conforme evidencia.

## Privacidade

Nao gravar:

- CPF/documentos;
- senha temporaria;
- tokens, secrets ou chaves;
- payload integral de compra/conector;
- email/telefone quando o bug ID basta para auditoria.

IDs tecnicos de ticket, loja, anuncio, commit e transacao podem aparecer apenas quando necessarios para reproduzir/auditar.

## Verificacoes antes de escrever

- contagens fecham com as linhas do report;
- `known + candidate + unknown = total`, considerando cada ticket uma unica vez pelo estado primario;
- writes propostos nao aparecem como confirmados;
- categorias secundarias nao aumentam `totalTickets`;
- paths citados existem ou estao marcados como pendentes;
- nenhuma informacao sensivel esta presente.

## Output

Retornar:

```json
{
  "reportPath": "docs/gleap-runs/run-YYYY-MM-DD-HHmm.md",
  "status": "ok|partial|failed",
  "metrics": {
    "coverageRate": 0,
    "unknownRate": 0,
    "queueCreated": 0,
    "promotions": 0
  },
  "warnings": []
}
```
