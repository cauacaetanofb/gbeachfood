#Requires -Version 5.1
# Teste isolado: as ferramentas de nuvem sao substituidas por funcoes locais.
$ErrorActionPreference = 'Stop'
$deployScript = Join-Path (Split-Path -Parent $PSScriptRoot) 'deploy.ps1'
$originalLocation = (Get-Location).Path
$global:deployCalls = [System.Collections.Generic.List[object]]::new()
$global:deployFailAt = 0

function global:gcloud.cmd {
    $global:deployCalls.Add(@{ Tool = 'gcloud'; Arguments = @($args) })
    $global:LASTEXITCODE = 0
    if ($global:deployCalls.Count -eq $global:deployFailAt) { $global:LASTEXITCODE = 17 }
}
function global:npx.cmd {
    $global:deployCalls.Add(@{ Tool = 'npx'; Arguments = @($args) })
    $global:LASTEXITCODE = 0
    if ($global:deployCalls.Count -eq $global:deployFailAt) { $global:LASTEXITCODE = 17 }
}
function Assert-DeployTest([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}
try {
    & $deployScript -Version 'test-local-only' -Plan
    Assert-DeployTest ($global:deployCalls.Count -eq 0) 'Plan executed a command.'

    & $deployScript -Version 'test-local-only'
    Assert-DeployTest ($global:deployCalls.Count -eq 6) 'Unexpected number of commands.'
    $sequence = @($global:deployCalls | ForEach-Object { $_.Arguments -join ' ' })
    Assert-DeployTest ($sequence[0] -match 'hosting:sites:list') 'Missing authentication preflight.'
    Assert-DeployTest ($sequence[1] -match '^builds submit') 'Build not first mutation.'
    Assert-DeployTest ($sequence[2] -match '^run jobs update') 'Job not updated.'
    Assert-DeployTest ($sequence[3] -match '^run jobs execute.*--wait') 'Migrations not awaited.'
    Assert-DeployTest ($sequence[4] -match '^run services update') 'Service not updated after migrations.'
    Assert-DeployTest ($sequence[5] -match 'deploy --only hosting') 'Hosting not last.'
    foreach ($i in @(1, 2, 4)) {
        Assert-DeployTest ($sequence[$i] -match 'app:test-local-only') 'Images differ between steps.'
    }
    Assert-DeployTest (-not ($sequence[4] -match 'set-env|set-secrets')) 'Service configuration overwritten.'

    foreach ($failAt in 1..6) {
        $global:deployCalls.Clear()
        $global:deployFailAt = $failAt
        $failed = $false
        try { & $deployScript -Version 'test-local-only' } catch { $failed = $true }
        Assert-DeployTest $failed "Failure $failAt was ignored."
        Assert-DeployTest ($global:deployCalls.Count -eq $failAt) "Commands continued after failure $failAt."
        Assert-DeployTest ((Get-Location).Path -eq $originalLocation) 'Working directory not restored.'
    }

    $global:deployCalls.Clear()
    $global:deployFailAt = 0
    & $deployScript -HostingOnly
    Assert-DeployTest ($global:deployCalls.Count -eq 2) 'Unexpected HostingOnly commands.'
    Assert-DeployTest (@($global:deployCalls | Where-Object { $_.Tool -eq 'gcloud' }).Count -eq 0) 'HostingOnly changed backend.'
    Write-Host 'OK: plan, image consistency, migration ordering, failure stops, HostingOnly and working directory.'
} finally {
    Remove-Item Function:\gcloud.cmd, Function:\npx.cmd
    Remove-Variable deployCalls, deployFailAt -Scope Global
    $global:LASTEXITCODE = 0
}
