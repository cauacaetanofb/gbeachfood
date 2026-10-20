#Requires -Version 5.1
<#
Publica a pasta local no projeto gbeachfood.
Uso: .\deploy.ps1 | .\deploy.ps1 -HostingOnly | .\deploy.ps1 -Plan
Nao executa comandos Git. A imagem e construida pelo Cloud Build.
#>
[CmdletBinding()]
param(
    [ValidatePattern('^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$')]
    [string]$Version = ('deploy-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')),
    [switch]$HostingOnly,
    [switch]$Plan
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
    $requiredFiles = @('firebase.json', '.firebaserc')
    if (-not $HostingOnly) {
        $requiredFiles += @('Dockerfile', '.dockerignore', '.gcloudignore', 'manage.py')
    }
    foreach ($file in $requiredFiles) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) {
            throw "Arquivo obrigatorio ausente: $file"
        }
    }
    if (-not (Test-Path -LiteralPath 'firebase-public' -PathType Container)) {
        throw 'Pasta firebase-public ausente.'
    }

    # Preferir os launchers .cmd evita depender da politica de scripts do npx.ps1.
    $firebaseTool = 'npx.cmd'
    $cloudTool = 'gcloud.cmd'
    if (-not $Plan) {
        if (-not (Get-Command $firebaseTool -ErrorAction SilentlyContinue)) {
            throw 'Instale o Node.js LTS e reabra o VS Code para disponibilizar npx.cmd.'
        }
        if (-not $HostingOnly -and -not (Get-Command $cloudTool -ErrorAction SilentlyContinue)) {
            throw 'Instale a Google Cloud CLI e reabra o VS Code para disponibilizar gcloud.cmd.'
        }
        # Verificar o acesso ao Firebase antes de alterar o backend.
        Invoke-DeployCommand $firebaseTool @('--yes', 'firebase-tools', 'hosting:sites:list',
            "--project=$projectId", '--non-interactive')
    }

    if (-not $HostingOnly) {
        Write-Host "Imagem desta publicacao: $image"
        Invoke-DeployCommand $cloudTool @('builds', 'submit', '.', "--tag=$image",
            "--region=$region", '--default-buckets-behavior=regional-user-owned-bucket',
            "--project=$projectId", '--quiet')

        # O job usa a MESMA imagem que sera publicada, preservando conexao e segredos.
        Invoke-DeployCommand $cloudTool @('run', 'jobs', 'update', 'gbeachfood-migrate',
            "--image=$image", '--command=python', '--args=manage.py,migrate,--noinput',
            "--region=$region", "--project=$projectId", '--quiet')
        Invoke-DeployCommand $cloudTool @('run', 'jobs', 'execute', 'gbeachfood-migrate',
            "--region=$region", "--project=$projectId", '--wait', '--quiet')

        # Atualizar so a imagem preserva hosts, variaveis, segredos e permissoes existentes.
        Invoke-DeployCommand $cloudTool @('run', 'services', 'update', 'gbeachfood',
            "--image=$image", "--region=$region", "--project=$projectId", '--quiet')
    }

    Invoke-DeployCommand $firebaseTool @('--yes', 'firebase-tools', 'deploy', '--only', 'hosting',
        "--project=$projectId", '--non-interactive')
    if ($Plan) {
        Write-Host 'Plano exibido. Nenhum comando externo foi executado.'
    } else {
        Write-Host 'Publicacao concluida: https://gbeachfood.web.app'
    }
} finally {
    Pop-Location
}
