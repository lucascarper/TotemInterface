# Paliativo (Windows): roda o totem neste PC, acessível pela rede local (tablet da recepção),
# enquanto a hospedagem na nuvem não está disponível. Equivalente ao paliativo-rede-local.sh do Mac.
#
# Uso:  powershell -ExecutionPolicy Bypass -File scripts\paliativo-rede-local.ps1   (Ctrl+C para parar)
# Pré-requisito: a chave nova do SGG em backend\.env (SGG_API_KEY).
param(
    [string]$IP = "",
    [int]$ApiPort = 8010,
    [int]$WebPort = 8080
)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

# Node instalado via winget pode não estar no PATH desta janela ainda.
$env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" +
            [Environment]::GetEnvironmentVariable("Path", "Machine")

if (-not $IP) {
    $IP = (Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254*" -and $_.PrefixOrigin -ne "WellKnown" } |
        Select-Object -First 1).IPAddress
}

if (-not (Test-Path "backend\.env")) {
    Copy-Item ".env.example" "backend\.env"
    Write-Host "!! backend\.env criado a partir do exemplo. Coloque a chave do SGG (SGG_API_KEY) e rode de novo." -ForegroundColor Yellow
    exit 1
}

# Variáveis de ambiente têm prioridade sobre backend\.env.
$env:APP_ENV = "production"
$env:SGG_MODE = "http"
$env:AUTO_CREATE_SCHEMA = "true"
$env:CORS_ORIGINS = "http://${IP}:${WebPort}"
# Segredo de sessão novo a cada execução (só invalida o login do painel ao reiniciar).
$env:JWT_SECRET = -join ((1..32) | ForEach-Object { "{0:x2}" -f (Get-Random -Maximum 256) })

Write-Host "==> Gerando a tela do totem apontando para http://${IP}:${ApiPort}"
$env:VITE_API_BASE_URL = "http://${IP}:${ApiPort}"
Push-Location frontend
npm.cmd run build | Out-Null
if ($LASTEXITCODE -ne 0) { throw "Falha no build do frontend" }
Pop-Location

$api = Start-Process -PassThru -NoNewWindow -WorkingDirectory "backend" `
    -FilePath "backend\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$ApiPort"
$web = Start-Process -PassThru -NoNewWindow -WorkingDirectory "frontend" `
    -FilePath "npx.cmd" `
    -ArgumentList "vite", "preview", "--host", "0.0.0.0", "--port", "$WebPort", "--strictPort"

# Impede o PC de dormir enquanto o paliativo estiver no ar.
Add-Type -Namespace Win32 -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[Win32.Power]::SetThreadExecutionState(0x80000003) | Out-Null  # CONTINUOUS | SYSTEM | DISPLAY

Write-Host ""
Write-Host "==> Totem:  http://${IP}:${WebPort}/totem" -ForegroundColor Green
Write-Host "==> Painel: http://${IP}:${WebPort}/admin" -ForegroundColor Green
Write-Host "    (Ctrl+C para parar)"
try {
    while (-not $api.HasExited -and -not $web.HasExited) { Start-Sleep -Seconds 2 }
    Write-Host "!! Um dos serviços parou." -ForegroundColor Red
} finally {
    foreach ($p in $api, $web) {
        if ($p -and -not $p.HasExited) { & taskkill.exe /PID $p.Id /T /F | Out-Null }
    }
    [Win32.Power]::SetThreadExecutionState(0x80000000) | Out-Null
}
