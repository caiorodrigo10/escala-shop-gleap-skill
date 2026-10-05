# Tarefa 28 — Erro fiscal ORIGIN / MEASURE_UNIT ao publicar

<!-- execucao-v2 -->
> **Execução:** `cat:28-origin-measure-unit` (alias `fila:origin-measure-unit`) = **suspenso** (NT-002: não executar agora). Tags só por união.
<!-- /execucao-v2 -->

> **Tags:** `cat:28-origin-measure-unit` + status `skill:*`. Alias: `fila:origin-measure-unit`. Legadas: `categoria:ncm-origem-ausentes`, `categoria:cadastro-fiscal-produto`.

**Status:** `draft` — plano escrito; dono mandou **não executar agora**  
**Versão:** 1  
**Canônico:** `references/necessidades-tecnicas.md#NT-002` (depende de `NT-001`)

## Quando usar

Shopee recusa publicar/editar com "ORIGIN, MEASURE_UNIT não está correto" (tax_info só com NCM) — tipicamente StockShop.

## Passos operacionais (resumo)

1. Ler a **NT-002** (e pré-requisito NT-001 / rota IP fixo).
2. Enquanto `suspenso`: **não** backfill, **não** republicar, **não** prometer prazo à aluna.
3. Se o dono liberar: corrigir código (dev) → backfill → republicação conforme a NT; depois nota + To test.

## Proibições

- Executar correção ou publicação enquanto a categoria estiver `suspenso`.
- Inventar workaround fiscal fora da NT-002.
