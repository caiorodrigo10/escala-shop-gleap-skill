# Contrato atual de ferramentas Gleap e Supabase

Leia este arquivo no preflight de qualquer operação Gleap. Ele prevalece sobre nomes ou argumentos históricos encontrados nos playbooks de `tarefas/`.

## Dependências

- Projeto Gleap esperado: **Escala Shop**.
- Projeto Supabase esperado: `<supabase-project-ref>`.
- Owner: `<gleap-id>`.
- Times: Engineering `<gleap-id>`, Support `<gleap-id>`, Backoffice `<gleap-id>`.

No Codex, use as ferramentas do plugin Gleap com prefixo `mcp__codex_apps__gleap_` e o SQL do plugin Supabase `mcp__codex_apps__supabase_execute_sql`. No Hermes, use o Tool Router Composio e os slugs retornados por `COMPOSIO_SEARCH_TOOLS`; nunca exija que o nome do slug seja igual ao nome lógico do Codex. Se alguma capacidade obrigatória não estiver disponível nem por equivalente validado, pare antes de qualquer write e informe qual capacidade falta. Não substitua writes por `curl` improvisado.

## Mapeamento Hermes + Composio validado

| Capacidade lógica | Implementação Composio |
|---|---|
| Tipos do projeto e keys das lanes | `GLEAP_GET_PROJECTS({})` → resolver ID de `Escala Shop` → `GLEAP_GET_PROJECT({ id })` → `projectTypes[].options.possibleLanes[]` |
| Sweep de tickets | `GLEAP_GET_ALL_TICKETS` |
| Ticket completo | `GLEAP_GET_A_TICKET` |
| Usuários e times | `GLEAP_GET_ALL_USERS_FOR_A_PROJECT`, `GLEAP_GET_ALL_TEAMS` |
| Healthcheck SQL read-only | `SUPABASE_RUN_READ_ONLY_QUERY` |
| Processar resposta grande | `COMPOSIO_REMOTE_WORKBENCH` ou `COMPOSIO_REMOTE_BASH_TOOL` |

O Tool Router pode salvar respostas grandes em `remote_file_info.file_path`, sob `/mnt/files/...`. Esse caminho pertence ao sandbox remoto do Composio, não ao filesystem local do Hermes. Passe o `session_id` retornado pelo fluxo para o Workbench/Bash remoto e processe o arquivo lá. Nunca interprete `remote_file_info` como perda de dados e nunca tente abrir esse path com o terminal local.

## Preflight obrigatório

1. Resolva tipos/status ao vivo. No Codex, `get_ticket_types({})`; no Hermes+Composio, `GLEAP_GET_PROJECTS({})`, encontre exatamente `Escala Shop` e chame `GLEAP_GET_PROJECT({ id: projectId })`. Localize `type="BUG"` em `projectTypes` e monte o mapa `title → key` usando `options.possibleLanes`. Nunca invente ou traduza uma key.
2. No Codex, `get_users({})` e `get_teams({})`; no Hermes+Composio, `GLEAP_GET_ALL_USERS_FOR_A_PROJECT({})` e `GLEAP_GET_ALL_TEAMS({})`. Confirme o owner e os IDs dos times.
3. No Codex, Supabase `execute_sql({ project_id: "<supabase-project-ref>", query: "select 1 as ok" })`; no Hermes+Composio, `SUPABASE_RUN_READ_ONLY_QUERY({ ref: "<supabase-project-ref>", query: "select 1 as ok" })`.
4. No Hermes+Composio, se qualquer chamada retornar `remote_file_info`, processe o arquivo com `COMPOSIO_REMOTE_WORKBENCH` usando o mesmo `session_id` antes de decidir que faltam dados.
5. Para cada ticket, una os campos de mídia do sweep e do detalhe: `screenshotUrl`, `attachments[]` e `latestComment.attachments[]`. Extraia as URLs no Workbench quando o resultado estiver remoto, baixe em `/tmp` no Hermes e inspecione visualmente antes de classificar. Se não houver visão disponível ou a mídia realmente falhar, mantenha o ticket manual.

## Operações canônicas

| Capacidade | Chamada/argumentos atuais |
|---|---|
| Buscar tickets estruturados | `find_tickets({ type, status, limit, skip, ... })` |
| Ler ticket completo | `get_ticket({ ticketId })` |
| Validar usuários/times | `get_users({})`, `get_teams({})` |
| Adicionar tags | `add_ticket_tags({ ticketId, tags })` |
| Atribuir | `assign_ticket({ ticketId, processingTeam?, processingUser? })` |
| Atualizar status/campos | `update_ticket({ ticketId, status?, priority?, title?, dueDate?, formData? })` |
| Nota interna | `send_message({ ticketId, text, isNote: true })` |
| Linkar dois tickets | `link_tickets({ ticketId, linkedTicketId })` |
| Consultar banco | `execute_sql({ project_id, query })` |

Os nomes acima são capacidades lógicas do contrato. No Hermes+Composio use o mapeamento validado desta página e consulte o schema atual com `COMPOSIO_GET_TOOL_SCHEMAS` antes de executar; não aborte apenas porque o slug literal da coluna não existe.

## Regras de escrita

- Preview é obrigatório. Nenhum write em ticket ou banco sem GO explícito do owner para os tickets e ações apresentados.
- Exceção versionada: quando `shopee-listing-replacement` estiver `active`, uma
  política vigente em `replacement_policies`, validada pelo endpoint para o
  fornecedor exato, vale como GO persistente somente para os efeitos descritos
  nesse playbook. O agente ainda registra o preview no report. Em `draft` ou
  `validated`, o canário continua exigindo GO explícito no contexto atual. A
  exceção nunca cobre mensagem pública, `Done`, outro fornecedor ou outro
  playbook.
- `get_ticket` aceita número humano, ObjectId ou share token. `update_ticket`, `add_ticket_tags`, `assign_ticket`, `send_message` e `link_tickets` devem receber o ObjectId retornado pelo ticket completo.
- Preserve tags humanas: use apenas `add_ticket_tags`. Nunca envie `tags` em `update_ticket` para representar um append.
- Resolva a key de status no preflight. Hoje o board BUG retorna `OPEN`, `INPROGRESS`, `TOTEST` e `DONE`, mas isso deve ser verificado a cada run.
- Atualize status e atribuição em chamadas separadas. Faça `update_ticket` primeiro e `assign_ticket` por último, com `processingUser` do Caio quando a tarefa exigir; isso evita o comportamento histórico que apagava o responsável.
- Toda comunicação interna usa `send_message(..., isNote: true)` e prefixo `[interno]`.
- Uma resposta visível para a aluna exige aprovação explícita do texto exato. Se não houver, apenas prepare o rascunho; não envie.
- Um retry de write exige conferir o estado atual antes. Não repita cegamente operações não idempotentes.

## Tradução de exemplos históricos

- `find_users(...)` ou `get_project_users(...)` significa `get_users({})` seguido de filtro local por ID.
- `processingTeamId` significa `processingTeam`.
- `processingUserId` significa `processingUser`.
- `tagsAdd=[...]` significa uma chamada separada `add_ticket_tags({ ticketId, tags: [...] })`; nunca é argumento de `update_ticket`.
