param(
    [switch]$Lan,
    [switch]$HttpsProxy,
    [int]$Port = 8081
)

$ErrorActionPreference = 'Stop'
$dataDir = Join-Path $PSScriptRoot 'cloud_data'
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

function Get-OrCreateSecret([string]$Path) {
    if (Test-Path $Path) {
        return (Get-Content -Raw $Path).Trim()
    }
    $bytes = New-Object byte[] 32
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    $value = [Convert]::ToBase64String($bytes)
    [System.IO.File]::WriteAllText($Path, $value, [System.Text.Encoding]::ASCII)
    return $value
}

$env:MECAM_DATA_DIR = $dataDir
$env:MECAM_SECRET_KEY = Get-OrCreateSecret (Join-Path $dataDir '.session-secret')
$env:MECAM_STORAGE_KEY = Get-OrCreateSecret (Join-Path $dataDir '.media-secret')
$env:MECAM_SETUP_KEY = Get-OrCreateSecret (Join-Path $dataDir '.owner-setup-key')
$env:MECAM_COOKIE_SECURE = '0'
$env:PORT = [string]$Port
if ($HttpsProxy) {
    if ($Lan) { throw 'Use either -Lan or -HttpsProxy, not both.' }
    $env:MECAM_COOKIE_SECURE = '1'
    $env:MECAM_HOST = '127.0.0.1'
    Write-Host "ME_CAM HTTPS-proxy origin: http://127.0.0.1:$Port"
    Write-Host 'The origin is private to this computer; expose it only through your HTTPS tunnel.'
} elseif ($Lan) {
    $env:MECAM_HOST = '0.0.0.0'
    $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object {
            $_.IPAddress -match '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)'
        } |
        Select-Object -ExpandProperty IPAddress -Unique
    if (-not $addresses) { throw 'No private IPv4 LAN address was found.' }
    Write-Host 'ME_CAM standalone LAN dashboard'
    foreach ($address in $addresses) { Write-Host "  http://${address}:$Port" }
} else {
    $env:MECAM_HOST = '127.0.0.1'
    Write-Host "ME_CAM standalone dashboard: http://127.0.0.1:$Port"
}
Write-Host "Owner setup key: $($env:MECAM_SETUP_KEY)"
Write-Host 'Data and encryption keys are stored in ME_CAM-DEV/cloud_data. Keep this folder backed up.'
Write-Host 'Press Ctrl+C to stop the dashboard.'

Push-Location $PSScriptRoot
try {
    if ($HttpsProxy) {
        python -m waitress --listen="127.0.0.1:$Port" cloud_dashboard:app
    } else {
        python cloud_dashboard.py
    }
} finally {
    Pop-Location
}
