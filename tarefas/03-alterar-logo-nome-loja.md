# Tarefa 03 — Logo/Nome da Loja orientado por feedback

**Status:** `validated`
**Revisão:** 2026-09-04 — canários ticket de exemplo, ticket de exemplo e ticket de exemplo verificados
**Execução externa:** individual, após preview e GO aplicável

Trata tickets `BUG` de alterar, corrigir ou trocar logo/nome de loja. Este documento substitui a política anterior que tratava lojas publicadas como bloqueadas sem uma rota de substituição segura.

> O histórico demonstrou que títulos semelhantes escondem causas diferentes. O procedimento está validado para repetição individual, mas não autoriza geração, upload, update Shopee, nota, tag, status ou mensagem sem preview e GO explícito aplicável.

## Casos validados em 2026-09-04

- **ticket de exemplo — rename antes da seleção:** atualizar `stores.name` e
  `identity_inputs.nome_loja_shopee`, gerar primeiro três logos e três
  descrições novas, verificar grafia/textos e só então desativar os assets
  antigos. Não selecionar pela aluna. Resultado confirmado: três logos e três
  descrições ativas com `AVRA STORE`; histórico antigo preservado inativo.
- **ticket de exemplo — rename corrigido pela metade:** quando nome e logo já estão certos,
  mas descrições ainda citam o nome antigo, gerar primeiro três descrições de
  catálogo com o nome atual, verificar os textos e desativar somente as
  descrições antigas divergentes. Resultado confirmado para `Sato Express`.
- **ticket de exemplo — seleção não reconhecida após publicação:** se existem três
  candidatas corretas prontas, não gerar novamente. Preservar a logo publicada
  no histórico, desativar sua seleção local, reabrir a fase de escolha e
  corrigir por substituição literal todas as descrições que carregam o nome
  incompleto. A publicação antiga permanece na Shopee até a aluna escolher;
  o fluxo normal volta a sincronizar a nova escolha quando ela concluir a fase.
- **ticket de exemplo e ticket de exemplo — logo própria em loja publicada:** baixar e inspecionar o
  anexo, persistir o arquivo no bucket `store-logos`, criar/reusar um
  `generation_run` de origem `support_identity_replacement`, preservar os
  assets anteriores, atualizar o ponteiro local e publicar a nova imagem no
  perfil Shopee. Confirmar por leitura do perfil Shopee antes de mover o ticket
  para `To Test`; não alterar o nome público da loja.

## Resultado esperado

O procedimento deve entregar exatamente o que o feedback concreto da aluna pede, sem escolher por ela quando a logo ainda não foi publicada e sem degradar uma vitrine já publicada.

- Logo não selecionada, ou selecionada mas não publicada: três novas variações disponíveis para a aluna escolher.
- Logo selecionada e publicada: uma nova candidata aprovada visualmente, substituída somente depois de estar pronta; o resultado precisa ser confirmado localmente e na Shopee.
- Logo própria utilizável: o arquivo exato é usado, sem recriação por IA.
- Correção de nome: logo e descrição refletindo o nome final; a descrição sofre apenas troca literal do trecho do nome antigo.
- O nome público da loja na Shopee é fora do escopo da equipe. A aluna pode alterá-lo se quiser.

## Sinais positivos

- Pedido diz o nome final exato, quando a alteração envolve nome.
- Feedback descreve a mudança visual pedida; referência/anexo existe quando aplicável.
- Ticket descreve logo própria e há arquivo utilizável anexado.
- Loja e estado de seleção/publicação podem ser ligados ao ticket por ID técnico confirmado.
- Em relato de divergência, é possível ler estado local, asset/descrição selecionados e vitrine Shopee.

## Contraexemplos e paradas imediatas

- “Não gostei” sem mudança visual concreta, nome final ou referência: não gerar.
- Logo própria sem anexo, arquivo corrompido ou não utilizável: pedir reenvio; nunca improvisar e nunca gerar por IA.
- Pedido para mudar somente o nome público da Shopee: fora do escopo.
- Status local afirma seleção/publicação, mas faltam evidências do que a aluna vê: investigar a divergência antes de alterar qualquer asset.
- Falha de geração, upload, OAuth, atualização Shopee ou verificação visual: preservar o estado anterior, registrar bloqueio e pedir nova decisão; nunca repetir automaticamente.

## Hard gates antes de qualquer canário

1. Ticket é `BUG` e está em lane elegível resolvida ao vivo.
2. Detalhe, comentários e toda mídia acessível foram lidos; mídia obrigatória foi inspecionada visualmente.
3. Feedback mínimo está completo:
   - nome final exato, quando houver rename;
   - mudança visual descrita;
   - referência/anexo, quando houver logo própria ou arte de referência.
4. Loja, fase, asset/descrição selecionados, publicação, cota/runs e eventuais falhas recentes foram lidos em modo read-only.
5. Para loja publicada, a rota de atualização de logo/descrição na Shopee e suas pré-condições estão confirmadas ao vivo, sem probe OAuth implícito.
6. Para qualquer write, existe preview por etapa e GO explícito do owner para aquele ticket.

## Diagnóstico obrigatório

### 1. Determinar o ramo correto

| Ramo | Condição | Resultado de diagnóstico |
|---|---|---|
| A — feedback insuficiente | Falta nome final, mudança concreta ou referência necessária | Investigation; não gerar |
| B — logo própria | Arquivo utilizável enviado pela aluna | Aplicar arquivo exato no ramo de publicação correspondente |
| C — não selecionada | Nenhuma logo selecionada | Gerar três variações; aluna escolhe |
| D — selecionada e não publicada | Existe seleção local, sem publicação | Gerar três variações; aluna escolhe novamente |
| E — selecionada e publicada | Há seleção e publicação confirmadas | Gerar uma candidata, preservar anterior e substituir só após validação |
| F — nome/descritivo divergente | Relato e dados local/Shopee não concordam | Auditar os três lados antes de escolher outro ramo |

### 2. Auditoria de divergência

Quando houver relato de logo ou nome antigo apesar de registro local de alteração, comparar:

1. nome e asset/descrição selecionados localmente;
2. conteúdo real da logo e da descrição selecionadas;
3. logo e descrição atualmente exibidas na Shopee.

Corrigir apenas a divergência confirmada. Não assumir que uma tag antiga, um run `ready` ou uma atualização sem erro representa o que a aluna vê.

### 3. Correção de nome

O nome informado pela aluna é a fonte para os nossos dados e assets. Para casos de rename, atualizar primeiro o nome dentro do nosso sistema e só então gerar as três novas logos com esse nome. Atualizar:

- logo, seguindo o ramo de seleção/publicação;
- somente o trecho que contém o nome antigo na descrição;
- outro asset somente se a leitura demonstrar que ele exibe o nome antigo.

Não alterar o nome público da Shopee e não reescrever criativamente a descrição. Se a substituição literal deixar a frase estranha, a decisão do owner é manter a troca literal.

## Preview de writes obrigatório

O preview do canário deve separar claramente:

1. geração de uma ou três candidatas, com custo/efeito declarado;
2. upload/registro de logo própria, quando aplicável;
3. atualização local do asset selecionado e/ou descrição;
4. atualização de logo e descrição na Shopee, somente para o ramo publicado;
5. verificação visual pós-atualização;
6. qualquer nota, tag, status ou atribuição, em chamadas separadas e somente depois da confirmação técnica.

O preview deve declarar explicitamente que não muda `shop_name`/nome público da Shopee.

## Execução prevista por ramo

### Ramo C/D — sem publicação

1. Gerar três variações baseadas apenas no feedback aprovado.
2. Confirmar que as três estão disponíveis e correspondem ao feedback.
3. Não selecionar automaticamente nenhuma opção.
4. A intervenção é considerada concluída quando as três opções podem ser escolhidas pela aluna; a seleção permanece pendente dela.

### Ramo B/E — logo própria ou loja publicada

1. Confirmar que o arquivo é uma logo utilizável ou que a candidata gerada atende ao feedback.
2. Para publicada, manter logo anterior ativa enquanto a nova candidata é gerada e aprovada visualmente.
3. Só depois atualizar localmente e atualizar logo/descrição na Shopee.
4. Reler estado local e inspecionar visualmente a vitrine Shopee.
5. Não declarar sucesso se uma das duas superfícies divergir.

## Falha e recuperação

- Falha antes da substituição: preservar logo/descrição anterior e interromper.
- Falha durante ou após atualização parcial: parar, reler ambos os estados, preparar preview de rollback específico e pedir novo GO.
- Nunca apagar assets anteriores antes de nova candidata pronta e visualmente aprovada.
- Nunca fazer retry automático.

## Verificação de sucesso

| Ramo | Critério |
|---|---|
| Sem publicação | Três opções novas disponíveis para seleção e correspondentes ao feedback |
| Logo própria sem publicação | Arquivo exato disponível para seleção ou aplicado conforme a fase permitir |
| Publicada | Nova logo e descrição corretas localmente e visualmente na Shopee, com a anterior preservada até a troca |
| Correção de nome | Nome final presente na logo; descrição contém a substituição literal esperada; outros assets só mudaram quando exibiam o nome anterior |

## Canary e promoção

- Selecionar exatamente um ticket sem ambiguidade e com todos os hard gates atendidos.
- Exibir o preview integral e pedir GO explícito apenas para esse ticket.
- Se passar com verificação real, mudar `draft -> validated`, registrar o resultado e manter repetição somente individual com novo GO.
- Promover a `active` somente após confirmação do owner de que o padrão é geral e todos os contraexemplos/riscos permanecem cobertos.

## Report

O report do canário deve registrar apenas IDs técnicos necessários, ramo escolhido, evidências, preview, writes realmente confirmados, verificação e qualquer divergência/rollback. Nunca incluir PII, URL privada, token ou payload integral.
