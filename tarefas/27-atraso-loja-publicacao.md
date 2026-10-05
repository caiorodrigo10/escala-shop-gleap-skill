# Tarefa 27 — Atraso de loja ou de publicação

<!-- execucao-v2 -->
> **Execução (modelo v2):** `cat:27-wave1-atrasada` (alias `fila:wave1-atrasada`) = **com_go**. Quem decide é a coluna `execucao` do SQLite; lote via `commands/fechar-categoria.py`. Tags só por união.
<!-- /execucao-v2 -->

> **Tags (padrão v4):** problema `cat:27-wave1-atrasada` + `skill:analisado` (ou `skill:impedido` / `skill:executado`). Alias legado: `fila:wave1-atrasada`.

**Status:** `validated` — rotina obrigatória (NT-007 + SKILL.md)  
**Versão:** 1  
**Canônico:** `references/necessidades-tecnicas.md#NT-007` e `SKILL.md` seção "Rotina obrigatoria: atraso de loja ou publicacao"

## Quando usar

Reclamação de atraso da loja ou da publicação (Wave 1 / waves).

## Passos operacionais (resumo)

1. Seguir a **NT-007** por inteiro: checar no banco onde a aluna está (fase, waves, conexão).
2. Se **já publicou**: nota interna + To test (sem republicar).
3. Se **parou** antes de publicar: publicar exige GO e a rota da Vercel (NT-001); não inventar atalho.
4. Tags por união: `cat:27-wave1-atrasada`, `skill:analisado` (e `skill:executado` ao concluir).

## Proibições

- Mensagem à aluna / DONE sem GO próprio.
- Publicar sem GO do lote e sem rota liberada.
- Reescrever a NT-007 neste arquivo — o canônico é a NT + SKILL.
