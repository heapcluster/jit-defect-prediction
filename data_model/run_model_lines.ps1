<#
.SYNOPSIS
  三条模型线（semantic / fused / e2e）一键执行脚本 —— 新机器拉取代码后按顺序直接跑。

.DESCRIPTION
  执行顺序与依赖关系（缺一不可，脚本会先做前置检查）：

    preparation/01–05（共享数据流水线，须先跑完）
        │  产出 data/dataset_szz.csv、data/split_szz_{train,test}.csv、
        │       data/commit_features_raw.csv、data/repos|camel（克隆仓库）
        ▼
    ① e2e/build_text_dataset   每个提交的 diff → 文本（commit_text.csv）
    ② semantic/train           文本 → 冻结 CodeBERT 768 维缓存（GPU 建议）
    ③ fused/train              Kamei14 ⊕ 语义缓存 = 782 维（纯 CPU，吃 ② 的缓存）
    ④ e2e/train                CodeBERT 微调（必须 GPU，4060 即可）

  expert 基线线与本脚本无关，单独跑：python -m pipelines.expert.train

.PARAMETER Lines
  要跑的线，逗号分隔；可选值 semantic,fused,e2e（默认全部，按依赖顺序执行）。

.PARAMETER Smoke
  冒烟模式：文本只取前 500 条、分类器只跑 lr/xgb、e2e 只训 1 轮 —— 用于新机环境验证。

.PARAMETER CheckOnly
  只做前置检查（数据文件 / 克隆仓库 / CUDA），不训练。

.PARAMETER RebuildText
  忽略已有 commit_text.csv，重新从克隆仓库提取。

.PARAMETER Python
  Python 解释器路径，默认 "python"（请先 conda activate 目标环境）。

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File data_model\run_model_lines.ps1 -Smoke
  powershell -ExecutionPolicy Bypass -File data_model\run_model_lines.ps1
  powershell -ExecutionPolicy Bypass -File data_model\run_model_lines.ps1 -Lines semantic,fused
#>
param(
  [string]$Lines = "semantic,fused,e2e",
  [switch]$Smoke,
  [switch]$CheckOnly,
  [switch]$RebuildText,
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
$dm = $PSScriptRoot                       # data_model 目录
Set-Location $dm
$logDir = Join-Path $dm "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$fail = 0

function Step($name, $argv) {
  $log = Join-Path $logDir ("{0}_{1}.log" -f $name, $stamp)
  Write-Output "===== [$name] $Python $($argv -join ' ')"
  Write-Output "===== [$name] 日志：$log"
  & $Python @argv 2>&1 | Tee-Object -FilePath $log
  if ($LASTEXITCODE -ne 0) {
    Write-Output "===== [$name] 失败（exit=$LASTEXITCODE），后续步骤终止。日志见 $log"
    $script:fail = 1
    return $false
  }
  return $true
}

# ── 前置检查 ────────────────────────────────────────────────────────────
Write-Output "===== 前置检查"
$need = @("data\dataset_szz.csv", "data\split_szz_train.csv",
          "data\split_szz_test.csv", "data\commit_features_raw.csv")
$missing = @($need | Where-Object { -not (Test-Path (Join-Path $dm $_)) })
if ($missing) {
  Write-Output "✗ 缺共享上游产物（先在 data_model 下跑 preparation/01–05）："
  $missing | ForEach-Object { Write-Output ("   - " + $_) }
  exit 2
}
Write-Output "✓ 共享上游产物齐全（01–05 已跑）"

$repoAuto = @("data\camel", "data\activemq") | Where-Object { Test-Path (Join-Path $dm "$_\.git") }
if (-not $repoAuto) {
  $cand = Get-ChildItem (Join-Path $dm "data") -Directory -ErrorAction SilentlyContinue |
    Where-Object { Test-Path (Join-Path $_.FullName ".git") } | Select-Object -First 1
  if ($cand) { $repoAuto = @($cand.FullName.Substring($dm.Length + 1)) }
}
$textCsv = Join-Path $dm "pipelines\e2e\data\commit_text.csv"
if ($RebuildText -or -not (Test-Path $textCsv)) {
  if (-not $repoAuto) {
    Write-Output "✗ 找不到克隆仓库（data/camel 等含 .git 的目录）—— e2e 建文本需要它；或先跑一次 preparation/01"
    exit 2
  }
  Write-Output ("✓ 克隆仓库：{0}（用于提取 diff 文本）" -f ($repoAuto -join ","))
} else {
  Write-Output "✓ 已有文本数据集：pipelines/e2e/data/commit_text.csv（-RebuildText 可重建）"
}

# CUDA 检查（e2e 必须用；semantic 用了更快）
$cuda = "unknown"
try {
  $cuda = (& $Python -c "import torch; print(torch.cuda.is_available())" 2>$null)
} catch { $cuda = "no-torch" }
if ($cuda -eq "True") {
  Write-Output "✓ CUDA 可用（e2e 将用 GPU + fp16）"
} elseif ($cuda -eq "False") {
  Write-Output "⚠ torch 存在但 CUDA 不可用 —— e2e 会退回 CPU（微调极慢，不现实）。"
  Write-Output "  4060 上请装 CUDA 版：pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124"
} else {
  Write-Output "⚠ 当前 Python 里没有 torch —— semantic/e2e 无法运行。先 pip install -r pipelines/e2e/requirements.txt"
}
if ($CheckOnly) { Write-Output "===== CheckOnly 结束（未训练）"; exit 0 }

# ── 按依赖顺序执行 ──────────────────────────────────────────────────────
$wanted = @($Lines.Split(",") | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ })
$smokeArgs = @{ semantic = @("--models", "lr,xgb"); fused = @("--models", "lr,xgb"); e2e = @("--epochs", "1") }
$textArgs = @()
if ($Smoke) { $textArgs = @("--limit", "500") }

# ① 文本（semantic/e2e 都吃它；已存在且未 -RebuildText 时跳过）
if (($wanted -contains "semantic" -or $wanted -contains "e2e") -and ($RebuildText -or -not (Test-Path $textCsv))) {
  $repoArg = if ($repoAuto) { @("--repo", ($repoAuto[0])) } else { @() }
  if (-not (Step "e2e_build_text" (@("-m", "pipelines.e2e.build_text_dataset") + $repoArg + $textArgs))) { exit 1 }
}

# ② semantic
if ($wanted -contains "semantic") {
  $extra = @(); if ($Smoke) { $extra = $smokeArgs.semantic }
  if (-not (Step "semantic" (@("-m", "pipelines.semantic.train", "--text-csv", "pipelines/e2e/data/commit_text.csv") + $extra))) { exit 1 }
}

# ③ fused（依赖 semantic 的编码缓存）
if ($wanted -contains "fused") {
  if (-not (Test-Path (Join-Path $dm "pipelines\semantic\data\semantic_embeddings.npz"))) {
    Write-Output "✗ fused 需要语义缓存 pipelines/semantic/data/semantic_embeddings.npz —— 先跑 semantic"
    exit 2
  }
  $extra = @(); if ($Smoke) { $extra = $smokeArgs.fused }
  if (-not (Step "fused" (@("-m", "pipelines.fused.train") + $extra))) { exit 1 }
}

# ④ e2e（微调，GPU）
if ($wanted -contains "e2e") {
  $extra = @(); if ($Smoke) { $extra = $smokeArgs.e2e }
  if (-not (Step "e2e" (@("-m", "pipelines.e2e.train") + $extra))) { exit 1 }
}

if ($fail) { exit 1 }
Write-Output "===== 全部完成。各线报告：pipelines/<line>/reports/model_metrics.md（+ figs/ 图表）"
Write-Output "===== 下一步：与 expert 基线（pipelines/expert/reports/model_metrics.md）并排做跨线对比"
