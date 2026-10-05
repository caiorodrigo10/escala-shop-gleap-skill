# Tarefa 34 — Loja conectada na conta Shopee errada (familiar)

<!-- execucao-v2 -->
> **Execução:** `cat:34-conta-shopee-errada` (alias `cat:00-conta-shopee-errada`) = **com_go**. Tags só por união.
<!-- /execucao-v2 -->

> **Tags:** `cat:34-conta-shopee-errada` + `skill:*`. Alias legado: `cat:00-conta-shopee-errada`. Tag legada: `categoria:conta-shopee-errada`.

**Status:** `validated` — decisão do Caio (ligação 04/10; execução #9695 em 05/10)  
**Versão:** 1  
**Canônico:** `references/known-case-solutions.md` seção "Loja conectada na conta Shopee errada…"

## Quando usar

Loja Pronta conectada na conta Shopee de outra pessoa (ex.: familiar); aluna quer a própria conta.

## Passos operacionais (resumo)

1. SELECT: loja + conexão (shop_id/nome/datas, sem tokens); `store_products` sem publicação; `archived_at` NULL.
2. Se já houver anúncio na conta do terceiro → parar e perguntar ao Caio.
3. Com GO: `DELETE` só da `shopee_connections` errada (não arquivar LP). Ver also known-case #4319 / desconectar sem arquivar.
4. Nota interna + To test + tags `cat:34-conta-shopee-errada`, `skill:analisado`.
5. Aluna reconecta via OAuth da Loja Pronta.

## Proibições

- Arquivar/excluir Loja Pronta.
- Desconectar sem GO.
- Mensagem à aluna / DONE sem GO próprio.
