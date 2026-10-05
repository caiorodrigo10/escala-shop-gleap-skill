# Tarefa 35 — Loja sem logo/descrição que pulou a Fase 1

<!-- execucao-v2 -->
> **Execução:** `cat:35-loja-sem-identidade-fase1` (alias `cat:00-loja-sem-identidade-fase1`) = **suspenso** (NT-008: não executar agora). Tags só por união.
<!-- /execucao-v2 -->

> **Tags:** `cat:35-loja-sem-identidade-fase1` + `skill:*`. Alias legado: `cat:00-loja-sem-identidade-fase1`.

**Status:** `draft` — solução na NT-008; dono mandou **não executar agora**  
**Versão:** 1  
**Canônico:** `references/necessidades-tecnicas.md#NT-008`

## Quando usar

Loja em 3.1 sem logo/descrição/fotos IA porque o OAuth pulou a Fase 1 (foi direto ao KYC). Ex.: #8067. Sempre passar antes pela rotina de atraso (tarefa 27 / NT-007).

## Passos operacionais (resumo)

1. Confirmar evidências da NT-008 (fase, fila de publicação vazia, identidade vazia).
2. Enquanto `suspenso`: não gerar identidade nem publicar.
3. Quando liberar (GO + rota Vercel NT-001): gerar logo/descrição e publicar waves 1–3 aceleradas conforme a NT.

## Proibições

- Executar publicação acelerada enquanto `suspenso`.
- Pular a NT-007 em ticket de "atraso".
