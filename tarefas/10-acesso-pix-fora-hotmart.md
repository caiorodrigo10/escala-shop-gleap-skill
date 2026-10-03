# Tarefa 10 — Investigar acesso comprado por PIX fora da Hotmart

**status: active**

## Objetivo

Tratar tickets de acesso SLL/MSL ou Loja Pronta em que nenhuma compra valida aparece na Hotmart porque o pagamento foi realizado por PIX direto, fora do checkout da Hotmart.

Este playbook nao presume direito apenas pela ausencia na Hotmart. A fonte alternativa precisa comprovar a identidade, o pagamento e o produto/oferta vendidos.

## Sinais positivos

- O ticket pede acesso, mas a busca Hotmart historica completa nao encontra compra `APPROVED` ou `COMPLETE` aplicavel.
- O owner ou o Support informa que o pagamento ocorreu por PIX direto.
- Existe linha em planilha de pagamentos externos ou confirmacao explicita do owner para a pessoa investigada.

## Contraexemplos

- Tentativa PIX criada dentro da Hotmart e depois `CANCELLED`: continua sendo compra nao efetivada.
- Transferencia encontrada, mas sem identidade suficiente para ligar ao ticket.
- PIX de outro produto: nao concede automaticamente SLL, MSL ou Loja Pronta.
- Refund posterior relacionado ao mesmo pagamento/produto: usar o playbook de acesso reembolsado.

## Evidencias e hard gates

1. Identificar o email e, quando necessario, o nome completo informados no ticket.
2. Consultar a Hotmart em todo o historico relevante, dividido em janelas aceitas pela API; nunca limitar silenciosamente ao ano atual.
3. Consultar conta, perfil, grants e entitlement atuais antes de propor criacao ou alteracao.
4. Buscar a pessoa na planilha de PIX externos por email e nome. A planilha deve estar publica ou compartilhada com a conexao ativa.
5. Se a planilha estiver inacessivel, aceitar como evidencia alternativa somente uma confirmacao explicita do owner de que aquela pessoa pagou por PIX fora da Hotmart.
6. Exigir identificacao do produto/oferta, do direito vendido e da duracao. Confirmacao generica de que "pagou um PIX" nao basta para escolher SLL, LP ou ambos, nem para presumir acesso vitalicio.
7. Se a duracao for limitada, exigir mecanismo tecnico com expiracao automatica e auditavel. `sll_grants` sem `expires_at` e contraexemplo: a linha concede acesso permanente e nao pode ser usada para representar um ano.
8. Nao persistir valor, CPF, comprovante integral ou outros dados financeiros na fila de aprendizado ou na nota Gleap.

Se os gates 5 e 6 nao forem satisfeitos, parar como `investigation` e perguntar ao owner qual produto/acesso foi vendido.

## Diagnostico antes da acao

Classificar um dos resultados:

- `pix_sll_msl_confirmado`: evidencia alternativa confirma oferta MSL/SLL e a duracao exata do direito.
- `pix_lp_confirmado`: evidencia alternativa confirma Loja Pronta; seguir o fluxo standalone aplicavel somente depois de validar seus gates.
- `pix_combo_confirmado`: evidencia confirma explicitamente ambos; executar cada provisionamento sem inferir um pelo outro.
- `pix_produto_nao_identificado`: pagamento confirmado, produto/direito ainda ambiguo; nenhuma escrita.
- `pix_duracao_sem_suporte_tecnico`: produto e prazo confirmados, mas o entitlement atual nao expira automaticamente; nenhuma escrita ate existir mecanismo seguro.
- `pix_nao_confirmado`: nem planilha nem owner confirmam; nenhuma escrita.

## Preview obrigatorio de writes

Antes de qualquer provisao, mostrar ao owner:

- destinatario exato;
- fonte da confirmacao (`planilha_pix` ou `owner_confirmou_pix_externo`);
- produto/oferta e entitlement que serao concedidos;
- inicio, fim e mecanismo automatico de expiracao quando o acesso for temporario;
- conta, perfil, grant, store/journey e workflows que serao criados ou preservados;
- mensagem GHL ou email que sera disparado;
- nota interna e mudanca de status propostas no Gleap.

Pedir GO para esse unico caso. Draft nunca executa escrita externa nem roda em lote.

## Passos de execucao apos validacao futura

1. Reconsultar ticket, conta e entitlement imediatamente antes da escrita.
2. Usar o fluxo canonico do entitlement confirmado; nao forjar uma transacao Hotmart inexistente e nao representar acesso temporario com grant permanente.
3. Registrar uma origem auditavel que diferencie PIX externo de webhook/backfill Hotmart.
4. Disparar somente o workflow correspondente ao produto confirmado.
5. Adicionar nota interna sem senha, token, valor do PIX ou dados bancarios.
6. Atualizar status somente pela lane resolvida ao vivo e aprovada no preview.

## Verificacao de sucesso

- Conta autenticavel existe para o email aprovado.
- RPC de entitlement confirma somente os acessos vendidos.
- Grant/store/journey possuem origem auditavel de PIX externo, quando aplicavel.
- Acesso temporario possui data final e a RPC deixa de retornar o entitlement depois dela sem depender de lembrete manual.
- Workflow aprovado aparece como enviado, sem erro terminal.
- Nota interna e status do ticket foram relidos.

## Parada e rollback

- Parar antes de escrever se planilha e owner divergirem, se o produto estiver ambiguo ou se houver refund relacionado.
- Parar antes de escrever quando o prazo for limitado e a fonte de entitlement nao possuir expiracao automatica.
- Parar na primeira falha de provisao; nao enviar mensagem afirmando sucesso parcial.
- Se conta foi criada mas grant/workflow falhou, manter o ticket aberto e registrar apenas uma nota interna aprovada descrevendo o estado parcial.
- Nunca remover acesso existente como compensacao automatica.

## Output para report

- fonte de evidencia alternativa;
- classificacao PIX;
- produto/entitlement confirmado;
- writes propostos/executados;
- verificacao e divergencias;
- decisao pendente do owner, sem PII financeira.

## Edge cases observados

- Caso ilustrativo: pessoa sem conta e com varias tentativas MSL `CANCELLED` na Hotmart; owner informou pagamento por PIX direto e indicou uma planilha externa como possivel fonte.
- Para esse caso, o owner confirmou SLL por um ano, sem certeza de vitaliciedade. O schema atual de `sll_grants` nao tem `expires_at`; conceder por ele seria permanente e esta bloqueado.
- Link da planilha pode existir, mas a conexao Google Drive nao ter permissao. Nesse caso, nao usar navegador autenticado sem autorizacao; pedir link publico, compartilhamento ou confirmacao explicita do owner.
- Caso ilustrativo: canario individual de SLL vitalicio confirmado pelo owner. Conta Auth, profile `aluna` e grant auditavel foram criados; a releitura confirmou `hasSLL=true` e `SLL_ONLY`, sem store, journey ou mensagem externa. Depois da promocao aprovada, os demais subcasos foram executados sequencialmente e as 12 identidades foram verificadas com `hasSLL=true` antes da mudanca para `TOTEST`.
