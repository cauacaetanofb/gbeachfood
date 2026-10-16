# Plano de correções

Aplicação em cinco etapas, preservando os dados existentes e as alterações anteriores do projeto.

1. [x] **Recargas:** restringir recarga presencial a caixa/admin e desativar o crédito direto do cliente. Validar permissões e ausência de movimentação na rota antiga.
2. [x] **Webhook:** exigir token configurado e correto, validar a confirmação PIX e impedir crédito duplicado. Testar rejeições e reenvios sem chamadas reais ao Asaas.
3. [x] **Saldo:** usar Decimal, validar valores, envolver operações em transações atômicas e bloquear registros durante alterações. Cobrir depósitos, retiradas, cartão temporário, cancelamento, transferência, pedidos e confirmação PIX. Simular falhas para verificar rollback.
4. [x] **Recuperação no navegador:** remover a declaração duplicada de CSRF e verificar o carregamento conjunto dos scripts e as requisições de recuperação.
5. [x] **E-mail:** configurar SMTP por ambiente, manter console apenas para desenvolvimento e tratar falhas de envio. Documentar variáveis sem credenciais e testar envio com backend em memória.

## Critérios de conclusão

- Testes executados em banco separado, sem acesso ao banco local ou ao Asaas.
- Checagens Django, migrações e diff sem erros.
- Documentação do que foi aplicado e de configurações externas ainda necessárias.
- PostgreSQL oferece bloqueio por linha; SQLite não implementa select_for_update. A validação concorrente de PostgreSQL será identificada separadamente quando esse banco não estiver disponível.

## Fontes técnicas

- https://docs.asaas.com/docs/sobre-os-webhooks
- https://docs.djangoproject.com/en/5.2/ref/databases/
- https://docs.djangoproject.com/en/5.2/topics/email/

## Aplicação e resultado

1. **Recargas concluídas:** `/api/cards/client/add/` retorna 410 para todos os perfis; `/api/cards/balance/add/` exige caixa/admin. A criação de um PIX apenas registra uma recarga pendente.
2. **Webhook concluído:** token obrigatório comparado em tempo constante, configuração vazia rejeitada, payload PIX validado, saldo e confirmação atômicos. Bloqueio da recarga impede crédito duplicado nos reenvios. Cartão bloqueado ou reatribuído exige revisão operacional e não é creditado.
3. **Movimentações concluídas:** valores e limites validados; saldo e lançamentos gravados juntos. Cartões bloqueados antes de ler/alterar saldo; transferências bloqueiam ambos em ordem de ID. SQLite usa IMMEDIATE. Testes simulam falha no extrato, no item do pedido e na gravação do cartão para verificar rollback.
4. **JavaScript concluído:** o token é declarado apenas em `base.js`, com leitura do formulário ou cookie. Teste Node carrega ambos os scripts no mesmo contexto e exercita abertura do modal, solicitação, redefinição e falha de envio.
5. **E-mail implementado:** SMTP Gmail com STARTTLS, configuração por ambiente e senha de app. Console somente por escolha explícita em desenvolvimento. Falhas retornam JSON sem expor credenciais e removem código não enviado. Códigos gerados com `secrets`.

## Configurações externas pendentes

- Informar a conta Gmail e a senha de app no `.env`/ambiente e validar entrega real. Nenhum e-mail foi enviado durante o trabalho.
- O token do webhook configurado no Asaas deve coincidir com `ASAAS_WEBHOOK_TOKEN`. A integração foi testada com chamadas simuladas, sem pagamentos reais.
- Testes de bloqueio concorrente em PostgreSQL estão preparados, mas não foram executados no ambiente SQLite disponível. Eles não são contabilizados como aprovados.

As mudanças não exigem migrações e não alteram dados existentes. As exclusões dos arquivos do antigo deploy e o `.gitignore` foram preservados.

## Validação executada

- Suíte Django: 43 testes encontrados; 41 aprovados e 2 de concorrência PostgreSQL ignorados no SQLite.
- Teste Node da recuperação de senha: aprovado.
- Django system check: sem problemas.
- `makemigrations --check --dry-run`: sem alterações de modelo.
- Análise estática dos módulos financeiros e testes alterados: sem problemas.
- `git diff --check`: sem erros de whitespace.
- Aviso de teste conhecido: `staticfiles/` ainda não existe, pois `collectstatic` não foi executado. Não afeta estes testes de backend.
