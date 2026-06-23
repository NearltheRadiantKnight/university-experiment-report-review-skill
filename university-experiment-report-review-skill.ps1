$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    $Python = Get-Command python3 -ErrorAction SilentlyContinue
}
if (-not $Python) {
    [Console]::Error.WriteLine('{"error":"Python was not found","error_type":"runtime","hint":"Install Python 3.10 or use the Python bundled with Codex."}')
    exit 1
}

& $Python.Source (Join-Path $ScriptDir "scripts\inspect_report.py") @args
exit $LASTEXITCODE
