<#
  按同一提交 SHA 一键复跑全部测试并归档证据（课程「四类产物 SHA 一致」要求）。
  人只需：启动前后端服务 -> 运行本脚本 -> 复核产物。脚本不启动服务、不改文档、不提交 git。

  用法（仓库根目录执行）：
    powershell -File backend/scripts/reproduce_all.ps1 -Sha <最终提交SHA>
    powershell -File backend/scripts/reproduce_all.ps1 -SkipBrowser     # 无 Playwright 环境时

  前置：后端 uvicorn @127.0.0.1:8000、前端 vite @127.0.0.1:5173、MySQL jit_demo/jit_test 就绪、
        环境变量 API_TOKEN 已设置（不要写进仓库文件）。
  产物：覆盖率 HTML -> docs/test/unit_test/coverage_report/htmlcov-<sha>/
        运行摘要   -> temp/reproduce-<sha>.json（temp 不入库，供人工复核）
#>
param(
    [string]$Sha = '',
    [switch]$SkipBrowser,
    [switch]$SkipCoverage
)

$ErrorActionPreference = 'Continue'
$backend = Split-Path -Parent $PSScriptRoot
$repo = Split-Path -Parent $backend
if (-not $Sha) { $Sha = (git -C $repo rev-parse --short HEAD).Trim() }

$results = @()

function Invoke-Step {
    param([string]$Name, [scriptblock]$Command)
    $t0 = Get-Date
    $out = (& $Command 2>&1 | Out-String)
    $code = $LASTEXITCODE
    $tail = (($out -split "`r?`n" | Where-Object { $_.Trim() } | Select-Object -Last 4) -join ' | ')
    $script:results += [pscustomobject]@{
        step = $Name; exit = $code
        seconds = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
        tail = $tail
    }
    Write-Host ("[{0}] exit={1} {2}s" -f $Name, $code, [math]::Round(((Get-Date) - $t0).TotalSeconds, 1))
    if ($code -ne 0) { Write-Host ("  tail: " + $tail) }
}

Write-Host "=== reproduce SHA=$Sha ==="
if (-not $env:API_TOKEN) { Write-Warning 'API_TOKEN 未设置；接口类脚本可能 401 失败' }

try {
    $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -Headers @{ 'X-API-Key' = $env:API_TOKEN } -TimeoutSec 5
    Write-Host ("health: status={0} db={1}" -f $health.data.status, $health.data.db)
} catch {
    Write-Warning '后端 /api/health 不可达，请先启动 uvicorn 再运行本脚本；已跳过的步骤会在摘要中标出。'
}

Push-Location $backend
try {
    if (-not $SkipCoverage) {
        Invoke-Step '单元+覆盖率' { python -m pytest -q --cov=app --cov-branch --cov-report=html:htmlcov --cov-report=term-missing }
        $src = Join-Path $backend 'htmlcov'
        if (Test-Path $src) {
            $dst = Join-Path $repo "docs/test/unit_test/coverage_report/htmlcov-$Sha"
            New-Item -ItemType Directory -Force -Path $dst | Out-Null
            Get-ChildItem -File $src | ForEach-Object { Copy-Item -LiteralPath $_.FullName -Destination $dst -Force }
            Write-Host "coverage HTML -> $dst"
        }
    }

    Invoke-Step '集成 35 条' { python scripts/integration_cases.py --json out.json }
    Invoke-Step '安全 12 条' { python scripts/security_cases.py }
    Invoke-Step '单客户端性能' { python scripts/perf_loop.py }
    Invoke-Step '并发负载 5x5' { $env:USERS = '5'; $env:REQUESTS = '5'; python scripts/load_test.py }
    Invoke-Step '并发负载 10x10' { $env:USERS = '10'; $env:REQUESTS = '10'; python scripts/load_test.py }
    Invoke-Step '系统异常 13 条' { python scripts/system_exceptions.py --scenario all }
    Invoke-Step '25 模型矩阵' { python scripts/online_models_matrix.py }
    Invoke-Step '验收 Scenario 清单' { python scripts/acceptance_scenarios.py }
    Invoke-Step '逐端点联调留痕' { python scripts/linkage_capture.py }

    if (-not $SkipBrowser) {
        Invoke-Step '三浏览器走查截图' { python scripts/browser_walkthrough.py --sha $Sha }
    }
} finally {
    Pop-Location
}

$tempDir = Join-Path $repo 'temp'
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
$summary = [pscustomobject]@{
    sha = $Sha
    generated_at = (Get-Date).ToString('o')
    steps = $results
    note = '自动复跑摘要；不自动修改 docs/test 文档、不自动提交。失败步骤须人工复核。'
}
$outFile = Join-Path $tempDir "reproduce-$Sha.json"
$summary | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $outFile -Encoding UTF8
Write-Host "summary -> $outFile"

$failed = @($results | Where-Object { $_.exit -ne 0 })
Write-Host ("=== done: total={0} failed={1} ===" -f $results.Count, $failed.Count)
if ($failed.Count -gt 0) {
    Write-Warning '存在失败步骤：请按 docs/test 交付文档如实登记，不得把失败写成通过。'
    exit 1
}
