#!/usr/bin/env python3
"""(Re)gera a tabela `categorias` do indice SQLite do suporte Gleap (modelo v2).

Fontes: catalog.json (categorias com problemTag) e a CURADORIA abaixo (uma
entrada por categoria, inclusive as ex-fila:*). A fila em arquivo
(learning/queue.json) foi descontinuada em 04/10/2026: o conteudo dela esta no
SQLite (coluna fila_legado) e caso novo vira categoria pendente pelo
commands/nova-pendente.py. O conteudo das solucoes e RECOPIADO dos Markdown a
cada execucao (upsert).

Uso:
  python3 commands/seed-index.py            # upsert de todas as categorias + aliases
  python3 commands/seed-index.py --dry-run  # mostra o que faria, sem gravar
  python3 commands/seed-index.py --db /caminho/outro.sqlite

Regras (modelo v2):
- status: `documentado` (tem solucao escrita: conteudo copiado de um Markdown
  ou resposta_dono registrada) ou `pendente` (precisa perguntar ao dono).
- execucao (so documentado): `sozinho` (so nota/tags/To test, sem producao),
  `com_go` (producao, rascunho ou duvida) ou `suspenso` (dono mandou nao
  executar agora). Na duvida, com_go.
- linha com status_manual=1 (registrar-solucao.py, nova-pendente.py ou UPDATE a
  mao) preserva status, execucao e caminho_md; o conteudo e recopiado a partir
  do caminho_md dessa linha. pergunta_dono e resposta_dono nunca sao apagadas.
- ALIASES: tags fila:* que eram duplicatas de cat:*; o seed garante o registro
  e funde a linha antiga se ela reaparecer.
- nenhuma categoria e apagada (fora a fusao de alias); as que sumiram das
  fontes ganham alerta.

Para cadastrar solucao nova NAO edite este arquivo: use
commands/registrar-solucao.py. Este arquivo nao contem dados de alunas nem
tokens. O banco fica fora da pasta da skill.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # nada de __pycache__ na pasta da skill
sys.path.insert(0, str(Path(__file__).resolve().parent))
from indice_comum import (EXECUCOES, SEM_ANALISE, SKILL_DIR, STATUS_VALIDOS, agora_iso,  # noqa: E402
                          conectar, extrair_markdown, fundir_alias, separar_caminho)

T = "tarefas/"
NT = "references/necessidades-tecnicas.md"
KC = "references/known-case-solutions.md"
SK = "SKILL.md"
CAT = "catalog.json"

# --------------------------------------------------------------------------
# Curadoria: uma entrada por categoria. Chaves:
#   nome, descricao (padrao geral, no maximo 1 ticket de exemplo),
#   status (pendente|documentado), execucao + motivo_execucao (documentado),
#   pergunta_dono (pendente), depende_producao,
#   fontes [(arquivo relativo, ancora|None)], fonte, criterio, legadas_extra
# Categorias do catalogo sem entrada aqui entram como pendente.
# --------------------------------------------------------------------------
CURADORIA = {
    # ---------------- catalog.json ----------------
    "cat:13-lojas-duplicadas": dict(
        nome="Lojas duplicadas da mesma aluna",
        descricao="Aluna com mais de uma store da Loja Pronta e o estado util dividido entre elas (conexao Shopee numa, compra ou identidade noutra). Consolidar numa store so quando ha uma unica compra LP ativa e a duplicada nao tem nada publicado.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (banco, destrutiva): GO do Caio", depende_producao=1, fontes=[(T + "13-consolidar-lojas-duplicadas.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 13, validated); escrita destrutiva no banco exige GO duplo"),
    "cat:08-acesso-reembolsado": dict(
        nome="Pedido de acesso a produto ja reembolsado",
        descricao="Aluna pede acesso a um produto cuja compra foi reembolsada. O playbook orienta o diagnostico sem reprovisionar acesso.",
        status="documentado", execucao="com_go",
        motivo_execucao="playbook em rascunho: nao roda sozinho", depende_producao=0, fontes=[(T + "08-acesso-produto-reembolsado.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 08), mas ainda draft: nao executar externamente sem canario"),
    "cat:04-refunded-cleanup": dict(
        nome="Ticket de aluna que ja pediu reembolso",
        descricao="Ticket aberto (em geral antes do reembolso) por aluna que ja saiu da plataforma: encerrar o ticket e excluir os anuncios publicados na Shopee.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (excluir anuncios na Shopee): GO do Caio", depende_producao=1, fontes=[(T + "04-refunded-cleanup.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 04, active); exclusao na Shopee e DONE exigem GO"),
    "cat:06-refund-chargeback": dict(
        nome="Reembolso, Reclame Aqui ou chargeback com pedido de acesso",
        descricao="Aluna em contexto de reversao (Reclame Aqui, chargeback ou reembolso revertido) que pede acesso de volta. O playbook decide entre reprovisionar, rota de senha ou nota interna.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (provisionar acesso): GO do Caio", depende_producao=1, fontes=[(T + "06-refund-reclame-chargeback.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 06, active); provisionamento e acao em producao com GO"),
    "cat:12-acesso-pelo-support": dict(
        nome="Acesso solicitado por membro do Support",
        descricao="Ticket BUG criado por membro autenticado do Support pedindo acesso ao SLL ou a Loja Pronta; a solicitacao e a fonte de autorizacao do acesso, mesmo sem compra Hotmart.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (provisionar acesso): GO do Caio", depende_producao=1, fontes=[(T + "12-acesso-solicitado-pelo-support.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 12, validated); provisionamento com GO"),
    "cat:09-sll-ja-ativo": dict(
        nome="Pedido de acesso ao SLL que ja esta ativo",
        descricao="Aluna pede acesso ao SLL, mas o acesso ja esta ativo; orientar o suporte sem nova escrita.",
        status="documentado", execucao="com_go",
        motivo_execucao="o catalogo ainda marca no-external-write e a politica de writes nao foi definida: na duvida, com GO", depende_producao=0, fontes=[(T + "09-acesso-sll-ja-ativo.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 09, validated)"),
    "cat:10-pix-fora-hotmart": dict(
        nome="Compra por Pix fora da Hotmart sem acesso",
        descricao="Aluna pagou por Pix fora da Hotmart e esta sem acesso; o playbook confere o pagamento e provisiona.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (provisionar acesso): GO do Caio", depende_producao=1, fontes=[(T + "10-acesso-pix-fora-hotmart.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 10, active); provisionamento com GO"),
    "cat:00-reset-senha": dict(
        nome="Reset de senha ou link de recuperacao",
        descricao="Problema de credencial (senha, link de recuperacao) com a conta ja provisionada; rota de suporte, sem mensagem externa.",
        status="documentado", execucao="com_go",
        motivo_execucao="rota de suporte sem tarefa escrita (inclui atribuicao): na duvida, com GO", depende_producao=0, fontes=[(CAT, "reset-senha")], fonte="catalogo",
        criterio="rota de suporte ativa descrita apenas no catalog.json (sem tarefa propria)"),
    "cat:00-nao-e-aluna-lp": dict(
        nome="Nao e aluna da Loja Pronta",
        descricao="Nenhuma compra LP complete/approved encontrada depois do cruzamento por email e telefone; rotear ao Support sem provisionar.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so SELECT + nota interna + tags + To test; a atribuicao ao Support fica de fora (so com GO)", depende_producao=0, fontes=[(T + "01-acesso-nao-provisionado.md", "2e. Route"), (CAT, "nao-e-aluna-lp")],
        fonte="tarefa", criterio="rota escrita na tarefa 01, passo 2e", legadas_extra=[]),
    "cat:01-acesso-nao-provisionado": dict(
        nome="Compra ativa sem acesso provisionado",
        descricao="Aluna com compra LP ou SLL valida que nao recebeu o acesso; identificar pela cascata email/telefone e provisionar pelo helper.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (provisionar acesso): GO do Caio", depende_producao=1, fontes=[(T + "01-acesso-nao-provisionado.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 01, active); provisionamento com GO"),
    "cat:14-gpt-sll-upload": dict(
        nome="Upload no GPT do SLL com limite zero",
        descricao="Aluna nao consegue enviar arquivos ao GPT do SLL (limite zero); orientar o uso correto.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna + tags + To test (playbook validado); a atribuicao fica de fora (so com GO)", depende_producao=0, fontes=[(T + "14-orientar-upload-gpt-sll.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 14, validated)"),
    "cat:18-sessao-expirada": dict(
        nome="Sessao Shopee expirada bloqueando acao tecnica",
        descricao="Ticket que precisa de acao na Shopee (imagem, anuncio, publicacao) com a conexao da loja expirada: nota interna com o bloqueio e o link de reconexao, e To test.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna com o link de reconexao + tags + To test (regra do dono)", depende_producao=0,
        fontes=[(T + "18-sessao-shopee-expirada-acao-bloqueada.md", None), (KC, "Sessao Shopee expirada")], fonte="tarefa",
        criterio="regra do dono escrita (tarefa 18, validated, e known-case)"),
    "cat:03-logo-nome-loja": dict(
        nome="Alterar logo ou nome da loja",
        descricao="Aluna pede troca do nome ou da logo da loja (logo propria enviada ou nova geracao). Troca de nome: sem Shopee e sem produtos, esconder as logos e descricoes com o nome errado, gerar 3 logos novas e To test para o suporte avisar; na selecao de produtos ou depois, 1 logo e 1 descricao novas substituidas direto (exemplo: #10311).",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (loja, logos, Shopee): GO do Caio", depende_producao=1,
        fontes=[(T + "03-alterar-logo-nome-loja.md", None), (KC, "Troca de nome da loja")], fonte="tarefa",
        criterio="playbook escrito (tarefa 03, validated) + regra do dono para troca de nome (2026-10-04 18h36); escrita na loja/Shopee com GO",
        legadas_extra=["categoria:nome-loja", "categoria:logo-loja"]),
    "cat:05-foto-ia-errada": dict(
        nome="Foto de IA errada em anuncio publicado",
        descricao="Imagem gerada por IA nao corresponde ao produto do fornecedor em anuncio ja publicado; regerar e reenviar a Shopee com GO.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (reenviar imagem a Shopee): GO do Caio", depende_producao=1, fontes=[(T + "05-foto-ai-errada-anuncio-publicado.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 05, active); envio a Shopee com GO em duas etapas"),
    "cat:02-variantes-fornecedor": dict(
        nome="Produtos 'repetidos' que sao variantes do fornecedor",
        descricao="Aluna reclama de produtos duplicados na wave, mas sao SKUs distintos (cores, lavagens, kits) que o fornecedor cataloga separado; nota de contexto para o atendimento.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so SELECT + nota interna + tags + To test (playbook ativo); a atribuicao fica de fora (so com GO)", depende_producao=0, fontes=[(T + "02-produtos-variantes-fornecedor.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 02, active)"),
    "cat:07-shopee-baniu-excluiu": dict(
        nome="Anuncio excluido ou banido pela Shopee",
        descricao="Aluna relata anuncio excluido, banido ou loja inativa: sondar o item_status real na Shopee e, se a Shopee removeu, repor pelo catalogo do mesmo fornecedor (tarefa 11).",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (sondagem e reposicao na Shopee): GO do Caio", depende_producao=1,
        fontes=[(T + "07-shopee-baniu-excluiu.md", None), (T + "11-repor-anuncio-shopee.md", None)], fonte="tarefa",
        criterio="playbooks escritos (tarefas 07 e 11, active); sondagem e reposicao exigem rota com IP fixo e GO"),
    "cat:11-repor-anuncio": dict(
        nome="Repor anuncio removido com produto whitelisted",
        descricao="Reposicao de anuncio removido pela Shopee usando produto do mesmo fornecedor, com o mesmo contrato de titulo, descricao e imagem da publicacao por wave.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (publicar na Shopee): GO do Caio", depende_producao=1, fontes=[(T + "11-repor-anuncio-shopee.md", None)], fonte="tarefa",
        criterio="playbook escrito (tarefa 11, active); publicacao na Shopee com GO"),
    "cat:19-imagem-recusada": dict(
        nome="Imagem recusada pela Shopee",
        descricao="Categoria unica para foto recusada ou errada (fundo nao limpo, borda branca, produto diferente): gerar a foto correta no Fal e trocar so a imagem afetada no mesmo produto, depois nota e To test (exemplo: #4319).",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-005 marcada 'nao executar agora' e a troca depende da rota da Vercel (NT-001); a autorizacao permanente de 04/10 15h11 fica parada ate o Caio liberar", depende_producao=1,
        fontes=[(T + "19-anuncio-nao-qualificado-fundo-limpo.md", None), (KC, "Imagem recusada pela Shopee"), (NT, "NT-005")],
        fonte="tarefa",
        criterio="playbook escrito (tarefa 19 v3) com autorizacao permanente do dono; troca na Shopee depende da rota da Vercel (NT-001)"),
    "cat:20-categoria-incorreta": dict(
        nome="Violacao Shopee por categoria incorreta",
        descricao="Print da Shopee com 'Informacao de Violacao' por categoria incorreta: nota interna sugerindo a categoria que a propria Shopee recomenda; a equipe aplica.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna com a categoria sugerida + tags + To test (playbook validado)", depende_producao=0,
        fontes=[(T + "20-violacao-categoria-incorreta-shopee.md", None), (KC, "Violacao Shopee por categoria incorreta")], fonte="tarefa",
        criterio="playbook escrito (tarefa 20, validated)"),
    "cat:21-erro-verificar-loja": dict(
        nome="Erro ao verificar loja em 'Usar loja selecionada'",
        descricao="Botao 'Usar loja selecionada' travado com 'Nao foi possivel verificar a loja': identificar a loja conectada na LP por binding ou jornada e orientar nova tentativa ou selecao.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so SELECT + nota interna + tags + To test (regra do dono)", depende_producao=0,
        fontes=[(T + "21-erro-verificar-loja-usar-selecionada.md", None), (KC, "Erro ao verificar loja"), (KC, "Atualizacao operacional da tarefa 21")],
        fonte="tarefa", criterio="regra do dono escrita (tarefa 21, validated)"),
    "cat:25-shopee-suporte": dict(
        nome="Duvida ou problema da Shopee fora da estrutura tecnica (encaminhar ao suporte)",
        descricao="Qualquer duvida ou problema da Shopee sem relacao direta com a estrutura tecnica da Escala Shop (conta, vinculo de loja, titular CPF/CNPJ, documentos, prazos, regras da plataforma): nao e caso tecnico; To test com nota interna para o suporte orientar a aluna e tratar reembolso, se houver (exemplo: #8561).",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna + tags + To test (regra do dono)", depende_producao=0,
        fontes=[(T + "25-shopee-fora-escopo-suporte.md", None), (KC, "Dúvida ou problema da Shopee fora da estrutura técnica")],
        fonte="tarefa", criterio="regra do dono na ligacao de 2026-10-04 17h14/17h15 (tarefa 25, validated)"),
    "cat:23-shop-id-divergente": dict(
        nome="shop_id da loja diferente do shop_id da conexao",
        descricao="stores.shopee_shop_id difere de shopee_connections.shop_id: identificar a LP pela store da jornada e registrar a divergencia; a reconciliacao do ID ainda depende de decisao do dono.",
        status="documentado", execucao="suspenso",
        motivo_execucao="so o diagnostico esta escrito; a correcao espera a decisao do dono", depende_producao=0,
        fontes=[(T + "23-identificar-loja-lp-shop-id-divergente.md", None), (KC, "Identificacao provisoria de LP com shop_id divergente")],
        fonte="tarefa",
        criterio="so o diagnostico esta escrito (tarefa 23, draft); a remediacao nao foi definida e espera o dono"),
    "cat:22-kyc-aprovado-fase": dict(
        nome="KYC aprovado na Shopee, loja nao avancou de fase",
        descricao="Consulta ao vivo com KYC aprovado e loja NORMAL enquanto a jornada segue parada antes da fase correspondente: encaminhar pela RPC oficial, nota interna e To test.",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (RPC no banco): GO do Caio", depende_producao=1,
        fontes=[(T + "22-kyc-aprovado-encaminhar-fase-correspondente.md", None), (KC, "KYC aprovado, loja nao sincronizada")], fonte="tarefa",
        criterio="regra do dono escrita (tarefa 22, validated); RPC no banco de producao com GO"),
    "cat:15-kyc-aprovado-reconectar": dict(
        nome="KYC aprovado com conexao Shopee expirada",
        descricao="KYC aprovado mas o token da Shopee venceu ou o refresh falhou: nota interna, To test e a aluna reconecta pela conta certa.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna + tags + To test (regra do dono)", depende_producao=0, fontes=[(T + "15-kyc-aprovado-conexao-expirada.md", None)], fonte="tarefa",
        criterio="regra do dono escrita (tarefa 15, validated)"),
    "cat:16-kyc-incompleto": dict(
        nome="Cadastro KYC incompleto na Shopee",
        descricao="Consulta ao vivo mostra kyc=incomplete: nota interna para concluir documento ou selfie na Central do Vendedor e To test.",
        status="documentado", execucao="com_go",
        motivo_execucao="a consulta ao vivo da Shopee exige GO por rodada", depende_producao=1, fontes=[(T + "16-kyc-cadastro-incompleto-shopee.md", None)], fonte="tarefa",
        criterio="regra do dono escrita (tarefa 16, validated); a consulta ao vivo usa a rota da Vercel com GO por rodada"),
    "cat:17-kyc-pending": dict(
        nome="KYC em analise na Shopee",
        descricao="KYC ainda pendente do lado da Shopee: confirmar pela API e mover para To test com nota dizendo que quem resolve e a Shopee (exemplo: #9416).",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-004 marcada 'nao executar agora'", depende_producao=1,
        fontes=[(NT, "NT-004"), (T + "17-kyc-pending-shopee-aguardar.md", None)], fonte="NT",
        criterio="solucao mapeada (NT-004 + tarefa 17 v2), mas a execucao esta suspensa por decisao do dono ate ele liberar"),
    "cat:00-avancar-etapa-kyc": dict(
        nome="Pedido generico de avancar etapa de KYC",
        descricao="Aluna pede para avancar a etapa de KYC sem que o caso caia nas tarefas 15, 16, 17 ou 22; causa e transicao segura ainda nao ensinadas.",
        status="pendente",
        pergunta_dono="Quando a aluna pede para avancar a etapa de KYC e o caso nao cai nas tarefas 15, 16, 17 ou 22, qual e a causa e o que fazemos?", depende_producao=0, fontes=[], fonte="catalogo",
        criterio="investigation draft sem solucao escrita"),
    "cat:00-fase-travada": dict(
        nome="Fase da loja travada",
        descricao="Loja parada numa fase sem causa conhecida; ainda precisa ser separada em playbook, FIX ou politica.",
        status="pendente",
        pergunta_dono="Loja parada numa fase sem causa conhecida: como diagnosticar e quem destrava (playbook, correcao de codigo ou regra sua)?", depende_producao=0, fontes=[], fonte="catalogo",
        criterio="investigation draft sem solucao escrita"),
    "cat:00-acelerar-processo": dict(
        nome="Pedido para acelerar ou priorizar o processo",
        descricao="Aluna pede urgencia ou prioridade sem erro tecnico; a politica de priorizacao ainda nao foi definida (atraso de publicacao segue a rotina NT-007, em fila:wave1-atrasada).",
        status="pendente",
        pergunta_dono="Pedido de urgencia ou prioridade sem erro tecnico (fora do atraso de publicacao, que segue a NT-007): qual e a regra?", depende_producao=0, fontes=[], fonte="catalogo",
        criterio="policy draft sem solucao escrita"),
    "cat:24-troca-email-titular": dict(
        nome="Troca do e-mail titular na plataforma",
        descricao="Aluna pede para trocar o e-mail de login da Escala Shop: To test com nota, e o suporte faz a troca pela Central de Acessos; nao cobre Hotmart, GHL nem Shopee.",
        status="documentado", execucao="sozinho",
        motivo_execucao="so nota interna + tags + To test; a troca e feita pelo suporte", depende_producao=0,
        fontes=[(T + "24-troca-email-titular-plataforma.md", None), (KC, "Troca do e-mail titular")], fonte="tarefa",
        criterio="playbook escrito (tarefa 24, validated); a troca e feita pela operadora do suporte, nao pelo Bob"),

    # ---------------- ex-fila (learning/queue.legacy.json, descontinuada em 04/10/2026) ----------------
    "cat:30-exclusao-loja-bloqueada": dict(
        nome="Exclusao ou desvinculacao de loja bloqueada",
        descricao="Aluna so da SLL nao consegue excluir ou desvincular a loja conectada ('em processo de configuracao da Loja Pronta'); corrigir ou criar a exclusao no produto (dev) e depois To test (exemplo: #10014).",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-003 marcada 'nao executar agora'", depende_producao=1,
        fontes=[(T + "30-exclusao-loja-bloqueada.md", None), (NT, "NT-003"), (KC, "Exclus")], fonte="tarefa",
        criterio="playbook escrito (tarefa 30); solucao na NT-003/known-case, mas o dono mandou NAO executar a correcao agora",
        legadas_extra=["categoria:exclusao-loja"]),
    "fila:sll-etapa2": dict(
        nome="Etapa 2 do SLL nao desbloqueia",
        descricao="Aluna do SLL diz ter concluido a etapa 1 e a etapa 2 segue bloqueada; regra de desbloqueio ainda nao conhecida.",
        status="pendente",
        pergunta_dono="Qual a regra de desbloqueio da etapa 2 do SLL (aulas, prazo ou tarefa) e onde conferimos o progresso da aluna?", depende_producao=0, fontes=[], fonte="fila",
        criterio="investigacao aberta, sem ownerAnswer"),
    "cat:33-curso-etapa3-oculta": dict(
        nome="Modulo de curso oculto ou ausente",
        descricao="Etapa ou modulo do curso nao aparece: confirmar pelo print se e conteudo oculto no player externo, manter em andamento ate a republicacao e depois To test.",
        status="documentado", execucao="com_go",
        motivo_execucao="depende de confirmar a republicacao do modulo fora do Gleap: na duvida, com GO", depende_producao=0,
        fontes=[(T + "33-curso-etapa3-oculta.md", None), (T + "00-analise-geral.md", "Conteudo de curso ausente")], fonte="tarefa",
        criterio="playbook escrito (tarefa 33) + rotina na tarefa 00"),
    "cat:28-origin-measure-unit": dict(
        nome="Erro fiscal ORIGIN/MEASURE_UNIT ao publicar (stockshopp)",
        descricao="A Shopee recusa publicar ou editar anuncio com 'ORIGIN, MEASURE_UNIT nao esta correto' porque o tax_info sai so com NCM; corrigir o codigo (dev), depois backfill e republicacao.",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-002 marcada 'nao executar agora'", depende_producao=1,
        fontes=[(T + "28-origin-measure-unit.md", None), (NT, "NT-002"), (NT, "NT-001")], fonte="tarefa",
        criterio="playbook escrito (tarefa 28); plano na NT-002, mas o dono mandou NAO executar agora",
        legadas_extra=["categoria:ncm-origem-ausentes", "categoria:cadastro-fiscal-produto"]),
    "cat:31-trafego-bloqueado": dict(
        nome="Trafego bloqueado para item novo (90 dias)",
        descricao="Anuncios com 'Trafego Bloqueado Para Novo Item (90 Dias)': nao e banimento; nota interna com as causas comuns e pedido do motivo por anuncio na Central do Vendedor, e To test (exemplo: #5494).",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-006 marcada 'nao executar agora'", depende_producao=0,
        fontes=[(T + "31-trafego-bloqueado.md", None), (NT, "NT-006")], fonte="tarefa",
        criterio="playbook escrito (tarefa 31); abordagem na NT-006, mas o dono mandou NAO executar agora",
        legadas_extra=["categoria:trafego-bloqueado"]),
    "cat:26-troca-fornecedor": dict(
        nome="Troca de fornecedor em caso atipico",
        descricao="Aluna ficou com o fornecedor errado (por bug ou engano): limpar anuncios do fornecedor errado na Shopee (se ainda houver), limpar catalogo/fornecedor no DB (sem desconectar Shopee), devolver a loja a selecao de fornecedor/produtos, nota para o suporte orientar a aluna a escolher, e To test. Nao remount nem publicar waves do fornecedor novo (exemplo: #8517, #8699).",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (excluir na Shopee e limpar DB/fase): GO do Caio", depende_producao=1,
        fontes=[(T + "26-troca-fornecedor-reset-selecao.md", None), (KC, "Troca de fornecedor em caso atípico")],
        fonte="playbook",
        criterio="decisao do dono 05/10/2026 ~13h36; playbook v3 (tarefa 26); writes exigem GO",
        legadas_extra=["categoria:troca-fornecedor", "categoria:fornecedor-reset", "categoria:fornecedor-incorreto"]),
    "cat:27-wave1-atrasada": dict(
        nome="Atraso de loja ou de publicacao",
        descricao="Reclamacao de atraso da loja ou da publicacao: checar primeiro no banco onde a aluna esta; se ja publicou, nota e To test; se parou, publicar (acao em producao com GO, depende da rota da Vercel).",
        status="documentado", execucao="com_go",
        motivo_execucao="o ramo 'parado' e publicar (producao); na duvida, com GO", depende_producao=1,
        fontes=[(T + "27-atraso-loja-publicacao.md", None), (NT, "NT-007"), (SK, "Rotina obrigatoria: atraso de loja ou publicacao")],
        fonte="tarefa", criterio="playbook escrito (tarefa 27) + NT-007/SKILL; publicar exige GO e a rota da Vercel"),
    "cat:32-ajuste-generico": dict(
        nome="Pedido generico de ajuste sem defeito identificado",
        descricao="Ticket so diz 'ajustar anuncio' ou mostra uma recomendacao do Otimizador, sem alvo nem defeito: nota pedindo link, o que esta errado e o esperado, e To test.",
        status="documentado", execucao="com_go",
        motivo_execucao="rotina escrita na tarefa 00/32: na duvida, com GO", depende_producao=0,
        fontes=[(T + "32-ajuste-generico.md", None), (T + "00-analise-geral.md", "Pedido generico de ajuste sem defeito")],
        fonte="tarefa", criterio="playbook escrito (tarefa 32) + rotina na tarefa 00"),
    "fila:sync-metricas": dict(
        nome="Falha de sincronizacao da loja com a Escala Shop",
        descricao="Loja nao sincroniza ou nao atualiza metricas ('Nao foi possivel atualizar as metricas agora'), em geral com shop_id da loja diferente do da conexao; causa e procedimento nao escritos (exemplo: #8876).",
        status="pendente",
        pergunta_dono="Loja que nao atualiza as metricas ('Nao foi possivel atualizar as metricas agora'): qual a causa e o que fazemos? Muitas vezes o shop_id da loja difere do da conexao.", depende_producao=0, fontes=[], fonte="fila",
        criterio="investigacao sem ownerAnswer; a tarefa 23 (draft) so identifica a divergencia de shop_id",
        legadas_extra=["categoria:sincronizacao-shopee"]),
    "fila:cadastro-sll-sem-evidencia": dict(
        nome="Erro de cadastro de loja SLL sem evidencia",
        descricao="Compra SLL sem loja criada e sem print do erro; causa nao identificada.",
        status="pendente",
        pergunta_dono="Compra do SLL sem loja criada e sem print do erro: pedimos o print a aluna pelo suporte ou existe outra checagem?", depende_producao=0, fontes=[], fonte="fila",
        criterio="investigacao sem ownerAnswer"),
    "cat:29-reembolso-por-demora": dict(
        nome="Pedido de reembolso por demora do atendimento",
        descricao="Aluna pede estorno ou abre Reclame Aqui pela demora do proprio ticket; seguir a rotina de atraso (NT-007) antes de tudo e tratar o problema tecnico do ticket.",
        status="documentado", execucao="com_go",
        motivo_execucao="segue a NT-007, que pode levar a publicar (producao): GO do Caio", depende_producao=1,
        fontes=[(T + "29-reembolso-por-demora.md", None), (SK, "Rotina obrigatoria: atraso de loja ou publicacao"), (NT, "NT-007")],
        fonte="tarefa", criterio="playbook escrito (tarefa 29); SKILL/NT-007; escalonamento ao time de reembolso segue em aberto",
        legadas_extra=["categoria:reembolso-atraso"]),

    # ---------------- pedidas pelo dono, ainda sem tag no catalogo ----------------
    "cat:34-conta-shopee-errada": dict(
        nome="Loja conectada na conta Shopee errada",
        descricao="Loja Pronta conectada na conta Shopee de outra pessoa (por exemplo um familiar): desconectar e refazer a autenticacao com a conta certa, conferindo antes se a loja ainda nao publicou e se a aluna tem conta de vendedora propria (exemplo: #9695).",
        status="documentado", execucao="com_go",
        motivo_execucao="acao em producao (desconectar a conta Shopee): GO do Caio", depende_producao=1,
        fontes=[(T + "34-conta-shopee-errada.md", None), (KC, "Loja conectada na conta Shopee errada")], fonte="tarefa",
        criterio="playbook escrito (tarefa 34) + known-case; desconectar e acao em producao"),
    "cat:35-loja-sem-identidade-fase1": dict(
        nome="Loja sem logo nem descricao que pulou a Fase 1",
        descricao="Loja parada em 3.1 sem logo, descricao nem fotos de IA porque pulou a Fase 1 (o OAuth levou direto ao KYC): gerar logo e descricao e publicar as waves 1, 2 e 3 em sequencia acelerada, com GO (exemplo: #8067).",
        status="documentado", execucao="suspenso",
        motivo_execucao="NT-008 marcada 'nao executar agora'", depende_producao=1,
        fontes=[(T + "35-loja-sem-identidade-fase1.md", None), (NT, "NT-008")], fonte="tarefa",
        criterio="playbook escrito (tarefa 35); solucao na NT-008, mas o dono mandou NAO executar agora"),
    "cat:07-anuncio-ativo-nao-aparece": dict(
        nome="Anuncio ativo que nao aparece",
        descricao="Aluna diz que os anuncios sumiram ou nao aparecem, mas a sondagem mostra item NORMAL (no ar): nota explicando o que esta publicado, sem republicar.",
        status="documentado", execucao="com_go",
        motivo_execucao="playbook em rascunho e a sondagem ao vivo precisa da rota com IP fixo", depende_producao=1,
        fontes=[(T + "07-shopee-baniu-excluiu.md", None)],
        fonte="tarefa", criterio="playbook compartilhado (tarefa 07, ramos Passo 1-2 e nota 5a); sondagem ao vivo precisa da rota com IP fixo",
        legadas_extra=["categoria:anuncios-nao-visiveis"]),

    # ---------------- especial ----------------
    SEM_ANALISE: dict(
        nome="Sem tag de analise",
        descricao="Ticket sem tag cat:*, fila:* nem tag legada mapeada; precisa passar pelo fluxo de analise de ticket novo do SKILL.md.",
        status="pendente", depende_producao=0, fontes=[], fonte="especial",
        criterio="categoria tecnica da sync para tickets sem analise"),
}


# Via Cursor (Caio 05/10/2026): A=suporte padrao/tools; B=codigo; duvida=atipico
VIA_CURSOR = {
    # --- A ---
    "cat:34-conta-shopee-errada": "A",
    "cat:35-loja-sem-identidade-fase1": "A",
    "cat:00-reset-senha": "A",
    "cat:01-acesso-nao-provisionado": "A",
    "cat:02-variantes-fornecedor": "A",
    "cat:03-logo-nome-loja": "A",
    "cat:04-refunded-cleanup": "A",
    "cat:05-foto-ia-errada": "A",
    "cat:06-refund-chargeback": "A",
    "cat:07-shopee-baniu-excluiu": "A",
    "cat:08-acesso-reembolsado": "A",
    "cat:09-sll-ja-ativo": "A",
    "cat:10-pix-fora-hotmart": "A",
    "cat:11-repor-anuncio": "A",
    "cat:12-acesso-pelo-support": "A",
    "cat:13-lojas-duplicadas": "A",
    "cat:14-gpt-sll-upload": "A",
    "cat:15-kyc-aprovado-reconectar": "A",
    "cat:16-kyc-incompleto": "A",
    "cat:17-kyc-pending": "A",
    "cat:18-sessao-expirada": "A",
    "cat:19-imagem-recusada": "A",
    "cat:20-categoria-incorreta": "A",
    "cat:22-kyc-aprovado-fase": "A",
    "cat:23-shop-id-divergente": "A",
    "cat:24-troca-email-titular": "A",
    "cat:25-shopee-suporte": "A",
    "cat:32-ajuste-generico": "A",
    "cat:30-exclusao-loja-bloqueada": "A",
    "cat:29-reembolso-por-demora": "A",
    "cat:26-troca-fornecedor": "A",
    "cat:27-wave1-atrasada": "A",
    # --- B ---
    "cat:07-anuncio-ativo-nao-aparece": "B",
    "cat:21-erro-verificar-loja": "B",
    "cat:28-origin-measure-unit": "B",
    "cat:31-trafego-bloqueado": "B",
    "fila:sync-metricas": "B",
    # --- duvida ---
    "cat:00-acelerar-processo": "duvida",
    "cat:00-avancar-etapa-kyc": "duvida",
    "cat:00-fase-travada": "duvida",
    "cat:00-nao-e-aluna-lp": "duvida",
    "fila:cadastro-sll-sem-evidencia": "duvida",
    "cat:33-curso-etapa3-oculta": "duvida",
    "fila:sll-etapa2": "duvida",
    SEM_ANALISE: "duvida",
}

# Tags fila:* fundidas numa cat:* (modelo v2). A sync e a busca resolvem a tag antiga para a cat:*.
ALIASES = {
    "fila:sll-em-verificacao-pos-kyc": "cat:22-kyc-aprovado-fase",
    "fila:kyc-fase-nao-avanca": "cat:15-kyc-aprovado-reconectar",
    "fila:alterar-nome-loja": "cat:03-logo-nome-loja",
    "fila:categoria-anuncio-limitado": "cat:20-categoria-incorreta",
    "fila:refund-pos-ticket": "cat:04-refunded-cleanup",
    "fila:usar-loja-conectada": "cat:21-erro-verificar-loja",
    "fila:titular-errado": "cat:25-shopee-suporte",
    "fila:sessao-expirada-acao": "cat:18-sessao-expirada",
    "fila:shop-id-diferente": "cat:23-shop-id-divergente",
    "fila:troca-fornecedor": "cat:26-troca-fornecedor",
    "fila:wave1-atrasada": "cat:27-wave1-atrasada",
    "fila:origin-measure-unit": "cat:28-origin-measure-unit",
    "fila:reembolso-por-demora": "cat:29-reembolso-por-demora",
    "fila:exclusao-loja-bloqueada": "cat:30-exclusao-loja-bloqueada",
    "fila:trafego-bloqueado": "cat:31-trafego-bloqueado",
    "fila:ajuste-generico": "cat:32-ajuste-generico",
    "fila:curso-etapa3-oculta": "cat:33-curso-etapa3-oculta",
    "cat:00-conta-shopee-errada": "cat:34-conta-shopee-errada",
    "cat:00-loja-sem-identidade-fase1": "cat:35-loja-sem-identidade-fase1",
}


def carregar_json(rel):
    return json.loads((SKILL_DIR / rel).read_text(encoding="utf-8"))


def copiar(fontes, catalogo_por_id):
    """Devolve (caminho_md, caminhos_extra, conteudo, faltando)."""
    blocos, caminhos, faltando = [], [], []
    for rel, ancora in fontes:
        absoluto = str(SKILL_DIR / rel)
        caminho = absoluto + (f"#{ancora}" if ancora else "")
        if rel == CAT:
            item = catalogo_por_id.get(ancora)
            texto = ("```json\n" + json.dumps(item, ensure_ascii=False, indent=2) + "\n```\n") if item else None
        else:
            texto = extrair_markdown(absoluto, ancora)
        if not texto or not texto.strip():
            faltando.append(caminho)
            continue
        caminhos.append(caminho)
        blocos.append(f"<!-- fonte: {caminho} -->\n{texto}")
    if not caminhos:
        return None, None, None, faltando
    return caminhos[0], ("; ".join(caminhos[1:]) or None), "\n\n".join(blocos), faltando


def montar_linhas(respostas=None):
    """respostas: {id: resposta_dono} ja gravadas no banco (documentado sem Markdown continua documentado)."""
    respostas = respostas or {}
    catalogo = carregar_json("catalog.json")
    cat_por_id = {c["id"]: c for c in catalogo["categories"]}
    base = {}
    for c in catalogo["categories"]:
        tag = c.get("problemTag")
        if not tag or tag in ALIASES:
            continue
        legadas = []
        for t in [c.get("tag")] + list(c.get("legacyTags") or []):
            if t and t != tag and t not in legadas:
                legadas.append(t)
        base[tag] = dict(estado_catalogo=c.get("status"), tipo=c.get("kind"), legadas=legadas,
                         tag_no_catalogo=1, origem="catalogo")
    for tag in CURADORIA:
        base.setdefault(tag, dict(estado_catalogo=None, tipo=None, legadas=[],
                                  tag_no_catalogo=1 if tag.startswith("fila:") else 0, origem="dono"))

    linhas = []
    for tag, b in base.items():
        cur = CURADORIA.get(tag)
        if cur is None:
            cur = dict(nome=tag, descricao=None, status="pendente", depende_producao=0, fontes=[],
                       fonte=b["origem"], criterio="sem curadoria no seed-index.py: revisar",
                       pergunta_dono="Categoria do catalogo sem curadoria: qual e a solucao?")
        caminho, extra, conteudo, faltando = copiar(cur.get("fontes", []), cat_por_id)
        status = cur["status"]
        execucao = cur.get("execucao")
        alertas = []
        if faltando:
            alertas.append("fonte nao encontrada: " + "; ".join(faltando))
        if status == "documentado" and not conteudo and not respostas.get(tag):
            alertas.append("documentado sem conteudo copiado nem resposta do dono: rebaixado para pendente")
            status, execucao = "pendente", None
        if status == "pendente":
            caminho = extra = conteudo = None
            execucao = None
        elif execucao not in EXECUCOES:
            alertas.append(f"execucao invalida ({execucao}): usado com_go")
            execucao = "com_go"
        tem_playbook = 1 if any(rel.startswith(T) and anc is None for rel, anc in cur.get("fontes", [])) else 0
        tem_playbook = tem_playbook if status != "pendente" else 0
        legadas = list(dict.fromkeys(b["legadas"] + cur.get("legadas_extra", [])))
        via = VIA_CURSOR.get(tag) or cur.get("via_cursor") or "duvida"
        if via not in ("A", "B", "duvida"):
            alertas.append(f"via_cursor invalida ({via}): usado duvida")
            via = "duvida"
        linhas.append(dict(
            id=tag, nome=cur["nome"], descricao=cur.get("descricao"), tem_playbook=tem_playbook,
            depende_producao=int(cur.get("depende_producao", 0)), status=status, execucao=execucao,
            motivo_execucao=cur.get("motivo_execucao") if status == "documentado" else None,
            pergunta_dono=cur.get("pergunta_dono"), caminho_md=caminho,
            conteudo_solucao=conteudo, fonte=cur.get("fonte"), tags_legadas=json.dumps(legadas, ensure_ascii=False),
            caminhos_extra=extra, estado_catalogo=b["estado_catalogo"], tipo=b["tipo"],
            criterio_status=cur.get("criterio"), tag_no_catalogo=b["tag_no_catalogo"],
            conteudo_sha=hashlib.sha256(conteudo.encode()).hexdigest()[:16] if conteudo else None,
            alerta=" | ".join(alertas) or None, via_cursor=via))
    return linhas


UPSERT = """
INSERT INTO categorias (id, nome, descricao, tem_playbook, depende_producao, status, execucao, motivo_execucao,
    pergunta_dono, caminho_md, conteudo_solucao, fonte, tags_legadas, atualizado_em, caminhos_extra, estado_catalogo,
    tipo, criterio_status, tag_no_catalogo, status_manual, conteudo_sha, alerta, via_cursor)
VALUES (:id, :nome, :descricao, :tem_playbook, :depende_producao, :status, :execucao, :motivo_execucao,
    :pergunta_dono, :caminho_md, :conteudo_solucao, :fonte, :tags_legadas, :atualizado_em, :caminhos_extra,
    :estado_catalogo, :tipo, :criterio_status, :tag_no_catalogo, 0, :conteudo_sha, :alerta, :via_cursor)
ON CONFLICT(id) DO UPDATE SET
    nome=excluded.nome, descricao=excluded.descricao, depende_producao=excluded.depende_producao,
    fonte=excluded.fonte,
    tags_legadas=excluded.tags_legadas,
    estado_catalogo=COALESCE(excluded.estado_catalogo, categorias.estado_catalogo),
    tipo=COALESCE(excluded.tipo, categorias.tipo), tag_no_catalogo=excluded.tag_no_catalogo,
    pergunta_dono=COALESCE(categorias.pergunta_dono, excluded.pergunta_dono),
    tem_playbook=CASE WHEN categorias.status_manual=1 THEN categorias.tem_playbook ELSE excluded.tem_playbook END,
    status=CASE WHEN categorias.status_manual=1 THEN categorias.status ELSE excluded.status END,
    execucao=CASE WHEN categorias.status_manual=1 THEN categorias.execucao ELSE excluded.execucao END,
    motivo_execucao=CASE WHEN categorias.status_manual=1 THEN categorias.motivo_execucao ELSE excluded.motivo_execucao END,
    caminho_md=CASE WHEN categorias.status_manual=1 THEN categorias.caminho_md ELSE excluded.caminho_md END,
    caminhos_extra=CASE WHEN categorias.status_manual=1 THEN categorias.caminhos_extra ELSE excluded.caminhos_extra END,
    conteudo_solucao=CASE WHEN categorias.status_manual=1 THEN categorias.conteudo_solucao ELSE excluded.conteudo_solucao END,
    conteudo_sha=CASE WHEN categorias.status_manual=1 THEN categorias.conteudo_sha ELSE excluded.conteudo_sha END,
    criterio_status=CASE WHEN categorias.status_manual=1 THEN categorias.criterio_status ELSE excluded.criterio_status END,
    via_cursor=CASE WHEN categorias.status_manual=1 THEN COALESCE(categorias.via_cursor, excluded.via_cursor) ELSE excluded.via_cursor END,
    alerta=excluded.alerta,
    atualizado_em=CASE WHEN categorias.conteudo_sha IS excluded.conteudo_sha AND categorias.status IS excluded.status
                       AND categorias.execucao IS excluded.execucao AND categorias.descricao IS excluded.descricao
                       AND COALESCE(categorias.via_cursor,'') IS COALESCE(excluded.via_cursor,'')
                       THEN categorias.atualizado_em ELSE excluded.atualizado_em END
"""


def recopiar_manuais(con):
    """Linhas com status_manual=1: recopia o conteudo a partir do caminho_md delas."""
    n = 0
    for r in con.execute("SELECT id, caminho_md FROM categorias WHERE status_manual=1 AND caminho_md IS NOT NULL").fetchall():
        p, a = separar_caminho(r["caminho_md"])
        texto = extrair_markdown(p, a)
        if texto:
            con.execute("UPDATE categorias SET conteudo_solucao=?, conteudo_sha=?, alerta=NULL WHERE id=?",
                        (f"<!-- fonte: {r['caminho_md']} -->\n{texto}", hashlib.sha256(texto.encode()).hexdigest()[:16], r["id"]))
        else:
            con.execute("UPDATE categorias SET alerta=? WHERE id=?", ("caminho_md manual nao encontrado: " + r["caminho_md"], r["id"]))
        n += 1
    return n


def aplicar_aliases(con, agora):
    fundidos = {}
    for alias, alvo in ALIASES.items():
        fundidos[alias] = fundir_alias(con, alias, alvo, "fila:* duplicada de cat:* (proposta aprovada em 04/10/2026)", agora)
    return fundidos


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", help="caminho do banco (padrao /home/box/agent-data/gleap-index/suporte.sqlite)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    agora = agora_iso()
    if args.dry_run:
        linhas = montar_linhas()
        for linha in sorted(linhas, key=lambda x: (x["status"], x["execucao"] or "", x["id"])):
            print(f"{linha['status']:12} {linha['execucao'] or '-':9} via={linha.get('via_cursor') or '-':6} {linha['id']:40} {linha['caminho_md'] or '-'}"
                  + (f"  !! {linha['alerta']}" if linha["alerta"] else ""))
        print(f"\n{len(linhas)} categorias + {len(ALIASES)} aliases (dry-run, nada gravado)")
        return
    con = conectar(args.db)
    respostas = {r["id"]: r["resposta_dono"] for r in con.execute("SELECT id, resposta_dono FROM categorias WHERE resposta_dono IS NOT NULL")}
    linhas = montar_linhas(respostas)
    for linha in linhas:
        assert linha["status"] in STATUS_VALIDOS, linha
        linha["atualizado_em"] = agora
    with con:
        con.executemany(UPSERT, linhas)
        fundidos = aplicar_aliases(con, agora)
        manuais = recopiar_manuais(con)
        ids = {l["id"] for l in linhas}
        orfas = [r["id"] for r in con.execute(
            "SELECT id FROM categorias WHERE COALESCE(fonte,'') NOT IN ('desconhecida','nova-pendente') AND status_manual=0")
            if r["id"] not in ids]
        for o in orfas:
            con.execute("UPDATE categorias SET alerta='nao gerada pelo seed atual (sumiu do catalogo/curadoria?)' WHERE id=?", (o,))
        con.execute("INSERT INTO sync_execucoes (tipo, iniciado_em, concluido_em, detalhes) VALUES ('seed', ?, ?, ?)",
                    (agora, agora_iso(), json.dumps({"categorias": len(linhas), "manuais_recopiadas": manuais, "orfas": orfas,
                                                     "aliases": len(ALIASES), "aliases_fundidos": len(fundidos)})))
    tot = con.execute("SELECT status, COALESCE(execucao,'-') e, COUNT(*) n FROM categorias GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    vias = con.execute("SELECT COALESCE(via_cursor,'-') v, COUNT(*) n FROM categorias GROUP BY 1 ORDER BY 1").fetchall()
    print("categorias: " + ", ".join(f"{r['status']}/{r['e']}={r['n']}" for r in tot)
          + f" | total={sum(r['n'] for r in tot)} | aliases={len(ALIASES)}")
    print("via_cursor: " + ", ".join(f"{r['v']}={r['n']}" for r in vias))
    for r in con.execute("SELECT id, alerta FROM categorias WHERE alerta IS NOT NULL ORDER BY id"):
        print(f"ALERTA {r['id']}: {r['alerta']}")


if __name__ == "__main__":
    main()
