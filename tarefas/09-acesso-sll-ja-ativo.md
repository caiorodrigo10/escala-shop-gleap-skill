# Tarefa 09 — Confirmar acesso SLL ja ativo e enviar para To Test

**status: draft**

## Objetivo e escopo

Tratar tickets em que a pessoa relata falta de acesso ao SLL, mas a conta autenticavel e o entitlement SLL ja estao ativos. O resultado e registrar uma nota interna objetiva e mover o ticket para To Test, sem criar ou alterar conta.

## Sinais positivos

- Identidade do email de acesso confirmada.
- Existe `auth.users` para o email confirmado.
- `public.get_user_entitlement(user_id)` retorna `hasSLL=true`.
- Nao existe bloqueio de refund relacionado que revogue o entitlement atual.

## Contraexemplos — nao executar

- Nao existe conta auth.
- `hasSLL=false` ou a RPC falha.
- A pessoa informou mais de um email e a identidade de acesso nao foi separada.
- O ticket agrupa varias pessoas e ainda existe qualquer pessoa sem diagnostico concluido.
- Existe apenas compra LP, sem compra/grant MSL ou SLL confirmado.

## Evidencias e hard gates

1. Confirmar o email correto da pessoa.
2. Confirmar `auth.users`, perfil e estado de credencial sem expor segredo.
3. Reler o entitlement consolidado pela RPC e exigir `hasSLL=true`.
4. Consultar compras e grants apenas para explicar a fonte do direito; uma fonte vigente basta.
5. Em ticket multi-identidade, concluir todas as pessoas antes de propor mudanca do status global do ticket.
6. Resolver ao vivo a key correspondente a To Test.

Somente produzir o sinal `derived:sll_account_and_entitlement_active` quando conta e entitlement estiverem confirmados.

## Preview de writes

Apresentar ao owner:

1. Nota interna exata:

   `[interno] A conta e o entitlement SLL ja estao ativos para o email informado. Encaminhado para To Test para validacao do acesso.`

2. Mudanca para a key ao vivo correspondente a **To Test**.

Nao enviar mensagem publica. Nao criar conta, trocar senha, enviar magic link ou alterar entitlement.

## Passos de execucao

1. Reobter o ticket.
2. Reconsultar conta e entitlement imediatamente antes dos writes.
3. Se o ticket for multi-identidade, confirmar que todos os subcasos estao resolvidos; caso contrario, parar sem writes.
4. Enviar a nota interna com `isNote: true`.
5. Atualizar o ticket para To Test.

Enquanto `draft`, o primeiro uso exige canario individual, preview e GO.

## Verificacao

- Nota interna presente uma unica vez.
- Status relido como a key To Test resolvida ao vivo.
- Nenhuma mensagem publica enviada.
- Conta e entitlement permanecem inalterados.

## Parada e rollback

- Parar se conta/entitlement divergirem, se houver identidade ambigua ou subcaso pendente.
- Se a nota foi criada e o status falhou, nao duplicar a nota; reler e reportar falha parcial.
- Reverter status somente com autorizacao explicita e registrar a correcao.

## Edge cases

- Uma compra LP reembolsada nao impede SLL quando existe grant ou compra MSL/SLL vigente.
- Uma compra MSL antiga reembolsada nao impede SLL quando existe compra posterior ativa.
- `must_change_password` ou tentativa de recovery descrevem credencial; nao anulam entitlement.
- Um ticket com varias pessoas nao pode ir para To Test enquanto uma delas permanecer em investigation.

## Output para o report

- conta e entitlement confirmados;
- fonte resumida do direito;
- nota/status propostos ou confirmados;
- blockers de identidade ou subcasos pendentes;
- garantia de nenhuma alteracao de conta.
