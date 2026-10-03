# Tarefa 99 — Compatibilidade do fluxo legado `novo-bug`

Este arquivo preserva invocacoes antigas. O fluxo evolutivo atual esta dividido entre:

- `96-ensinar-padrao.md` para desconhecidos, playbooks, policies, investigations e rotas Support;
- `97-fix.md` para defeitos tecnicos e `/gleap bug-fixed`.

## Quando executar

- Um dispatcher antigo invocou `99-novo-bug.md`.
- O owner pediu "novo bug" sem escolher entre ensino e FIX.
- Uma automacao antiga chamou `/gleap bug-fixed` apontando para este arquivo.

## Roteamento

### Unknowns vindos do sweep

1. Fazer `upsert` de cada grupo em `../learning/queue.json`, seguindo `../references/learning-contract.md`.
2. Nao aplicar tag, status, nota ou atribuicao apenas porque o grupo foi descoberto.
3. Mostrar a classificacao sugerida:
   - procedimento repetivel -> `playbook`;
   - defeito tecnico -> `fix`;
   - decisao comercial -> `policy`;
   - evidencia insuficiente -> `investigation`;
   - trabalho humano conhecido -> `support`.
4. Encaminhar para `96-ensinar-padrao.md`.
5. Se o owner confirmar `fix`, encaminhar para `97-fix.md`.

### `/gleap bug-fixed BUG-...`

Encaminhar diretamente para `97-fix.md`. Nao manter uma segunda implementacao do protocolo neste arquivo.

## Compatibilidade de opcoes antigas

| Opcao antiga | Novo comportamento |
|---|---|
| nova categoria + procedimento | cria draft local via tarefa 96; nao aplica ao cluster |
| route Support | cria/valida rota `support`; canario antes de ativar |
| bug tecnico | cria/linka FIX via tarefa 97 |
| pular por agora | fila permanece `open`; sem write externo |
| cancelar | salva somente o report/estado local ja produzido |

## Regra de seguranca

Qualquer instrucao historica ou report antigo que sugira criar um MD e imediatamente aplicar aos N tickets esta obsoleta. Draft nunca executa em lote.

## Output

Informar o item da fila, o tipo sugerido, a tarefa moderna selecionada e o proximo passo seguro. O report final e gerado por `95-report-final.md`.
