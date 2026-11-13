# GBeachFood — Sistema de Gerenciamento para Restaurante

<p align="center">
  <strong>Sistema completo de gerenciamento de restaurante com cartão pré-pago e QR Code</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?style=for-the-badge&logo=django" alt="Django 5.2">
  <img src="https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
</p>

---

## Trabalhar no projeto em novos chats

Abra o novo chat do Codex vinculado à pasta deste repositório, a que contém
`manage.py`. O [AGENTS.md](AGENTS.md) reúne as regras para trabalhar no código,
os combinados com o responsável e os comandos de validação. Este README descreve
o funcionamento, a configuração e as decisões do produto. Ambos ficam na raiz
para serem versionados; `/docs/` continua ignorado.

Use um chat por assunto ou tarefa, por exemplo: “Pagamentos”, “Interface do caixa”
ou “Relatórios”. Não conte com a transferência automática do histórico de outra
conversa. Um ponto de partida para cada chat é:

> Leia o AGENTS.md e as seções relevantes do README.md. Neste chat vamos trabalhar
> em [assunto]. Minha tarefa é [resultado desejado]. Confira o código atual antes
> de alterar e siga os combinados registrados no projeto.

Ao concluir uma mudança que altere regras ou configuração, atualize a documentação
correspondente. Evite dois chats editando os mesmos arquivos ao mesmo tempo;
ao passar uma tarefa adiante, informe o que foi concluído, os arquivos alterados,
as verificações realizadas e o que falta fazer.

### Decisões e pendências conhecidas

Contexto revisado em **11/11/2026** a partir do código local e das decisões do
responsável. A seção de hospedagem registra também a configuração econômica,
a publicação solicitada e as verificações realizadas na nuvem nessa data.
As referências dos segredos e o estado da integração Asaas foram atualizados em
**13/11/2026**, conforme descrito na seção de pagamentos.

- O aplicativo foi publicado em `https://gbeachfood.web.app` com o perfil econômico,
  migrations aplicadas e administrador configurado. O desenvolvimento também pode
  continuar localmente; novas publicações não devem ocorrer automaticamente.
- Recargas online estão pausadas com `ASAAS_PAYMENTS_ENABLED=False`. A chave e o
  token da conta Asaas indicada pelo responsável já estão vinculados ao Cloud Run
  pelas versões `2` dos segredos. A autenticação e a configuração do webhook foram
  verificadas; o fluxo completo de pagamento ainda precisa ser validado antes da
  ativação. Recargas presenciais, saldo e pedidos continuam disponíveis. A
  recuperação de senha por e-mail aguarda SMTP.
- Cartões de visitantes são emitidos como etiquetas pelo caixa. O cartão físico
  em branco é opcional, pode ser comprado novamente e tem preço definido pelo admin.
- A área do cartão físico no admin deve permanecer compacta: título, preço e
  botão de salvar. O modelo da impressora de etiquetas ainda não foi definido;
  as medidas continuam ajustáveis na tela de impressão.
- Asaas oferece PIX e crédito à vista em uma vez. Sandbox ou produção dependem
  do ambiente configurado, e não da pasta ou do computador em que o app roda.
- Emissão de nota fiscal ainda não está implementada. O responsável informou
  empresa no ES e regime Simples Nacional. O cadastro já aceita NCM opcional;
  os códigos e demais dados fiscais ainda precisam ser definidos e validados
  antes de implementar essa integração.

---

## 📋 Sobre o Projeto

O **GBeachFood** atende o restaurante do Guriri Beach Acqua Park e utiliza um modelo de **cartão pré-pago com QR Code**. Os clientes cadastrados usam cartão virtual; visitantes sem conta recebem uma etiqueta emitida pelo caixa. Ambos utilizam o QR Code para consumir o saldo no restaurante.

O sistema foi desenvolvido com foco em **uso mobile** (celular), mas funciona perfeitamente em computadores. Cada tipo de usuário possui sua própria interface, e a navegação acontece em uma **página única** (SPA-like) sem recarregamento.

### ✨ Principais Funcionalidades

- 🔐 **4 tipos de usuário** com dashboards independentes (Admin, Caixa, Balcão, Cliente)
- 💳 **Cartão virtual com QR Code** para clientes
- 📱 **Etiqueta com QR Code** criada e impressa pelo caixa para clientes sem cadastro
- 💰 **Recarga de saldo** presencial (dinheiro, PIX, cartão) ou via app (PIX e crédito à vista pelo Asaas)
- 🛒 **Carrinho de pedidos** com débito automático do saldo
- 📊 **Relatórios de vendas** com filtros por período e método de pagamento
- 🔍 **Busca por CPF** para localizar cartões
- 🔄 **Transferência de saldo** entre cartões
- 🚫 **Bloqueio/cancelamento** de cartões temporários
- 📲 **PWA** (Progressive Web App) — instalável no celular como um app
- 🔑 **Recuperação de senha** via código enviado por e-mail

---

## 👥 Tipos de Usuário

### 🔴 Administrador
- Gerencia **produtos** (criar, editar, excluir, ativar/desativar)
- Gerencia **usuários staff** (admin, balcão, caixa)
- Gerencia **clientes** (visualizar, editar, excluir)
- Acessa **relatórios completos** de vendas e transações
- Pode acessar os painéis operacionais via `?as=caixa` e `?as=balcao`
- Define o preço do **cartão físico**, em um item fixado no topo de Produtos
- Edita seu próprio perfil

### 🟡 Caixa
- Cria **cartões temporários** com QR Code para clientes sem cadastro
- Imprime e reimprime **etiquetas**, com venda opcional de cartão físico em branco pelo preço definido pelo administrador
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
- **Adiciona saldo** via PIX ou cartão de crédito à vista (integração Asaas)
- Visualiza **extrato de transações**
- Pode instalar o app no celular (PWA)

---

## 🏗️ Arquitetura do Projeto

```
gbeachfood/
├── AGENTS.md               # Instruções compartilhadas entre chats do Codex
├── README.md               # Funcionamento e configuração do projeto
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
│   ├── models.py           # Card, Transaction, Recarga, CardIssuance
│   ├── views.py            # Saldo, etiquetas, cartão físico, recargas Asaas, bloqueio
│   ├── signals.py          # Cria cartão automaticamente para novos clientes
│   └── urls.py             # Rotas da API de cartões e da impressão
│
├── products/               # 🍕 App de produtos e categorias
│   ├── models.py           # Category, Product e PhysicalCardPrice
│   ├── views.py            # CRUD de produtos (admin only)
│   └── urls.py             # Rotas de produtos e do preço do cartão físico
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
│   ├── css/custom.css      # Identidade visual do parque, responsiva e sem Bulma
│   ├── js/
│   │   ├── base.js         # Utilitários (CSRF, fetch, PWA)
│   │   ├── dashboard_admin.js
│   │   ├── dashboard_caixa.js
│   │   ├── temp_cards.js   # Emissão da etiqueta e total com cartão físico opcional
│   │   ├── card_label.js   # Configuração e impressão da etiqueta
│   │   ├── dashboard_balcao.js
│   │   └── dashboard_cliente.js
│   ├── images/             # Logo, ícones PWA e sprite SVG ui-icons.svg
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
| **CSS próprio responsivo** | Identidade visual do parque, sem dependência de framework CSS |
| **JavaScript (Vanilla)** | Frontend interativo (SPA-like) |
| **QR Code (qrcode)** | Geração de QR Codes para cartões |
| **Asaas API** | Gateway de pagamento (PIX e cartão de crédito) |
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
git clone https://github.com/cauacaetanofb/gbeachfood.git
cd gbeachfood
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
ASAAS_PAYMENTS_ENABLED=False
ASAAS_API_KEY=sua-chave-asaas
ASAAS_BASE_URL=https://api-sandbox.asaas.com/v3
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

Esse comando dá acesso ao admin do Django em `/admin/`. O perfil do painel do
aplicativo é controlado também por `user_type`, que deve ser `admin` para um
administrador. O comando `create_superuser_auto` configura ambos, usando
`DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` e `DJANGO_SUPERUSER_PASSWORD`
do ambiente, sem expor a senha no comando ou na documentação.

7. **Inicie o servidor**
```powershell
.\venv\Scripts\python.exe manage.py runserver --insecure
```

`--insecure` é usado apenas no desenvolvimento local para servir os estáticos
mesmo com `DEBUG=False`. Em produção, os estáticos são servidos pelo WhiteNoise.

8. **Acesse o sistema**
- Abra o navegador em: `http://localhost:8000`
- Faça login com o superusuário criado

---

## Deploy no Google Cloud / Firebase

O Django é executado no Cloud Run, com PostgreSQL e segredos no Secret Manager.
O Firebase Hosting encaminha as requisições de `https://gbeachfood.web.app`
para o serviço `gbeachfood` no Cloud Run, em `southamerica-east1`.

### Publicar pelo terminal do VS Code (Windows)

Instale a Google Cloud CLI e o Node.js LTS, reabra o VS Code e autentique:

```powershell
gcloud.cmd auth login
gcloud.cmd config set project gbeachfood
npx.cmd --yes firebase-tools login
```

O script publica os arquivos locais usando o Cloud Build, sem Docker local,
ZIP manual ou comandos Git. O `.env` e o banco local não são enviados.

```powershell
# Somente visualizar; não publica nem gera custos de build:
.\deploy.ps1 -Plan

# Publicar quando o banco e o faturamento estiverem disponíveis:
.\deploy.ps1
```

O script constrói uma imagem, atualiza o job `gbeachfood-migrate`, executa as
migrations e só então atualiza o serviço com a mesma imagem e publica o Hosting.
O acesso ao Firebase é verificado antes do build. O perfil econômico de processamento
e escala descrito abaixo é reaplicado ao serviço e ao job. Variáveis, segredos,
conexão SQL e permissões existentes são preservados. O banco é configurado
separadamente. Qualquer falha interrompe os passos seguintes, sem
reverter migrations já concluídas.

Em **11/11/2026**, após a configuração econômica, o responsável solicitou colocar
o aplicativo no ar. O código atual foi publicado, as migrations foram aplicadas
no PostgreSQL novo e o administrador foi criado. O endereço público é
**https://gbeachfood.web.app**. A infraestrutura gera cobrança; confira o estado
real dos recursos e as pendências abaixo antes de novas alterações.

Para publicar somente a configuração do Hosting, depois de validar o backend:

```powershell
.\deploy.ps1 -HostingOnly
```

Esse comando pode reativar um site desativado e não executa migrations nem liga o
banco. Deve ser usado somente quando a publicação for solicitada e o backend
estiver pronto.

### Pausa da hospedagem e retomada

O registro histórico de 26/10/2026 indicava Hosting desativado, Cloud SQL parado
com disco de 250 GB e acesso público do Cloud Run removido. A criação de uma
instância menor estava bloqueada pelo faturamento. Esse registro **não comprova
o estado atual da nuvem**.

Posteriormente, o responsável informou que os dados eram apenas de teste,
dispensou backup e pediu instruções para excluir o banco. A consulta de 11/11/2026,
antes da configuração econômica, retornou nenhuma instância Cloud SQL no projeto.
O banco econômico descrito abaixo é novo; não foi uma redução do disco antigo.

A solicitação inicial de 11/11/2026 autorizou configurar o cenário econômico e
seus alertas. Em seguida, uma nova solicitação autorizou a publicação pública,
as migrations e a preparação do administrador. Não houve importação dos dados
locais. O pagamento de uma fatura, por si só, não solicita publicação. Este registro
é uma fotografia da configuração verificada, não uma auditoria de faturas nem
garantia do estado futuro dos recursos.

Em futuras retomadas, confira o banco disponível, os dados que devem
ser mantidos, a configuração aprovada, os segredos, a conexão do serviço e do job
`gbeachfood-migrate` e as permissões de acesso. Só então execute migrations e
publique. O `deploy.ps1` aplica o perfil econômico de escala e preserva IAM; sozinho ele não recria recursos nem
restaura uma permissão pública que tenha sido removida.

### Perfil econômico para fins de semana

Cenário escolhido pelo responsável em **11/11/2026**: pico previsto de cerca de
50 pessoas simultâneas, fins de semana e feriados das 9h às 17h, com uso diário e
maior movimento nas férias escolares. A capacidade precisa ser validada com carga
representativa de pedidos, recargas e relatórios antes da operação real.

| Recurso | Configuração do cenário |
|---|---|
| Região | `southamerica-east1` (São Paulo) |
| Cloud Run | 1 vCPU, 512 MiB, concorrência 8, execução gen2 |
| Cobrança e escala do serviço | Por requisição (`--cpu-throttling`), escala automática, mínimo 0 e máximo 2 no serviço e na revisão |
| Job de migrations | 1 vCPU, 512 MiB, 1 tarefa, paralelismo 1, sem repetição automática, timeout de 300 segundos |
| Cloud SQL | PostgreSQL 17, Enterprise, `db-g1-small` (CPU compartilhada e 1,7 GiB de RAM), uma zona, sem réplica |
| Disco SQL | SSD inicial de 10 GiB; crescimento automático limitado a 20 GiB |
| Backups SQL | Diários, retenção de 7 backups, recuperação para um ponto no tempo com 3 dias de logs |
| Acesso ao banco | Conector Cloud SQL, conexões criptografadas, sem redes externas autorizadas |

O `deploy.ps1` aplica apenas a configuração de processamento do serviço e do job,
além das etapas usuais de publicação. Ele não cria nem redimensiona o Cloud SQL.
`-Plan` mostra os parâmetros sem executar comandos externos; `-HostingOnly` não
altera o perfil de processamento.

Não há desligamento agendado. O Cloud Run pode reduzir a zero quando ocioso e
iniciar novamente no próximo acesso; o primeiro acesso pode demorar mais. O banco
fica disponível continuamente, inclusive para confirmações de pagamento fora do
horário do parque. Feriados e férias não dependem de um agendamento de ativação.

A previsão inicial é **R$ 280–420/mês** para operação em fins de semana, usando
US$ 1 = R$ 5,50 apenas como conversão ilustrativa. O processamento do banco custa
cerca de US$ 38,33/mês (730 horas); disco, backups, Cloud Run, tráfego e serviços
auxiliares são adicionais. Férias e aumento de uso exigem nova previsão. Valores
não incluem tributos, domínio, serviço de e-mail pago ou taxas Asaas.

Essa faixa não é um teto de cobrança. Os limites de instâncias e de disco não
limitam todos os custos, e o banco pode parar de aceitar gravações se o disco
atingir o limite. Monitorar espaço livre, conexões, memória, tráfego e faturamento.
As máquinas SQL compartilhadas não têm SLA. Os alertas da conta são configurados
separadamente e não são criados pelo deploy. O responsável escolheu **alertas sem
desligamento automático**; não foi criado um limite de gasto que bloqueie o app.

Estado verificado em **11/11/2026**, após a configuração:

- Faturamento habilitado. Instância SQL `gbeachfood` em estado `RUNNABLE`, com
  o perfil da tabela, proteção contra exclusão e backups às 06h UTC (03h em
  São Paulo). Banco `gbeachfood` e usuário `gbeachfood_app` criados. As migrations
  foram aplicadas pelo job `gbeachfood-migrate`; não houve importação ou restauração.
- Serviço `gbeachfood` e job `gbeachfood-migrate` configurados com os limites
  acima. Ambos mantêm a mesma conexão SQL e referência de senha no Secret Manager;
  as referências e a permissão `Cloud SQL Client` foram verificadas sem exibir
  credenciais. Migrations, criação do administrador e login confirmaram a conexão
  efetiva do Django com o banco.
- Firebase Hosting publicado e Cloud Run com acesso público habilitado por
  `--no-invoker-iam-check`. O login e as permissões continuam sendo verificados
  pelo Django. O deploy preserva essa configuração; não a habilita por conta própria.
- Imagem publicada: `app:deploy-20261111-173344-244`, no repositório
  `southamerica-east1-docker.pkg.dev/gbeachfood/gbeachfood`.
  Revisão do serviço: `gbeachfood-00015-pn6`. Build e job de migrations concluíram
  com sucesso antes da atualização do serviço.
- Administrador `admin` criado pelo job existente `gbeachfood-create-admin`, usando
  a imagem da publicação inicial e a senha previamente guardada no Secret Manager. O job usa 1 CPU,
  512 MiB, uma tarefa, nenhuma repetição automática e timeout de 300 segundos.
  Não há agendamento de execução desse job.
- Orçamento mensal do projeto: **R$ 420**, com alertas em R$ 210, R$ 336 e R$ 420,
  além de alerta quando a previsão mensal atingir R$ 420. Esse orçamento substitui
  o antigo aviso de R$ 25 do mesmo projeto; os de outros projetos foram preservados.
- Orçamento mensal específico de Cloud Run: **R$ 100**, com alertas em R$ 50,
  R$ 80 e R$ 100, além de previsão mensal de R$ 100. Esse consumo também integra o
  orçamento total de R$ 420; os valores não devem ser somados.
- Ambos avisam os destinatários padrão do faturamento, consideram consumo antes
  dos créditos e não acionam Pub/Sub ou desligamento. A entrega de notificações
  não foi testada por envio real. Alertas podem atrasar e não impedem excedentes.

Validação da publicação:

- Suíte Django isolada: 138 testes, com 6 testes de concorrência específicos de
  PostgreSQL pulados no SQLite; verificação de migrations sem alterações pendentes.
  Testes JavaScript de login, recarga e PWA e o teste simulado do deploy aprovados.
- Pelo endereço público: login de `admin`, painel administrativo, Django Admin,
  cookie seguro `__session`, rejeição de POST sem CSRF, arquivos estáticos,
  manifest, service worker e logout verificados.
- Na publicação inicial, uma rodada de 50 consultas paralelas de leitura a `/api/profile/` retornou
  50 respostas HTTP 200: mediana de 0,91 s, percentil 95 de 3,56 s e máximo de
  5,46 s. Essa checagem pontual não substitui teste sustentado de pedidos e recargas
  concorrentes, nem garante a capacidade em férias.
- Webhook sem token rejeitado com HTTP 401. Um evento de verificação não financeiro,
  ignorado pelo código, retornou HTTP 200 com o token correto. Nenhum pedido,
  cliente, crédito, cobrança ou e-mail foi criado como teste na nuvem.

Após a publicação inicial, o responsável informou que a conta Asaas configurada
não é a correta e adiou essa conexão. **Novas recargas online estão desativadas**:
`ASAAS_PAYMENTS_ENABLED=False`, e a referência `ASAAS_API_KEY` foi retirada do
serviço Cloud Run, preservando o segredo armazenado. O app orienta o cliente a
recarregar no caixa; a API recusa novas cobranças e não oferece links de recargas
pendentes durante a pausa. Registros de recargas e consultas de status são preservados.

O webhook autenticado continua processando confirmações de recargas já existentes,
inclusive estornos e contestações. A configuração anterior do webhook na conta
Asaas não foi apagada: URL `https://gbeachfood.web.app/api/asaas/webhook/`, com os
oito eventos tratados pelo aplicativo. Cobranças sem uma recarga correspondente
no banco são ignoradas. Nenhuma cobrança real foi gerada na validação. Os testes
simulados confirmam o bloqueio de PIX/crédito e reenvios sem chamadas ao provedor,
a preservação de pendências, do webhook e das recargas presenciais.

Em **13/11/2026**, após o responsável salvar as versões `2` dos segredos e desativar
as versões `1`, o deploy parou porque o Cloud Run ainda referenciava o token antigo.
As migrations dessa publicação já haviam concluído com sucesso. Com autorização
explícita, o serviço foi atualizado para as duas versões `2`, aproveitando a imagem
já construída. A revisão `gbeachfood-00019-ns6` ficou pronta e recebeu 100% do tráfego,
com recargas online ainda pausadas. Não houve novo build, nova execução de migrations
ou publicação do Hosting nessa correção; o endereço existente do Hosting respondeu
normalmente. As verificações e limitações estão detalhadas na seção de pagamentos.

Pendências: validar o fluxo completo de pagamento da conta Asaas antes de habilitar
recargas online; configurar o envio de e-mail para recuperação de senha (não havia
credenciais SMTP no serviço, no Secret Manager ou no ambiente local), cadastrar
produtos e funcionários conforme a operação e validar fluxos de pagamento e carga
representativos antes do uso operacional amplo. A senha do administrador foi
preservada; não depender de recuperação por e-mail enquanto SMTP estiver pendente.

Referências: [preços Cloud SQL](https://cloud.google.com/sql/pricing),
[preços Cloud Run](https://cloud.google.com/run/pricing),
[limites de gasto](https://docs.cloud.google.com/billing/docs/how-to/budgets-spend-caps).

### Sessão e arquivos estáticos

A produção usa o cookie `__session`, único encaminhado pelo Firebase Hosting, e `CSRF_USE_SESSIONS=True`. O token CSRF é
fornecido no HTML para chamadas JavaScript e a proteção permanece ativa.
Se o nome do cookie tiver mudado em um deploy anterior, será necessário novo login.
O WhiteNoise serve arquivos estáticos. A PWA guarda somente recursos em `/static/`,
sem armazenar páginas autenticadas ou respostas de APIs.
Configure `ALLOWED_HOSTS` com `gbeachfood.web.app`, `gbeachfood.firebaseapp.com`
e o host do serviço Cloud Run. Se houver
origens HTTPS adicionais autorizadas, ajuste `CSRF_TRUSTED_ORIGINS`.
Atualize a URL do webhook Asaas ao mudar o endereço público do app.

### Validação sem publicar

```powershell
python -B manage.py test --settings=gfood.test_settings
node tests/login_recovery.test.cjs
node tests/service_worker.test.cjs
node tests/credit_recharge.test.cjs
powershell -NoProfile -ExecutionPolicy Bypass -File tests/deploy_smoke.ps1
```

O teste do deploy substitui a CLI por funções locais e não chama a nuvem.
Valida a ordem das etapas, a mesma imagem, a interrupção em falhas e a restauração
da pasta de trabalho. Os testes de sessão validam login, logout e CSRF por HTTPS com o filtro de cookies
do Firebase Hosting.

### Arquivos de publicação

- `firebase.json`, `.firebaserc` e `firebase-public/.gitkeep`: configuram o Hosting
  e o encaminhamento para o Cloud Run; os estáticos são servidos pelo WhiteNoise.
- `Dockerfile`: instala dependências, coleta estáticos e inicia Gunicorn na porta
  `PORT`. Não executa migrations ao iniciar o servidor.
- `.dockerignore` e `.gcloudignore`: enviam apenas código e arquivos de build,
  excluindo credenciais, ambiente virtual e dados locais.
- `gfood/production.py`: exige PostgreSQL, chave secreta e hosts; configura HTTPS
  atrás do proxy Cloud Run. Localmente, o app usa `gfood.settings`.

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
| `ASAAS_PAYMENTS_ENABLED` | `False` por padrão; `True` exige chave, token de webhook distinto e URL oficial configurados |
| `ASAAS_BASE_URL` | URL sandbox ou produção correspondente à chave Asaas |
| `ASAAS_WEBHOOK_TOKEN` | Token do webhook no Secret Manager; o mesmo cadastrado no Asaas |

Alternativa ao Cloud SQL: sem `INSTANCE_CONNECTION_NAME`, informe `DATABASE_URL`
de um PostgreSQL externo. A configuração de produção recusa SQLite.

### Validação local da preparação

A suíte isolada inclui testes da configuração de produção e do login atrás do
proxy HTTPS. Isso não substitui a validação de uma nova imagem Docker e do ambiente
de hospedagem antes de uma publicação. Verifique os resultados atuais; não use
relatos antigos de testes ou de ferramentas instaladas como garantia de prontidão.

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
[conexão com Cloud SQL](https://docs.cloud.google.com/sql/docs/postgres/connect-run),
[cookies no Firebase Hosting](https://firebase.google.com/docs/hosting/manage-cache#using_cookies).

---

## 💳 Integração Asaas (PIX e cartão de crédito)

O sistema utiliza a [API do Asaas](https://docs.asaas.com) para processar recargas via PIX e cartão de crédito à vista.

### Como funciona

1. O cliente solicita uma recarga no app
2. O sistema cria uma cobrança PIX ou CREDIT_CARD no Asaas
3. O app mostra o QR Code PIX ou um link para pagar com cartão na página do Asaas
4. Após o pagamento, o Asaas envia um **webhook** confirmando
5. O sistema **credita o saldo** automaticamente no cartão do cliente

### Configuração

- **Pausa das recargas online**: `ASAAS_PAYMENTS_ENABLED=False` (padrão). O cliente
  recebe orientação para recarregar no caixa. A API bloqueia novas cobranças antes
  de chamar o Asaas e não expõe links pendentes; saldo, pedidos, recargas presenciais,
  status e webhook autenticado continuam funcionando.
- **Ativação**: somente após conectar e validar a conta correta, configurar a chave,
  o ambiente e o webhook correspondentes e definir `ASAAS_PAYMENTS_ENABLED=True`.
  Ao trocar de conta, conferir os clientes Asaas e as recargas pendentes existentes:
  identificadores e links da conta anterior não devem ser reutilizados na nova.
- **Sandbox** (testes): `ASAAS_BASE_URL=https://api-sandbox.asaas.com/v3`
- **Produção**: `ASAAS_BASE_URL=https://api.asaas.com/v3`

A API de criação, a lista de faturas pendentes e a tela do cliente só oferecem
recargas online com chave e token de webhook preenchidos, diferentes entre si,
e uma das duas URLs oficiais acima. Essa verificação é local: não comprova que
a chave esteja ativa nem que o webhook tenha sido cadastrado na conta correta.
As chamadas autenticadas ao Asaas não seguem redirecionamentos, para evitar
encaminhar a chave a outro destino. A pausa de novas cobranças não interrompe
o webhook autenticado nem o processamento das recargas já registradas.

A `ASAAS_API_KEY` precisa ser válida e pertencer ao mesmo ambiente da URL.
HTTP 401 (`invalid_access_token`) indica chave recusada, não CPF inválido.
Confira se a chave foi copiada integralmente e continua ativa no painel do Asaas;
substitua-a no `.env` local e reinicie o servidor após a alteração. Em produção,
a chave é gerenciada no Secret Manager. Não publique a chave em logs ou no Git.
O app diferencia falhas de configuração, conexão e cadastro, sem expor respostas
sensíveis do provedor. Um timeout pode deixar o resultado da solicitação incerto;
confira o painel antes de repetir a criação.

### Conectar a conta de produção sem expor a chave

O responsável confirmou em **13/11/2026** que criou uma chave de produção da conta
correta e salvou a chave e o token como versões `2` no Secret Manager. O serviço
`gbeachfood` usa `ASAAS_API_KEY=gbeachfood-asaas-api-key:2` e
`ASAAS_WEBHOOK_TOKEN=gbeachfood-asaas-webhook-token:2`, com
`ASAAS_BASE_URL=https://api.asaas.com/v3` e `ASAAS_PAYMENTS_ENABLED=False`.
As versões `1` estão desativadas. O job `gbeachfood-migrate` não referencia os
segredos Asaas e não precisou de alteração.

Verificações realizadas sem criar cobranças nem movimentar saldo:

- Login pelo Firebase Hosting: HTTP 200.
- POST ao webhook sem token: HTTP 401.
- POST com o token da versão `2` e um evento de verificação ignorado pelo app: HTTP 200.
- Consulta autenticada de webhooks no Asaas de produção: HTTP 200, com um webhook
  para a URL do app, ativo, fila não interrompida, API v3, envio sequencial e todos
  os oito eventos necessários. A consulta não retornou o token cadastrado no Asaas;
  não foi possível compará-lo com o segredo do servidor por essa resposta.

Esses resultados confirmam acesso à API e autenticação do endpoint, mas **não
substituem a validação de uma entrega do Asaas e do fluxo completo de pagamento**.
As recargas online continuam pausadas. Valores secretos foram usados apenas em
memória e não foram impressos nem incluídos nos arquivos do projeto.

Procedimento para configurar ou substituir os segredos:

1. Abra o [Secret Manager do projeto](https://console.cloud.google.com/security/secret-manager?project=gbeachfood).
   Em `gbeachfood-asaas-api-key`, escolha **Adicionar nova versão** e cole a nova
   chave diretamente no campo de valor secreto. Preserve todos os caracteres,
   inclusive `$`, e anote apenas o número da versão. Não cole a chave no chat,
   terminal, JavaScript, HTML ou arquivos versionados. Não precisa salvar a chave
   de produção no `.env` local para configurar a hospedagem.
2. No Asaas de **produção**, abra **Menu do usuário > Integrações > Webhooks >
   Criar webhook**. Preencha os campos da seção abaixo. Use **Gerar token** e salve
   esse valor como nova versão de `gbeachfood-asaas-webhook-token` no Secret Manager.
   Esse token deve ter entre 32 e 255 caracteres, sem espaços, e ser diferente da
   chave de API. Deixe o novo webhook desativado durante a preparação do servidor.
3. Antes da troca, confira se há clientes vinculados, faturas pendentes ou pagamentos
   da conta anterior. Não apague históricos nem reutilize seus links na nova conta.
   A troca do token também afeta as entregas do webhook antigo; pendências exigem
   reconciliação e planejamento da transição antes de substituir a configuração.
4. Na publicação autorizada, configure o serviço `gbeachfood` do Cloud Run,
   região `southamerica-east1`, com as referências abaixo. Escolha as **versões
   numéricas recém-salvas**, e não `latest`. Salvar uma versão no Secret Manager
   não atualiza automaticamente a revisão que referencia outra versão.

   | Variável do serviço | Configuração |
   | --- | --- |
   | `ASAAS_API_KEY` | Referência ao segredo `gbeachfood-asaas-api-key`, na nova versão |
   | `ASAAS_WEBHOOK_TOKEN` | Referência ao segredo `gbeachfood-asaas-webhook-token`, na nova versão |
   | `ASAAS_BASE_URL` | `https://api.asaas.com/v3` |
   | `ASAAS_PAYMENTS_ENABLED` | Manter `False` durante a configuração |

   A conta de serviço do app precisa acessar esses segredos. Preserve as demais
   variáveis, referências, permissões e limites de escala. O `deploy.ps1` publica
   o código, mas não cadastra a nova chave nem troca as referências dos segredos.
5. Com o servidor atualizado e o token correspondente, ative o novo webhook e
   confira suas entregas em **Logs de Webhooks**. O endpoint deve responder
   HTTP 200 a eventos autenticados válidos; token incorreto retorna 401 e ausência
   de token configurado retorna 503. Abrir a URL no navegador faz GET e retorna
   405, pois a integração usa POST. A URL deve ser HTTPS e responder diretamente,
   sem redirecionamento.
6. Valide os fluxos PIX, crédito, reenvio e revisão em um ambiente Sandbox separado,
   com chave, token e banco próprios. O Asaas não alcança `localhost`; o ambiente
   de testes também precisa de uma URL HTTPS acessível para receber notificações.
   Não aponte o Sandbox para o banco de produção. Só habilite
   `ASAAS_PAYMENTS_ENABLED=True` em produção depois de validar a configuração da
   conta correta. Uma verificação com cobrança real exige solicitação específica.

A chave de API é usada apenas pelo Django nas chamadas ao Asaas. O navegador recebe
o QR Code PIX ou o link de pagamento e consulta o status da própria recarga.
A URL pública do webhook não contém segredos: o servidor autentica cada POST pelo
cabeçalho `asaas-access-token`. Retornar da página de pagamento não confirma saldo.

Referências: [autenticação Asaas](https://docs.asaas.com/docs/authentication-2),
[configuração de webhooks](https://central.ajuda.asaas.com/hc/pt-br/articles/55669339031835-Quais-s%C3%A3o-as-op%C3%A7%C3%B5es-de-configura%C3%A7%C3%A3o-de-um-Webhook-no-Asaas),
[versões de segredos](https://docs.cloud.google.com/secret-manager/docs/add-secret-version),
[segredos no Cloud Run](https://docs.cloud.google.com/run/docs/configuring/services/secrets).

### Deploy falha porque uma versão de segredo está desativada

O `deploy.ps1` preserva as referências de segredos já configuradas no Cloud Run.
Criar uma nova versão no Secret Manager não muda essas referências. Se a versão
antiga for desativada antes da troca, o serviço pode falhar com
`SecretsAccessCheckFailed` ou `Secret Version [...] is in DISABLED state`.

Confira quais etapas já terminaram antes de repetir o deploy. Na correção de
13/11/2026, build e migrations já tinham concluído, e bastou atualizar o serviço
com as versões habilitadas. O comando aplicado foi:

```powershell
gcloud.cmd run services update gbeachfood --project=gbeachfood --region=southamerica-east1 --update-secrets="ASAAS_API_KEY=gbeachfood-asaas-api-key:2,ASAAS_WEBHOOK_TOKEN=gbeachfood-asaas-webhook-token:2" --update-env-vars="ASAAS_BASE_URL=https://api.asaas.com/v3,ASAAS_PAYMENTS_ENABLED=False"
```

Esse comando altera produção e exige solicitação do responsável. Ele preserva as
outras variáveis, referências de segredos e limites de escala. Em futuras rotações,
use os números das versões corretas e habilitadas; não reative uma credencial antiga
apenas para contornar o erro. Valide a nova revisão e os consumidores antes de
desativar a versão anterior. O token também precisa corresponder ao do webhook Asaas.

### Webhook

Configure a URL do webhook no painel do Asaas:
```
https://gbeachfood.web.app/api/asaas/webhook/
```

| Campo no Asaas | Valor |
| --- | --- |
| Nome | `GBeachFood - Producao` |
| URL | `https://gbeachfood.web.app/api/asaas/webhook/` (com a barra final) |
| E-mail | E-mail do responsável para alertas de falha |
| Versão da API | `3` |
| Token de autenticação | Token próprio gerado no painel; mesmo valor de `ASAAS_WEBHOOK_TOKEN` no servidor |
| Tipo de envio | Sequencial (`SEQUENTIALLY`) |
| Ativar webhook | Após configurar o token correspondente no servidor |
| Fila de sincronização | Ativa, sem interrupção, quando iniciar a operação |

Eventos que devem ser habilitados:
- `PAYMENT_CONFIRMED`
- `PAYMENT_RECEIVED`
- `PAYMENT_REFUNDED`
- `PAYMENT_PARTIALLY_REFUNDED`
- `PAYMENT_REFUND_IN_PROGRESS`
- `PAYMENT_CHARGEBACK_REQUESTED`
- `PAYMENT_CHARGEBACK_DISPUTE`
- `PAYMENT_AWAITING_CHARGEBACK_REVERSAL`

### Crédito à vista

O cliente escolhe cartão de crédito, informa o valor (mínimo de R$ 5,00 no app)
e abre a fatura `invoiceUrl` do Asaas. A cobrança é única, sem parcelamento;
o app não recebe nem armazena número do cartão, validade ou CVV. Cobranças
pendentes podem ser retomadas na tela de recarga sem gerar uma nova cobrança.

Os pagamentos pertencem à conta Asaas da `ASAAS_API_KEY` configurada no servidor.
Não há split nem transferência para outra conta. Confira se essa é a conta de
recebimento desejada e se está habilitada para cartão de crédito. Taxas, análise
de risco e prazo de disponibilização dependem do contrato e da conta no Asaas.

`PAYMENT_CONFIRMED` pode liberar o saldo no parque antes de o dinheiro estar
disponível para saque no Asaas; `PAYMENT_RECEIVED` indica disponibilidade na
conta. Ambos creditam uma única vez, pelo valor bruto da recarga, sem descontar
as tarifas do saldo do cliente. Navegar para a fatura, voltar ao app, autorizar o
cartão ou passar pela análise de risco não libera saldo.

Estorno (inclusive parcial ou em processamento) e contestação colocam a recarga
em revisão e bloqueiam o cartão virtual do mesmo titular. Não há débito automático
nem desbloqueio automático: o atendimento precisa reconciliar os valores, pois o
saldo pode já ter sido utilizado. Confirmações posteriores não creditam novamente
uma recarga em revisão. O Django Admin lista essas recargas e o evento recebido,
sem permitir alterar seus dados financeiros diretamente.

Antes de usar em produção, habilite os eventos acima no webhook da conta Asaas e
valide no sandbox a fatura, confirmação e revisão. Os testes automatizados usam
respostas simuladas e não substituem essa validação da conta. O estado da infraestrutura
está registrado na seção de hospedagem; as recargas online seguem pausadas até a conexão
e validação da conta correta. Nenhuma cobrança real faz parte dos testes automatizados.

Referências: [pagamento por cartão](https://docs.asaas.com/docs/payments-via-credit-card),
[eventos de cobrança](https://docs.asaas.com/docs/webhook-para-cobrancas).

---

## SKU e NCM dos produtos

Em **Administrador → Produtos**, cada produto recebe automaticamente um SKU
único ao ser criado, no formato `GBF-` seguido de 32 caracteres hexadecimais.
O código é somente leitura e permanece igual nas edições. Ele também é gerado
em criações pelo ORM e por `bulk_create`; não é um número sequencial.

O **NCM** é opcional e pode ser preenchido ou removido no formulário. Quando
informado, deve conter exatamente oito dígitos, sem pontuação; zeros à esquerda
são preservados. O sistema valida o formato, sem consultar a tabela fiscal nem
escolher a classificação do produto. Isso não implementa emissão de nota fiscal.

A lista administrativa exibe SKU e NCM e permite buscar pelos dois códigos ou
pelo nome. As APIs de listagem e criação retornam `sku` e `ncm`; na atualização,
omitir `ncm` mantém o valor atual e enviar vazio limpa o campo. Enviar `sku` nas
APIs de criação ou atualização é recusado, pois o servidor gera esse código.
Somente o perfil `admin` pode cadastrar ou alterar produtos.

As migrações de `products.0005` a `products.0007` preenchem um SKU diferente em
cada produto existente e deixam o NCM vazio, preservando os demais dados. Aplique as
migrations no banco do ambiente desejado antes de usar a versão atualizada.
O item separado **Cartão físico** mantém seu cadastro de preço atual.

## Cartão temporário com etiqueta

Em **Administrador → Produtos**, o item **Cartão físico** fica fixado no topo,
mesmo ao buscar ou filtrar o cardápio. O administrador pode alterar seu preço,
mas não excluir o item. O preço inicial é R$ 2,00, salvo no banco pela migração
`products.0004_physical_card_price`; são aceitos valores positivos com até duas
casas decimais. O item é exclusivo do caixa e não aparece no cardápio de alimentos.

No caixa, preencha nome, CPF e telefone (os dois últimos são opcionais), valor
inicial e forma de pagamento. O UUID é gerado automaticamente; não é preciso
escanear nem informar um QR existente. Marque **Incluir cartão físico**, ao lado do preço atual,
se o cliente comprar o cartão em branco para colar a etiqueta.

O cartão é cobrado à parte: por exemplo, com preço de R$ 2,00, R$ 50,00 de saldo e um cartão físico totalizam
R$ 52,00 recebidos, com R$ 50,00 disponíveis para consumo. A venda fica registrada
como **Venda de cartão físico**, separada do depósito, com método e operador.
Os relatórios do caixa e do administrador exibem a venda separadamente; o total
recebido por método no caixa inclui depósitos e cartões físicos pagos por meios externos. Cada componente
é um lançamento, mesmo quando ambos são recebidos em um único pagamento.

Após confirmar o recebimento, clique em **Criar e imprimir cartão**. A tela da
etiqueta permite ajustar largura (40 a 100 mm) e altura (30 a 100 mm), inicialmente
60 × 40 mm. Essas medidas ficam salvas neste navegador. Clique em **Imprimir
etiqueta** e escolha a impressora instalada no computador, ou **Salvar como PDF**.
No driver, use o tamanho de papel correspondente, escala 100%, margens zero e
desative cabeçalhos e rodapés. A impressão física deve ser calibrada quando o
modelo da impressora e o papel forem escolhidos.

A etiqueta contém a marca, o QR Code, o número e o UUID do cartão; não imprime
CPF, telefone nem saldo. A API só permite emissão e impressão para caixa/admin.
Se o navegador bloquear a nova janela ou a impressão falhar, use **Imprimir /
reimprimir etiqueta** no resultado. Também há reimpressão em **Cartões**, após
buscar por CPF, e em **Saldo**, após consultar o QR. Reimprimir não movimenta saldo
nem registra outra venda. Cartões cancelados não podem ser reimpressos.

Se o cliente levou somente a etiqueta e quiser comprar o cartão físico depois,
abra **Saldo**, consulte o QR da etiqueta e use **Comprar cartão físico**, com o preço atual exibido.
Escolha a forma de pagamento nessa seção. Para PIX, dinheiro, crédito ou débito,
registre após receber o preço do cartão à parte. A opção **Usar saldo** desconta esse preço
da própria etiqueta e atualiza o saldo exibido. É necessário ter saldo suficiente para o preço atual;
se faltar saldo, nenhuma venda ou débito é registrado. O QR permanece o mesmo.
A venda entra nos relatórios como **Venda de cartão físico** com o método escolhido.
Quando paga com saldo, aparece no total pago via saldo e na venda de cartões,
mas não como uma nova entrada de dinheiro no caixa. O caixa também mostra a
parcela das vendas de cartões paga com saldo. Basta colar a etiqueta no cartão em branco.
A consulta mostra quantas compras de cartão físico já foram registradas. É possível
comprar várias unidades para a mesma etiqueta, inclusive para substituir um cartão
perdido. Cada nova compra registra o preço vigente nos relatórios. O saldo só é descontado
quando a forma de pagamento escolhida é **Usar saldo**; o QR permanece o mesmo.
A reimpressão da etiqueta continua gratuita e não registra a venda do cartão.

Os dois formulários usam o mesmo preço do banco, inclusive nos totais e no desconto
do saldo. O caixa atualiza o preço ao abrir a página ou voltar à aba do navegador.
Se o administrador alterar o preço entre a consulta e uma nova compra, a API recusa
a tentativa sem gerar cobrança, atualiza o valor na tela e pede nova confirmação.
Vendas concluídas e reenvios de tentativas já registradas mantêm o preço original.
O campo `preco_cartao` enviado pelo navegador apenas confirma o valor exibido;
o servidor define o preço cobrado e recusa valores divergentes.

Cada compra tem um `request_id` único. Repetir a mesma solicitação, com a mesma
etiqueta, método e operador, retorna a venda já registrada; uma nova solicitação
registra outra unidade. Venda e desconto do saldo são gravados na mesma transação;
reenvios não descontam novamente, mesmo se o primeiro pagamento tiver zerado o saldo.
Se a conexão falhar, use **Retomar compra** antes de cobrar
outra unidade. A tentativa pendente fica salva na sessão da aba, por operador e
etiqueta, e pode ser retomada após recarregar a página e consultar o mesmo QR.

Se a conexão cair durante a criação, use **Retomar criação e imprimir cartão**.
O mesmo identificador recupera a emissão já registrada, sem duplicar a recarga
ou a venda. Os dados pendentes ficam na sessão da aba até a confirmação; não
inicie outra emissão para resolver uma falha de impressão.

As migrações `0008` e `0009` preservam a continuidade de bancos que receberam a
implementação anterior: removem a estrutura de lotes impressos antecipadamente,
mantêm cartões, UUIDs, saldos e transações, e adicionam o registro de emissão.
Execute `python manage.py migrate` ao atualizar outro ambiente.

## 🔐 Recargas e consistência do saldo

- Recargas presenciais exigem perfil `caixa` ou `admin`. Clientes geram cobranças PIX ou crédito; o crédito ocorre após confirmação autenticada.
- Configure `ASAAS_WEBHOOK_TOKEN` no ambiente e use o mesmo valor como token de autenticação do webhook no painel Asaas. Esse token é diferente da chave da API. Sem configuração, o endpoint retorna HTTP 503; sem token válido na requisição, HTTP 401.
- O webhook aceita POST e valida cobrança, valor, forma de pagamento registrada e status confirmado/recebido. A recarga é creditada uma única vez, mesmo com reenvios ou os dois eventos `PAYMENT_CONFIRMED` e `PAYMENT_RECEIVED`.
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
DEFAULT_FROM_EMAIL=GBeachFood <sua-conta@gmail.com>
```

Ative a verificação em duas etapas na conta e gere uma **senha de app** nas [configurações do Google](https://support.google.com/accounts/answer/185833?hl=pt-BR). Informe-a somente no `.env` local ou nos segredos da hospedagem. A disponibilidade de senhas de app depende das políticas da conta. Não use a senha normal da conta. Reinicie a aplicação após configurar.

Para desenvolvimento sem envio real, defina explicitamente `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` e `DEBUG=True`. Console é rejeitado com `DEBUG=False`. TLS e SSL não podem ser habilitados ao mesmo tempo.

Se faltar configuração ou o SMTP falhar, a API retorna erro JSON (HTTP 503). Um código que não foi enviado é removido. Os testes usam mensagens em memória e SMTP simulado, sem enviar e-mails reais.

## 🧪 Validação das correções

```bash
python -B manage.py test --settings=gfood.test_settings
node tests/login_recovery.test.cjs
node tests/product_codes.test.cjs
```

A configuração de testes ignora `.env`, usa SQLite em memória, senhas de teste e e-mail em memória. Os testes da API Asaas simulam as chamadas externas. Os testes de concorrência que exigem PostgreSQL são ignorados no SQLite. Para executá-los, forneça `TEST_DATABASE_URL` de um ambiente PostgreSQL exclusivo de testes (com permissão de criar o banco de teste) ao executar a mesma suíte; não use credenciais de produção.

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
| POST | `/api/cards/physical/purchase/` | Registra uma unidade pelo preço definido pelo admin; recebe `qr_data`, `metodo`, `request_id` e confirmação `preco_cartao` (caixa/admin) |
| POST | `/api/cards/temp/create/` | Cria cartão e saldo inicial; recebe `request_id`, `incluir_cartao_fisico` booleano e confirmação `preco_cartao` (caixa/admin) |
| GET | `/cards/<id>/label/` | Tela de impressão/reimpressão da etiqueta, sem nova cobrança (caixa/admin) |
| POST | `/api/cards/client/add/` | Rota antiga desativada: retorna HTTP 410 sem alterar saldo |
| GET | `/api/cards/client/<id>/transactions/` | Transações de um cliente (admin) |
| GET | `/api/cards/my/transactions/` | Minhas transações (cliente) |
| GET | `/api/cards/search-cpf/?cpf=XXX` | Busca cartão por CPF |
| POST | `/api/cards/block/` | Bloqueia cartão |
| POST | `/api/cards/transfer/` | Transfere saldo |

### Asaas — PIX e crédito (`cards/`)
| Método | Endpoint | Descrição |
|---|---|---|
| POST | `/api/asaas/create-payment/` | Cria cobrança PIX ou crédito (`metodo`: `pix` ou `credito`) |
| POST | `/api/asaas/webhook/` | Recebe webhook do Asaas |
| GET | `/api/asaas/check-payment/<id>/` | Verifica status do pagamento |

### Produtos (`products/`)
| Método | Endpoint | Descrição |
|---|---|---|
| GET | `/api/products/` | Lista produtos disponíveis |
| GET | `/api/products/all/` | Lista todos (admin) |
| GET | `/api/products/physical-card/` | Consulta o preço do cartão físico (caixa/admin) |
| POST | `/api/products/physical-card/update/` | Atualiza o preço do cartão físico (admin); sem rota de exclusão |
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

O GBeachFood pode ser instalado como um app no celular:

1. Acesse o site pelo **navegador do celular**
2. Toque em **"Adicionar à tela inicial"** (ou "Instalar app")
3. O GBeachFood aparecerá como um app na sua tela inicial

---

## 📄 Licença

Este projeto foi desenvolvido por **Cauã Caetano** — [cauacaetanofb@gmail.com](mailto:cauacaetanofb@gmail.com)
