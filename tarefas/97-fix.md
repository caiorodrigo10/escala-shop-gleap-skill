# Tarefa 97 — FIX de produto

Registra, acompanha e encerra defeitos tecnicos descobertos em tickets Gleap. O conceito e `fix`, mas o identificador externo continua `BUG-YYYY-MM-DD-NN` para preservar tags e historico existentes.

## Quando executar

- `/gleap fix`
- `/gleap fix --ticket-id={bugId}`
- um item de ensino foi confirmado como `fix`
- `/gleap bug-fixed BUG-YYYY-MM-DD-NN [--commit={sha}]`

Carregar `../bugs-backlog.md`, `../references/learning-contract.md`, `../references/tool-contract.md`, a evidencia do ticket/grupo e a skill `github-issue-escalashop`.

## O que esta tarefa nao autoriza

- Nao editar codigo, criar migration, fazer deploy ou `git push` como efeito colateral do intake.
- Nao marcar bug como resolvido porque existe um commit; precisa haver deploy e verificacao proporcionais ao risco.
- Nao mover tickets nem escrever notas sem preview e GO.
- Nao criar, editar ou mover issue no GitHub sem preview e GO para a escrita proposta; o intake pode apenas preparar e deduplicar o payload.
- Nao concluir causa raiz quando ha apenas correlacao.

Implementacao de codigo exige pedido explicito do owner e deve seguir o fluxo de story/desenvolvimento do repositorio.

## Ciclo do FIX

`observed -> confirmed -> planned -> implemented -> deployed -> verified -> closed`

- `observed`: sintoma registrado, causa incerta.
- `confirmed`: reproducao ou evidencia tecnica suficiente.
- `planned`: criterio de aceite, testes e rollback definidos.
- `implemented`: mudanca existe localmente/branch, ainda nao necessariamente implantada.
- `deployed`: versao/commit implantado no ambiente alvo.
- `verified`: comportamento real conferido e amostra de tickets revisada.
- `closed`: backlog e tickets tratados segundo GO do owner.

Nunca pule de `observed` para `closed`.

## Fluxo A — Encontrar ou criar BUG

1. Comparar o grupo com bugs abertos usando:
   - mesmo comportamento observavel;
   - mesmo componente/estado quando conhecido;
   - sobreposicao de evidencias, nao apenas titulo;
   - lojas/tickets distintos para estimar recorrencia.
2. Se houver candidato, mostrar semelhancas e diferencas. Owner confirma o link quando houver ambiguidade.
3. Sem match, gerar `BUG-{YYYY-MM-DD}-{NN}` em horario de Brasilia. O contador considera abertos e resolvidos e nunca reutiliza slug.

## Fluxo B — Documento detalhado

Criar `docs/fixes/BUG-YYYY-MM-DD-NN.md` com:

```markdown
# BUG-YYYY-MM-DD-NN — Titulo

**Estado:** observed
**Detectado em:** YYYY-MM-DD
**Ultima atualizacao:** YYYY-MM-DD
**GitHub Issue:** pendente de deduplicacao e GO

## Impacto
- Tickets e lojas afetados
- Severidade e frequencia
- Risco para cliente/receita/operacao

## Comportamento observado
- Esperado
- Atual
- Passos/evidencias de reproducao

## Evidencias
- Tickets, screenshots, queries read-only e estados remotos
- Fatos separados de hipoteses

## Hipoteses de causa
- Hipotese, evidencia a favor/contra e probe seguinte

## Escopo da correcao
- Dentro e fora do escopo
- Dependencias e riscos

## Criterios de aceite
- Resultados verificaveis

## Plano de teste
- Regressao, integracao e canario

## Rollback
- Sinal de falha e como reverter/parar

## Deploy e verificacao
- Story, branch, commit, ambiente, horario e resultado

## Plano para tickets Gleap
- DONE, TOTEST/Support ou manter OPEN; texto de nota proposto
```

Nao gravar credenciais, tokens, payloads integrais ou PII desnecessaria.

## Fluxo C — Backlog compacto

Criar/atualizar a entrada de `bugs-backlog.md` com:

- slug e titulo;
- estado do FIX;
- link para `docs/fixes/BUG-....md`;
- tickets afetados sem duplicacao;
- quantidade de lojas;
- sintomas;
- severidade e prioridade;
- ultima atualizacao.

O backlog e indice. Evidencia, hipoteses e plano detalhado ficam no documento do FIX.

## Fluxo D — Criar ou vincular issue no GitHub Project

Executar para todo FIX confirmado que exija corrigir codigo, banco, integracao ou infraestrutura.

1. Usar `github-issue-escalashop` para pesquisar issue pai existente por comportamento, componente, slug `BUG-*`, tickets vinculados e evidencia. Nunca criar duplicata por diferenca pequena de titulo.
2. Se existir issue equivalente, registrar a URL no documento `docs/fixes/BUG-*.md` e em `bugs-backlog.md`; atualizar somente se o preview e o GO cobrirem a alteracao.
3. Sem equivalente, preparar o preview da issue pai: repositorio, titulo, label `bug`, status `Backlog`, prioridade justificada, problema/impacto, evidencias, criterios de aceite iniciais, link do BUG local e tickets afetados sem PII desnecessaria.
4. Aplicar a prioridade com autonomia conforme a skill GitHub. Perguntar somente quando a evidencia nao permitir distinguir impacto normal, drastico ou critico.
5. Depois de GO explicito, criar a issue pai no Project, reler issue e item do Project, e persistir URL/numero no documento e no backlog local. Enquanto nao existir plano Superpowers, nao criar subissues e nao mover para `A fazer`.
6. Em `/gleap scan`, executar apenas os passos de deduplicacao e preview; nao escrever no GitHub.

**Concluido quando:** cada FIX de codigo confirmado referencia uma issue GitHub existente ou um preview deduplicado e pronto para GO.

## Fluxo E — Vincular tickets

Escritas opcionais no Gleap, somente depois de mostrar o lote e receber GO:

1. `add_ticket_tags` com `categoria:novo-bug`, `bug:BUG-...` e `skill:analisado`.
2. Nota interna proposta, com `isNote:true` e prefixo `[interno]`.
3. Manter `OPEN` por padrao enquanto aguarda correcao.
4. Atribuir Engineering/owner apenas se o preview incluiu essa atribuicao.

Se o GO nao vier, o FIX local continua valido e registra `externalLinkPending: true`.

## Fluxo F — Atualizacoes durante desenvolvimento

Ao receber evidencias como story, branch, commit, teste ou deploy:

- verificar o fato quando possivel;
- avancar somente um estado coerente;
- registrar data e evidencia;
- nao alterar tickets ainda.

Um commit pode levar a `implemented`, nao a `deployed`. Deploy sem verificacao leva a `deployed`, nao a `closed`.

## Fluxo G — `/gleap bug-fixed`

### Preflight

1. Encontrar o BUG aberto e seu documento.
2. Listar todos os tickets unicos vinculados.
3. Confirmar estado minimo `deployed` e evidencias de verificacao; se ausentes, oferecer registrar dados, nao fechar.
4. Resolver status keys ao vivo e reler os tickets.

### Escolha do owner

Mostrar tres opcoes:

1. mover para `DONE` — somente se a verificacao comprovar que nao ha trabalho humano restante;
2. mover para `TOTEST` e atribuir Support — validacao caso a caso;
3. manter `OPEN` e apenas registrar a implantacao.

Antes do GO, mostrar para cada ticket:

- ObjectId e bug ID humano;
- status atual e status proposto;
- tags adicionadas;
- atribuicao;
- texto exato da nota interna.

### Execucao

- Sequencial.
- Releitura imediatamente antes do write.
- Adicionar `skill:bug-fixed` ou `skill:bug-fixed-pending-validation` conforme a opcao.
- Atualizar status, depois nota interna, depois atribuicao separada e por ultimo.
- Parar se a premissa compartilhada mudar ou se mais de 30% falharem.

### Verificacao e fechamento

1. Reler os tickets alterados.
2. Atualizar documento para `verified` ou `closed` conforme o que foi comprovado.
3. Mover a entrada para resolvidos no backlog apenas quando estiver `closed`.
4. Preservar tickets, commit, branch, deploy, decisao e falhas.
5. Gerar report `bug-fixed` via `95-report-final.md`.

## Reabertura

Se o sintoma reaparecer:

- reabrir o mesmo BUG quando for regressao da mesma causa;
- criar novo BUG e relacionar ao anterior quando a causa for diferente;
- registrar ticket, versao e evidencia;
- nunca apagar o historico de resolucao anterior.

## Output

Retornar:

- slug e estado do FIX;
- documento detalhado e entrada do backlog;
- issue GitHub vinculada ou preview pendente, com prioridade e motivo;
- tickets vinculados/pedentes;
- evidencias faltantes;
- proxima transicao permitida;
- writes externos realizados ou explicitamente nao autorizados.
