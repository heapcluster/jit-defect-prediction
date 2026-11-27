import {
  fetchCleanOutput,
  fetchCollectOutput,
  fetchEvaluateOutput,
  fetchExplainOutput,
  fetchPredictOutput,
  fetchTrainOutput,
  getJobs
} from '../api'
import { saveBlob } from './download'

const FETCHERS = {
  collect: fetchCollectOutput,
  clean: fetchCleanOutput,
  train: fetchTrainOutput,
  predict_batch: fetchPredictOutput,
  evaluate: fetchEvaluateOutput,
  explain: fetchExplainOutput
}

const KIND_LABELS = {
  collect: '数据收集',
  clean: '数据清洗',
  train: '模型训练',
  predict_batch: '模型预测',
  evaluate: '预测评估',
  explain: '结果解释'
}

const STATUS_LABELS = {
  queued: '排队中',
  running: '运行中',
  success: '成功',
  failed: '失败',
  cancelled: '已取消'
}

function shortId(jobId) {
  const value = String(jobId || '')
  return value.length > 8 ? value.slice(-8) : value
}

function artifactValue(kind, jobId, name) {
  return `${kind}::${jobId}::${name}`
}

function companionName(name) {
  return String(name || '').replace(/\.(csv|xlsx)$/i, '.manifest.json')
}

function jobLabel(job) {
  const summary = job.output_ref_json?.summary || {}
  const models = job.output_ref_json?.models || []
  switch (job.kind) {
    case 'collect':
      return summary.total_rows != null ? `收集结果（${summary.total_rows} 条）` : '收集结果'
    case 'clean':
      return summary.output_rows != null ? `清洗结果（${summary.output_rows} 条）` : '清洗结果'
    case 'train':
      return models.length
        ? `训练结果（${models.length} 个模型）`
        : '训练结果'
    case 'predict_batch':
      return summary.input_rows != null ? `预测结果（${summary.input_rows} 条）` : '预测结果'
    case 'evaluate':
      return summary.rows != null ? `评估结果（${summary.rows} 条）` : '评估结果'
    case 'explain':
      return summary.input_rows != null ? `解释结果（${summary.input_rows} 条）` : '解释结果'
    default:
      return '处理结果'
  }
}

function jobSummary(job) {
  const summary = job.output_ref_json?.summary || {}
  switch (job.kind) {
    case 'collect':
      return summary.total_rows != null ? `${summary.total_rows} 条提交` : ''
    case 'clean':
      return summary.output_rows != null
        ? `${summary.input_rows ?? '-'} → ${summary.output_rows} 条`
        : ''
    case 'train': {
      const models = job.output_ref_json?.models || []
      if (!models.length) return ''
      return `${models.filter(item => item.status === 'success').length} / ${models.length} 个模型成功`
    }
    case 'predict_batch':
      return summary.success_count != null ? `${summary.success_count} / ${summary.input_rows ?? '-'} 条成功` : ''
    case 'evaluate':
      return summary.rows != null ? `${summary.rows} 条样本` : ''
    case 'explain':
      return summary.success_count != null ? `${summary.success_count} 条成功` : ''
    default:
      return ''
  }
}

function metric(label, value) {
  return { label, value: value == null || value === '' ? '—' : value }
}

function jobMetrics(kind, job) {
  const summary = job.output_ref_json?.summary || {}
  const models = job.output_ref_json?.models || []
  switch (kind) {
    case 'collect':
      return [metric('采集行数', summary.total_rows ?? summary.rows), metric('正样本', summary.positive_rows),
        metric('负样本', summary.negative_rows), metric('未标注', summary.unlabeled_rows)]
    case 'clean':
      return [metric('输入行数', summary.input_rows), metric('输出行数', summary.output_rows),
        metric('未标注', summary.label_dist?.unlabeled), metric('启用步骤', Array.isArray(summary.enabled_steps) ? summary.enabled_steps.length : null)]
    case 'train':
      return [metric('训练行数', summary.train_rows), metric('测试行数', summary.test_rows),
        metric('成功模型', summary.success_count), metric('失败模型', summary.failed_count)]
    case 'predict_batch':
      return [metric('输入行数', summary.input_rows), metric('预测成功', summary.success_count),
        metric('预测失败', summary.failed_count), metric('判定阈值', summary.decision_threshold)]
    case 'evaluate':
      return [metric('样本行数', summary.rows),
        metric('模型数', Array.isArray(summary.models) ? summary.models.length : models.length || null),
        metric('主指标', summary.primary_metric), metric('判定阈值', summary.threshold)]
    case 'explain':
      return [metric('输入行数', summary.input_rows), metric('解释成功', summary.success_count),
        metric('缓存命中', summary.cache_hits)]
    default:
      return []
  }
}

function jobMeta(kind, job) {
  const summary = job.output_ref_json?.summary || {}
  const config = job.params_json?.config || {}
  const steps = Array.isArray(config.steps) ? config.steps : []
  const meta = []
  if (kind === 'clean' && steps.length) meta.push({ label: '启用清洗项', value: `${steps.filter(step => step.enabled).length} 项` })
  if (kind === 'collect' && summary.dataset_name) meta.push({ label: '数据集', value: summary.dataset_name })
  if (kind === 'predict_batch' && summary.model_name) meta.push({ label: '模型', value: summary.model_name })
  if (kind === 'explain' && Array.isArray(summary.techniques) && summary.techniques.length) {
    meta.push({ label: '解释方法', value: summary.techniques.join('、') })
  }
  if (kind === 'evaluate' && summary.primary_metric) meta.push({ label: '主指标', value: summary.primary_metric })
  meta.push({ label: '任务编号', value: shortId(job.job_id) })
  return meta
}

function normalizeJob(job, kind) {
  const outputs = job.output_ref_json?.outputs || job.outputs || []
  const config = job.params_json?.config || {}
  const files = outputs.map(item => {
    const name = String(item?.name || '')
    return {
      name,
      value: artifactValue(kind, job.job_id, name),
      label: `${KIND_LABELS[kind] || '处理'}（${shortId(job.job_id)}）${name}`,
      kind,
      job_id: job.job_id,
      size_bytes: item.size_bytes,
      companions: outputs
        .map(candidate => String(candidate?.name || ''))
        .filter(candidate => candidate === companionName(name))
    }
  })
  return {
    job_id: job.job_id,
    kind,
    models: job.output_ref_json?.models || [],
    label: `${jobLabel(job)}（${shortId(job.job_id)}）`,
    summary: jobSummary(job),
    created_at: job.created_at,
    finished_at: job.finished_at || '',
    status: job.status,
    statusLabel: STATUS_LABELS[job.status] || job.status || '',
    title: typeof config.output_name === 'string' && config.output_name ? config.output_name : jobLabel(job),
    metrics: jobMetrics(kind, job),
    meta: jobMeta(kind, job),
    files
  }
}

export async function loadArtifactJobs(kind, { page = 1, size = 100, status = 'success' } = {}) {
  const data = await getJobs({ kind, status, page, size })
  if (!Array.isArray(data?.items) || typeof data.total !== 'number') throw new Error('任务记录响应不完整')
  return {
    items: data.items.filter(item => item.kind === kind).map(item => normalizeJob(item, kind)),
    total: data.total,
    page: data.page || page
  }
}

export function artifactSources(jobs, extensions = []) {
  const accepted = extensions.map(ext => String(ext).toLowerCase())
  return jobs.flatMap(job => job.files.filter(file => (
    !accepted.length || accepted.some(ext => file.name.toLowerCase().endsWith(ext))
  )))
}

function findFile(jobs, value, extensions = []) {
  const sources = artifactSources(jobs, extensions)
  return sources.find(item => item.value === value) || sources.find(item => artifactValue(item.kind, item.job_id, item.name) === value)
}

export async function materializeArtifact(jobs, value, { extensions = [], includeCompanions = false } = {}) {
  const file = findFile(jobs, value, extensions)
  if (!file) throw new Error('所选文件不存在，请刷新后重试')
  const fetcher = FETCHERS[file.kind]
  if (!fetcher) throw new Error('暂不支持下载该文件')
  const names = [file.name]
  if (includeCompanions) {
    names.push(...file.companions.filter(name => !names.includes(name)))
  }
  const blobs = await Promise.all(names.map(name => fetcher(file.job_id, name)))
  return names.map((name, index) => new File([blobs[index]], name))
}

export async function downloadArtifact(file) {
  const fetcher = FETCHERS[file.kind]
  if (!fetcher) throw new Error('暂不支持下载该文件')
  const blob = await fetcher(file.job_id, file.name)
  saveBlob(blob, file.name)
}
