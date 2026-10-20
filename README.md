# 🍔 GFood — Sistema de Gerenciamento para Restaurante

<p align="center">
  <strong>Sistema completo de gerenciamento de restaurante com cartão pré-pago e QR Code</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django" alt="Django 5.2">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
</p>

---

## 📋 Sobre o Projeto

O **GFood** é um sistema web para restaurantes que utiliza um modelo de **cartão pré-pago com QR Code**. Os clientes carregam saldo em seus cartões virtuais e pagam nos balcões do restaurante apresentando o QR Code.

O sistema foi desenvolvido com foco em **uso mobile** (celular), mas funciona perfeitamente em computadores. Cada tipo de usuário possui sua própria interface, e a navegação acontece em uma **página única** (SPA-like) sem recarregamento.

### ✨ Principais Funcionalidades

- 🔐 **4 tipos de usuário** com dashboards independentes (Admin, Caixa, Balcão, Cliente)
- 💳 **Cartão virtual com QR Code** para clientes
- 📱 **QR Code temporário** criado pelo caixa para clientes sem cadastro
- 💰 **Recarga de saldo** presencial (dinheiro, PIX, cartão) ou via app (PIX Asaas)
- 🛒 **Carrinho de pedidos** com débito automático do saldo
- 📊 **Relatórios de vendas** com filtros por período e método de pagamento
- 🔍 **Busca por CPF** para localizar cartões
- 🔄 **Transferência de saldo** entre cartões
- 🚫 **Bloqueio/cancelamento** de cartões com liberação do QR para reutilização
- 📲 **PWA** (Progressive Web App) — instalável no celular como um app
- 🔑 **Recuperação de senha** via código enviado por e-mail

---

## 👥 Tipos de Usuário

### 🔴 Administrador
- Gerencia **produtos** (criar, editar, excluir, ativar/desativar)
- Gerencia **usuários staff** (admin, balcão, caixa)
- Gerencia **clientes** (visualizar, editar, excluir)
- Acessa **relatórios completos** de vendas e transações
- Pode visualizar qualquer dashboard via `?as=caixa`, `?as=balcao`, `?as=cliente`
- Edita seu próprio perfil

### 🟡 Caixa
- Cria **cartões temporários** com QR Code para clientes sem cadastro
- **Adiciona e remove saldo** dos cartões
- **Busca cartões por CPF**
- **Bloqueia/cancela** cartões
- **Transfere saldo** entre cartões
- Monta pedidos e processa pagamentos
- Visualiza **relatório diário** simplificado

### 🟢 Balcão
- Visualiza o **cardápio** de produtos disponíveis
- Monta o **carrinho de pedidos**
- Lê o **QR Code** do cliente para processar o pagamento
- **Consulta saldo** do cliente

### 🔵 Cliente
- Possui **cartão virtual com QR Code**
- **Consulta saldo** do cartão
- **Adiciona saldo** via PIX (integração Asaas)
- Visualiza **extrato de transações**
- Pode instalar o app no celular (PWA)

---

## 🏗️ Arquitetura do Projeto

```
projeto_restaurante/
├── gfood/                  # ⚙️ Configuração principal do Django
│   ├── settings.py         # Configurações (DB, auth, Asaas, etc.)
│   ├── urls.py             # Roteamento principal
│   ├── wsgi.py             # WSGI para produção
│   └── asgi.py             # ASGI
│
├── accounts/               # 👤 App de autenticação e gestão de usuários
│   ├── models.py           # User customizado + PasswordResetCode
│   ├── views.py            # Login, registro, CRUD staff/clientes, perfil
│   ├── forms.py            # LoginForm, ClienteRegisterForm, StaffUserForm
│   ├── backends.py         # Login por email ou username
│   └── management/         # Comando create_superuser_auto
│
├── cards/                  # 💳 App de cartões, saldo e transações
│   ├── models.py           # Card, Transaction, Recarga
│   ├── views.py            # Saldo, QR Code, recarga, Asaas PIX, bloqueio
│   ├── signals.py          # Cria cartão automaticamente para novos clientes
│   └── urls.py             # 15 endpoints de API
│
├── products/               # 🍕 App de produtos e categorias
│   ├── models.py           # Category, Product (com imagem)
│   ├── views.py            # CRUD de produtos (admin only)
│   └── urls.py             # 5 endpoints de API
│
├── orders/                 # 📦 App de pedidos
│   ├── models.py           # Order, OrderItem
│   ├── views.py            # Criação de pedido com débito de saldo
│   └── urls.py             # 1 endpoint de API
│
├── reports/                # 📊 App de relatórios
│   ├── views.py            # Relatório admin, relatório caixa, transações
│   └── urls.py             # 3 endpoints de API
│
├── templates/              # 🎨 Templates HTML
│   ├── base.html           # Template base
│   ├── login.html          # Tela de login + recuperação de senha
│   ├── register.html       # Cadastro de cliente
│   ├── dashboard_admin.html
│   ├── dashboard_caixa.html
│   ├── dashboard_balcao.html
│   ├── dashboard_cliente.html
│   └── partials/
│       └── admin_sidebar.html
│
├── static/                 # 📁 Arquivos estáticos
│   ├── css/custom.css      # Estilos customizados (dark theme)
│   ├── js/
│   │   ├── base.js         # Utilitários (CSRF, fetch, PWA)
│   │   ├── dashboard_admin.js
│   │   ├── dashboard_caixa.js
│   │   ├── dashboard_balcao.js
│   │   └── dashboard_cliente.js
│   ├── images/             # Ícones PWA
│   ├── manifest.json       # PWA manifest
│   └── sw.js               # Service Worker
│
├── media/                  # 📷 Uploads (imagens de produtos)
├── manage.py
├── requirements.txt
└── .env                    # Variáveis de ambiente (NÃO vai para o git)
```

---

## 🛠️ Stack Tecnológica

| Tecnologia | Uso |
|---|---|
| **Django 5.2** | Framework backend (Python) |
| **PostgreSQL** | Banco de dados em produção |
| **SQLite** | Banco de dados em desenvolvimento |
| **Bulma CSS** | Framework CSS para estilização |
| **JavaScript (Vanilla)** | Frontend interativo (SPA-like) |
| **QR Code (qrcode)** | Geração de QR Codes para cartões |
| **Asaas API** | Gateway de pagamento (PIX) |
| **Gunicorn** | Servidor WSGI para produção |
| **WhiteNoise** | Servir arquivos estáticos em produção |

---

## 🚀 Como Rodar Localmente

### Pré-requisitos
- Python 3.12+
- pip (gerenciador de pacotes Python)

### Passo a passo

1. **Clone o repositório**
```bash
git clone https://github.com/cauacaetanofb/projeto_restaurante.git
cd projeto_restaurante
```

2. **Crie e ative o ambiente virtual**
```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

4. **Configure as variáveis de ambiente**

Crie um arquivo `.env` na raiz do projeto:
```env
SECRET_KEY=sua-chave-secreta-aqui
ASAAS_API_KEY=sua-chave-asaas
ASAAS_BASE_URL=https://sandbox.asaas.com/api/v3
ASAAS_WEBHOOK_TOKEN=seu-token-webhook
```

5. **Execute as migrations**
```bash
python manage.py migrate
```

6. **Crie um superusuário (admin)**
```bash
python manage.py createsuperuser
```

7. **Inicie o servidor**
```bash
python manage.py runserver
```

8. **Acesse o sistema**
- Abra o navegador em: `http://localhost:8000`
- Faça login com o superusuário criado

---

## ☁️ Deploy no Google Cloud / Firebase

O projeto Firebase `gbeachfood` compartilha os recursos do Google Cloud. O Django
será executado no **Cloud Run**, conectado ao **Cloud SQL PostgreSQL**, com senhas
no **Secret Manager**. A primeira publicação usará o endereço HTTPS do Cloud Run.
O Firebase Hosting encaminha o endereço público `https://gbeachfood.web.app`
para o serviço Cloud Run `gbeachfood` em `southamerica-east1`. A configuração local
está em `firebase.json` e `.firebaserc`; é necessário publicar essas configurações
com a CLI Firebase após atualizar a imagem do Cloud Run.

### Publicar pelo terminal do VS Code (Windows)

O script `deploy.ps1`, na raiz, publica os arquivos salvos no computador diretamente
no projeto `gbeachfood`. O build continua no Cloud Build: não precisa de Docker local,
ZIP manual ou Cloud Shell. O script não executa comandos Git.

Preparação única neste computador:

1. Instalar a [Google Cloud CLI para Windows](https://docs.cloud.google.com/sdk/docs/install-sdk#windows),
   incluindo o PATH, e fechar/reabrir o VS Code.
2. Ter Node.js LTS com `npx` disponível.
3. No PowerShell do VS Code, autenticar com a conta que administra `gbeachfood`:

```powershell
gcloud.cmd auth login
gcloud.cmd config set project gbeachfood
npx.cmd --yes firebase-tools login
```

O login feito no Cloud Shell não autentica automaticamente este computador.

Para publicar, a partir da raiz do projeto:

```powershell
.\deploy.ps1
```

Se o PowerShell bloquear scripts, execute apenas este processo com a política adequada,
sem mudar a política permanente do Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy.ps1
```

O script verifica acesso ao Firebase, envia o código respeitando `.gcloudignore`,
constrói uma imagem com versão baseada na data/hora UTC, atualiza o job
`gbeachfood-migrate` para essa imagem, executa migrations e aguarda o sucesso.
Depois atualiza a imagem do serviço e publica o Firebase Hosting. Mantém as variáveis,
os segredos, a conexão SQL e as permissões já cadastradas. O `.env` e o banco local
não são enviados. Novas variáveis/segredos exigem configuração separada no Cloud Run.

Qualquer erro interrompe os passos seguintes. Não há reversão automática das etapas
já concluídas nem das migrations: mudanças no banco devem ser compatíveis com a
versão do app que ainda está atendendo durante a publicação.

Opções:

```powershell
# Mostra o plano sem chamar ferramentas externas nem publicar:
.\deploy.ps1 -Plan

# Somente alteracoes no firebase.json ou arquivos em firebase-public/:
.\deploy.ps1 -HostingOnly
```

Mudanças em Python, templates, CSS, JavaScript e dependências precisam do deploy
completo, pois esses arquivos são servidos pela imagem do Cloud Run. Execute uma
publicação por vez e teste o site ao terminar.

Validação do script, sem nuvem ou credenciais:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/deploy_smoke.ps1
```

O teste simula as ferramentas e verifica ordem das etapas, uso da mesma imagem,
interrupção em erros, restauração da pasta atual e modo somente Hosting. O deploy
real depende da CLI instalada e das autenticações locais.

### Arquivos de publicação

- `Dockerfile`: instala Python e dependências, coleta estáticos e inicia Gunicorn
  na porta `PORT`. Não executa migrations ao iniciar o servidor.
- `.dockerignore` e `.gcloudignore`: enviam apenas as pastas de código e os arquivos
  de build permitidos. Excluem `.env`, banco local, ambiente virtual e credenciais locais.
- `gfood/production.py`: desabilita DEBUG e leitura de `.env`, exige PostgreSQL,
  chave secreta e hosts; configura HTTPS e cookies seguros atrás do proxy Cloud Run.
  A execução local continua usando `gfood.settings`.

### Firebase Hosting (`gbeachfood.web.app`)

A configuração de produção usa `SESSION_COOKIE_NAME="__session"` e
`CSRF_USE_SESSIONS=True`, porque o Hosting encaminha apenas esse cookie ao backend.
O template base disponibiliza o token CSRF no HTML para as chamadas JavaScript em
todas as telas. A proteção CSRF permanece ativa. A troca de nome do cookie exige
um novo login para sessões antigas.

`firebase-public/` permanece sem páginas HTML: todas as rotas são encaminhadas ao
Django. Não coloque `index.html` nessa pasta, pois ele substituiria a tela inicial.
Os arquivos estáticos continuam sendo servidos pelo WhiteNoise. A configuração do
Hosting define `Cache-Control: private, no-store`; a PWA armazena somente recursos
em `/static/`, sem guardar páginas com tokens ou respostas de APIs.

Antes do deploy do Hosting, publique uma imagem com esses ajustes no Cloud Run e
inclua `gbeachfood.web.app` e `gbeachfood.firebaseapp.com` em `ALLOWED_HOSTS`, mantendo
o host original do Cloud Run. Inclua as duas origens HTTPS em
`CSRF_TRUSTED_ORIGINS`. Use `--update-env-vars` para preservar as outras variáveis.

No Cloud Shell, a partir da pasta com `firebase.json`:

```bash
npx --yes firebase-tools login --no-localhost
npx --yes firebase-tools deploy --only hosting --project=gbeachfood
```

A conta usada na CLI deve ter acesso ao projeto `gbeachfood`. A configuração já
está criada; não é necessário executar `firebase init`. Não há migrations novas
nesta mudança. Para testar o fluxo completo publicado, ainda é necessário criar
um usuário, entrar pelo domínio web.app, executar uma ação autenticada e sair.

Testes locais: `python -B manage.py test --settings=gfood.test_settings`,
`node tests/login_recovery.test.cjs` e `node tests/service_worker.test.cjs`.
Eles cobrem login, alteração de perfil, logout, rejeição de CSRF inválido, token em
todos os dashboards e exclusão de páginas/APIs do cache da PWA. O filtro de cookies
do Hosting é simulado; isso não substitui a validação na hospedagem real.

### Configuração do serviço

Use a mesma região para Cloud Run e Cloud SQL, por exemplo `southamerica-east1`
(São Paulo). Na configuração do Cloud Run, vincule a instância Cloud SQL e use uma
conta de serviço com `Cloud SQL Client` e acesso somente aos segredos necessários
(`Secret Manager Secret Accessor`). Use a segunda geração de execução do Cloud Run.

| Variável | Valor/configuração |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `gfood.production` (já definido na imagem) |
| `SECRET_KEY` | Segredo com chave aleatória exclusiva de produção, de pelo menos 50 caracteres |
| `ALLOWED_HOSTS` | Host exato do serviço Cloud Run, sem `https://`; outros domínios separados por vírgula |
| `CSRF_TRUSTED_ORIGINS` | Origens HTTPS adicionais, se houver; acesso na mesma origem não exige esta variável |
| `INSTANCE_CONNECTION_NAME` | Nome de conexão da instância, no formato `gbeachfood:REGIAO:INSTANCIA` |
| `DB_NAME` | `gbeachfood` |
| `DB_USER` | Usuário PostgreSQL dedicado à aplicação |
| `DB_PASSWORD` | Senha desse usuário, referenciada pelo Secret Manager |
| `EMAIL_HOST_USER` | Conta Gmail que envia a recuperação de senha |
| `EMAIL_HOST_PASSWORD` | Senha de app Gmail, referenciada pelo Secret Manager |
| `DEFAULT_FROM_EMAIL` | Remetente, por exemplo `GBeachFood <sua-conta@gmail.com>` |
| `ASAAS_API_KEY` | Chave Asaas no Secret Manager |
| `ASAAS_BASE_URL` | URL sandbox ou produção correspondente à chave Asaas |
| `ASAAS_WEBHOOK_TOKEN` | Token do webhook no Secret Manager; o mesmo cadastrado no Asaas |

Alternativa ao Cloud SQL: sem `INSTANCE_CONNECTION_NAME`, informe `DATABASE_URL`
de um PostgreSQL externo. A configuração de produção recusa SQLite.

### Validação local da preparação

A suíte isolada inclui testes da configuração de produção e do login atrás do
proxy HTTPS. A coleta e a entrega de estáticos pelo WhiteNoise também foram
verificadas localmente. `check --deploy` mantém apenas os avisos de HSTS para
subdomínios e preload, deixados desabilitados até a definição de um domínio próprio.
A imagem Docker ainda precisa ser construída e testada no Google Cloud; Docker e
gcloud não estavam disponíveis nesta máquina durante a preparação.

### Ordem da primeira publicação

1. Criar a instância PostgreSQL, banco e usuário. Revisar o custo estimado antes
   de confirmar: Cloud SQL tem cobrança própria, mesmo sem visitas ao app.
2. Cadastrar os segredos no Secret Manager, usando versões numéricas nas referências
   do Cloud Run. A senha do banco não deve ser enviada pelo chat nem incluída na imagem.
3. Construir a imagem e criar um Cloud Run Job com essa mesma imagem, conexão SQL,
   conta de serviço e variáveis. Sobrescrever o comando para `python` e os argumentos
   para `manage.py,migrate,--noinput`. Executar o job e verificar sua conclusão.
4. Publicar o serviço com acesso público (o Django continua controlando o login),
   configurar seu host em `ALLOWED_HOSTS` e verificar a tela de login por HTTPS.
   Começar com mínimo de 0 e máximo de 2 instâncias, concorrência 8; ajustar após medir.
5. Criar o administrador por um job separado e configurar a URL HTTPS do webhook
   no Asaas. Validar login, recuperação de senha e pagamento no sandbox antes do uso real.

O PostgreSQL novo começa vazio: migrations criam as tabelas, mas não transferem
cadastros, saldos nem pedidos do SQLite local. Caso seja necessário preservar esses
dados, planejar a migração antes de abrir o app aos clientes.

O disco do Cloud Run é temporário. As imagens cadastradas pelo painel atual ficam
no banco em base64. Imagens antigas que dependam de arquivos em `media/`, ou uploads
pelo Django Admin, precisam de armazenamento persistente antes de serem usados no deploy.

Referências: [Django no Cloud Run](https://docs.cloud.google.com/python/django/run),
[conexão com Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/connect-run) e
[cookies no Firebase Hosting](https://firebase.google.com/docs/hosting/manage-cache#using_cookies).

---

## 💳 Integração Asaas (Pagamento PIX)

O sistema utiliza a [API do Asaas](https://docs.asaas.com) para processar recargas via PIX.

### Como funciona

1. O cliente solicita uma recarga no app
2. O sistema cria uma cobrança PIX no Asaas
3. O Asaas retorna um **QR Code PIX** para pagamento
4. Após o pagamento, o Asaas envia um **webhook** confirmando
5. O sistema **credita o saldo** automaticamente no cartão do cliente

### Configuração

- **Sandbox** (testes): `ASAAS_BASE_URL=https://sandbox.asaas.com/api/v3`
- **Produção**: `ASAAS_BASE_URL=https://api.asaas.com/api/v3`

### Webhook

Configure a URL do webhook no painel do Asaas:
```
https://app.exemplo.com/api/asaas/webhook/
```

Eventos que devem ser habilitados:
- `PAYMENT_CONFIRMED`
- `PAYMENT_RECEIVED`

---

## 🔐 Recargas e consistência do saldo

- Recargas presenciais exigem perfil `caixa` ou `admin`. Clientes geram PIX; o crédito ocorre após confirmação autenticada.
- Configure `ASAAS_WEBHOOK_TOKEN` no ambiente e use o mesmo valor como token de autenticação do webhook no painel Asaas. Esse token é diferente da chave da API. Sem configuração, o endpoint retorna HTTP 503; sem token válido na requisição, HTTP 401.
- O webhook aceita POST e valida cobrança, valor, tipo PIX e status confirmado/recebido. A recarga é creditada uma única vez, mesmo com reenvios ou os dois eventos `PAYMENT_CONFIRMED` e `PAYMENT_RECEIVED`.
- Cartão bloqueado ou que mudou de proprietário não recebe a recarga pendente: o webhook retorna HTTP 409, sem crédito, para revisão operacional.
- Depósitos, retiradas, cancelamentos, transferências e pedidos gravam saldo e histórico na mesma transação. Uma falha desfaz todas as gravações da operação.
- Valores monetários locais usam `Decimal`; entradas não finitas, negativas, acima do limite ou com fração de centavo são rejeitadas.
- PostgreSQL utiliza bloqueios por linha. SQLite usa transações `IMMEDIATE`, serializando escritores; sua capacidade de concorrência é diferente da de PostgreSQL.

## ✉️ Recuperação de senha com Gmail

O backend padrão é SMTP. Adicione as entradas abaixo ao seu `.env`, preservando as configurações já existentes:

```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=sua-conta@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-app
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_TIMEOUT=15
DEFAULT_FROM_EMAIL=GFood <sua-conta@gmail.com>
```

Ative a verificação em duas etapas na conta e gere uma **senha de app** nas [configurações do Google](https://support.google.com/accounts/answer/185833?hl=pt-BR). Informe-a somente no `.env` local ou nos segredos da hospedagem. A disponibilidade de senhas de app depende das políticas da conta. Não use a senha normal da conta. Reinicie a aplicação após configurar.

Para desenvolvimento sem envio real, defina explicitamente `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` e `DEBUG=True`. Console é rejeitado com `DEBUG=False`. TLS e SSL não podem ser habilitados ao mesmo tempo.

Se faltar configuração ou o SMTP falhar, a API retorna erro JSON (HTTP 503). Um código que não foi enviado é removido. Os testes usam mensagens em memória e SMTP simulado, sem enviar e-mails reais.

## 🧪 Validação das correções

```bash
python -B manage.py test --settings=gfood.test_settings
node tests/login_recovery.test.cjs
```

A configuração de testes ignora `.env`, usa SQLite em memória, senhas de teste e e-mail em memória. Os testes da API Asaas simulam as chamadas externas. Dois testes de concorrência exigem PostgreSQL e são ignorados no SQLite. Para executá-los, forneça `TEST_DATABASE_URL` de um ambiente PostgreSQL exclusivo de testes (com permissão de criar o banco de teste) ao executar a mesma suíte; não use credenciais de produção.

---

## 🔌 API Endpoints

### Autenticação (`accounts/`)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/profile/` | Retorna perfil do usuário logado |
| POST | `/api/profile/update/` | Atualiza perfil |
| POST | `/api/forgot-password/` | Envia código de recuperação |
| POST | `/api/reset-password/` | Reseta senha com código |

### Gestão de Staff (`accounts/` — admin only)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/staff/` | Lista staff |
| POST | `/api/staff/create/` | Cria staff |
| POST | `/api/staff/<id>/update/` | Atualiza staff |
| POST | `/api/staff/<id>/delete/` | Exclui staff |

### Gestão de Clientes (`accounts/` — admin only)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/clients/` | Lista clientes |
| POST | `/api/clients/<id>/update/` | Atualiza cliente |
| POST | `/api/clients/<id>/delete/` | Exclui cliente |

### Cartões (`cards/`)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/cards/my/` | Retorna cartão do cliente logado |
| GET | `/api/cards/balance/?qr_data=UUID` | Consulta saldo por QR Code |
| POST | `/api/cards/balance/add/` | Adiciona saldo (caixa) |
| POST | `/api/cards/balance/remove/` | Remove saldo (caixa) |
| POST | `/api/cards/temp/create/` | Cria cartão temporário (caixa) |
| POST | `/api/cards/client/add/` | Rota antiga desativada: retorna HTTP 410 sem alterar saldo |
| GET | `/api/cards/client/<id>/transactions/` | Transações de um cliente (admin) |
| GET | `/api/cards/my/transactions/` | Minhas transações (cliente) |
| GET | `/api/cards/search-cpf/?cpf=XXX` | Busca cartão por CPF |
| POST | `/api/cards/block/` | Bloqueia cartão |
| POST | `/api/cards/transfer/` | Transfere saldo |

### Asaas — Pagamento PIX (`cards/`)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/asaas/create-payment/` | Cria cobrança PIX |
| POST | `/api/asaas/webhook/` | Recebe webhook do Asaas |
| GET | `/api/asaas/check-payment/<id>/` | Verifica status do pagamento |

### Produtos (`products/`)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/products/` | Lista produtos disponíveis |
| GET | `/api/products/all/` | Lista todos (admin) |
| POST | `/api/products/create/` | Cria produto (admin) |
| POST | `/api/products/<id>/update/` | Atualiza produto (admin) |
| POST | `/api/products/<id>/delete/` | Exclui produto (admin) |

### Pedidos (`orders/`)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/orders/create/` | Cria pedido com débito de saldo |

### Relatórios (`reports/` — admin/caixa)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/reports/sales/?period=today` | Relatório completo (admin) |
| GET | `/api/reports/daily/` | Relatório diário (caixa) |
| GET | `/api/reports/transactions/` | Transações de pagamento (admin) |

---

## 📱 PWA (Progressive Web App)

O GFood pode ser instalado como um app no celular:

1. Acesse o site pelo **navegador do celular**
2. Toque em **"Adicionar à tela inicial"** (ou "Instalar app")
3. O GFood aparecerá como um app na sua tela inicial

---

## 📄 Licença

Este projeto foi desenvolvido por **Cauã Caetano** — [cauacaetanofb@gmail.com](mailto:cauacaetanofb@gmail.com)
