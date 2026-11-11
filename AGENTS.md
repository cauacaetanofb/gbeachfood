# GBeachFood — instruções para trabalhar neste projeto

## Comece por aqui

O GBeachFood atende o restaurante do Guriri Beach Acqua Park. É um aplicativo
Django com saldo pré-pago, QR Code, etiquetas para visitantes sem cadastro,
pedidos e pagamentos Asaas. O pacote Python de configuração continua sendo `gfood`.

- Leia as seções relevantes do [README.md](README.md) e o código da área da tarefa.
  Não é necessário reler o repositório inteiro a cada alteração.
- Trabalhe na pasta que contém `manage.py`; não suponha caminhos absolutos ou
  nomes antigos de pastas. Não dependa do histórico de outros chats.
- Confira o estado atual dos arquivos antes de editar e preserve alterações do
  usuário e de outros chats. Evite editar simultaneamente os mesmos arquivos.
- Mantenha este arquivo para regras duradouras e o README para funcionamento,
  configuração e decisões do produto. Atualize a documentação quando uma mudança
  aprovada alterar essas informações; não registre como concluído o que está pendente.

## Combinados com o responsável

- Responda em português brasileiro, com explicações diretas.
- **Não execute comandos Git.** Entregue-os prontos para o usuário executar;
  essa preferência inclui consultas Git. Use leitura de arquivos para investigar.
- Após alterações, mostre os arquivos e o que mudou, a validação realizada e
  eventuais limitações. Use patches e links para facilitar a revisão.
- Ao entregar alterações, inclua os três comandos `git add -A`,
  `git commit -m "mensagem correspondente à alteração"` e `git push origin HEAD`,
  além dos comandos de execução local e deploy abaixo. Não proponha `--force`
  como procedimento normal e não execute esses comandos pelo usuário.
- O estado atual da hospedagem está registrado no README. Não execute deploy,
  crie recursos pagos, reative serviços pausados ou aumente a capacidade sem uma
  solicitação nesse sentido. Preserve os limites econômicos aprovados.
  Autorizações antigas para migração não significam autorização atual.
- Não publique nem imprima conteúdo de `.env`, chaves, senhas ou dados de clientes.
  O usuário não quer um arquivo `.env.example`.
- `/docs/` permanece ignorado por preferência do usuário. Instruções compartilhadas
  entre máquinas/chats devem ficar em arquivos versionáveis na raiz, como estes.

## Mapa do código

| Área | Arquivos e responsabilidades |
|---|---|
| Configuração | `gfood/settings.py` local; `gfood/production.py` produção; `gfood/test_settings.py` testes isolados |
| Contas | `accounts/`: perfis, autenticação, recuperação de senha, gestão de usuários |
| Cartões e dinheiro | `cards/models.py`, `cards/views.py`, `cards/validation.py`: saldo, emissões, vendas de cartão, Asaas |
| Produtos | `products/`: cardápio e `PhysicalCardPrice`, preço único do cartão físico |
| Pedidos | `orders/`: itens, total e débito de saldo |
| Relatórios | `reports/`: vendas, movimentações, métodos de pagamento |
| Interface | `templates/`, `static/css/custom.css`, `static/js/`, `static/images/ui-icons.svg` |
| Publicação | `deploy.ps1`, `Dockerfile`, `firebase.json`, `gfood/production.py` |

## Regras que as mudanças devem preservar

- Perfis: `admin`, `caixa`, `balcao`, `cliente`. Somente clientes possuem cartão
  pessoal; funcionários não têm a opção “Meu cartão”. Verifique permissões na API,
  além de controlar a interface. `user_type='admin'` e superusuário Django são
  atributos diferentes; não presuma que um implique automaticamente o outro.
- O caixa cria um cartão temporário sem conta de usuário; o sistema gera o UUID
  e imprime o QR em uma etiqueta. Não exige QR pré-impresso ou digitado para criar.
  Reimpressão mantém UUID e saldo e não cria uma venda. Tamanho da etiqueta é ajustável.
- O cartão físico em branco é opcional. Seu preço vem de
  `products.models.PhysicalCardPrice`, editável apenas pelo administrador,
  fixado no topo de Produtos e sem exclusão pela interface/API. R$ 2,00 é somente
  o preço inicial. Ele não pertence ao cardápio de alimentos.
- Na emissão, cartão físico é cobrado à parte do saldo inicial. Em Saldo, permite
  várias compras/reposições para a mesma etiqueta, com pagamento externo ou
  “Usar saldo”. Saldo insuficiente não gera venda nem débito.
- O servidor determina os preços. O `preco_cartao` enviado pelo navegador confirma
  o valor exibido; preço desatualizado exige nova confirmação para uma nova venda.
  Reenvios de compras concluídas e vendas antigas mantêm o preço original.
- Preserve a idempotência: `CardIssuance` identifica a emissão e
  `Transaction.physical_purchase_request_id` identifica cada compra posterior.
  Repetir uma solicitação não duplica cartão, crédito, venda ou débito. Uma nova
  chave representa outra compra. Preserve a recuperação das tentativas pendentes na UI.
- Use `Decimal` nos cálculos monetários, validação de centavos e transações atômicas
  para saldo e histórico. Preserve bloqueios concorrentes e rollback em falhas.
- Recargas presenciais exigem caixa/admin. Recargas pelo app usam PIX ou crédito
  à vista, em uma vez, na página do Asaas. O app não coleta dados do cartão de crédito.
  O saldo só é creditado após confirmação autenticada, uma vez por recarga.
- O webhook exige `ASAAS_WEBHOOK_TOKEN` válido. Preserve a validação de cobrança,
  valor, método e estado. Não reative o crédito direto pela rota antiga do cliente.
- Vendas de cartão físico são `Transaction.tipo='cartao'`. Pagamento com saldo é
  consumo de crédito já existente; não somá-lo novamente ao dinheiro recebido no caixa.
- Mantenha o visual do parque: logo existente, CSS próprio, bordas discretas e
  ícones SVG padronizados. Não reintroduza Bulma nem emojis na interface.
- Preserve migrations já existentes. Ajustes de modelo exigem novas migrations;
  não apague o banco para resolver divergências de schema.

## Ambientes e validação

- Desenvolvimento: SQLite por padrão; `DATABASE_URL` pode mudar o banco.
  Confirme o ambiente antes de executar migrations ou comandos com gravação.
- Asaas é configurado por variáveis de ambiente. Não suponha sandbox só por estar
  rodando localmente: o padrão de `ASAAS_BASE_URL` no código é produção. Use testes
  simulados; não gere cobranças ou envie e-mails reais como verificação rotineira.
- Hospedagem preparada: Firebase Hosting encaminha ao Django no Cloud Run;
  PostgreSQL fornece o banco. Não há dependência de Firestore ou Firebase Functions.
  A configuração no repositório não comprova que os recursos estejam ativos.
- Produção usa WhiteNoise, cookie `__session` e CSRF em sessão para funcionar atrás
  do Firebase Hosting. A PWA não deve armazenar páginas autenticadas nem APIs.
- Execute testes pertinentes à mudança. Para dinheiro, autorização e idempotência,
  valide falhas e reenvios. Para ajustes visuais simples, confira a renderização e
  atualize apenas testes existentes que tenham ficado incompatíveis.

Comandos na raiz do projeto, em PowerShell:

```powershell
# Executar localmente; --insecure serve estáticos no teste local com DEBUG=False.
.\venv\Scripts\python.exe manage.py runserver --insecure

# Suíte Django isolada, sem usar o .env ou serviços externos reais.
.\venv\Scripts\python.exe -B manage.py test --settings=gfood.test_settings --noinput

# Verificação quando houver alterações de modelos/migrations.
.\venv\Scripts\python.exe -B manage.py makemigrations --check --dry-run --settings=gfood.test_settings

# Verificações adicionais conforme a área alterada.
node tests/login_recovery.test.cjs
node tests/service_worker.test.cjs
node tests/credit_recharge.test.cjs
powershell -NoProfile -ExecutionPolicy Bypass -File tests/deploy_smoke.ps1

# Apenas fornecer ao usuário quando entregar alterações; não executar automaticamente.
.\deploy.ps1
```

Os testes Django usam SQLite em memória por padrão e simulam Asaas e e-mail.
Testes de concorrência que exigem PostgreSQL são pulados nesse ambiente; informe
isso ao relatar a validação. `TEST_DATABASE_URL` deve apontar apenas para um banco
exclusivo de testes. `tests/deploy_smoke.ps1` simula as CLIs e não publica.

O deploy real executa migrations antes de atualizar o Cloud Run e publicar o
Hosting. Ele exige infraestrutura disponível e não recria banco, faturamento ou
permissões públicas removidas. Para apenas inspecionar o plano, existe
`.\deploy.ps1 -Plan`.
