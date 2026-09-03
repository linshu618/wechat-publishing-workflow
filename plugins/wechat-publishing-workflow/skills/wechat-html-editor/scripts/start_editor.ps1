[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Article,

    [ValidateRange(1, 65535)]
    [int]$Port = 17863,

    [string]$Cover,

    [switch]$Open
)

$ErrorActionPreference = 'Stop'

if ([System.Environment]::OSVersion.Platform -ne [System.PlatformID]::Win32NT) {
    throw 'wechat-html-editor 目前仅支持 Windows。'
}

function Get-PythonLaunch {
    $python = Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($python) {
        return @{ FilePath = $python.Source; Prefix = @() }
    }

    $py = Get-Command py -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($py) {
        return @{ FilePath = $py.Source; Prefix = @('-3') }
    }

    throw '找不到 Python 3.10 或更高版本。请安装 Python，并确认 python.exe 或 py.exe 已加入 PATH。'
}

function Test-LocalPortAvailable([int]$CandidatePort) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $CandidatePort)
    try {
        $listener.Start()
        return $true
    }
    catch {
        return $false
    }
    finally {
        $listener.Stop()
    }
}

$editorScript = Join-Path $PSScriptRoot 'edit_html.py'
if (-not (Test-Path -LiteralPath $editorScript -PathType Leaf)) {
    throw "找不到编辑器脚本：$editorScript"
}

$articlePath = (Resolve-Path -LiteralPath $Article -ErrorAction Stop).ProviderPath
$coverPath = $null
if ($Cover) {
    $coverPath = (Resolve-Path -LiteralPath $Cover -ErrorAction Stop).ProviderPath
}

$selectedPort = $Port
while (-not (Test-LocalPortAvailable $selectedPort)) {
    $selectedPort += 1
    if ($selectedPort -gt 65535) {
        throw "从端口 $Port 开始未找到可用的本机端口。"
    }
}

$pythonLaunch = Get-PythonLaunch
$arguments = @($pythonLaunch.Prefix)
$arguments += '"' + $editorScript + '"'
$arguments += '"' + $articlePath + '"'
$arguments += @('--port', [string]$selectedPort)
if ($coverPath) {
    $arguments += @('--cover', '"' + $coverPath + '"')
}
if ($Open) {
    $arguments += '--open'
}

$startParameters = @{
    FilePath = $pythonLaunch.FilePath
    ArgumentList = $arguments
    WindowStyle = 'Hidden'
    PassThru = $true
}
$process = Start-Process @startParameters

$url = "http://127.0.0.1:$selectedPort/"
$health = $null
for ($attempt = 0; $attempt -lt 50; $attempt += 1) {
    if ($process.HasExited) {
        throw "编辑器进程在健康检查通过前退出，退出代码为 $($process.ExitCode)。"
    }
    try {
        $health = Invoke-RestMethod -Uri ($url + '__wechat_editor/health') -TimeoutSec 1
        break
    }
    catch {
        Start-Sleep -Milliseconds 200
    }
}

if (-not $health -or -not $health.ok) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "编辑器未能在 10 秒内通过健康检查：$url"
}

@{
    ok = $true
    url = $url
    port = $selectedPort
    processId = $process.Id
    health = $health
} | ConvertTo-Json -Compress -Depth 4
