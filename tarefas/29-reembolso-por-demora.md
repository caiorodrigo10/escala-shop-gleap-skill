# Tarefa 29 — Pedido de reembolso por demora do atendimento

<!-- execucao-v2 -->
> **Execução:** `cat:29-reembolso-por-demora` (alias `fila:reembolso-por-demora`) = **com_go**. Tags só por união.
<!-- /execucao-v2 -->

> **Tags:** `cat:29-reembolso-por-demora` + `skill:*`. Alias: `fila:reembolso-por-demora`. Legada: `categoria:reembolso-atraso`.

**Status:** `validated` — SKILL manda seguir NT-007 antes de tratar estorno  
**Versão:** 1  
**Canônico:** `SKILL.md#Rotina obrigatoria: atraso de loja ou publicacao` + `references/necessidades-tecnicas.md#NT-007`

## Quando usar

Aluna pede estorno / abre Reclame Aqui pela demora do próprio ticket de atraso ou publicação.

## Passos operacionais (resumo)

1. **Primeiro** aplicar a rotina de atraso (tarefa 27 / NT-007): diagnosticar e, se couber, destravar a loja.
2. Tratar o problema técnico do ticket; o pedido de reembolso administrativo segue com o time de reembolso (não inventar política aqui).
3. Nota interna clara sobre o estado da loja + o que falta do suporte/reembolso; To test.
4. Publicar (se o ramo da NT-007 exigir) só com GO.

## Proibições

- Prometer estorno ou falar com a aluna sem GO.
- Pular a NT-007 e ir direto para "encaminhar reembolso".
