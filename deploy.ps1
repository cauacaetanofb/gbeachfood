#Requires -Version 5.1
<#
Publica a pasta local no Cloud Run e Firebase Hosting do projeto gbeachfood.
Uso: .\deploy.ps1 | .\deploy.ps1 -Plan | .\deploy.ps1 -HostingOnly
Nao executa comandos Git. A imagem e construida pelo Cloud Build.
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$')]
    [string]$Version = ('deploy-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')),
    [switch]$Plan,
    [switch]$HostingOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$projectId = 'gbeachfood'
$region = 'southamerica-east1'
$image = "${region}-docker.pkg.dev/${projectId}/gbeachfood/app:${Version}"

function Invoke-DeployCommand {
    param([string]$Tool, [string[]]$Arguments)
    if ($Plan) {
        $display = ($Arguments | ForEach-Object { "'" + $_.Replace("'", "''") + "'" }) -join ' '
        Write-Host "$Tool $display"
        return
    }
    & $Tool @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Falha em $Tool (codigo $LASTEXITCODE). Deploy interrompido; veja o erro acima."
    }
}

Push-Location -LiteralPath $PSScriptRoot
try {
    foreach ($file in @('Dockerfile', '.dockerignore', '.gcloudignore', 'manage.py', 'firebase.json', '.firebaserc', 'firebase-public/.gitkeep')) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Arquivo obrigatorio ausente: $file"
        }
    }
    $cloudTool = 'gcloud.cmd'
    if (-not $Plan -and -not $HostingOnly -and -not (Get-Command $cloudTool -ErrorAction SilentlyContinue)) {
        throw 'Instale a Google Cloud CLI e reabra o VS Code para disponibilizar gcloud.cmd.'
    }

    $firebaseTool = 'npx.cmd'
    if (-not $Plan -and -not (Get-Command $firebaseTool -ErrorAction SilentlyContinue)) {
        throw 'Instale o Node.js LTS e reabra o VS Code para disponibilizar npx.cmd.'
    }
    # Validar acesso ao Hosting antes de iniciar um build pago.
    Invoke-DeployCommand $firebaseTool @('--yes', 'firebase-tools', 'hosting:sites:list',
        "--project=$projectId", '--non-interactive')

    if (-not $HostingOnly) {
        Write-Host "Imagem desta publicacao: $image"
        Invoke-DeployCommand $cloudTool @('builds', 'submit', '.', "--tag=$image",
            "--region=$region", '--default-buckets-behavior=regional-user-owned-bucket',
            "--project=$projectId", '--quiet')

        # O job usa a mesma imagem que sera publicada, preservando conexao e segredos.
        Invoke-DeployCommand $cloudTool @('run', 'jobs', 'update', 'gbeachfood-migrate',
            "--image=$image", '--command=python', '--args=manage.py,migrate,--noinput',
            "--region=$region", "--project=$projectId", '--quiet')
        Invoke-DeployCommand $cloudTool @('run', 'jobs', 'execute', 'gbeachfood-migrate',
            "--region=$region", "--project=$projectId", '--wait', '--quiet')

        # Atualizar so a imagem preserva hosts, variaveis, segredos e permissoes existentes.
        Invoke-DeployCommand $cloudTool @('run', 'services', 'update', 'gbeachfood',
            "--image=$image", "--region=$region", "--project=$projectId", '--quiet')
    }
    Invoke-DeployCommand $firebaseTool @('--yes', 'firebase-tools', 'deploy', '--only=hosting',
        "--project=$projectId", '--non-interactive')
    if ($Plan) {
        Write-Host 'Plano exibido. Nenhum comando externo foi executado.'
    } else {
        Write-Host 'Publicacao concluida: https://gbeachfood.web.app'
    }
} finally {
    Pop-Location
}
