param([ValidateSet('experiment','predict','test')][string]$Action='experiment')
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONIOENCODING='utf-8'
$pythonExe=Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) {
    $bundledPython=Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Reikalingas Python 3.12. Idiekite ji is python.org.' }
    } elseif (Test-Path -LiteralPath $bundledPython) {
        & $bundledPython -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Nepavyko sukurti Python aplinkos.' }
    } else { throw 'Reikalingas Python 3.12: https://www.python.org/downloads/' }
}
$ready=Join-Path $PSScriptRoot '.venv/air_quality_ready'
if (-not (Test-Path -LiteralPath $ready)) {
    & $pythonExe -m pip install -r requirements-lock.txt
    if ($LASTEXITCODE -ne 0) { throw 'Nepavyko idiegti biblioteku. Patikrinkite interneto rysi.' }
    Set-Content -LiteralPath $ready -Value 'requirements-lock.txt installed'
}
switch ($Action) {
    'experiment' { & $pythonExe run_experiment.py --config config.yaml }
    'test' { & $pythonExe -m unittest discover -s tests -v }
    'predict' {
        $inputCsv=(Read-Host 'Iveskite CSV failo kelia (Enter = pavyzdys)').Trim('"')
        if (-not $inputCsv) { $inputCsv='examples/unseen_format.csv' }
        $outputCsv='predictions/prediction_'+(Get-Date -Format 'yyyyMMdd_HHmmss')+'.csv'
        & $pythonExe predict.py --input $inputCsv --output $outputCsv
        if ($LASTEXITCODE -eq 0) { Write-Host "Rezultatas: $outputCsv" }
    }
}
if ($LASTEXITCODE -ne 0) { throw "Programa baigta su klaida: $LASTEXITCODE" }
