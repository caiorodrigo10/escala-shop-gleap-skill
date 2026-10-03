# Tarefa 07 — Anúncio/Loja Banida ou Excluída pela Shopee

Trata "anúncio excluído", "subir novamente", "produto banido", "loja inativa", "produtos não aparecem".

> Criada em 2026-08-04, depois de uma sondagem real de 150 anúncios. Antes disso a categoria era triada só pelo relato da aluna — e o relato erra. **Este é o maior bloco do backlog (22 tickets numa varredura só).**

---

## A regra que resume tudo

**O banco pode estar atrasado.** Em uma sondagem historica, `store_products.shopee_item_status` divergiu da Shopee em 8 de 8 casos analisados. Use esse campo como indicio, nunca como prova; consulte a API ao vivo.

Nunca classifique, responda ou execute com base no que o banco diz sobre status de item. **Sonde a Shopee primeiro.**

---

## Passo 1 — Sondar (SEMPRE, antes de qualquer coisa)

Script pronto e reusável: `scripts/probe-shopee-item-status.ts`

```bash
pnpm exec tsx scripts/probe-shopee-item-status.ts --store-id=<uuid>
# opcional: --item-id=<shopee_item_id> (pode repetir) e --json
```

Chama `get_item_base_info` para os `shopee_item_id` da loja e lê o `item_status` real.

O script usa `createShopeeClientFromStore`; nunca leia ou injete token cru. Ele nao altera tickets, anuncios ou `store_products`, mas pode renovar e persistir o token OAuth se estiver perto de expirar. Se a rede estiver bloqueada, solicite egress apenas para Supabase/Shopee.

A sondagem é barata, somente-leitura e costuma **resolver o ticket sozinha**: na primeira rodada, 142 de 150 anúncios estavam no ar. Boa parte das queixas é sobre algo que não aconteceu, ou que atingiu 1 item entre 30.

---

## Passo 2 — Ler o status certo

| `item_status` | O que significa | Republicar? |
|---|---|---|
| `NORMAL` | Está no ar | ❌ Não há o que fazer — a queixa é outra coisa |
| `SHOPEE_DELETE` | **A Shopee** removeu | Candidato — mas ver Passo 3 |
| `SELLER_DELETE` | Exclusão registrada como ação do seller | Somente pelo gate contextual do ticket; isoladamente, não |
| `REVIEWING` | Em análise | ❌ Não é remoção. Esperar |
| `BANNED` | **A Shopee** baniu o item | Candidato à reposição segura — mas ver Passos 3 e 6 |
| outros | Ler caso a caso | — |

**Não confundir `SELLER_DELETE` com `SHOPEE_DELETE`.** O estado isolado continua
insuficiente. Exceção estreita: ticket `BUG` da própria cliente reclamando da
remoção, item alvo identificado, exatamente um `SELLER_DELETE` ao vivo na loja e
GO explícito do owner. Nesse contexto o status entra como fato do caso, não como
prova de violação pela Shopee.

**`REVIEWING` antigo (semanas) é suspeito.** Comparar o `item_name` da Shopee com o nosso `final_title`: se divergir, **a aluna editou o anúncio à mão**. Republicar apaga o trabalho dela. Caso real: `"TENIS MASCULINO SPORT ESP"` na Shopee vs. título completo no nosso banco.

---

## Passo 3 — Checar recorrência do SKU (diagnóstico, não gate de reposição)

Antes de tratar como caso da aluna, verificar se o mesmo produto caiu em outras lojas:

```sql
SELECT p.id, left(p.title,60) AS produto,
       count(sp.id) AS lojas_com_o_produto,
       count(sp.id) FILTER (WHERE sp.shopee_item_id IS NOT NULL) AS publicado_em
FROM store_products sp JOIN products p ON p.id = sp.product_id
WHERE p.id = (SELECT product_id FROM store_products WHERE id = $STORE_PRODUCT_ID)
GROUP BY 1,2;
```

**Se o produto aparece em dezenas/centenas de lojas, o problema é do catálogo, não da aluna.** Caso confirmado: `TENIS SLIP ON` (`<uuid>`) — 647 lojas, 612 publicações, e a Shopee vem derrubando em massa.

Nesse cenário **republicar é contraindicado**: o mesmo conteúdo cai de novo e vira 2ª infração na conta da aluna — caminho para suspensão da loja. Escalar como problema de curadoria de catálogo.

Recorrência ajuda a diagnosticar o risco, mas não é requisito para repor. Uma
remoção isolada confirmada como `SHOPEE_DELETE` ou `BANNED` também pode seguir
para o Passo 6 quando todos os gates e a whitelist estiverem válidos.

---

## Passo 4 — `get_item_base_info` NÃO diz por que caiu

Conferido no payload cru: `deboost`, `item_dangerous` e afins vêm neutros em 100% dos removidos. **Não existe campo de motivo.**

Para saber a razão: Seller Center da loja (só a aluna ou alguém com acesso), ou outro endpoint ainda não implementado aqui.

Consequência prática: **não afirme o motivo na nota**. Peça à aluna que veja no painel dela.

---

## Passo 5 — Republicação

O fluxo versionado atual nao oferece republicacao isolada segura: `shared/lib/publication/publishWave.ts` opera por loja e wave, e a rota admin impede re-publicar quando ja existem produtos publicados. Confirme o codigo atual antes de afirmar que isso mudou.

Enquanto não existir, a nota deve deixar claro que não vamos recolocar o anúncio. Dois fatos obrigatórios na resposta:

- A Shopee **não restaura** item deletado: cria outro, com link novo e **sem o histórico de visitas e avaliações**
- Se a remoção foi por violação, republicar igual **repete a infração**

---

## Templates de nota

### 5a. Sondagem mostrou tudo `NORMAL`

```
[interno] Sondei os {N} anúncios da loja direto na Shopee: todos estão no ar,
nenhum removido.

Como responder: pedir à aluna que aponte qual anúncio especificamente ela não
encontra, com print ou link. Pode ser vitrine demorando a atualizar, filtro de
busca, ou ela olhando outra conta.

Não afirmar que "está tudo certo" de forma seca — perguntar o que ela vê.
```

### 5b. `SHOPEE_DELETE` confirmado, SKU sistêmico

```
[interno] Confirmei na Shopee: o anúncio foi mesmo removido por ela.

Mas não é caso isolado desta aluna — o mesmo produto foi derrubado em
{N} lojas. É rejeição de catálogo, não algo que ela fez.

Não vamos republicar: subir o mesmo item de novo tende a cair outra vez, e
reincidência pesa contra a conta dela.

Como responder: reconhecer a remoção, deixar claro que a causa é do produto e
não da loja dela, e que os próximos produtos entram normalmente.
Não prometer recolocar este item.
```

### 5c. `SELLER_DELETE`

```
[interno] Esse anúncio consta como excluído pela PRÓPRIA conta da aluna, não
pela Shopee.

Como responder: confirmar com ela se foi ela mesma que apagou. Se foi sem
querer, aí sim avaliamos. Não recolocar sem essa confirmação.
```

---

## Passo 6 — Reposição por catálogo local do mesmo fornecedor

Quando `SHOPEE_DELETE`/`BANNED` for confirmado, ou quando `SELLER_DELETE` passar
integralmente pelo gate contextual acima, **não republicar o mesmo SKU** continua
sendo o guardrail. A reposição avalia outro produto do
**mesmo fornecedor canônico da loja**, independentemente de a remoção ser
isolada ou sistêmica.

### Invariante do owner

**É proibido misturar fornecedores em uma loja.** O candidato precisa ter o mesmo `products.supplier_id` do produto removido e do fornecedor canônico da loja. Categoria, preço ou disponibilidade não justificam trazer produto de fornecedor diferente.

Se a identidade do fornecedor estiver ambígua ou a loja tiver fornecedores divergentes no histórico, parar em `investigation`; não escolher o fornecedor mais conveniente.

### Gates de candidato

Antes de apresentar uma reposição, exigir todos:

1. vínculo do ticket ao `store_product` removido, produto e fornecedor exatos — não tratar todo o catálogo da loja como removido;
2. produto ativo, com estoque registrado, categoria e imagens, ainda ausente em `store_products` da loja;
3. triagem de título, marca/modelo, metadados e imagens relevantes;
4. exclusão de marca/logo, personagem, termo licenciado, réplica/cópia e variante materialmente equivalente ao produto/risco removido;
5. classificação explícita `BLOCKED`, `UNKNOWN` ou `SAFE_CANDIDATE`.

`SAFE_CANDIDATE` só libera a curadoria da whitelist: não cria `store_products`,
não gera conteúdo, não chama OAuth/fal.ai/Shopee e não publica. A entrada ativa
em `replacement_products` representa aprovação humana prévia daquele produto e
fornecedor; existir em `products` ou receber o rótulo automaticamente não basta.

### Descoberta registrada em 2026-08-31

A análise de 16 tickets BUG encontrou 53 candidatos únicos do fornecedor correto: 41 passaram no screening inicial, 5 foram bloqueados (Labubu, Batman ou sapatilha semelhante ao Slip On removido) e 7 ficaram `UNKNOWN`. O padrão comprovado em 9 tickets com mídia foi risco de PI/réplica em tênis feminino Slip On/sem cadarço. Os números são um snapshot de evidência, não autorização de publicação.

A especificação está em `docs/stories/LP-SHOPEE-REPLACEMENT-SAFETY-1.story.md`.
Quando todos os gates acima estiverem presentes, despachar a categoria secundária
`shopee-listing-replacement` e carregar `11-repor-anuncio-shopee.md`. Ela usa
somente produtos já persistidos em `products` e explicitamente whitelisted em
`replacement_products`; não consulta nem sincroniza a API da Envio Velox.

O playbook está `active` desde 2026-09-02. Executar `preview` e obter GO explícito
do owner antes de `apply`, preservando todos os gates e verificações documentados.
O executor já reutiliza o padrão canônico da wave para título, descrição e
imagem; detalhes e verificações estão em `11-repor-anuncio-shopee.md`.

---

## Status e tags

| Situação | Status | Tags |
|---|---|---|
| Tudo `NORMAL` | `TOTEST` | `skill:analisado`, `categoria:shopee-baniu-excluiu`, `skill:sondado-tudo-normal` |
| `SHOPEE_DELETE`, SKU sistêmico | `TOTEST` | + `blocker:sku-sistemico` |
| `SHOPEE_DELETE` ou `BANNED`, reposição elegível | manter durante execução; depois `TOTEST` | + `categoria:shopee-listing-replacement` |
| `SELLER_DELETE` sem gate contextual | `TOTEST` | + `skill:precisa-conferencia-aluna` |
| `SELLER_DELETE` com gate contextual e reposição elegível | manter durante execução; depois `TOTEST` | + `categoria:shopee-listing-replacement` |
| `REVIEWING` | `TOTEST` | + `skill:precisa-conferencia-aluna` |

Regras gerais de escrita (ObjectId, 2 chamadas por causa do `processingUser`) em `../SKILL.md`.

---

## NÃO fazer

- ❌ Classificar por `store_products.shopee_item_status` — erra em 100%
- ❌ Republicar sem sondar — duplica item que está vivo
- ❌ Tratar `SELLER_DELETE` isolado como remoção elegível
- ❌ Afirmar o motivo da remoção — a API não entrega
- ❌ Republicar SKU sistêmico — repete a infração na conta dela

---

## Referências

- Probe reutilizavel: `scripts/probe-shopee-item-status.ts`
- Cliente autenticado: `shared/lib/shopee/client.ts`
- Persistencia/sync historico: `scripts/backfill-shopee-item-statuses.ts`
- Publicacao por wave: `shared/lib/publication/publishWave.ts`
- Guard de re-publicacao: `app/api/lojapronta/internal/admin/publish-store/[storeId]/route.ts`
