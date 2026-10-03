---
name: gleap
description: Triage, resolve, teach, and track Escala Shop Gleap BUG tickets using connected Gleap and Supabase capabilities, visual evidence, versioned playbooks, and owner-approved writes. Use for explicit Gleap scans, ticket operations, learning new support procedures, or tracking product fixes; never send autonomous customer messages.
---

# Gleap — Escala Shop

Triar tickets `BUG`, executar procedimentos conhecidos com seguranca e transformar casos desconhecidos em conhecimento versionado. A skill separa observacao, ensino, execucao e FIX para nunca converter uma hipotese em automacao de lote.

Escopo de tickets: toda analise, scan, metrica, classificacao, fila de aprendizado, prioridade, aging, SLA, cobertura e proposta de acao considera exclusivamente tickets `BUG`. Tickets `BOT` e `INQUIRY` sao sempre excluidos na origem da consulta e nunca aparecem, nem como contexto separado.

## Resultado esperado

- Casos conhecidos usam somente playbooks `active` do catalogo.
- Casos desconhecidos entram numa fila local persistente com evidencias e perguntas em aberto.
- Procedimentos novos passam por `draft -> validated -> active`.
- Defeitos de codigo, banco, integracao ou infraestrutura viram FIX rastreavel e intake na skill `github-issue-escalashop`; excecoes comerciais nao viram automacao por engano.
- Toda escrita externa tem preview exato e GO do owner no contexto atual.

Regra do owner para acesso: um ticket `BUG` criado manualmente por um membro
autenticado do Support e que pede explicitamente acesso ao SLL ou a Loja Pronta
e a fonte de autorizacao do entitlement. A ausencia de compra Hotmart nao
invalida essa solicitacao. Identidade e produto continuam obrigatorios, e os
writes externos continuam sujeitos a preview e GO.

Excecao estreita: depois de `shopee-listing-replacement` ser promovido a
`active`, uma `replacement_policy` vigente pode representar a aprovacao
persistente do owner para reposicoes daquele fornecedor. Essa excecao nao vale
durante `draft`/`validated`, nao dispensa preview auditavel, nao autoriza outro
playbook e nunca autoriza mensagem publica ou transicao para `Done`.

Para reposicao Shopee, `SELLER_DELETE` nunca e elegivel sozinho. Ele so pode
compor o fato do caso quando o ticket e `BUG` da cliente reclamando da remocao,
o alvo e o unico `SELLER_DELETE` confirmado ao vivo na loja e existe GO explicito
do owner. Esse caminho nao alimenta taxa adversa nem quarentena. Toda reposicao
usa o mesmo contrato de titulo, descricao e imagem da publicacao por wave,
conforme `tarefas/11-repor-anuncio-shopee.md`.

## Modos

| Invocacao | Modo | Escrita permitida |
|---|---|---|
| `/gleap`, `/gleap scan`, `/gleap --dry-run` | `scan` | Somente report e fila locais; nenhuma escrita em Gleap, Supabase, Shopee ou GHL |
| `/gleap --ticket-id=X` | `scan` de um ticket | Igual ao `scan` |
| `/gleap teach` | ensino | Arquivos canonicos locais da skill; nenhuma escrita externa |
| `/gleap teach --validate={slug} --ticket-id=X` | canario | Um unico ticket, somente depois de preview e GO explicito |
| `/gleap apply [--ticket-id=X] [--category=slug]` | execucao | Playbooks `active`, depois de preview e GO; sequencial |
| `/gleap fix [--ticket-id=X]` | intake de FIX | Backlog/documento local e proposta para GitHub Issue; toda escrita externa exige preview e GO separado |
| `/gleap bug-fixed BUG-... [--commit=sha]` | encerramento de FIX | Tickets ligados ao bug, depois de preview e GO |

`--dry-run` e alias legado de `scan`. Nao existe GO implicito. A frase do owner precisa autorizar o lote mostrado, e uma autorizacao anterior nao vale para uma nova run.

## Fonte canonica compartilhada

- Fonte editavel desta distribuição: raiz do repositório.
- Copie ou crie um link simbólico para esta pasta no diretório de skills do seu agente.
- Mantenha uma fonte única para evitar divergência entre agentes.
- Depois de alterar catálogo, fila, tarefa ou playbook, valide o conhecimento:

```bash
node commands/validate-knowledge.mjs
```

Configure caminhos e conectores conforme o ambiente em que a skill for instalada.

## Carregamento progressivo obrigatorio

1. Sempre carregar `references/tool-contract.md` e `catalog.json`.
2. Validar o conhecimento com `commands/validate-knowledge.mjs` antes de `teach`, `apply` ou promocao.
3. Carregar somente a tarefa do modo atual:
   - `scan` ou `apply`: `tarefas/00-analise-geral.md`;
   - `teach`: `tarefas/96-ensinar-padrao.md` e `references/learning-contract.md`;
   - `fix` ou `bug-fixed`: `tarefas/97-fix.md`, `references/learning-contract.md`, `bugs-backlog.md` e a skill `github-issue-escalashop`;
   - invocacao legada `novo-bug`: `tarefas/99-novo-bug.md`.
4. Carregar `contexto/lp-arquitetura.md` apenas quando a decisao exigir dados da Loja Pronta.
5. Carregar o MD completo de uma categoria somente depois de match no catalogo ou selecao explicita do owner.
   - Quando houver ticket anterior, produto/anuncio recorrente ou pedido para
     reutilizar uma solucao conhecida, carregar tambem
     `references/known-case-solutions.md` e confirmar os identificadores e o
     estado atual antes de reaplicar qualquer acao.
   - Para `shopee-baniu-excluiu`, carregar tambem `tarefas/11-repor-anuncio-shopee.md`
     somente quando o status adverso estiver confirmado e existir candidato
     whitelisted. Enquanto essa categoria estiver `draft`, limitar a preview local.
6. Ao fim de uma run, carregar `tarefas/95-report-final.md`.

## Modelo de conhecimento

### Tipos

| Tipo | Quando usar | Resultado |
|---|---|---|
| `playbook` | Resolucao operacional repetivel | Tarefa versionada e matcher no catalogo |
| `fix` | Defeito de codigo, banco, integracao ou infraestrutura que exige mudanca de produto | `BUG-*`, documento de FIX e issue pai no GitHub Project |
| `policy` | Excecao ou decisao comercial do owner | Registro da decisao; nunca automatizar como regra geral |
| `investigation` | Evidencia insuficiente ou causa ainda incerta | Perguntas e proximos probes na fila |
| `support` | Trabalho humano conhecido que nao vale automatizar | Rota segura para o time correto |

### Estados do catalogo

- `draft`: descrito, ainda nao testado; nunca executar externamente.
- `validated`: um canario real funcionou; pode ser repetido individualmente com GO, nunca em lote.
- `active`: aprovado para uso recorrente; ainda exige preview e GO para writes.
- `deprecated`: nao usar; manter historico e motivo.

O contrato completo de captura, canario, promocao e deprecacao esta em `references/learning-contract.md`.

## Classificacao

`catalog.json` e a unica fonte do roteamento. Nao duplicar regex no dispatcher ou no `SKILL.md`.

Para cada ticket:

1. Obter detalhe, comentarios e todas as midias disponiveis.
2. Montar um pacote de evidencia com titulo, descricao, tags humanas, sessao/custom data, anexos, estado da loja, consultas externas necessarias e resultados anteriores.
3. Avaliar todos os matchers do catalogo; nao parar no primeiro.
4. Definir uma categoria primaria pela prioridade do catalogo e conservar categorias secundarias para nao perder casos multi-intencao.
5. Somente uma categoria `active` pode ser despachada em lote.
6. Match `draft` ou `validated` aparece como sugestao, nunca como certeza automatica.
7. Sem match confiavel, atualizar `learning/queue.json` por `clusterKey`, sem duplicar o item.

Heuristica ou similaridade pode sugerir um caso, mas nao promove conhecimento nem autoriza writes.

## Evidencia visual

Todo ticket com `screenshotUrl`, anexo de imagem ou midia em comentario precisa de inspecao visual antes da classificacao final.

- No Codex, baixar para `/tmp` e usar `view_image`.
- No Hermes+Composio, considerar `screenshotUrl`, `attachments[]` e `latestComment.attachments[]`.
- Se o resultado estiver em `remote_file_info`, usar o mesmo `session_id` no Workbench remoto, extrair as URLs, baixar localmente e inspecionar.
- Se a imagem continuar inacessivel, marcar `screenshot_unreadable`, deixar o caso em `investigation` e nao executar pela leitura do titulo apenas.

## Preflight proporcional ao modo

### Todos os modos

- `catalog.json` e `learning/queue.json` validos.
- Contrato de ferramentas carregado.
- Projeto alvo confirmado como **Escala Shop**.

### `scan`

- Leitura dos tickets e detalhes Gleap e obrigatoria.
- Consultar somente `type=BUG`; excluir `BOT` mesmo quando a ferramenta retornar todos os tipos por default. Nunca misturar `BOT` nos totais ou metricas da run.
- Falha do Supabase nao aborta categorias independentes do banco; registrar bloqueio por ticket.
- Tipos/status podem ser warning se nenhuma escrita for proposta.

### `apply` ou canario

- Resolver ao vivo as keys das lanes; nunca assumir `OPEN`, `INPROGRESS`, `TOTEST` ou `DONE` sem consultar o board.
- Confirmar as capacidades de escrita exatas pelo `tool-contract.md`.
- Supabase e hard gate apenas para playbooks que dependem dele.
- Confirmar owner/time somente quando houver atribuicao.
- Releitura do ticket imediatamente antes de cada write.

### `fix`

- Criar e atualizar artefatos locais mesmo se conectores externos estiverem indisponiveis, marcando evidencias pendentes.
- Nao alterar codigo como efeito colateral do intake. Implementacao exige pedido explicito e fluxo de desenvolvimento/story do repositorio.
- Ao confirmar que a correcao exige codigo, banco, integracao ou infraestrutura, carregar a skill `github-issue-escalashop` na mesma run para deduplicar, classificar prioridade e preparar ou criar a issue pai correspondente.

## Invariantes de seguranca

- Nunca enviar mensagem visivel para a aluna autonomamente.
- Nota interna exige preview do texto e GO; usar `isNote:true` e prefixo `[interno]`.
  Se o owner conceder explicitamente um GO persistente para um ciclo definido
  de `To test` + nota interna, esse GO vale para os tickets seguintes que
  satisfaçam a política apresentada. Não interromper o ciclo para repetir o
  mesmo pedido; registrar tickets, texto e evidências no report. Esse GO não
  cobre mensagem visível, `Done` ou outro tipo de write.
- Nunca enviar magic link sem GO explicito para destinatario e acao apresentados.
- Nunca remover ou sobrescrever tags humanas; usar operacao aditiva.
- Nunca mover ticket para `DONE` autonomamente.
- Atribuir em chamada separada e por ultimo.
- Acoes destrutivas, cobradas ou irreversiveis exigem um segundo GO imediatamente antes da acao.
- Um playbook `draft` ou `validated` nunca roda em lote.
- Em `scan`, nao escrever em sistemas externos. Report e fila local sao as unicas escritas.
- Em `scan`, a skill `github-issue-escalashop` pode ser carregada somente para deduplicar, classificar e preparar o payload de FIX; criar, editar ou mover issue no GitHub continua exigindo preview e GO no contexto atual.
- Nao persistir CPF, senha, token, segredo ou payload sensivel na fila, catalogo ou reports.
- Abort de lote: interromper se mais de 30% falharem preflight ou se uma premissa compartilhada mudar.

## Identificadores conhecidos

| Recurso | ID/valor |
|---|---|
| Projeto | Escala Shop; resolver ID ao vivo |
| Tipo do sweep | `BUG` |
| Owner Caio | `<gleap-id>` |
| Engineering | `<gleap-id>` |
| Support | `<gleap-id>` |
| Projeto Supabase | `<supabase-project-ref>` |

IDs de status e capacidades nunca sao considerados estaveis; resolva-os ao vivo.

## Tags da skill

- Categoria conhecida: `categoria:{slug}`.
- Analisado: `skill:analisado`.
- Aguardando owner: `skill:aguardando-owner`.
- Ainda nao catalogado: `skill:tbd`.
- FIX ligado: `bug:BUG-YYYY-MM-DD-NN`.
- FIX implantado aguardando verificacao: `skill:bug-fixed-pending-validation`.

Tags sao evidencias de estado externo; a memoria de aprendizado vive no catalogo e na fila, nao apenas nas tags.

## Reports e metricas

Cada run escreve um report append-only em `runs/`. Medir no minimo:

- cobertura do catalogo (`known / total`);
- unknown rate;
- itens novos e reabertos na fila;
- drafts, canarios e promocoes;
- correcoes do owner/falsos positivos;
- sucesso e falha por playbook;
- tickets reabertos quando o dado estiver disponivel.

O report e auditoria; `learning/queue.json` e `catalog.json` sao memoria operacional.

## Referencias

- Dispatcher: `tarefas/00-analise-geral.md`
- Ensino: `tarefas/96-ensinar-padrao.md`
- FIX: `tarefas/97-fix.md`
- GitHub Project: skill `github-issue-escalashop`
- Compatibilidade: `tarefas/99-novo-bug.md`
- Report: `tarefas/95-report-final.md`
- Contrato de aprendizado: `references/learning-contract.md`
- Contrato de ferramentas: `references/tool-contract.md`
- Solucoes observadas: `references/known-case-solutions.md`
- Contexto LP: `contexto/lp-arquitetura.md`
- Catalogo: `catalog.json`
- Fila: `learning/queue.json`
- Backlog tecnico: `bugs-backlog.md`
