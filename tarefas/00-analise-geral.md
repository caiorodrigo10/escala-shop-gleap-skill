# Tarefa 00 — Scan, classificacao e dispatch

Orquestra o sweep de tickets `BUG`, monta evidencias, classifica pelo catalogo, persiste desconhecidos e, somente em modo `apply`, despacha playbooks ativos depois do GO do owner.

## Entradas

- `/gleap`, `/gleap scan` ou `/gleap --dry-run`: `mode=scan`.
- `/gleap --ticket-id=X`: `mode=scan`, escopo de um ticket.
- `/gleap apply`: `mode=apply`.
- `/gleap apply --ticket-id=X`: canario/execucao individual, conforme estado do catalogo.
- `/gleap apply --category=slug`: filtra a categoria, mas ainda exige classificacao, preview e GO.

O default nunca e `apply`.

## Carga obrigatoria

1. `../SKILL.md`
2. `../references/tool-contract.md`
3. `../catalog.json`
4. `../learning/queue.json`
5. `../contexto/lp-arquitetura.md` somente quando um diagnostico depender da Loja Pronta

Antes de `apply`, executar:

```bash
node .claude/skills/gleap/commands/validate-knowledge.mjs
```

Falha local de validacao e hard stop. Nao usar regex ou task alternativa para contornar catalogo invalido.

## Estado da run

Manter em memoria:

```text
runId, mode, invocation, startedAt
tickets[]
classifications[]
queueChanges[]
playbookResults[]
canaryResults[]
ownerCorrections[]
warnings[]
failures[]
toolsUsed[]
externalWrites[]
githubIssueCandidates[]
```

O report nao substitui a fila; a fila nao substitui o report.

## Passo 1 — Preflight proporcional

### Leitura Gleap

- Confirmar o projeto pelo nome **Escala Shop** e obter seu ID.
- Confirmar capacidade equivalente de listar tickets e obter detalhe.
- Para `apply`, resolver ao vivo tipos e lanes possiveis.
- Nao falhar por ausencia de um nome literal de ferramenta se o conector oferecer capacidade equivalente.

### Supabase e outros servicos

- Em `scan`, testar somente quando necessario para a categoria. Falha vira blocker daquele ticket.
- Em `apply`, cada dependencia do playbook e hard gate antes do preview final.
- Nao consultar fal.ai, Shopee ou GHL em categorias que nao os usam.

### Identidade e atribuicao

- Confirmar owner/time apenas se uma acao proposta incluir atribuicao.
- IDs conhecidos ajudam a localizar, mas o estado/capacidade atual prevalece.

## Passo 2 — Obter tickets

### Sweep

Listar somente tickets do tipo `BUG` na lane Open resolvida ao vivo. Paginar ate esgotar o escopo autorizado. `BOT` e sempre excluido: nao entra em totais, metricas, classificacao, fila, preview ou report; se aparecer na resposta do conector, descartar antes de qualquer agregacao. Se o owner forneceu `--ticket-id`, obter o detalhe desse ticket e nao executar sweep.

Guardar separadamente:

- ObjectId usado nas escritas;
- bug ID humano usado na apresentacao;
- titulo, descricao, tags, status, time/responsavel;
- sessao/custom data;
- screenshots, anexos e midias de comentarios;
- referencias a loja, compra ou anuncio.

## Passo 3 — Evidencia visual

Para cada midia de imagem:

1. resolver a URL real, inclusive via Workbench remoto quando o Composio fizer offload;
2. baixar para `/tmp/ticket-{bugId}-{n}.{ext}`;
3. inspecionar com a ferramenta visual disponivel;
4. registrar apenas uma descricao objetiva da evidencia.

Se a imagem obrigatoria nao puder ser lida, adicionar blocker `screenshot_unreadable` e impedir execucao automatica. Nunca inferir o conteudo pelo nome do arquivo.

## Passo 4 — Pacote de evidencia

Montar por ticket:

```json
{
  "ticketId": "ObjectId",
  "bugId": "5897",
  "text": "titulo + descricao + contexto relevante",
  "humanTags": [],
  "signals": [],
  "visualFacts": [],
  "localState": {},
  "remoteState": {},
  "missingEvidence": [],
  "blockers": []
}
```

Exemplos de `signals`: `session.customData.has_refund=true`, `tag:Reclame Aqui`, `derived:lp_purchase_not_found`, `shopee:kyc-approved`, `local:phase-verification`.

### Sinais de solicitacao de acesso criada pelo Support

Produzir `derived:ticket-created-by-support` somente quando o detalhe do ticket
confirmar `type=BUG`, `initiatedByAgent=true` e `manuallyAdded=true`.
Tickets assim podem estar associados a sessao da cliente beneficiaria; nao
exigir que `session.userId` seja o agente criador. Comentario posterior de
agente em ticket criado pela cliente nao produz esse sinal.

Produzir `derived:explicit-access-request` somente quando titulo, descricao ou
tags pedirem inequivocamente um destes produtos para identidades extraiveis:

- SLL/MSL: `SLL`, `MSL`, `liberar SLL` ou equivalente explicito;
- Loja Pronta: `Loja Pronta`, `Loja 3.0`, `liberar acesso a loja` ou
  equivalente explicito.

Registrar tambem `requestedProduct:SLL` ou `requestedProduct:LP` por
identidade. Se um ticket misturar produtos sem mapear cada identidade, manter o
subcaso ambiguo bloqueado.

Consultas externas devem produzir sinais e fatos resumidos, nao despejos integrais.

### Resolver pelo sintoma original e pela linha do tempo

Antes de manter um ticket como pendente, separar o problema escrito pela cliente
das etapas posteriores da jornada. Extrair o marco que estava bloqueado e
comparar `createdAt` do ticket com fases, eventos e resultados atuais.

- Se evidencia confiavel mostra que a conta ultrapassou o marco reclamado depois
  do ticket, registrar `derived:original-symptom-resolved-after-ticket` e tratar
  o ticket original como resolvido, propondo `To test` quando autorizado.
- Um trabalho posterior incompleto nao mantem o relato original aberto. Registrar
  esse trabalho separadamente somente se ele representar outro defeito ou uma
  entrega ainda devida.
- Nao atribuir o avanço à cliente quando o ator nao estiver demonstrado. Dizer
  que a conta ou a jornada avançou.
- Se o estado atual ainda estiver no mesmo marco, regrediu ou nao houver linha do
  tempo confiavel, manter o ticket em investigacao.

Exemplo: “nao consigo selecionar produtos” fica resolvido quando uma selecao
posterior criou os produtos, mesmo que publicacao e imagens ainda estejam
pendentes. Essas pendencias nao sao o sintoma descrito no ticket.

### Correção publicada aguardando novo teste

Quando uma correção compatível com o sintoma já estiver publicada, mas não
houver tentativa posterior suficiente para confirmar o resultado, o estado
correto do ticket é `To test`, não `In progress`. Esse estado indica que o
trabalho técnico provável terminou e que a próxima evidência depende de uma
nova tentativa da cliente.

Antes da mudança, preparar uma nota interna com prefixo `[interno]` para o
suporte. A nota deve conter:

- o sintoma original e a etapa em que ocorreu;
- a correção publicada ou a evidência que torna o caso aparentemente corrigido;
- o passo exato que a cliente deve repetir e o resultado esperado;
- quais evidências coletar se o erro persistir, como URL, horário e captura de
  tela.

Apresentar o texto exato da nota e a mudança para `To test` no mesmo preview.
Após o GO, reler o ticket, adicionar a nota com `isNote:true` e mover para a
lane resolvida ao vivo. Se o owner conceder explicitamente GO persistente para
esse padrão durante um ciclo definido, continuar nos tickets elegíveis sem
pedir novamente o mesmo aceite; registrar cada texto e write no report. Se o
ticket já estiver em `To test`, adicionar somente a nota faltante. A nota é
interna e não substitui uma mensagem aprovada para a cliente. O GO persistente
não autoriza `Done`, mensagem visível nem writes fora do padrão concedido.

#### Cliente precisa conectar ou reconectar a Shopee

Quando a verificação mostrar que o próximo passo depende somente de a cliente
concluir a autorização da Shopee, tratar o caso como validação do suporte:

- mover o ticket para `To test`;
- quando já existir loja local, adicionar nota interna orientando o suporte a
  enviar a URL canônica
  `https://lojapronta.app/lojapronta/reconectar-shopee`;
- quando ainda não existir loja local, orientar o primeiro vínculo por
  `https://lojapronta.app/sll/minhas-lojas`, seguindo `Adicionar loja > Shopee
  > Já tenho loja Shopee`; a rota de reconexão exibe “sem loja LP configurada”
  nesse estado e não deve ser enviada;
- pedir que a cliente entre na conta correta e conclua toda a autorização;
- orientar o suporte a confirmar o retorno ao Escala Shop com a conexão ativa;
- se falhar, coletar horário, URL final, mensagem de erro e captura da tela.

A rota de reconexão é phase-aware e encaminha uma loja existente ao OAuth
adequado. Não manter em `In progress` um ticket cujo único próximo passo seja
essa ação da cliente.

Se a reconexão for apenas uma pré-condição para uma correção técnica ainda
pendente, a nota deve dizer isso explicitamente. O suporte valida a reconexão e
devolve o ticket à equipe técnica; não tratar a autorização renovada como
conclusão de toda a demanda.

#### Pedido genérico de ajuste sem defeito identificado

Quando o ticket disser apenas “ajustar anúncio”, “corrigir imagem” ou equivalente
e não identificar o alvo nem a diferença entre o resultado atual e o esperado,
não alterar anúncio ou imagem por suposição. Se a próxima ação for obter essa
informação com a cliente, mover para `To test` com uma nota interna em linguagem
simples, orientando o suporte a coletar:

- link do anúncio afetado;
- o que a cliente vê como errado;
- como ela espera que fique;
- captura atual da tela quando houver erro, bloqueio ou problema visual.

Explicar na nota quando uma captura mostrar somente uma recomendação do
Otimizador da Shopee. Depois que os dados chegarem, o suporte devolve o ticket à
equipe técnica. Não apresentar uma recomendação de melhoria como bug confirmado.

## Passo 5 — Avaliar o catalogo

### Semantica do matcher

- Compilar `matcher.textRegex` com `catalog.matcherFlags`.
- Comparar com titulo, descricao e texto relevante de comentarios, preservando qual campo bateu.
- `matcher.signalsAny` bate por igualdade com um sinal calculado.
- Uma entrada e candidata se ao menos um regex ou sinal bater.
- `requiredEvidence` nao e matcher: e gate que precisa estar satisfeito antes de executar.

Avaliar **todas** as entradas. Nao parar no primeiro match.

### Resultado por entrada

- `active` + evidencia suficiente: `known`.
- `active` + evidencia faltante: `candidate-blocked`.
- `validated`: `candidate-validated`; somente ticket individual pode ser testado.
- `draft`: `candidate-draft`; nunca executar.
- `deprecated`: ignorar para execucao e registrar aviso se ainda casar.

### Primaria e secundarias

Ordenar candidatas pelo menor `priority`. A primeira vira `primary`; as demais ficam em `secondary` com os motivos do match.

Uma categoria primaria de seguranca pode bloquear as demais, mas nao as apaga. Exemplo: refund confirmado impede alteracao de anuncio, enquanto `shopee-baniu-excluiu` permanece como intencao secundaria no report.

Se duas categorias ativas propuserem writes incompatíveis, manter em preview/manual e pedir decisao.

### Confianca

O campo `confidence` do catalogo descreve maturidade do conhecimento, nao certeza sobre o ticket. Calcular separadamente a confianca do match:

- `high`: sinal especifico + evidencias obrigatorias presentes;
- `medium`: texto forte, mas falta confirmacao nao destrutiva;
- `low`: similaridade, titulo generico ou evidencia incompleta.

Somente `high` pode entrar no preview de execucao automatica. `medium/low` vai para fila ou revisao do owner.

## Passo 6 — Desconhecidos e agrupamento

Um ticket vai para aprendizado quando:

- nao ha match;
- so ha match draft/deprecated;
- o match e medium/low;
- categorias conflitam;
- falta evidencia essencial;
- o owner corrige a classificacao.

Agrupar por comportamento, nao apenas por palavras. Use como sinais:

- superficie/etapa afetada;
- resultado esperado vs observado;
- estado local e remoto;
- erro ou transicao comum;
- anexos visualmente semelhantes;
- titulo/descricao como apoio.

Jaccard de titulo e somente sugestao. Nao agrupar quando a mesma frase pode representar causas diferentes.

### Conteudo de curso ausente

Quando o relato citar etapa, modulo ou aulas, identificar a superficie pelo print antes
de consultar progresso ou rotas do produto. Um player externo de curso com a sequencia
de modulos pulando um numero comprova conteudo oculto/despublicado nessa plataforma;
nao deve ser diagnosticado como gate de progresso ou rota quebrada do SLL novo.

Se o BUG foi criado a partir de um atendimento vinculado, ler tambem as mensagens e
anexos do ticket vinculado: o ticket tecnico pode conter apenas o resumo e perder a
evidencia que distingue configuracao editorial de defeito de desenvolvimento. Manter
em andamento ate confirmar a republicacao do modulo; depois mover para `To test` com
o caminho e o resultado esperado para o suporte validar com a aluna.

### Confirmacao apos writes na Shopee

Depois de criar anuncio, inicializar variacoes ou reativar item, a leitura da Shopee
pode demorar alguns segundos para refletir a grade e o status novos. Nao tratar uma
primeira leitura vazia ou ainda `UNLIST` como falha definitiva. Fazer polling limitado,
reler o inventario completo e so entao decidir por rollback ou nova tentativa.

Em recuperacoes retomaveis, usar um SKU deterministico e registrar o par de IDs antigo
e novo em auditoria. Antes de repetir qualquer write, procurar esse SKU ao vivo e
completar apenas a etapa ausente; isso evita anuncios duplicados quando uma resposta
ou leitura chega atrasada.

Gerar `clusterKey` kebab-case estavel, baseado no comportamento. Casos sem base para cluster recebem `ticket-{bugId}-investigation`.

## Passo 7 — Persistir a fila local

Em `scan` e `apply`, fazer `upsert` dos desconhecidos em `../learning/queue.json`:

- unir `ticketIds` e titulos sem duplicar;
- atualizar `lastSeenAt` e `occurrences`;
- preservar `ownerAnswer`, `artifact` e historico de canario;
- registrar sinais, evidencias faltantes e perguntas;
- reabrir item `closed` apenas se a recorrencia contradizer o conhecimento ativo, guardando o motivo;
- nao persistir PII ou segredos.

Fila local e report sao permitidos em `scan`. Nenhuma tag `skill:tbd` e aplicada externamente nesse modo.

Depois do upsert, validar novamente o conhecimento. Se a fila ficar invalida, restaurar logicamente o ultimo conteudo valido e registrar falha; nao sincronizar uma fila quebrada.

## Passo 7A — Encaminhar defeitos tecnicos para GitHub

Para cada ticket ou cluster com evidencia suficiente de comportamento incorreto que exige mudanca de codigo, banco, integracao ou infraestrutura:

1. Classificar como `fix`; nao encaminhar procedimentos de suporte, comportamento esperado de fornecedor, decisoes comerciais ou hipoteses ainda sem evidencia.
2. Carregar a skill `github-issue-escalashop` e pesquisar duplicatas pelo comportamento, componente/estado, ticket/slug `BUG-*` e evidencias, nao somente pelo titulo.
3. Preparar um candidato de issue pai com titulo, problema/impacto, fatos observados, criterios de aceite iniciais, links para tickets e para o documento `docs/fixes/BUG-*.md` quando ele existir. Deixar hipoteses explicitamente marcadas como hipoteses.
4. Classificar `Priority` pela matriz da skill GitHub: `P2` para trabalho normal, `P1` para impacto drastico/inoperancia e `P0` para risco critico imediato. Quando a evidencia nao permitir decidir, registrar perguntas objetivas em vez de escolher por conveniencia.
5. Em `scan`, registrar o candidato como `prepared` ou o link existente como `linked`; nao criar nem editar issue no GitHub. Em `/gleap fix`, apresentar o preview da issue e subissues somente quando houver plano; criar/escrever no GitHub apenas apos GO explicito do owner.
6. Guardar em `githubIssueCandidates[]`: ticketIds, BUG slug se existir, decisao `linked|prepared|needs-clarification`, URL existente ou payload proposto, prioridade/raciocinio e perguntas pendentes.

**Concluido quando:** cada FIX confirmado tem uma issue GitHub existente vinculada ou um candidato completo e deduplicado aguardando GO; nenhum caso de suporte/policy/investigation gera issue de codigo.

## Passo 8 — Preview

Mostrar:

```text
Gleap — Escala Shop — {runId}
Modo: SCAN | APPLY

Total BUG OPEN: N
Known active: N (cobertura X%)
Candidate/blocked: N
Unknown: N (unknown rate Y%)

Por categoria:
- slug: N primary, M secondary, confidence, status do catalogo

FIXes para GitHub:
- vinculados: N
- candidatos prontos: N
- aguardando esclarecimento: N

Fila:
- novos: N
- atualizados: N
- reabertos: N

Blockers e conflitos:
- ticket, evidencia ausente, impacto
```

Para cada ticket em `apply`, incluir ObjectId, bug ID, categoria, task, estado atual, writes propostos, texto exato de nota/mensagem, atribuicao, risco e verificacao.

## Passo 9 — Comportamento por modo

### `scan`

- Encerrar sem write externo.
- Para cada `fix` confirmado, mostrar link da issue existente ou candidato GitHub com prioridade e raciocinio; pedir somente as informacoes que faltam para classificar ou autorizar a escrita.
- Nao carregar nem simular detalhes de execucao desnecessarios dos playbooks.
- Oferecer como proximo passo `/gleap teach` para os clusters prioritarios ou `/gleap apply` para conhecidos.
- Gerar report.

### `apply`

1. Aceitar somente categorias `active` com match `high` e hard gates completos.
2. Se o owner escolheu subconjunto/categoria, limitar exatamente a ele.
3. Perguntar GO para o lote exibido.
4. Sem GO, gerar report como `cancelled`; nao executar.
5. Com GO, carregar o `task` de cada categoria e executar sequencialmente.
6. Reobter o ticket imediatamente antes de cada write.
7. Depois de cada playbook, verificar o estado real exigido em `verification`.
8. Se um ticket tem segunda categoria executavel, reclassificar depois da primeira acao antes de propor outro playbook.
9. Parar se mais de 30% falharem ou uma premissa compartilhada mudar.

### Categoria `validated`

Nao roda por `/gleap apply` em lote. Use `/gleap teach --validate={slug} --ticket-id=X`, seguindo `96-ensinar-padrao.md`.

## Passo 10 — Report

Chamar `95-report-final.md` com, no minimo:

```text
totalTickets
knownCount, candidateCount, unknownCount
coverageRate, unknownRate
primaryAndSecondaryClassifications
queueCreated, queueUpdated, queueReopened
draftsCreated, canariesRun, canariesSucceeded, promotions
ownerCorrections
playbookResults
externalWrites
warnings, failures
```

O report e append-only. Falha no report nao reverte writes externos ja confirmados; imprimir fallback no canal atual.

## Recovery

- Nova run reutiliza catalogo e fila, nao recomeca desconhecidos do zero.
- Tags Gleap ajudam a comparar o estado externo, mas nao sao a memoria primaria.
- Se a sessao cair durante `apply`, reler ticket e report parcial antes de tentar novamente.
- Nunca repetir write apenas porque o retorno anterior se perdeu; confirmar o estado real primeiro.

## Output

Retornar resumo, path do report, alteracoes da fila, cobertura, unknown rate, writes externos realizados e proximo passo seguro.
