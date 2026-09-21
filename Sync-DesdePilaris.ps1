<#
.SINOPSIS
    Trae el codigo de Pilaris (ProgramC#\DynamicSepticSystem) a CalandriaSys
    aplicando el rebrand, y deja intactos los archivos que SI deben diferir.

.USO
    .\Sync-DesdePilaris.ps1            # muestra que cambiaria (no escribe)
    .\Sync-DesdePilaris.ps1 -Aplicar   # escribe; revisa despues con git diff

    Flujo normal: trabajas en Pilaris -> corres esto -> git diff -> commit ->
    .\publicar-release.ps1 -Version X con el MISMO numero que publicaste alla.
#>
param(
    [switch]$Aplicar,
    [string]$Origen = (Join-Path (Split-Path $PSScriptRoot -Parent) "DynamicSepticSystem")
)

$ErrorActionPreference = "Stop"
$destino = $PSScriptRoot

if (-not (Test-Path $Origen)) { Write-Error "No existe el origen: $Origen" }

# Carpetas que se sincronizan (lo demas -installer.iss, publicar-release.ps1,
# los .zip/.exe- es infraestructura propia de cada marca).
$carpetas = @("DynamicSepticSystem", "Calandria.Api", "Updater")

# Rutas (relativas a la raiz del repo) que NUNCA se copian: cada marca tiene
# la suya y pisarla rompe el despliegue.
$noTocar = @(
    "DynamicSepticSystem\App.config"                 # GitHubRepo = CalandriaSys
    "DynamicSepticSystem\Properties\AssemblyInfo.cs"  # version + AssemblyCompany propios (ver chequeo al final)
    "DynamicSepticSystem\Resources\Logo.png"         # logo propio
    "DynamicSepticSystem\app.ico"                    # icono propio
    "Calandria.Api\App.config"                       # puerto 8734, JwtHorasVigencia 2
    "Calandria.Api\Configuracion.cs"                 # puerto por defecto
    "Calandria.Api\CalandriaService.cs"              # ServiceName = CalandriaSysApi
    "Calandria.Api\consola.bat"
    "Calandria.Api\iniciar-servicio.bat"
    "Calandria.Api\detener-servicio.bat"
    "Calandria.Api\reiniciar-servicio.bat"
    "Calandria.Api\instalar-servicio.bat"
    "Calandria.Api\desinstalar-servicio.bat"
)
# Nada de salidas de compilacion, paquetes, secretos ni despliegues.
$excluirDir = @("bin","obj","packages","deploy","publish","publish-nuevo","logs",".vs",".git",".claude",".localpilot","pruebas-ui")
$excluirArchivo = '(secrets\.config|connectionStrings\.config|\.bak|\.user|\.suo)$'

# Extensiones que se tratan como texto (se les aplica el rebrand). El resto se
# copia tal cual.
$textos = '\.(cs|html|js|css|config|csproj|resx|sln|md|sql|json|xml|txt)$'

# Intercambio SIMULTANEO de marca: asi un comentario de Pilaris que menciona a
# CalandriaSys como "el otro producto" queda bien orientado de este lado.
#
# Trabaja sobre BYTES, no sobre texto. En el repo conviven archivos UTF-8 y
# ISO-8859-1 (~100 de estos ultimos): decodificarlos como UTF-8 convierte cada
# acento en U+FFFD y eso ya rompio una compilacion, porque la "n" de TamanioKB
# vivia dentro de un identificador. Latin-1 mapea cada byte a un caracter y de
# vuelta sin perder nada, asi que las secuencias UTF-8 pasan intactas y solo se
# tocan los tokens de marca, que son ASCII puro.
$LATIN1 = [Text.Encoding]::GetEncoding(28591)

function RebrandBytes([byte[]]$bytes) {
    # Hay archivos de 0 bytes en el repo (licenses.licx, UpdateServer.cs...) y
    # PowerShell convierte el arreglo vacio en $null al enlazar el parametro.
    if ($null -eq $bytes -or $bytes.Length -eq 0) { return ,([byte[]]@()) }
    $t = $LATIN1.GetString($bytes)
    $t = [regex]::Replace($t, 'Pilaris|CalandriaSys', {
        param($m) if ($m.Value -eq 'Pilaris') { 'CalandriaSys' } else { 'Pilaris' } })
    # Los dos repos venian con finales de linea distintos (CRLF alla, LF aqui):
    # normalizar a CRLF evita que cada sync marque como "modificado" medio repo.
    $t = [regex]::Replace($t, "\r?\n", "`r`n")
    ,$LATIN1.GetBytes($t)
}

$cambiados = @(); $nuevos = @()
foreach ($c in $carpetas) {
    $raizOrigen = Join-Path $Origen $c
    if (-not (Test-Path $raizOrigen)) { continue }
    foreach ($f in Get-ChildItem $raizOrigen -Recurse -File) {
        $rel = $f.FullName.Substring($Origen.Length).TrimStart('\')
        if ($rel.Split([char]92) | Where-Object { $excluirDir -contains $_ }) { continue }
        if ($rel -match $excluirArchivo) { continue }
        if ($noTocar -contains $rel) { continue }

        $dst = Join-Path $destino $rel
        $existe = Test-Path $dst

        if ($rel -match $textos) {
            $nuevo = RebrandBytes ([IO.File]::ReadAllBytes($f.FullName))
            # Los dos repos son PUBLICOS: no dejar que un secreto de Pilaris
            # viaje hasta aca de contrabando. Aborta en vez de avisar y seguir.
            if ($nuevo.Length -gt 0 -and $LATIN1.GetString($nuevo) -match 'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,}') {
                Write-Error "$rel trae un token de GitHub. Limpialo en Pilaris antes de sincronizar."
            }
            if ($existe -and @(Compare-Object $nuevo ([IO.File]::ReadAllBytes($dst)) -SyncWindow 0).Count -eq 0) { continue }
            if ($Aplicar) {
                New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
                [IO.File]::WriteAllBytes($dst, $nuevo)
            }
        } else {
            if ($existe -and (Get-FileHash $f.FullName).Hash -eq (Get-FileHash $dst).Hash) { continue }
            if ($Aplicar) {
                New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
                Copy-Item $f.FullName $dst -Force
            }
        }
        if ($existe) { $cambiados += $rel } else { $nuevos += $rel }
    }
}

foreach ($r in $nuevos)    { Write-Host "  + $r" -ForegroundColor Green }
foreach ($r in $cambiados) { Write-Host "  ~ $r" -ForegroundColor Yellow }
Write-Host ""
Write-Host "$($nuevos.Count) nuevos, $($cambiados.Count) modificados." -ForegroundColor Cyan
if ($Aplicar) {
    Write-Host "Aplicado. Revisa con: git -C `"$destino`" diff" -ForegroundColor Cyan
} else {
    Write-Host "Simulacion. Corre con -Aplicar para escribir." -ForegroundColor DarkGray
}

# AssemblyInfo.cs no se copia (cada marca tiene el suyo), asi que la paridad de
# version hay que verificarla aparte: es justo el numero que el auto-updater
# compara contra la release de GitHub.
function VersionDe($raiz) {
    $ai = Join-Path $raiz "DynamicSepticSystem\Properties\AssemblyInfo.cs"
    if (-not (Test-Path $ai)) { return "?" }
    $m = [regex]::Match([IO.File]::ReadAllText($ai), 'AssemblyVersion\("([^"]+)"\)')
    if ($m.Success) { $m.Groups[1].Value } else { "?" }
}
$vP = VersionDe $Origen; $vC = VersionDe $destino
Write-Host ""
if ($vP -eq $vC) {
    Write-Host "Version a la par: $vC" -ForegroundColor Green
} else {
    Write-Host "VERSION DESALINEADA  Pilaris=$vP  CalandriaSys=$vC" -ForegroundColor Red
    Write-Host "  Empareja publicando aqui: .\publicar-release.ps1 -Version $vP" -ForegroundColor Red
}
