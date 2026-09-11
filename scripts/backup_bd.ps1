<#
Backup diario de la base de datos SGD-SINOLE via pg_dump.
No requiere contraseña en este archivo: usa %APPDATA%\postgresql\pgpass.conf
(ver instrucciones de instalación en el README).

Uso manual: powershell -ExecutionPolicy Bypass -File backup_bd.ps1
#>

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$EnvFile = Join-Path $ProjectDir ".env"

if ($env:OneDrive) {
    $BackupDir = Join-Path $env:OneDrive "SGD-Sinole-Backups"
} else {
    $BackupDir = "C:\SGD-SINOLE-Backups"
}
if ($env:SGD_BACKUP_DIR) {
    $BackupDir = $env:SGD_BACKUP_DIR
}

$LogFile = Join-Path $BackupDir "backup.log"

function Escribir-Log($mensaje) {
    $linea = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $mensaje"
    Add-Content -Path $LogFile -Value $linea -Encoding utf8
    Write-Output $linea
}

try {
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }

    # --- Detectar pg_dump.exe ---
    $PgDump = $null
    $enPath = Get-Command pg_dump -ErrorAction SilentlyContinue
    if ($enPath) {
        $PgDump = $enPath.Source
    } else {
        $candidatos = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe" -ErrorAction SilentlyContinue
        if ($candidatos) {
            $PgDump = ($candidatos | Sort-Object FullName -Descending | Select-Object -First 1).FullName
        }
    }
    if (-not $PgDump) {
        throw "No se encontró pg_dump.exe (ni en PATH ni en C:\Program Files\PostgreSQL\*\bin\). Verificar instalación de PostgreSQL."
    }

    # --- Leer host/puerto/usuario/BD desde .env (sin exponer la contraseña) ---
    if (-not (Test-Path $EnvFile)) {
        throw "No se encontró .env en $ProjectDir"
    }
    $linea = Get-Content $EnvFile | Where-Object { $_ -match '^DATABASE_URL=' } | Select-Object -First 1
    if (-not $linea) {
        throw "DATABASE_URL no encontrado en .env"
    }
    if ($linea -notmatch 'postgresql(\+psycopg2)?://([^:]+):[^@]+@([^:/]+):(\d+)/(.+)$') {
        throw "No se pudo interpretar DATABASE_URL"
    }
    $DbUser = $Matches[2]
    $DbHost = $Matches[3]
    $DbPort = $Matches[4]
    $DbName = $Matches[5]

    # --- Generar backup ---
    $fecha = Get-Date -Format "yyyy-MM-dd"
    $archivo = Join-Path $BackupDir "sgd_sinole_$fecha.dump"

    & $PgDump -h $DbHost -p $DbPort -U $DbUser -Fc -f $archivo $DbName
    if ($LASTEXITCODE -ne 0) {
        throw "pg_dump terminó con código $LASTEXITCODE"
    }

    $tamano = (Get-Item $archivo).Length
    Escribir-Log "OK: backup creado en $archivo ($tamano bytes)"

    # --- Rotación: borrar backups de más de 30 días ---
    $limite = (Get-Date).AddDays(-30)
    Get-ChildItem $BackupDir -Filter "sgd_sinole_*.dump" |
        Where-Object { $_.LastWriteTime -lt $limite } |
        ForEach-Object {
            Remove-Item $_.FullName -Force
            Escribir-Log "Rotación: eliminado backup antiguo $($_.Name)"
        }

} catch {
    Escribir-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
