# Tarefa 14 — Orientar upload bloqueado no GPT SLL

**Status:** `validated`
**Canário:** ticket de exemplo em 2026-09-04

## Quando usar

Use quando o erro de upload aparece dentro do ChatGPT/GPT SLL com mensagem de
limite máximo de zero carregamentos simultâneos, sem evidência de falha em uma
tela ou endpoint hospedado pela Escala Shop.

Não use para upload de logo, briefing, produto ou imagem dentro da plataforma.
Esses casos exigem diagnóstico técnico próprio.

## Procedimento

1. Ler o ticket completo, a captura e todas as identidades agrupadas.
2. Confirmar visualmente que a superfície é o ChatGPT/GPT SLL.
3. Preparar esta nota interna exata:

   `[interno] O erro ocorre no envio de imagens dentro do ChatGPT/GPT SLL, não na plataforma Escala Shop. Orientar a aluna a abrir uma nova conversa no GPT, recarregar a página e enviar apenas uma imagem por vez. Se persistir, testar janela anônima ou outro navegador e registrar print e horário da tentativa para nova análise. Não solicitar senha. Validar o envio de uma imagem antes de encerrar.`

4. Depois do preview e GO aplicável, enviar somente como nota interna.
5. Adicionar `skill:analisado` e `resolucao:orientacao-suporte`, preservando as
   tags existentes.
6. Resolver ao vivo a key `To Test`, atualizar o status e atribuir ao Support
   em chamada separada e por último.
7. Reler o card e confirmar nota, tags, status e equipe.

Nunca enviar mensagem pública, pedir senha, afirmar que a ferramenta externa
foi corrigida ou mover diretamente para Done.

## Resultado validado

No ticket de exemplo, a nota interna foi gravada, o card foi movido para `TOTEST`, as tags
foram preservadas e o ticket foi atribuído ao Support. O procedimento passa a
ser reutilizável individualmente; promoção para `active` depende de repetição
bem-sucedida em outro ticket.
