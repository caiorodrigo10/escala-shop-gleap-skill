# Tarefa 26 — Troca de fornecedor: limpar catálogo e devolver à seleção

<!-- execucao-v2 -->
> **Execução (modelo v2 de 04/10/2026; prevalece sobre o resto deste arquivo):** `cat:26-troca-fornecedor` (alias `fila:troca-fornecedor`) = **com_go** (ação em produção: limpar Shopee/DB e resetar fase). Quem decide é a coluna `execucao` do SQLite; execução por categoria com `commands/fechar-categoria.py` (solução nova: 1 ticket, conferir, depois o resto). Tags só por união.
<!-- /execucao-v2 -->

> **Tags (padrão v4):** problema `cat:26-troca-fornecedor` + `skill:analisado` (ou `skill:impedido` / `skill:executado`); o estado fica nas tags do Gleap e o motivo na nota `[interno]`. Tags legadas possíveis: `categoria:troca-fornecedor`, `categoria:fornecedor-reset`, `categoria:fornecedor-incorreto` (não remover).

**Status:** `validated` — decisão do Caio em 05/10/2026 (~13h36 BRT)  
**Versão:** 3 (substitui o procedimento de remount / republicar StockShop)  
**Casos de referência:** #8517, #8699

## Objetivo e regra do owner (05/10/2026)

Quando a aluna ficou com o **fornecedor errado** (bug ou engano) e a troca foi autorizada:

1. **Não** fazer remount forçado nem publicar as 3 waves do fornecedor novo pela gente.
2. **Limpar** no banco o catálogo / vínculo de fornecedor / `store_products` do fornecedor errado.
3. Se ainda houver anúncios do outro fornecedor **na Shopee**, apagar esses anúncios (`delete-items`, reason `supplier_swap`) e conferir ao vivo.
4. **Devolver a loja à etapa de seleção de fornecedor e produtos** (fase da jornada que permite a aluna escolher de novo — tipicamente a partir de `2.5_shopee_conectada` / entrada em `2.6_browsing_catalogo`, sem desconectar a Shopee).
5. Nota interna avisando o **suporte** para orientar a aluna a **escolher os produtos** que quer.
6. Mover o ticket para **To test**. Sem mensagem à aluna e sem `DONE`.

**“Desvincular” aqui = só limpar catálogo/fornecedor no DB (+ anúncios Shopee do fornecedor errado).**  
**Não** desconectar a conta Shopee e **não** arquivar a Loja Pronta.

## Quando carregar

Tickets com `cat:26-troca-fornecedor` / `fila:troca-fornecedor` (ou aliases) pedindo troca de fornecedor / reset de catálogo / “montar StockShop no lugar de Niterói” etc.

## Pré-checagens (só SELECT)

1. Confirmar loja, conexão Shopee ativa e KYC (se a sessão estiver expirada → tarefa 18).
2. Confirmar fornecedor atual dos `store_products` (`products.supplier_id` → `suppliers`).
3. Conferir ao vivo na Shopee (`items-status` / `store-diagnosis`, começando com `live:false`): quantos `NORMAL` ainda existem do fornecedor errado.
4. Se o catálogo **já** estiver limpo e a fase **já** estiver na seleção: só nota + To test (ticket desatualizado).

## Procedimento (com GO do lote)

### A) Shopee — só se ainda houver produtos do outro fornecedor no ar

1. `delete-items` dry_run → plan_hash → live com `confirm_store_id` + `Idempotency-Key`, reason `supplier_swap`.
2. Conferir ao vivo: `remote NORMAL` do fornecedor errado = 0.
3. Se `shopee_ops_runs` ficar `reconcile_required`, destravar só depois da conferência e só com `UPDATE … WHERE id = '<run_id>' AND status = 'reconcile_required'`.

### B) Banco — limpar catálogo / fornecedor

1. Remover ou anular os `store_products` (e vínculos de catálogo/fornecedor da loja) do fornecedor errado, no caminho oficial/documentado — **sem** inventar rota e **sem** desconectar `shopee_connections`.
2. Reconciliar `status_db` local com o remoto quando a Shopee já estiver `SELLER_DELETE` e o DB ainda mostrar `NORMAL` (só alinhamento, não remount).
3. Zerar / ajustar timestamps de wave da jornada conforme o reset de fase (para o sistema não tentar republicar o fornecedor errado).

### C) Jornada — devolver à seleção

1. Colocar `journey_state.current_phase` na etapa em que a aluna **escolhe fornecedor e produtos** de novo (manter Shopee conectada).
2. Não escolher fornecedor nem produtos pela aluna.
3. Não publicar waves neste procedimento.

### D) Gleap

1. Nota `[interno]` (modelo abaixo) + tags por união: `cat:26-troca-fornecedor`, `skill:analisado`, e ao concluir `skill:executado` (trocando `skill:impedido` se existir).
2. Status **To test**.
3. Registrar apply-log do dia.

## Modelo da nota interna

```text
[interno] O catálogo do fornecedor anterior foi limpo na plataforma{ e os anúncios dele foram removidos da Shopee, se ainda existiam}. A loja voltou para a etapa de escolher fornecedor e produtos. A conexão com a Shopee foi mantida.

Falta: o suporte avisar a aluna para entrar na Loja Pronta, escolher o fornecedor e os produtos que quiser. Depois que ela escolher e publicar, validar aqui.
```

## Proibições

- Remount SQL/código montando StockShop (ou outro fornecedor) **pela gente**.
- Publicar as 3 waves do fornecedor novo neste fluxo.
- Desconectar Shopee / apagar Loja Pronta / mensagem à aluna / `DONE`.
- UPDATE global em `shopee_ops_runs` ou writes sem GO do lote.

## Mesma categoria = mesma solução

Tickets irmãos (`#8517`, `#8699`, …) seguem **este** playbook; não pedir GO de novo só porque é outro número, salvo se o caso for diferente (outra categoria ou exceção do dono).

## Histórico (substituído)

Até 05/10/2026 o known-case pedia: excluir na Shopee + republicar ondas 1–3 do fornecedor novo (ex.: StockShop) em sequência. O Caio substituiu por **limpar + devolver à seleção da aluna** (esta tarefa v3).
