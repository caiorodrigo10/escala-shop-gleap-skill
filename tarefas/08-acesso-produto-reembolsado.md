# Tarefa 08 — Encerrar pedido de acesso cujo produto foi reembolsado

**status: draft**

## Objetivo e escopo

Encerrar um ticket de acesso somente quando a compra que concederia o **produto solicitado no ticket** estiver efetivamente reembolsada e nao existir compra posterior ativa nem outra fonte vigente de entitlement para o mesmo produto.

Este playbook separa os dominios SLL/MSL e Loja Pronta. Um refund antigo ou de outro produto nunca decide sozinho o acesso atual.

## Sinais positivos

- O ticket pede acesso a um produto identificavel: SLL/MSL ou Loja Pronta.
- A identidade foi confirmada por email de compra e, quando necessario, por telefone/transacao.
- A compra relacionada ao produto solicitado esta com status `refunded`.
- A linha do tempo completa nao contem compra posterior `complete` ou `approved` que conceda o mesmo produto.
- Nao existe grant, perfil, store grandfather ou outra fonte vigente que conceda o produto solicitado.

## Contraexemplos — nao executar

- Compra MSL antiga reembolsada, mas compra MSL/SLL posterior esta ativa.
- Compra Loja Pronta reembolsada, mas o ticket pede SLL e existe entitlement SLL ativo.
- Compra SLL reembolsada, mas existe `sll_grants`, produto SLL/MSL ativo no perfil ou outra compra ativa que concede SLL.
- Refund pertence a outra pessoa, outro email nao confirmado ou outro produto.
- Status `refund_requested`, `chargeback`, `canceled`, `expired` ou `pending`: nao tratar como `refunded` sem regra propria.
- Ha promessa comercial, acesso vitalicio ou bundle nao materializado e ainda nao validado pelo owner.

## Evidencias e hard gates

1. Confirmar o produto solicitado no texto/contexto do ticket.
2. Resolver a identidade correta; ticket com multiplos emails permanece manual ate separar cada pessoa.
3. Consultar **todas** as compras da identidade, com `product_id`, status e datas relevantes.
4. Classificar cada `product_id` pelas familias vigentes SLL, MSL e LP; nao inferir pelo nome livre.
5. Ordenar cronologicamente e procurar compra posterior ativa (`complete` ou `approved`) do mesmo entitlement.
6. Consultar todas as fontes alternativas do entitlement solicitado:
   - SLL: compra SLL/MSL ativa, `profiles.hotmart_product_id` aplicavel e `sll_grants`;
   - LP: compra LP ativa, `profiles.hotmart_product_id` aplicavel e grandfather por `stores.owner_user_id`.
7. Quando existir conta, reler `public.get_user_entitlement(user_id)` como verificacao consolidada.
8. Somente produzir o sinal `derived:requested_product_access_refunded_without_later_active_entitlement` quando todos os gates acima forem verdadeiros.

Qualquer divergencia ou fonte de acesso ativa bloqueia o fechamento e reclassifica o caso para credencial, provisionamento, policy ou investigation.

## Diagnostico antes da acao

Registrar no pacote de evidencia, sem PII:

- produto solicitado;
- transacao/compra relacionada;
- status e data do refund;
- compras posteriores avaliadas;
- fontes alternativas de entitlement avaliadas;
- conclusao por produto (`sem direito vigente` ou `direito vigente encontrado`).

Nunca usar apenas `session.customData.has_refund`, uma linha historica isolada ou o status de uma compra de outro produto.

## Preview de writes

Depois de resolver ao vivo a key da lane Done, apresentar ao owner:

1. Nota interna exata:

   `[interno] A compra relacionada ao acesso solicitado foi confirmada como reembolsada. Nao existe compra posterior ativa nem outra fonte vigente que conceda acesso a este produto.`

2. Mudanca de status do ticket para a key ao vivo correspondente a **Done**.

Nao enviar mensagem visivel para a cliente. Nao criar, excluir ou alterar conta, grant, perfil, compra ou store.

## Passos de execucao

1. Reobter o ticket imediatamente antes dos writes.
2. Reconsultar a compra relacionada e as fontes de entitlement imediatamente antes dos writes.
3. Se o sinal derivado continuar verdadeiro, adicionar a nota interna com `isNote: true` e prefixo `[interno]`.
4. Atualizar o ticket para a lane Done resolvida ao vivo.
5. Nao atribuir responsavel; se uma atribuicao for solicitada separadamente, ela ocorre por ultimo.

Enquanto este playbook estiver `draft`, nenhum passo de escrita pode ser executado. O primeiro uso exige canario individual, preview e GO explicito.

## Verificacao de sucesso

- Reler o ticket e confirmar a nota interna presente uma unica vez.
- Confirmar que o status atual e a key Done resolvida no preflight.
- Confirmar que nenhuma mensagem publica foi enviada.
- Confirmar que nenhuma conta ou entitlement foi modificado.

## Parada e rollback

- Parar antes dos writes se aparecer compra ativa posterior, grant, entitlement vigente, identidade ambigua ou produto incerto.
- Se a nota foi criada mas a mudanca de status falhou, nao duplicar a nota; reler o ticket e reportar falha parcial.
- Se o ticket foi fechado por classificacao incorreta, reabrir somente com autorizacao explicita e registrar a correcao do owner; este playbook nao faz rollback autonomo.

## Edge cases observados

- Uma pessoa pode ter LP reembolsada e SLL ativo; o ticket SLL nao e encerrado por causa do refund LP.
- Uma pessoa pode ter MSL antigo reembolsado e uma compra posterior ativa; a compra posterior prevalece para o entitlement.
- Um bundle pode conceder mais de um produto; cada entitlement precisa ser avaliado separadamente.
- Acesso vitalicio prometido e nao materializado e policy/investigation ate validacao humana; nao equivale automaticamente a refund sem direito.

## Output para o report

- produto solicitado e fonte que seria concessora;
- compra refunded confirmada;
- ausencia/presenca de compra posterior ativa;
- fontes alternativas verificadas;
- nota interna e status apenas como `confirmed` depois da releitura;
- blockers, skips e correcoes de classificacao.
