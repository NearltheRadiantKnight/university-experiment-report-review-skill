$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $Python) {
    [Console]::Error.WriteLine('{"error":"Python was not found","error_type":"runtime","hint":"Install Python 3.10 or use the Python bundled with your agent runtime."}')
    exit 1
}

& $Python.Source (Join-Path $ScriptDir "scripts\run_pipeline.py") @args
exit $LASTEXITCODE
