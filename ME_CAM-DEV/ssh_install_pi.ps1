param(
    [Parameter(Mandatory = $true)]
    [string]$PiHost,
    [string]$DashboardUrl = 'https://me-cam.com',
    [string]$InstallerDir = '',
    [switch]$AllowInsecureLan
)

$ErrorActionPreference = 'Stop'
if (-not $InstallerDir) {
    $downloads = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
    $InstallerDir = Join-Path $downloads 'me_cam_installer'
}
if (-not (Test-Path $InstallerDir)) { throw "Installer folder not found: $InstallerDir" }
$DashboardUrl = $DashboardUrl.TrimEnd('/')
$dashboardUri = [uri]$DashboardUrl
if ($dashboardUri.Scheme -ne 'https') {
    if (-not $AllowInsecureLan -or $dashboardUri.Scheme -ne 'http') {
        throw 'Use HTTPS. For a trusted home LAN only, pass -AllowInsecureLan with a private LAN URL.'
    }
    $address = [System.Net.IPAddress]::None
    $isPrivateLan = $false
    if ([System.Net.IPAddress]::TryParse($dashboardUri.Host, [ref]$address)) {
        $bytes = $address.GetAddressBytes()
        $isPrivateLan = ($bytes[0] -eq 10) -or
            ($bytes[0] -eq 192 -and $bytes[1] -eq 168) -or
            ($bytes[0] -eq 172 -and $bytes[1] -ge 16 -and $bytes[1] -le 31)
    } else {
        $isPrivateLan = $dashboardUri.Host.EndsWith('.local', [StringComparison]::OrdinalIgnoreCase)
    }
    if (-not $isPrivateLan) { throw 'HTTP is allowed only for RFC1918 or .local home-LAN addresses.' }
}

$health = Invoke-RestMethod -Uri "$DashboardUrl/healthz" -TimeoutSec 12
if (-not $health.ok) { throw 'The cloud dashboard health check did not return ok.' }

$agentPath = Join-Path $InstallerDir 'me_cam_agent.py'
$agentSource = Get-Content -Raw $agentPath
if ($agentSource -notmatch 'Motion recording failed; suppressing clipless alert') {
    throw 'The installer agent is missing the clipless-motion fix. Update me_cam_installer first.'
}

$activationSecure = Read-Host 'Paste the one-time camera enrollment code' -AsSecureString
$activationPtr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($activationSecure)
$activationCode = ''
try {
    $activationCode = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($activationPtr).Trim()
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($activationPtr)
}
if ($activationCode -notmatch '^[A-Za-z0-9_-]{16,128}$') {
    if ($activationCode -match '^[A-Za-z0-9+/]{40,}={0,2}$') {
        throw 'This looks like the dashboard owner setup key, not a camera enrollment code. Create the owner account in the browser, then create a camera in Devices and use that camera enrollment code here.'
    }
    throw 'Enrollment code format is invalid. Create a camera in the dashboard and paste its one-time camera enrollment code, not the owner setup key.'
}

$cpuInfo = ssh $PiHost 'cat /proc/cpuinfo'
if ($LASTEXITCODE -ne 0) { throw 'SSH could not read the Pi CPU information.' }
$serialMatch = [regex]::Match(($cpuInfo -join "`n"), '(?m)^Serial\s*:\s*([0-9a-fA-F]+)')
if ($serialMatch.Success) {
    $serial = $serialMatch.Groups[1].Value
    $deviceSuffix = $serial.Substring([Math]::Max(0, $serial.Length - 12))
} else {
    $hostname = (ssh $PiHost 'hostname').Trim()
    if ($LASTEXITCODE -ne 0 -or -not $hostname) { throw 'Could not identify the Pi.' }
    $deviceSuffix = $hostname -replace '[^A-Za-z0-9-]', '-'
}
$deviceId = "mecam-$deviceSuffix"
$configPath = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString() + '.conf')
$stagePath = '/tmp/mecam-ssh-stage'
$agentFiles = @(
    'me_cam_agent.py', 'auto_update.py', 'power_manager.py', 'config_manager.py',
    'hardware_detect.py', 'audio_recorder.py', 'offline_queue.py', 'encryptor.py',
    'me_cam.service'
)

try {
    $config = @"
DASHBOARD_URL='$DashboardUrl'
DEVICE_ID='$deviceId'
DEVICE_TOKEN=''
MECAM_ACTIVATION_CODE='$activationCode'
AUTO_UPDATE='false'
CAMERA_MODULE='ov5647'
RESOLUTION='1280x720'
STREAM_PORT='8080'
AUTO_RECORD='true'
CLIP_DURATION='30'
AUDIO_ENABLED='true'
BATTERY_CAPACITY_MAH='10000'
POWER_SOURCE_TYPE='powerbank'
POWER_MODE='balanced'
"@
    [System.IO.File]::WriteAllText($configPath, $config, [System.Text.Encoding]::ASCII)
    ssh $PiHost "mkdir -p $stagePath"
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Pi staging folder.' }

    $paths = foreach ($file in $agentFiles) {
        $path = Join-Path $InstallerDir $file
        if (-not (Test-Path $path)) { throw "Required installer file is missing: $path" }
        $path
    }
    scp @paths "${PiHost}:${stagePath}/"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the Pi agent files.' }
    scp $configPath "${PiHost}:${stagePath}/me_cam.conf"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the staged device configuration.' }
    $installScript = Join-Path $PSScriptRoot 'install_pi_agent.sh'
    scp $installScript "${PiHost}:${stagePath}/install_pi_agent.sh"
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy the Pi install script.' }
    ssh -t $PiHost "sudo bash $stagePath/install_pi_agent.sh $stagePath"
    if ($LASTEXITCODE -ne 0) { throw 'Pi installation failed; inspect the SSH output and journal.' }
} finally {
    Remove-Item -Force -ErrorAction SilentlyContinue $configPath
    $activationCode = $null
    $activationSecure = $null
}