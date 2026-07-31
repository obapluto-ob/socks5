# SOCKS5 Proxy Installer for Windows
# Run with: irm https://raw.githubusercontent.com/YOUR_USERNAME/socks5/main/install.ps1 | iex

$ErrorActionPreference = "Stop"
$INSTALL_DIR = "C:\socks5"
$DANTE_DIR = "C:\dante"
$REPO_URL = "https://github.com/obapluto-ob/socks5/archive/refs/heads/main.zip"

function Write-Header($msg) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Step($msg) {
    Write-Host "[+] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[!] $msg" -ForegroundColor Yellow
}

# ── 1. Check Admin ──────────────────────────────────────────────
Write-Header "SOCKS5 Proxy Installer"
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Please run this script as Administrator." -ForegroundColor Red
    exit 1
}

# ── 2. Install Chocolatey ───────────────────────────────────────
Write-Step "Checking Chocolatey..."
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Write-Step "Installing Chocolatey..."
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
}

# ── 3. Install Python & PostgreSQL ─────────────────────────────
Write-Step "Installing Python 3.11..."
choco install python311 -y --no-progress | Out-Null

Write-Step "Installing PostgreSQL..."
choco install postgresql15 --params '/Password:socks5pass' -y --no-progress | Out-Null

# ── 4. Download Project ─────────────────────────────────────────
Write-Step "Downloading SOCKS5 project..."
New-Item -ItemType Directory -Force -Path $INSTALL_DIR | Out-Null
$zipPath = "$env:TEMP\socks5.zip"
Invoke-WebRequest -Uri $REPO_URL -OutFile $zipPath
Expand-Archive -Path $zipPath -DestinationPath $env:TEMP -Force
Copy-Item "$env:TEMP\socks5-main\*" $INSTALL_DIR -Recurse -Force

# ── 5. Install Python Dependencies ─────────────────────────────
Write-Step "Installing Python dependencies..."
Set-Location $INSTALL_DIR
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
python -m pip install -r requirements.txt --quiet

# ── 6. Setup PostgreSQL Database ───────────────────────────────
Write-Step "Setting up database..."
$env:PGPASSWORD = "socks5pass"
& "C:\Program Files\PostgreSQL\15\bin\psql.exe" -U postgres -c "CREATE DATABASE socks5db;" 2>$null

# Write .env
$publicIP = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10)
$secretKey = [System.Web.Security.Membership]::GeneratePassword(32, 4)
$jwtKey = [System.Web.Security.Membership]::GeneratePassword(32, 4)

@"
SECRET_KEY=$secretKey
JWT_SECRET_KEY=$jwtKey
DATABASE_URL=postgresql://postgres:socks5pass@localhost:5432/socks5db
DANTE_LOG=C:/dante/logs/sockd.log
DANTE_CONF=C:/dante/sockd.conf
DANTE_PASSWD=C:/dante/sockd.passwd
PROXY_PORT=$proxyPort
MAX_CONNECTIONS_PER_USER=2
"@ | Set-Content "$INSTALL_DIR\.env"

# ── 7. Run Migrations ───────────────────────────────────────────
Write-Step "Running database migrations..."
Set-Location $INSTALL_DIR
$env:FLASK_APP = "run.py"
python -m flask db init 2>$null
python -m flask db migrate -m "initial" 2>$null
python -m flask db upgrade

# ── 8. Create Admin Account ─────────────────────────────────────
Write-Step "Creating admin account..."
$adminUser = Read-Host "Enter admin username"
$adminPass = Read-Host "Enter admin password" -AsSecureString
$adminPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($adminPass))

# ── Ask for proxy port ──────────────────────────────────────────
$proxyPortInput = Read-Host "Enter proxy port (press Enter for default 10800)"
if ([string]::IsNullOrWhiteSpace($proxyPortInput)) {
    $proxyPort = 10800
} else {
    $proxyPort = [int]$proxyPortInput
}
Write-Step "Using proxy port: $proxyPort"

python -c @"
import sys
sys.path.insert(0, '$INSTALL_DIR')
from app import create_app, db
from app.models import Admin
app = create_app()
with app.app_context():
    db.create_all()
    a = Admin(username='$adminUser')
    a.set_password('$adminPassPlain')
    db.session.add(a)
    db.session.commit()
    print('Admin created.')
"@

# ── 9. Setup Dante ──────────────────────────────────────────────
Write-Step "Setting up Dante SOCKS5..."
New-Item -ItemType Directory -Force -Path $DANTE_DIR | Out-Null
New-Item -ItemType Directory -Force -Path "$DANTE_DIR\logs" | Out-Null
New-Item -ItemType File -Force -Path "$DANTE_DIR\sockd.passwd" | Out-Null

# Detect active network interface
$interface = (Get-NetAdapter | Where-Object { $_.Status -eq "Up" } | Select-Object -First 1).Name
$confContent = Get-Content "$INSTALL_DIR\dante\sockd.conf" -Raw
$confContent = $confContent -replace "YOUR_NETWORK_INTERFACE", $interface
$confContent | Set-Content "$DANTE_DIR\sockd.conf"

# Update Dante config with chosen port
$confContent = $confContent -replace "port = 10800", "port = $proxyPort"
$confContent | Set-Content "$DANTE_DIR\sockd.conf"

Write-Warn "Download Dante for Windows from https://www.inet.no/dante/ and place sockd.exe in C:\dante\"
Write-Warn "Press Enter after placing sockd.exe in C:\dante\"
Read-Host

# ── 10. Open Firewall Port ──────────────────────────────────────
Write-Step "Opening firewall port $proxyPort..."
netsh advfirewall firewall add rule name="SOCKS5 Proxy" dir=in action=allow protocol=TCP localport=$proxyPort | Out-Null

# ── 11. Register Windows Services ──────────────────────────────
Write-Step "Registering Windows services for auto-start..."

# Flask service via NSSM
if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    choco install nssm -y --no-progress | Out-Null
}

nssm install SOCKS5-Flask python "$INSTALL_DIR\run.py"
nssm set SOCKS5-Flask AppDirectory $INSTALL_DIR
nssm set SOCKS5-Flask Start SERVICE_AUTO_START
nssm start SOCKS5-Flask

# Dante service
nssm install SOCKS5-Dante "$DANTE_DIR\sockd.exe" "-f $DANTE_DIR\sockd.conf"
nssm set SOCKS5-Dante AppDirectory $DANTE_DIR
nssm set SOCKS5-Dante Start SERVICE_AUTO_START
nssm start SOCKS5-Dante

# ── 12. Print Final Credentials ────────────────────────────────
Write-Header "SETUP COMPLETE!"
Write-Host ""
Write-Host "  Admin Panel:  http://localhost:5000/dashboard" -ForegroundColor White
Write-Host "  Public IP:    $publicIP" -ForegroundColor White
Write-Host "  Proxy Port:   $proxyPort" -ForegroundColor White
Write-Host ""
Write-Host "  Add your brother via the admin panel, then copy" -ForegroundColor Gray
Write-Host "  the proxy string and send it to him:" -ForegroundColor Gray
Write-Host ""
Write-Host "  Format:  username:password@${publicIP}:${proxyPort}" -ForegroundColor Green
Write-Host ""
Write-Host "  He pastes it in Potatso or any SOCKS5 app." -ForegroundColor Gray
Write-Host ""
Write-Host "  Services registered — proxy auto-starts on reboot." -ForegroundColor Cyan
Write-Host ""
