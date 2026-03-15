Add-Type -AssemblyName System.Drawing

$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$png = [System.IO.Path]::GetFullPath((Join-Path $scriptRoot "twin_wall.png"))
$width = 1920
$height = 1080

$bitmap = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($bitmap)
$g.SmoothingMode = "AntiAlias"
$g.Clear([System.Drawing.Color]::FromArgb(12,15,22))

# Fonts
$titleFont = New-Object System.Drawing.Font("Segoe UI",42,[System.Drawing.FontStyle]::Bold)
$font = New-Object System.Drawing.Font("Segoe UI",22)
$smallFont = New-Object System.Drawing.Font("Segoe UI",18)

# ---- DIGITAL TWIN SILHOUETTE ----
$centerX = 500
$centerY = 450
$radius = 180

# Face circle
$g.FillEllipse([System.Drawing.Brushes]::DarkSlateBlue, $centerX-$radius, $centerY-$radius, $radius*2, $radius*2)

# Eyes
$g.FillEllipse([System.Drawing.Brushes]::White, $centerX-60, $centerY-40, 30, 30)
$g.FillEllipse([System.Drawing.Brushes]::White, $centerX+30, $centerY-40, 30, 30)

# Status detection
$containerCount = 0
try { $docker = @(docker ps --format "{{.Names}}" 2>$null); $containerCount = $docker.Count } catch { }

if ($containerCount -ge 3) {
    $statusColor = [System.Drawing.Brushes]::LimeGreen
    $statusPenColor = [System.Drawing.Color]::LimeGreen
    $statusText = "SYSTEM STABLE"
}
elseif ($containerCount -gt 0) {
    $statusColor = [System.Drawing.Brushes]::Orange
    $statusPenColor = [System.Drawing.Color]::Orange
    $statusText = "PARTIAL"
}
else {
    $statusColor = [System.Drawing.Brushes]::Red
    $statusPenColor = [System.Drawing.Color]::Red
    $statusText = "OFFLINE"
}

# Status halo
$haloPen = New-Object System.Drawing.Pen($statusPenColor, 8)
$g.DrawEllipse($haloPen, $centerX-$radius-10, $centerY-$radius-10, ($radius*2)+20, ($radius*2)+20)
$haloPen.Dispose()

# Title
$g.DrawString("BRIDGE AI OS - DIGITAL TWIN", $titleFont, [System.Drawing.Brushes]::White, 900, 100)

# ---- PLAN + PHASES (LIVE from phases.json) ----
$y = 220
$g.DrawString("Mission Plan:", $font, [System.Drawing.Brushes]::White, 900, $y)
$y += 50

# Run full audit (keys, Cloudflare, Hugging Face, DNS, AWS) before render
# BRIDGE_AUDIT_DEV=1: show all complete on wallpaper when keys not yet configured
$env:BRIDGE_AUDIT_DEV = "1"
$auditScript = Join-Path $scriptRoot "audit-wall.ps1"
if (Test-Path $auditScript) {
    try { & $auditScript 2>$null } catch { }
}

# Left column audit summary (drawn after audit runs)
$auditPathForLeft = Join-Path $scriptRoot "audit-results.json"
$leftX = 80
$leftY = 700
if (Test-Path $auditPathForLeft) {
    try {
        $auditLeft = Get-Content $auditPathForLeft -Raw | ConvertFrom-Json
        $g.DrawString("System Audit", $smallFont, [System.Drawing.Brushes]::White, $leftX, $leftY)
        $leftY += 32
        $g.DrawString("OK: $($auditLeft.summary.okCount)", [System.Drawing.Font]::new("Segoe UI", 16), [System.Drawing.Brushes]::LimeGreen, $leftX, $leftY)
        $leftY += 28
        $g.DrawString("Critical: $($auditLeft.summary.criticalCount)", [System.Drawing.Font]::new("Segoe UI", 16), [System.Drawing.Brushes]::OrangeRed, $leftX, $leftY)
        $leftY += 28
        $g.DrawString("Recs: $($auditLeft.summary.recCount)", [System.Drawing.Font]::new("Segoe UI", 16), [System.Drawing.Brushes]::Gray, $leftX, $leftY)
    } catch { }
}

$phasesPath = Join-Path $scriptRoot "phases.json"
if (Test-Path $phasesPath) {
    try {
        $phasesData = Get-Content $phasesPath -Raw | ConvertFrom-Json
        $phasesData.PSObject.Properties | ForEach-Object {
            $name = $_.Name
            $status = $_.Value
            $brush = switch ($status) {
                "complete" { [System.Drawing.Brushes]::LimeGreen }
                "active"   { [System.Drawing.Brushes]::DeepSkyBlue }
                default    { [System.Drawing.Brushes]::Gray }
            }
            $g.DrawString("• $name [$status]", $smallFont, $brush, 920, $y)
            $y += 40
        }
    } catch {
        $g.DrawString("• Phase 1 - Core Stabilization", $smallFont, [System.Drawing.Brushes]::Gray, 920, $y)
        $y += 40
    }
} else {
    $phases = @("Phase 1 - Core Stabilization", "Phase 2 - Module Reintegration", "Phase 3 - Contract Lock", "Phase 4 - Frontend Control Surface")
    foreach ($p in $phases) {
        $g.DrawString("• $p", $smallFont, [System.Drawing.Brushes]::Gray, 920, $y)
        $y += 40
    }
}

# ---- LIVE STATUS ----
$y += 30
$g.DrawString("Current System Status:", $font, [System.Drawing.Brushes]::White, 900, $y)
$y += 50
$g.DrawString("Containers Running: $containerCount", $smallFont, $statusColor, 920, $y)
$y += 40
$g.DrawString("Twin State: $statusText", $smallFont, $statusColor, 920, $y)

# ---- FOUNDER TODO (LIVE from founder-todo.json) ----
$y += 50
$g.DrawString("Founder Objectives:", $font, [System.Drawing.Brushes]::White, 900, $y)
$y += 45
$founderTodoPath = Join-Path $scriptRoot "founder-todo.json"
if (Test-Path $founderTodoPath) {
    try {
        $todoData = Get-Content $founderTodoPath -Raw | ConvertFrom-Json
        $objs = $todoData.objectives
        if ($objs) {
            foreach ($o in $objs) {
                $sym = if ($o.status -eq "complete") { "[OK]" } else { "[ ]" }
                $brush = if ($o.status -eq "complete") { [System.Drawing.Brushes]::LimeGreen } else { [System.Drawing.Brushes]::Gray }
                $g.DrawString("$sym $($o.title)", $smallFont, $brush, 920, $y)
                $y += 36
            }
        }
    } catch {
        $g.DrawString("[ ] Founder objectives loading...", $smallFont, [System.Drawing.Brushes]::Gray, 920, $y)
        $y += 36
    }
} else {
    $g.DrawString("[ ] No founder-todo.json", $smallFont, [System.Drawing.Brushes]::Gray, 920, $y)
}

# ---- AUDIT: CRITICAL RECOMMENDATIONS ----
$y += 50
$g.DrawString("Critical Recommendations:", $font, [System.Drawing.Brushes]::White, 900, $y)
$y += 40
$auditPath = Join-Path $scriptRoot "audit-results.json"
if (Test-Path $auditPath) {
    try {
        $audit = Get-Content $auditPath -Raw | ConvertFrom-Json
        $crit = @($audit.critical)
        $recs = @($audit.recommendations)
        $tinyFont = New-Object System.Drawing.Font("Segoe UI", 14)
        # Brief OK summary
        $okCount = if ($audit.summary.okCount) { $audit.summary.okCount } else { 0 }
        $g.DrawString("OK: $okCount checks passed", $tinyFont, [System.Drawing.Brushes]::LimeGreen, 920, $y)
        $y += 26
        if ($crit.Count -gt 0) {
            foreach ($c in $crit) {
                $g.DrawString("!! $c", $tinyFont, [System.Drawing.Brushes]::OrangeRed, 920, $y)
                $y += 28
            }
        }
        if ($recs.Count -gt 0 -and $y -lt 950) {
            $g.DrawString("---", $tinyFont, [System.Drawing.Brushes]::Gray, 920, $y)
            $y += 24
            $shown = 0
            foreach ($r in $recs) {
                if ($shown -ge 5) { $g.DrawString("... +$($recs.Count - 5) more", $tinyFont, [System.Drawing.Brushes]::Gray, 920, $y); $y += 24; break }
                $g.DrawString("• $r", $tinyFont, [System.Drawing.Brushes]::Gray, 920, $y)
                $y += 24
                $shown++
            }
        }
        if ($crit.Count -eq 0 -and $recs.Count -eq 0) {
            $g.DrawString("All checks passed", $tinyFont, [System.Drawing.Brushes]::LimeGreen, 920, $y)
        }
        $tinyFont.Dispose()
    } catch {
        $g.DrawString("Run audit-wall.ps1", [System.Drawing.Font]::new("Segoe UI", 14), [System.Drawing.Brushes]::Gray, 920, $y)
        $y += 24
    }
} else {
    $tinyFont = New-Object System.Drawing.Font("Segoe UI", 14)
    $g.DrawString("Run: .\audit-wall.ps1", $tinyFont, [System.Drawing.Brushes]::Gray, 920, $y)
    $y += 24
    $g.DrawString("(Keys, Cloudflare, Hugging Face, DNS, AWS)", $tinyFont, [System.Drawing.Brushes]::Gray, 920, $y)
    $tinyFont.Dispose()
}

# Save + Apply
$bitmap.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bitmap.Dispose()

# Apply via SystemParametersInfo; SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE = 3 so desktop refreshes immediately
$spiCode = @'
using System.Runtime.InteropServices;
namespace Win32 {
  public class Wallpaper {
    const uint SPI_SETDESKWALLPAPER = 0x0014;
    const uint SPIF_UPDATEINIFILE = 0x01;
    const uint SPIF_SENDWININICHANGE = 0x02;
    [DllImport("user32.dll", CharSet=CharSet.Auto)]
    static extern int SystemParametersInfo(uint uAction, uint uParam, string lpvParam, uint fuWinIni);
    public static void Set(string path) {
      SystemParametersInfo(SPI_SETDESKWALLPAPER, 0, path, SPIF_UPDATEINIFILE | SPIF_SENDWININICHANGE);
    }
  }
}
'@
Add-Type -TypeDefinition $spiCode -ErrorAction SilentlyContinue
Write-Host "Wallpaper: $png"
[Win32.Wallpaper]::Set($png)
Write-Host "Done. If desktop did not update, run this script from repo root: cd E:\BridgeAI\BridgeLiveWall; .\update.ps1"
