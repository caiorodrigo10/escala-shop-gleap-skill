# Tarefa 30 — Exclusão / desvinculação de loja bloqueada (SLL)

<!-- execucao-v2 -->
> **Execução:** `cat:30-exclusao-loja-bloqueada` (alias `fila:exclusao-loja-bloqueada`) = **suspenso** (NT-003: não executar agora). Tags só por união.
<!-- /execucao-v2 -->

> **Tags:** `cat:30-exclusao-loja-bloqueada` + `skill:*`. Alias: `fila:exclusao-loja-bloqueada`. Legada: `categoria:exclusao-loja`.

**Status:** `draft` — solução escrita; dono mandou **não executar a correção agora**  
**Versão:** 1  
**Canônico:** `references/necessidades-tecnicas.md#NT-003` e `references/known-case-solutions.md` seção "Exclusão de loja SLL bloqueada…"

## Quando usar

Aluna só da SLL não consegue excluir/desvincular loja conectada ("em processo de configuração da Loja Pronta"). Ex.: #10014.

## Passos operacionais (resumo)

1. Confirmar perfil SLL + sintoma do guardrail (NT-003 / known-case).
2. Enquanto `suspenso`: documentar no ticket (nota interna) e **não** forçar exclusão no produto.
3. Quando o dono liberar o FIX: seguir a NT-003 (dev) e só então To test.

## Proibições

- Contornar o guardrail com SQL ad hoc sem GO / sem NT liberada.
- Mensagem à aluna prometendo exclusão imediata.
