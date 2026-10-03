# Contrato de aprendizado da `/gleap`

Este contrato define como um caso desconhecido vira conhecimento reutilizavel sem transformar uma hipotese em automacao perigosa.

## Separacao obrigatoria

Classifique cada desconhecido antes de documentar a solucao:

| Tipo | Criterio | Artefato |
|---|---|---|
| `playbook` | Procedimento operacional repetivel e verificavel | Entrada no catalogo + tarefa em `tarefas/` |
| `fix` | Comportamento incorreto de codigo, dados, integracao ou infraestrutura | `BUG-*` no backlog + `docs/fixes/BUG-*.md` + issue pai rastreavel no GitHub Project |
| `policy` | Excecao, prioridade ou decisao comercial | Item na fila com decisao e validade; sem automacao generica |
| `investigation` | Faltam dados ou a causa ainda e ambigua | Item na fila com probes e perguntas |
| `support` | Procedimento humano conhecido que nao deve ser automatizado | Entrada de rota no catalogo |

Nao use `playbook` apenas porque varios titulos se parecem. Recorrencia de sintoma pode esconder causas diferentes.

## Fila persistente

Arquivo canonico: `skills-shared/gleap/learning/queue.json`.

Cada item usa este formato logico:

```json
{
  "clusterKey": "kyc-status-nao-sincroniza",
  "status": "open",
  "suggestedKind": "investigation",
  "ticketIds": ["5897", "5503"],
  "titles": ["Cadastro aprovado..."],
  "signals": ["kyc remoto aprovado", "fase local em verificacao"],
  "evidence": ["screenshot_inspected", "remote_status_pending"],
  "questions": ["Qual transicao local e esperada?"],
  "ownerAnswer": null,
  "artifact": null,
  "firstSeenAt": "ISO-8601",
  "lastSeenAt": "ISO-8601",
  "occurrences": 2
}
```

Estados permitidos da fila:

- `open`: ainda nao ensinado.
- `questions-answered`: owner forneceu a regra, falta redigir.
- `draft-created`: artefato local criado.
- `canary-ready`: diagnostico e verificacao permitem testar um caso.
- `canary-failed`: teste falhou; registrar por que e voltar a investigar.
- `validated`: canario passou e evidencias foram registradas.
- `closed`: conhecimento promovido, roteado ou descartado com motivo.

Atualizacao e `upsert` por `clusterKey`: unir ticket IDs sem duplicar, incrementar `occurrences`, preservar respostas do owner e atualizar `lastSeenAt`. Nao grave email, telefone, CPF, senha, token, segredo ou payload integral.

## Pacote minimo de evidencia

Antes de perguntar ao owner, capture o que estiver disponivel:

- ticket ID, titulo, descricao e tags humanas;
- status, time e responsavel atuais;
- screenshots e anexos inspecionados;
- loja/compra apenas por IDs tecnicos necessarios;
- fase e estado local;
- estado remoto de Shopee/Gleap quando pertinente;
- consultas read-only e seus resultados resumidos;
- categorias candidatas e por que foram rejeitadas;
- tickets parecidos e diferencas relevantes.

Se uma midia obrigatoria nao puder ser lida, o caso permanece `investigation`.

## Perguntas de ensino

Pergunte somente o que a evidencia nao respondeu. Obtenha obrigatoriamente:

1. Resultado esperado.
2. Como confirmar o diagnostico e quais precondicoes valem.
3. Acoes seguras e sua ordem.
4. O que nunca deve ser feito.
5. Como verificar sucesso.
6. O que fazer em falha e como reverter quando aplicavel.
7. Sinais positivos e contraexemplos para reconhecer o caso no futuro.

Se o owner responder apenas com uma acao, faca as perguntas restantes antes de criar um playbook executavel. Inferencias do agente devem ficar marcadas como hipotese.

## Ciclo do playbook

### 1. Draft

- Criar `tarefas/{NN}-{slug}.md` com diagnostico, hard gates, acao, verificacao, rollback e edge cases.
- Criar ou atualizar a entrada correspondente em `catalog.json` com `status: draft`.
- Registrar exemplos positivos e pelo menos um contraexemplo quando conhecido.
- Validar e sincronizar as projecoes.
- Nao escrever no ticket nem aplicar ao cluster.

### 2. Canary

- Selecionar exatamente um ticket representativo.
- Reobter toda a evidencia e apresentar plano, writes, mensagens/notas e verificacao.
- Pedir GO explicito para esse ticket.
- Executar sequencialmente e parar na primeira divergencia.
- Verificar o resultado real, nao apenas o retorno da ferramenta.
- Registrar sucesso/falha no item da fila e no report.

Canario falhou: manter `draft`, registrar contraexemplo e ajustar diagnostico. Nunca compensar silenciosamente nem tentar o restante do cluster.

### 3. Validated

Depois de um canario bem-sucedido, mudar para `validated`. Nesse estado, a categoria pode ser repetida somente em ticket individual com novo GO. Ainda nao pode rodar em lote.

### 4. Active

Promover para `active` somente quando:

- diagnostico e verificacao forem deterministas;
- pelo menos um canario real tiver sucesso;
- o owner confirmar que a regra e geral, nao uma excecao;
- riscos e contraexemplos estiverem documentados;
- o validador passar.

Playbooks destrutivos, cobrados ou com comunicacao externa continuam exigindo gates adicionais mesmo quando `active`.

### 5. Deprecated

Quando a regra deixar de valer, marcar `deprecated`, registrar motivo/data/substituto e nao apagar o historico. Tickets que casariam com ela voltam para `investigation` ou para o substituto ativo.

## Registro atomico

Um conhecimento novo so esta registrado quando estes itens concordam:

1. tarefa existe;
2. entrada existe no `catalog.json`;
3. matcher aponta para a tarefa correta;
4. fila referencia o artefato;
5. `validate-knowledge.mjs` passa;
6. links Claude/Codex/Hermes apontam para a fonte compartilhada.

Se qualquer etapa falhar, manter `draft` e nao executar.

## Multi-intencao

Um ticket pode ter uma categoria primaria e varias secundarias. A primaria define a primeira acao segura; as secundarias permanecem no report e na fila. Uma flag de refund pode bloquear outras acoes sem apagar o relato de anuncio, KYC ou acesso.

## Correcao do owner e qualidade

Toda correcao do owner deve:

- registrar qual classificacao estava errada;
- adicionar um contraexemplo ou ajustar matcher/evidencia;
- incrementar `ownerCorrections` no report;
- rebaixar `active -> validated` se a falha puder afetar outros tickets;
- deprecar imediatamente se houver risco de escrita incorreta.

## FIX

O tipo `fix` preserva o identificador `BUG-YYYY-MM-DD-NN` usado nas tags e no backlog. O documento detalhado vive em `docs/fixes/BUG-YYYY-MM-DD-NN.md`; quando a correcao exigir codigo, banco, integracao ou infraestrutura, o documento referencia tambem a issue pai criada ou preparada pela skill `github-issue-escalashop`. O protocolo completo esta em `tarefas/97-fix.md`.

## Stopping conditions

Interromper e pedir decisao quando:

- nao for possivel distinguir `playbook`, `fix` e `policy` com as evidencias atuais;
- a regra do owner conflitar com um hard gate existente;
- o canario produzir resultado diferente do esperado;
- a verificacao depender de dado inacessivel;
- uma acao ampliaria o escopo para codigo, deploy ou comunicacao externa sem pedido explicito.
