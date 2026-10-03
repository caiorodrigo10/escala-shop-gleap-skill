# Skill `/gleap` — Escala Shop

Skill operacional para analisar tickets `BUG` no Gleap, manter um catálogo de playbooks e preparar ações com revisão do owner. O fluxo detalhado está em [SKILL.md](SKILL.md).

## Instalação

Copie este repositório para o diretório de skills do seu agente com o nome `gleap` ou crie um link simbólico para ele. No Codex, por exemplo, use `.codex/skills/gleap`. Configure os conectores Gleap e Supabase e os identificadores da sua organização antes de executar uma operação.

```bash
node commands/validate-knowledge.mjs
```

A invocação `/gleap` faz apenas uma varredura. Os modos de escrita exigem prévia e autorização explícita do owner, conforme [SKILL.md](SKILL.md) e [contrato de ferramentas](references/tool-contract.md).

Esta distribuição pública contém o catálogo, os playbooks e os comandos. A fila de tickets, o backlog e o histórico de casos privados foram substituídos por arquivos vazios ou modelos. Emails, IDs de contas e identificadores de produção foram removidos. Alguns playbooks chamam scripts da aplicação Escala Shop, que precisam estar disponíveis no ambiente de execução; este repositório, sozinho, não concede acesso aos sistemas.
