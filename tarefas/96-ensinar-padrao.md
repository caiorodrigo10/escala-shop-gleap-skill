# Tarefa 96 — Ensinar e validar um padrao

Transforma itens de `learning/queue.json` em conhecimento reutilizavel sem executar uma hipotese em lote.

## Quando executar

- `/gleap teach`
- `/gleap teach --cluster={clusterKey}`
- `/gleap teach --ticket-id={bugId}`
- `/gleap teach --validate={slug} --ticket-id={bugId}`
- `/gleap teach --promote={slug}`

Carregar antes:

- `../references/learning-contract.md`
- `../catalog.json`
- `../learning/queue.json`
- `../references/tool-contract.md` somente para canario

## Regras fundamentais

- Ensino normal escreve somente arquivos locais canonicos.
- Nao adicionar tags, notas, status ou atribuicoes durante a coleta de conhecimento.
- Nao criar um playbook executavel com uma explicacao superficial.
- Nunca aplicar um draft a todos os tickets do cluster.
- Canario usa exatamente um ticket e exige GO explicito depois do preview.
- Atualizar `skills-shared/gleap/` e validar; os caminhos Claude/Codex/Hermes sao links para a mesma fonte.

## Fluxo A — Selecionar o que ensinar

1. Ler a fila e ordenar por:
   - recorrencia;
   - impacto/risco;
   - quantidade de evidencias disponiveis;
   - antiguidade.
2. Exibir grupos compactos, sem PII:

```text
[1] kyc-status-nao-sincroniza — 5 ocorrencias — investigation — 2 perguntas
[2] anuncios-informacoes-pendentes — 10 ocorrencias — playbook? — 4 perguntas
[3] reset-fornecedor — 1 ocorrencia — investigation — 3 perguntas
```

3. Se o owner nao escolheu um item, recomendar primeiro os recorrentes com evidencia suficiente. Nao assumir que todos pertencem a mesma causa.

## Fluxo B — Confirmar o tipo

Apresentar a sugestao com justificativa e pedir confirmacao somente quando a classificacao mudar o artefato:

- `playbook`: procedimento operacional repetivel;
- `fix`: comportamento incorreto do produto;
- `policy`: decisao ou excecao comercial;
- `investigation`: causa ou evidencia insuficiente;
- `support`: trabalho humano conhecido.

Se `fix`, encaminhar para `97-fix.md`. Se houver mistura de causas, dividir o cluster antes de continuar.

## Fluxo C — Entrevista orientada por lacunas

Primeiro mostre o que ja foi inferido das evidencias. Depois pergunte, em blocos curtos, somente o que falta:

1. Qual resultado correto deve aparecer?
2. Como confirmar que este e realmente o caso?
3. Qual sequencia de acoes resolve?
4. O que jamais deve ser feito?
5. Como comprovar que resolveu?
6. Como parar/reverter se falhar?
7. Que caso parecido **nao** pertence a este procedimento?

Registre a resposta integralmente resumida em `ownerAnswer`, sem inventar detalhes. Marque inferencias do agente como `hypothesis`.

## Fluxo D — Criar o artefato local

### Playbook

1. Escolher slug kebab-case estavel.
2. Escolher o proximo prefixo numerico livre entre `08` e `94`.
3. Criar `tarefas/{NN}-{slug}.md` com:
   - objetivo e escopo;
   - `status: draft` no topo;
   - sinais positivos e contraexemplos;
   - evidencias e hard gates;
   - diagnostico antes da acao;
   - preview de writes;
   - passos de execucao;
   - verificacao real de sucesso;
   - parada/rollback;
   - output para o report;
   - edge cases observados.
4. Criar entrada no `catalog.json` com o mesmo slug, `kind: playbook`, `status: draft`, `task` correto, matcher conservador, `approval: no-external-write` e confianca `low`.
5. Atualizar o item da fila para `draft-created` e apontar `artifact` para a tarefa.

O matcher fica apenas no catalogo. O MD explica os sinais, mas nao e fonte de roteamento.

### Support

Criar entrada `support` em `catalog.json` inicialmente como `draft`, com rota, evidencia e verificacao. Uma atribuicao tambem e write externo e precisa de canario antes de ficar `active`.

### Policy

Registrar na fila:

- decisao;
- escopo;
- quem pode autorizar;
- data/condicao de expiracao;
- exemplos e excecoes.

So criar uma referencia versionada se a politica for recorrente. Nao converter uma concessao individual em matcher ativo.

### Investigation

Atualizar `questions` e `nextProbes` com leituras concretas. Probes read-only podem ser realizados na run atual; qualquer mutacao exige outro modo e GO.

## Fluxo E — Validar a consistencia local

Executar:

```bash
node .claude/skills/gleap/commands/validate-knowledge.mjs
node scripts/sync-agent-skills.mjs
```

Se falhar, corrigir antes de anunciar o draft. O item permanece `draft-created`; nunca promover parcialmente.

## Fluxo F — Canary de um ticket

Gatilho: `/gleap teach --validate={slug} --ticket-id={bugId}`.

1. Confirmar que a entrada esta `draft` ou `validated` e que o ticket representa o padrao.
2. Refazer detalhe, evidencias visuais, estado local/remoto e preflight do playbook.
3. Mostrar:
   - diagnostico;
   - acao exata;
   - todos os writes e textos;
   - riscos;
   - verificacao e stopping condition.
4. Perguntar GO para **esse unico ticket**.
5. Se autorizado, executar sequencialmente e parar na primeira divergencia.
6. Reconsultar o estado real e registrar `canaryResult` na fila e no report.

### Canary bem-sucedido

- Mudar catalogo `draft -> validated`.
- Trocar `approval: no-external-write` pela politica real do playbook.
- Atualizar o topo do MD para `status: validated`.
- Adicionar o ticket aos exemplos positivos e qualquer aprendizado aos edge cases.
- Atualizar fila para `validated`.
- Validar e sincronizar.

### Canary falhou

- Manter/rebaixar para `draft`.
- Atualizar fila para `canary-failed` com resultado esperado, resultado observado e etapa da falha.
- Acrescentar contraexemplo ou corrigir diagnostico.
- Nao tentar os demais tickets.

## Fluxo G — Promover para active

Gatilho: `/gleap teach --promote={slug}`.

Apresentar ao owner:

- canarios e resultados;
- matcher atual;
- exemplos e contraexemplos;
- writes e risco;
- tickets atualmente candidatos.

Somente apos confirmacao explicita:

1. alterar catalogo e MD para `active`;
2. fechar os itens correspondentes da fila com motivo `promoted-to-active`;
3. validar e sincronizar;
4. gerar report de ensino.

Promocao nao executa o playbook nos tickets candidatos. Isso exige `/gleap apply` e outro GO.

## Correcao posterior

Se o owner corrigir uma classificacao ativa:

- registrar a correcao;
- ajustar matcher/contraexemplo;
- rebaixar para `validated` se outros tickets puderem ser afetados;
- deprecar se houver risco material;
- nunca esconder o falso positivo no report.

## Output

Informar:

- item da fila atualizado;
- tipo escolhido;
- artefatos criados/alterados;
- status anterior e novo;
- validacao/sincronizacao;
- proximo passo seguro: investigar, canario, promover ou aplicar.
