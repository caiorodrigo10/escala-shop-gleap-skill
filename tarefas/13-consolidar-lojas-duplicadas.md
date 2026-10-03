# Tarefa 13 — Consolidar lojas duplicadas

**status: validated**

## Objetivo e escopo

Resolver tickets `BUG` em que uma única aluna possui várias stores da Loja
Pronta e o estado útil ficou dividido entre elas, por exemplo: conexão Shopee
em uma store e compra, identidade ou assets em outra.

Este procedimento consolida somente duplicidades causadas por uma única compra
LP ativa vigente. Ele não combina direitos de duas compras LP ativas
independentes e não altera uma loja que tenha produtos publicados.

## Sinais positivos

- Duas ou mais stores pertencem ao mesmo `owner_user_id`.
- Existe exatamente uma compra LP ativa e sem refund/chargeback.
- A store com maior progresso irreversível não possui o vínculo da compra ativa.
- Identidade, logo ou descrição úteis estão em outra store sem conexão Shopee.

Exemplos validados: ticket de exemplo e ticket de exemplo.

## Contraexemplos

- Duas compras LP ativas independentes: são duas lojas legítimas; não consolidar.
- Stores de usuários diferentes ou identidade ambígua: parar.
- Duplicada com `store_products`, anúncio Shopee, banner publicado ou outra
  saída irreversível: não excluir nem mover automaticamente.
- Refund sem recompra LP ativa posterior: usar `refunded-cleanup`.
- Duas conexões Shopee diferentes: decisão humana sobre qual loja manter.

## Precedência da loja principal

Escolher a store com o maior marco irreversível confirmado, nesta ordem:

1. Loja com produtos publicados ou fase publicada — bloqueia a consolidação
   automática e exige análise manual.
2. Shopee conectada e aprovada/ready.
3. Shopee conectada com KYC pendente.
4. Identidade completa: logo e descrição selecionados.
5. Logo selecionado.
6. Onboarding inicial.

Data de criação e `state_version` servem apenas como desempate. A compra ativa
é transferida para a principal; ela não vence uma conexão Shopee mais avançada.

## Evidências e hard gates

1. Reobter o ticket completo, mídias e ObjectId; confirmar `type=BUG` e lane
   ativa.
2. Confirmar uma única identidade por email/telefone e `owner_user_id`.
3. Ler a timeline completa de `hotmart_purchases`, incluindo todos os IDs LP,
   status e datas de refund/chargeback.
4. Exigir exatamente uma compra LP ativa aplicável. Compra histórica refunded
   permanece histórica e não invalida recompra posterior.
5. Listar todas as stores, journeys, conexões Shopee, produtos, generation
   runs, drafts, banners, waves, outbox e demais filhos relevantes.
6. Exigir que todas as stores candidatas pertençam ao mesmo owner.
7. Exigir zero produtos e zero publicação nas stores que seriam removidas.
8. Se principal e duplicada tiverem valores úteis conflitantes de identidade,
   logo ou descrição, parar e apresentar a escolha ao owner.
9. Reler constraints/FKs vigentes antes de preparar SQL; não reutilizar SQL
   histórico sem confirmar o schema.
10. Mostrar preview exato e obter GO destrutivo no contexto atual.

## Preview obrigatório

Para cada ticket, mostrar:

- ObjectId e bug ID;
- store principal, fase, conexão e motivo da precedência;
- compra ativa e vínculo final proposto;
- stores preservadas por refund;
- stores superseded que serão removidas;
- campos e rows transferidos, com contagens;
- dados que serão apagados por cascade ou convertidos para `NULL`;
- tags, lane e atribuição propostas;
- rollback possível antes do commit e irreversibilidade depois do delete.

O GO precisa citar o ticket ou lote exibido. Alterar os alvos exige novo preview.

## Execução

Executar uma transação SQL única, com assertions que abortam se qualquer estado
mudar entre preview e write:

1. Bloquear/revalidar stores, journeys e compra ativa pelos IDs esperados.
2. Liberar o vínculo único da transação na store superseded.
3. Transferir para a principal apenas os dados úteis confirmados no preview:
   nome, nicho, perfil, identidade, logo, descrição, generation runs e drafts.
4. Preservar a conexão Shopee já existente na principal; nunca mover ou expor
   tokens como parte deste playbook.
5. Vincular `stores.hotmart_transaction_id`, `hotmart_purchases.user_id` e
   `hotmart_purchases.store_id` à principal.
6. Manter stores de compra refundada com journey `refunded`.
7. Remover somente as stores superseded listadas no preview. O delete é
   permanente e só ocorre depois de todos os dados úteis terem sido movidos.
8. Se qualquer assertion, FK ou uniqueness falhar, toda a transação deve
   rollbackar; não compensar parcialmente.

Não existe SQL universal para colar: o statement deve conter IDs, estados,
contagens e assertions exatos do preview vigente.

## Verificação real

Após o commit, reconsultar e exigir:

- exatamente uma store operacional principal para a compra ativa;
- principal com transaction ID, `hotmart_purchases.user_id/store_id`, fase e
  conexão Shopee esperados;
- identidade/logo/descrição e contagens transferidas iguais ao preview;
- stores superseded ausentes;
- stores refunded preservadas e ainda em `refunded`;
- nenhum produto/anúncio perdido ou duplicado.

Somente após tudo passar:

1. adicionar `categoria:consolidar-lojas-duplicadas`, `skill:analisado` e
   `resolucao:lojas-consolidadas` com `add_ticket_tags`;
2. mover para a key ao vivo de `To Test`;
3. atribuir ao Support em chamada separada e por último.

Nota interna só pode ser adicionada se o texto exato tiver sido incluído no
preview e aprovado. Nunca enviar mensagem pública automaticamente.

## Parada e recuperação

- Antes do commit, qualquer divergência causa rollback completo.
- Depois do delete, a store superseded não é recuperável como registro. Os
  dados úteis devem estar comprovadamente na principal antes da exclusão.
- Se a consolidação no banco passou mas o Gleap falhou, não repetir o SQL.
  Reconsultar o banco e retomar somente tags/status/atribuição.
- Se a verificação pós-write divergir, manter o ticket aberto e escalar com os
  IDs técnicos, sem tentativa destrutiva adicional.

## Output para o report

Registrar principal, stores removidas/preservadas, compra vinculada, contagens
transferidas, assertions, verificações, writes Gleap e qualquer divergência.
Não registrar PII, tokens ou payloads integrais.
