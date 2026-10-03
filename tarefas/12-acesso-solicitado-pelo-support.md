# Tarefa 12 — Acesso solicitado pelo Support

**status: validated**

Canário SLL validado no ticket ticket de exemplo em 2026-09-17. O ramo Loja Pronta ainda
requer canário individual com GO antes de qualquer proposta de promoção para
`active`.

## Regra do owner

Um ticket `BUG` criado manualmente por um membro autenticado do Support e que
pede explicitamente acesso ao SLL ou a Loja Pronta confirma o direito ao produto
pedido, mesmo quando nenhuma compra Hotmart e localizada. A solicitacao do
Support e a fonte auditavel da autorizacao.

Esta regra e geral para solicitacoes de acesso cadastradas pelo Support. Ela nao
transforma tickets criados por clientes, `BOT` ou `INQUIRY` em autorizacao.

## Hard gates

1. Confirmar projeto Escala Shop, `type=BUG` e ticket criado manualmente.
2. Confirmar `initiatedByAgent=true` e `manuallyAdded=true`. Essa combinacao
   representa o ticket cadastrado pelo time interno; a sessao associada pode ser
   a da cliente beneficiaria. Nao inferir origem Support apenas por texto, tag
   ou comentario posterior.
3. Extrair e deduplicar todas as identidades citadas no ticket.
4. Discriminar o produto pedido por identidade: `SLL` ou `Loja Pronta`.
5. Reler conta, profile, entitlement, store e journey antes de qualquer write.
6. Se identidade ou produto forem ambiguos, parar somente aquele subcaso.
7. Exibir preview completo e obter GO no contexto atual.

A ausencia de compra, grant ou transaction ID nao e blocker quando os gates
acima estao satisfeitos. Refund historico tambem nao revoga esta nova
autorizacao explicita do Support; preservar outros produtos e estados existentes.

## Ramo SLL

- Se `hasSLL=true`, preservar a conta e considerar o subcaso ja liberado.
- Se faltar conta, usar `scripts/grant-sll-standalone.ts` primeiro em dry-run
  e depois com seus gates redundantes de execucao.
- Se a conta existe e `hasSLL=false`, fazer upsert idempotente em
  `sll_grants` por email, com `source='gleap_support_ticket'` e nota
  `Gleap #{bugId}: acesso solicitado pelo Support`.
- O grant SLL desta politica e permanente; nao inventar expiracao.
- Nunca criar Loja Pronta por consequencia de um pedido somente SLL.
- Reler `get_user_entitlement` e exigir `hasSLL=true`.

## Ramo Loja Pronta

- Se ja houver store/journey acessivel, preservar e considerar o subcaso
  liberado.
- Se nao houver conta, usar `scripts/grant-lp-standalone.ts` primeiro em
  dry-run e depois com `--approval-ticket={bugId}`, confirmacao do email,
  `--owner-approved --execute`.
- Se a conta existir mas faltar profile, store ou journey, o runner standalone
  atual recusa a operacao. Nao improvisar inserts: manter o subcaso bloqueado
  ate existir um runner idempotente que complete somente os componentes
  ausentes.
- A origem auditavel e o `approval-ticket` do runner; nao sintetizar transacao
  Hotmart falsa.
- Disparar o workflow LP Fase 1 somente para uma nova provisao, depois de
  mostrar destinatario e efeito no preview.
- Reler conta, store e journey e exigir acesso LP efetivo.

## Ticket multi-identidade

Processar cada identidade separadamente. O ticket so pode ir para `TOTEST`
quando todos os subcasos estiverem verificados. Falha parcial preserva os
sucessos e mantem o ticket aberto, com nota interna aprovada descrevendo apenas
IDs tecnicos necessarios e os subcasos pendentes.

## Preview obrigatorio

Para cada identidade, mostrar:

- produto solicitado e estado atual;
- conta/profile/grant/store/journey que serao criados ou preservados;
- workflow externo e destinatario, quando houver;
- tags, nota interna e status propostos;
- risco de concessao permanente.

Nenhum write ocorre sem GO. Mensagem publica, magic link e senha nunca sao
enviados por este playbook.

## Writes Gleap apos verificacao

1. Adicionar `categoria:acesso-solicitado-pelo-support` e `skill:analisado`.
2. Adicionar nota interna com prefixo `[interno]`, listando resultado por
   subcaso sem senha, token ou payload sensivel.
3. Mover para a key ao vivo de `To Test` somente se todos os subcasos passaram.
4. Atribuir ao Support em chamada separada e por ultimo.

## Verificacao

- Fonte Support e criador relidos.
- Cada identidade possui somente o produto solicitado.
- SLL: RPC retorna `hasSLL=true`.
- Loja Pronta: conta, store e journey existem e estao vinculadas.
- Nota interna e status relidos; nenhuma mensagem publica enviada.

## Canario e promocao

Enquanto `draft`, executar somente um ticket individual com preview e GO.
Validar separadamente pelo menos um caso SLL e um caso Loja Pronta antes de
propor promocao para lote `active`.
