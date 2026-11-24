<template>
  <section class="explain">
    <p class="hint">
      上传提交 / 清洗表格，按技术库配置解释。无需展示库路径或预先预测；解释产物不写入展示库。
    </p>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <section
      class="panel"
      data-testid="explain-input"
      aria-labelledby="explain-input-title"
    >
      <h2 id="explain-input-title">
        解释输入
      </h2>
      <div class="fields">
        <label for="explain-files">提交 / 清洗表格及可选模型、预测与同名 manifest
          <input
            id="explain-files"
            data-testid="explain-files"
            type="file"
            multiple
            accept=".csv,.xlsx,.zip,.json"
            :disabled="locked"
            @change="selectFiles"
          >
        </label>
        <label for="explain-model">已登记模型（无 ZIP 时使用，必须已加载）
          <select
            id="explain-model"
            v-model="draft.model_name"
            :disabled="locked || modelsLoading"
          >
            <option value="">选择已加载模型，或上传模型 ZIP</option>
            <option
              v-for="model in models"
              :key="model.model_name"
              :value="model.model_name"
              :disabled="model.loaded === false || model.is_loaded === false"
            >{{ model.model_name }} · {{ model.line }}</option>
          </select>
        </label>
        <label for="explain-dataset">数据集（无提交 / 清洗表格时使用）
          <select
            id="explain-dataset"
            v-model="draft.dataset_id"
            :disabled="locked || datasetsLoading"
          >
            <option value="">不使用数据集，可直接上传</option>
            <option
              v-for="item in datasets"
              :key="item.dataset_id"
              :value="item.dataset_id"
            >{{ item.name }}</option>
          </select>
        </label>
        <p class="hint">
          模型 ZIP 可直接在沙箱解释，不自动登记或加载。已登记模型请先在 <router-link to="/predict">
            预测页加载模型
          </router-link>。
        </p>
      </div>
      <p
        v-if="modelsLoading || datasetsLoading"
        role="status"
        class="hint"
      >
        读取模型 / 数据集元数据…
      </p>
      <div
        v-if="modelsError || datasetsError"
        class="actions"
      >
        <p class="hint">
          {{ modelsError || datasetsError }}
        </p>
        <el-button
          data-testid="explain-retry-inputs"
          :disabled="locked"
          @click="loadInputs"
        >
          重试输入元数据
        </el-button>
      </div>
      <ul
        v-if="files.length"
        class="file-list mono"
      >
        <li
          v-for="file in files"
          :key="file.name"
        >
          {{ file.name }} · {{ file.size }} bytes
        </li>
      </ul>
      <el-button
        v-if="files.length"
        size="small"
        :disabled="locked"
        @click="files = []"
      >
        移除文件
      </el-button>
      <div class="fields">
        <label for="explain-source-artifact">训练 / 收集 / 清洗 / 批量预测产物库
          <select
            id="explain-source-artifact"
            v-model="selectedArtifact"
            :disabled="locked || sourcesLoading"
          >
            <option value="">{{ sources.length ? '选择已登记文件' : '暂无产物，可直接上传' }}</option>
            <option
              v-for="source in sources"
              :key="source.value"
              :value="source.value"
            >{{ source.kind }} · {{ source.name }} · {{ source.job_id }}</option>
          </select>
        </label>
        <div class="actions">
          <el-button
            data-testid="explain-use-artifact"
            :disabled="!selectedArtifact || locked || sourcesLoading"
            @click="useArtifact"
          >
            使用文件及已登记 manifest
          </el-button>
          <el-button
            data-testid="explain-retry-sources"
            :disabled="locked || sourcesLoading"
            @click="loadSources"
          >
            刷新 / 重试来源
          </el-button>
        </div>
      </div>
      <p
        v-if="sourcesLoading"
        class="hint"
        role="status"
      >
        读取来源任务…
      </p>
      <p
        v-if="sourcesError"
        data-testid="explain-source-error"
        class="hint"
        role="alert"
      >
        {{ sourcesError }}
      </p>
    </section>

    <section
      class="panel"
      aria-labelledby="explain-techniques-title"
    >
      <h2 id="explain-techniques-title">
        解释技术与参数
      </h2>
      <el-skeleton
        v-if="metadataLoading"
        :rows="3"
        animated
      />
      <div
        v-if="metadataError"
        class="actions"
      >
        <p role="alert">
          {{ metadataError }}
        </p>
        <el-button
          data-testid="explain-retry-metadata"
          :disabled="locked || metadataLoading"
          @click="loadMetadata"
        >
          重试技术库
        </el-button>
      </div>
      <div class="actions">
        <label
          class="checkbox"
          for="explain-compare"
        ><input
          id="explain-compare"
          v-model="compare"
          type="checkbox"
          :disabled="locked || !compareEnabled || !metadataReady"
          @change="limitSelection"
        >双技术比较（最多两项）</label>
        <el-button
          v-if="metadataReady && !compareEnabled"
          data-testid="explain-enable-compare"
          :disabled="locked"
          @click="enableComparison"
        >
          启用比较配置
        </el-button>
      </div>
      <p
        v-if="metadataReady && !compareEnabled"
        class="hint"
      >
        服务端 explain.compare_enabled 未启用，仅可运行单技术；启用按钮会显式保存配置。
      </p>
      <ul class="techniques">
        <li
          v-for="technique in techniques"
          :key="technique.key"
          data-testid="explain-technique"
        >
          <label
            class="checkbox"
            :for="`explain-technique-${technique.key}`"
          >
            <input
              :id="`explain-technique-${technique.key}`"
              type="checkbox"
              :checked="selected.includes(technique.key)"
              :disabled="locked || (compare && selected.length >= 2 && !selected.includes(technique.key))"
              @change="toggleTechnique(technique.key, $event.target.checked)"
            >{{ technique.name }} <code>{{ technique.key }}</code>
          </label>
          <p class="hint">
            {{ technique.description }}
          </p>
          <div
            v-if="selected.includes(technique.key)"
            class="fields parameters"
          >
            <label
              v-for="param in technique.params_schema || []"
              :key="param.name"
              :for="`explain-param-${technique.key}-${param.name}`"
            >{{ param.description || param.name }} <code>{{ param.name }}</code>
              <select
                v-if="param.choices?.length"
                :id="`explain-param-${technique.key}-${param.name}`"
                v-model="params[technique.key][param.name]"
                :disabled="locked"
              >
                <option
                  v-for="choice in param.choices"
                  :key="String(choice)"
                  :value="choice"
                >{{ choice }}</option>
              </select>
              <input
                v-else-if="isBoolean(param)"
                :id="`explain-param-${technique.key}-${param.name}`"
                v-model="params[technique.key][param.name]"
                type="checkbox"
                :disabled="locked"
              >
              <input
                v-else
                :id="`explain-param-${technique.key}-${param.name}`"
                v-model="params[technique.key][param.name]"
                :type="isNumber(param) ? 'number' : 'text'"
                :min="param.min"
                :max="param.max"
                :step="isInteger(param) ? 1 : 'any'"
                :disabled="locked"
              >
            </label>
          </div>
        </li>
      </ul>
      <details v-if="compatibility.length">
        <summary>模型家族兼容性（技术库元数据）</summary>
        <ul class="hint">
          <li
            v-for="(item, index) in compatibility"
            :key="index"
          >
            {{ item.family }} · {{ item.technique }} · {{ item.supported ? '支持' : '不支持' }} {{ item.reason_code }}
          </li>
        </ul>
      </details>
      <div class="fields">
        <label for="explain-top-n">Top N<input
          id="explain-top-n"
          v-model="draft.top_n"
          type="number"
          min="1"
          step="1"
          :disabled="locked"
        ></label>
        <label for="explain-format">输出格式<select
          id="explain-format"
          v-model="draft.format"
          :disabled="locked"
        ><option value="csv">CSV</option><option value="xlsx">XLSX</option></select></label>
        <label for="explain-cache-ttl">缓存 TTL（秒，可选）<input
          id="explain-cache-ttl"
          v-model="draft.cache_ttl"
          type="number"
          min="0"
          step="1"
          :disabled="locked"
        ></label>
        <label for="explain-commit-hashes">提交 hash 筛选（可选，逗号 / 换行分隔）<textarea
          id="explain-commit-hashes"
          v-model="draft.commit_hashes"
          rows="2"
          :disabled="locked"
        /></label>
        <label for="explain-default">保存默认技术<select
          id="explain-default"
          v-model="defaultTechnique"
          :disabled="locked || !metadataReady"
        ><option value="">选择技术</option><option
          v-for="technique in techniques"
          :key="technique.key"
          :value="technique.key"
        >{{ technique.name }}</option></select></label>
        <div class="actions">
          <el-button
            id="explain-save-default"
            data-testid="explain-save-default"
            :disabled="locked || !metadataReady || !defaultTechnique"
            @click="saveDefault"
          >
            保存默认技术
          </el-button><span class="hint">{{ configMessage }}</span>
        </div>
      </div>
      <div class="actions">
        <el-button
          id="explain-run"
          data-testid="explain-run"
          type="primary"
          :loading="busy"
          :disabled="locked || !canRun"
          @click="submit"
        >
          运行解释
        </el-button><span class="hint">不自动导入、训练或预测</span>
      </div>
    </section>

    <section
      class="panel"
      aria-labelledby="explain-job-title"
    >
      <h2 id="explain-job-title">
        解释任务
      </h2>
      <p
        v-if="restoring"
        class="hint"
        role="status"
      >
        恢复最近的 explain 任务…
      </p>
      <p
        v-else-if="!job"
        class="hint"
      >
        暂无解释任务，可在空展示库中直接上传运行。
      </p>
      <p
        v-if="job"
        class="mono"
        role="status"
      >
        {{ job.job_id }} · {{ job.status }} · {{ job.done ?? 0 }} / {{ job.total ?? 0 }} · retry {{ job.retry_count ?? 0 }}
      </p>
      <el-progress
        v-if="running"
        :percentage="percentage"
      />
      <p
        v-if="job?.error_log"
        class="hint"
      >
        {{ job.error_log }}
      </p>
      <div class="actions">
        <el-button
          data-testid="explain-refresh-job"
          :disabled="busy || auth || refreshing || restoring"
          @click="job ? refreshJob() : restoreJob()"
        >
          刷新 / 恢复任务
        </el-button>
        <el-button
          v-if="job?.status === 'failed'"
          data-testid="explain-retry"
          :disabled="busy || auth"
          @click="retry"
        >
          重试原任务
        </el-button>
        <el-button
          v-if="running"
          data-testid="explain-cancel"
          :disabled="busy || auth"
          @click="cancel"
        >
          取消任务
        </el-button>
      </div>
    </section>

    <section
      v-if="job?.status === 'success'"
      class="panel"
      aria-labelledby="explain-result-title"
    >
      <h2 id="explain-result-title">
        解释结果
      </h2>
      <p
        v-if="outputLoading"
        class="hint"
        role="status"
      >
        读取已登记比较数据与贡献图…
      </p>
      <div
        v-if="outputError"
        class="actions"
      >
        <p role="alert">
          {{ outputError }}
        </p><el-button
          data-testid="explain-retry-output"
          :disabled="busy || auth || outputLoading"
          @click="loadOutputs"
        >
          重试产物
        </el-button>
      </div>
      <p
        v-if="summary"
        data-testid="explain-summary"
        class="mono"
      >
        输入 {{ summary.input_rows }} × {{ summary.techniques?.length ?? 0 }} 技术 · 成功解释 {{ summary.success_count }}（提交 × 技术，非输入行数）· 缓存命中 {{ summary.cache_hits ?? 0 }}
      </p>
      <ul
        v-if="summary"
        class="hint"
      >
        <li
          v-for="(count, reason) in summary.reason_counts || {}"
          :key="reason"
        >
          {{ reason }} · {{ count }}
        </li>
      </ul>
      <p
        v-if="comparison && !comparison.rows.length"
        class="hint"
      >
        暂无可解释贡献，请查看原因及任务产物。
      </p>
      <div
        v-if="comparison"
        data-testid="explain-comparison"
      >
        <p class="hint">
          SHAP 线性模型：log_odds；树模型：tree_raw。LIME：local_probability_coefficient，局部概率系数，非精确加性；不同输出空间的贡献不可直接相加或比较绝对大小。
        </p>
        <div class="comparison-grid">
          <article
            v-for="result in firstComparison"
            :key="result.technique"
            class="comparison-card"
            data-testid="explain-comparison-technique"
          >
            <h3>{{ result.technique }} <code>{{ result.commit_hash }}</code></h3>
            <p class="mono">
              output_space: {{ result.output_space || '未提供' }} · base_value: {{ signed(result.base_value) || '未提供' }}
            </p>
            <p
              v-if="result.reason_code || result.message"
              class="hint"
            >
              {{ result.reason_code }} {{ result.message }}
            </p>
            <div
              class="table-scroll"
              tabindex="0"
              :aria-label="`${result.technique} 贡献表`"
            >
              <table>
                <thead><tr><th>特征</th><th>原值</th><th>有符号贡献（0 轴）</th><th>方向</th><th>排名</th></tr></thead>
                <tbody>
                  <tr
                    v-for="(item, index) in result.items || []"
                    :key="index"
                  >
                    <td>{{ item.feature }}</td><td>{{ item.raw_value ?? '' }}</td><td>
                      <div class="bar-track">
                        <span
                          v-if="numeric(item.contribution)"
                          class="contribution-bar"
                          :class="direction(item)"
                          :style="barStyle(item, result.items)"
                        />
                      </div><span class="mono">{{ signed(item.contribution) }}</span>
                    </td><td>{{ item.direction }}</td><td>{{ item.rank ?? '' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>
        <h3>前 20 行（完整数据见下载）</h3>
        <div
          class="table-scroll"
          tabindex="0"
          aria-label="解释结果前二十行"
        >
          <table>
            <thead><tr><th>提交</th><th>模型</th><th>技术</th><th>特征</th><th>原值</th><th>有符号贡献</th><th>方向</th><th>排名</th><th>标签</th><th>模型版本</th><th>特征版本</th><th>原因</th></tr></thead>
            <tbody>
              <tr
                v-for="(row, index) in comparison.rows.slice(0, 20)"
                :key="index"
                data-testid="explain-row"
              >
                <td>{{ row.commit_hash }}</td><td>{{ row.model_name }}</td><td>{{ row.technique }}</td><td data-testid="explain-feature">
                  {{ row.reason_code ? '' : row.feature ?? '' }}
                </td><td>{{ row.reason_code ? '' : row.raw_value ?? '' }}</td><td data-testid="explain-contribution">
                  {{ row.reason_code ? '' : signed(row.contribution) }}
                </td><td>{{ row.direction }}</td><td>{{ row.rank ?? '' }}</td><td>{{ row.label ?? '' }}</td><td>{{ row.model_version }}</td><td>{{ row.feature_version }}</td><td>{{ row.reason_code }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <ul class="hint">
          <li
            v-for="(result, index) in warnings"
            :key="index"
          >
            {{ result.commit_hash }} · {{ result.technique }} · {{ result.reason_code }} {{ result.message }}
          </li>
        </ul>
      </div>
      <figure
        v-for="image in images"
        :key="image.name"
        data-testid="explain-figure"
      >
        <img
          :src="image.url"
          alt="以零为中心的有符号特征贡献图"
        ><figcaption class="mono">
          {{ image.name }}
        </figcaption>
      </figure>
      <h3>已登记产物</h3>
      <ul
        class="output-list"
        data-testid="explain-output-list"
      >
        <li
          v-for="output in registeredOutputs"
          :key="output.name"
        >
          <div class="mono">
            {{ output.name }}<code>SHA256 {{ output.sha256 || output.sha || '未提供' }} · {{ output.size_bytes ?? output.size ?? '未提供' }} bytes</code>
          </div><el-button
            size="small"
            :data-testid="`explain-download-${output.name}`"
            :disabled="busy || auth || downloading"
            @click="download(output.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
    </section>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { getExplainTechniques, runExplain, fetchExplainOutput, getModels, getDatasets, getJobs, getJob, retryJob, cancelJob, putConfigKey, fetchTrainOutput, fetchCollectOutput, fetchCleanOutput, fetchPredictOutput } from '../api'
import { configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'ExplainView' })

const files = ref([]), models = ref([]), datasets = ref([]), sources = ref([]), selectedArtifact = ref('')
const techniques = ref([]), compatibility = ref([]), selected = ref([]), params = reactive({})
const compare = ref(false), compareEnabled = ref(false), defaultTechnique = ref(''), configMessage = ref('')
const metadataReady = ref(false), metadataLoading = ref(false), modelsLoading = ref(false), datasetsLoading = ref(false), sourcesLoading = ref(false)
const metadataError = ref(''), modelsError = ref(''), datasetsError = ref(''), sourcesError = ref(''), error = ref('')
const busy = ref(false), auth = ref(false), job = ref(null), restoring = ref(false), refreshing = ref(false)
const outputLoading = ref(false), outputError = ref(''), comparison = ref(null), images = ref([]), downloading = ref(false)
const draft = reactive({ model_name: '', dataset_id: '', top_n: 8, format: 'csv', cache_ttl: '', commit_hashes: '' })
let mounted = true, timer, epoch = 0, outputJob = '', refreshToken = 0, restoreToken = 0
const running = computed(() => ['queued', 'running'].includes(job.value?.status))
const locked = computed(() => busy.value || auth.value || running.value)
const registeredOutputs = computed(() => (job.value?.output_ref_json?.outputs || job.value?.outputs || []).filter(item => typeof item?.name === 'string'))
const summary = computed(() => comparison.value?.summary || job.value?.output_ref_json?.summary || job.value?.summary)
const percentage = computed(() => job.value?.total ? Math.max(0, Math.min(100, Math.floor((job.value.done || 0) / job.value.total * 100))) : 0)
const hasModel = computed(() => files.value.some(file => role(file.name) === 'model') || models.value.some(model => model.model_name === draft.model_name && model.loaded !== false && model.is_loaded !== false))
const hasTable = computed(() => files.value.some(file => role(file.name) === 'features') || datasets.value.some(item => item.dataset_id === draft.dataset_id))
const canRun = computed(() => metadataReady.value && selected.value.length > 0 && selected.value.length <= (compare.value && compareEnabled.value ? 2 : 1) && selected.value.every(key => techniques.value.some(item => item.key === key)) && hasModel.value && hasTable.value)
const firstComparison = computed(() => {
  const results = comparison.value?.results || [], hash = results[0]?.commit_hash
  return results.filter(result => result.commit_hash === hash).slice(0, 2)
})
const warnings = computed(() => (comparison.value?.results || []).filter(result => result.reason_code || result.message))
const isInteger = param => ['int', 'integer'].includes(param.type)
const isNumber = param => isInteger(param) || ['float', 'number'].includes(param.type)
const isBoolean = param => ['bool', 'boolean'].includes(param.type)
const numeric = value => typeof value === 'number' && Number.isFinite(value)
const signed = value => numeric(value) ? `${value > 0 ? '+' : ''}${value.toFixed(6)}` : ''
function direction(item) { return !numeric(item.contribution) || item.contribution === 0 ? 'neutral' : item.contribution > 0 ? 'increase' : 'decrease' }
function barStyle(item, items) {
  const max = Math.max(...items.filter(entry => numeric(entry.contribution)).map(entry => Math.abs(entry.contribution)), 0)
  const width = max ? Math.abs(item.contribution) / max * 50 : 0
  return { width: `${width}%`, left: `${item.contribution < 0 ? 50 - width : 50}%` }
}
function message(err) {
  if (err.code === 40100 || err.response?.status === 401) { auth.value = true; clearTimeout(timer); return '鉴权失败，请检查部署环境中的 API Key' }
  return err.code === 50000 ? '解释服务异常，请稍后重试' : err.detail || err.message || '请求失败，请重试'
}
function role(name) {
  if (/\.zip$/i.test(name)) return 'model'
  if (/\.(csv|xlsx)$/i.test(name)) return /predict(?:ion|ions|_)/i.test(name) ? 'predictions' : 'features'
  return 'manifest'
}
const manifestName = name => name.replace(/\.[^.]+$/, '.manifest.json')
function mergeFiles(incoming) {
  const all = [...files.value, ...incoming], lastRole = new Map()
  for (const file of all) if (role(file.name) !== 'manifest') lastRole.set(role(file.name), file)
  const kept = new Set(lastRole.values()), companions = new Set([...kept].map(file => manifestName(file.name)))
  const manifests = new Map()
  for (const file of all) if (role(file.name) === 'manifest' && companions.has(file.name)) manifests.set(file.name, file)
  files.value = all.filter(file => kept.has(file) || manifests.get(file.name) === file)
}
function selectFiles(event) {
  if (locked.value) return
  const incoming = Array.from(event.target.files || [])
  event.target.value = ''
  if (incoming.some(file => !/\.(csv|xlsx|zip|json)$/i.test(file.name))) { error.value = '仅接受 CSV / XLSX / ZIP / JSON 文件'; return }
  mergeFiles(incoming)
}
function toggleTechnique(key, checked) {
  if (locked.value) return
  if (!checked) selected.value = selected.value.filter(item => item !== key)
  else if (!compare.value || !compareEnabled.value) selected.value = [key]
  else if (!selected.value.includes(key) && selected.value.length < 2) selected.value.push(key)
}
function limitSelection() { if (!compare.value || !compareEnabled.value) selected.value = selected.value.slice(0, 1) }
async function loadMetadata() {
  if (auth.value || metadataLoading.value) return
  metadataLoading.value = true; metadataError.value = ''; metadataReady.value = false
  try {
    const data = await getExplainTechniques({})
    if (!mounted || auth.value) return
    if (!Array.isArray(data?.techniques) || typeof data.compare_enabled !== 'boolean' || data.techniques.some(item => !item.key || !Array.isArray(item.params_schema))) throw new Error('技术库响应不完整，请重试')
    techniques.value = data.techniques; compatibility.value = data.compatibility || []; compareEnabled.value = data.compare_enabled
    for (const item of data.techniques) {
      params[item.key] = { ...Object.fromEntries(item.params_schema.map(param => [param.name, param.default])), ...(params[item.key] || {}) }
    }
    const saved = configuration.items.find(item => item.config_key === 'default_xai')?.value
    const initial = data.techniques.some(item => item.key === saved) ? saved : data.default_technique
    selected.value = selected.value.filter(key => data.techniques.some(item => item.key === key))
    if (!selected.value.length && data.techniques.some(item => item.key === initial)) selected.value = [initial]
    if (!data.techniques.some(item => item.key === defaultTechnique.value)) defaultTechnique.value = initial || ''
    if (!compareEnabled.value) compare.value = false
    limitSelection(); metadataReady.value = true
  } catch (err) { if (mounted) { metadataError.value = message(err); techniques.value = []; compareEnabled.value = false } }
  finally { if (mounted) metadataLoading.value = false }
}
async function loadInputs() {
  if (auth.value || modelsLoading.value || datasetsLoading.value) return
  modelsLoading.value = true; datasetsLoading.value = true; modelsError.value = ''; datasetsError.value = ''
  await Promise.all([
    getModels().then(data => {
      if (!mounted || auth.value) return
      if (!Array.isArray(data?.lines)) throw new Error('模型库响应不完整')
      models.value = data.lines.flatMap(line => (line.models || []).map(model => typeof model === 'string' ? { model_name: model, line: line.line } : { ...model, line: line.line }))
    }).catch(err => { if (mounted) modelsError.value = message(err) }).finally(() => { if (mounted) modelsLoading.value = false }),
    getDatasets({ size: 100, status: 'ready' }).then(data => {
      if (!mounted || auth.value) return
      if (!Array.isArray(data?.items)) throw new Error('数据集响应不完整')
      datasets.value = data.items
    }).catch(err => { if (mounted) datasetsError.value = message(err) }).finally(() => { if (mounted) datasetsLoading.value = false })
  ])
}
async function loadSources() {
  if (auth.value || sourcesLoading.value) return
  sourcesLoading.value = true; sourcesError.value = ''
  try {
    const kinds = ['train', 'collect', 'clean', 'predict_batch']
    const responses = await Promise.all(kinds.map(kind => getJobs({ kind, status: 'success', size: 100 })))
    if (!mounted || auth.value) return
    if (responses.some(data => !Array.isArray(data?.items))) throw new Error('来源任务响应不完整')
    sources.value = responses.flatMap((data, index) => data.items.filter(item => item.kind === kinds[index]).flatMap(item => {
      const outputs = item.output_ref_json?.outputs || item.outputs || []
      return outputs.filter(output => /\.(csv|xlsx|zip)$/i.test(output.name || '') && (item.kind !== 'train' || /\.zip$/i.test(output.name))).map(output => ({ ...output, kind: item.kind, job_id: item.job_id, value: `${item.kind}/${item.job_id}/${output.name}`, companions: outputs.filter(candidate => candidate.name === manifestName(output.name)) }))
    }))
  } catch (err) { if (mounted) sourcesError.value = message(err) }
  finally { if (mounted) sourcesLoading.value = false }
}
async function useArtifact() {
  if (locked.value) return
  const source = sources.value.find(item => item.value === selectedArtifact.value)
  if (!source) return
  busy.value = true; error.value = ''
  try {
    const fetcher = { train: fetchTrainOutput, collect: fetchCollectOutput, clean: fetchCleanOutput, predict_batch: fetchPredictOutput }[source.kind]
    const staged = await Promise.all([source, ...source.companions].map(async output => new File([await fetcher(source.job_id, output.name)], output.name)))
    if (mounted && !auth.value) mergeFiles(staged)
  } catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) busy.value = false }
}
async function saveDefault() {
  if (locked.value || !metadataReady.value || !techniques.value.some(item => item.key === defaultTechnique.value)) return
  busy.value = true; configMessage.value = ''
  try { await putConfigKey('default_xai', defaultTechnique.value); await loadConfiguration(); if (mounted) configMessage.value = '默认技术已保存；未启动任务' }
  catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) busy.value = false }
}
async function enableComparison() {
  if (locked.value || !metadataReady.value) return
  busy.value = true
  try { await putConfigKey('explain.compare_enabled', true); if (mounted && !auth.value) await loadMetadata() }
  catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) busy.value = false }
}
function normalize(param, value) {
  if (value == null || value === '') return undefined
  if (isNumber(param)) {
    const number = Number(value)
    if (!Number.isFinite(number) || (isInteger(param) && !Number.isInteger(number)) || (param.min != null && number < param.min) || (param.max != null && number > param.max)) throw new Error(`${param.name} 必须符合技术库数值范围${isInteger(param) ? '，且为整数' : ''}`)
    value = number
  } else if (isBoolean(param)) value = value === true || value === 'true'
  if (param.choices?.length && !param.choices.includes(value)) throw new Error(`${param.name} 必须选择技术库列出的值`)
  return value
}
function snapshot() {
  const config = { techniques: [...selected.value], params: {}, top_n: normalize({ name: 'top_n', type: 'int', min: 1 }, draft.top_n), format: draft.format }
  if (config.top_n == null) throw new Error('top_n 不能为空')
  for (const key of selected.value) {
    config.params[key] = {}
    for (const param of techniques.value.find(item => item.key === key).params_schema) {
      const value = normalize(param, params[key][param.name])
      if (value !== undefined) config.params[key][param.name] = value
    }
  }
  if (draft.cache_ttl !== '') config.cache_ttl = normalize({ name: 'cache_ttl', type: 'int', min: 0 }, draft.cache_ttl)
  const hashes = [...new Set(draft.commit_hashes.split(/[\s,]+/).filter(Boolean))]
  if (hashes.length) config.commit_hashes = hashes
  if (!files.value.some(file => role(file.name) === 'model')) config.model_name = draft.model_name
  if (!files.value.some(file => role(file.name) === 'features')) config.dataset_id = draft.dataset_id
  return config
}
function resetOutputs() {
  epoch++; refreshToken++; clearTimeout(timer); refreshing.value = false; outputJob = ''; outputLoading.value = false; outputError.value = ''; comparison.value = null
  for (const image of images.value) URL.revokeObjectURL(image.url)
  images.value = []
}
function validJob(data) { return data?.job_id && data.kind === 'explain' && ['queued', 'running', 'success', 'failed', 'cancelled'].includes(data.status) }
async function submit() {
  if (locked.value || !canRun.value) return
  busy.value = true; error.value = ''
  try {
    const config = snapshot()
    resetOutputs(); restoreToken++
    const ownEpoch = epoch
    const accepted = await runExplain(config, files.value)
    if (!mounted || auth.value || ownEpoch !== epoch) return
    if (!accepted?.job_id || !['queued', 'running', 'success', 'failed'].includes(accepted.status)) throw new Error('解释任务响应不完整')
    job.value = { ...accepted, kind: 'explain' }
    await refreshJob()
  } catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) busy.value = false }
}
async function blobJSON(blob) {
  const text = typeof blob.text === 'function' ? await blob.text() : await new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(new Error('解释比较文件读取失败')); reader.readAsText(blob)
  })
  return JSON.parse(text)
}
async function loadOutputs() {
  if (!mounted || auth.value || outputLoading.value || job.value?.status !== 'success' || outputJob === job.value.job_id) return
  const id = job.value.job_id, ownEpoch = epoch, outputs = [...registeredOutputs.value]
  outputLoading.value = true; outputError.value = ''
  try {
    const comparisonOutput = outputs.find(item => item.name === `explain_comparison_${id}.json`)
    if (!comparisonOutput) throw new Error('任务未登记解释比较 JSON，请刷新任务')
    const figures = outputs.filter(item => item.name === `explain_contributions_${id}.png`)
    const [data, staged] = await Promise.all([
      fetchExplainOutput(id, comparisonOutput.name).then(blobJSON),
      Promise.all(figures.map(async item => ({ name: item.name, blob: await fetchExplainOutput(id, item.name) })))
    ])
    if (!mounted || auth.value || ownEpoch !== epoch || job.value?.job_id !== id) return
    if (!Array.isArray(data?.rows) || !Array.isArray(data?.results) || !data?.summary) throw new Error('解释比较文件结构不完整')
    const nextImages = []
    try { for (const item of staged) nextImages.push({ name: item.name, url: URL.createObjectURL(item.blob) }) }
    catch (err) { for (const image of nextImages) URL.revokeObjectURL(image.url); throw err }
    for (const image of images.value) URL.revokeObjectURL(image.url)
    images.value = nextImages; comparison.value = data; outputJob = id
  } catch (err) { if (mounted && ownEpoch === epoch && job.value?.job_id === id) outputError.value = message(err) }
  finally { if (mounted && ownEpoch === epoch) outputLoading.value = false }
}
async function refreshJob() {
  if (!mounted || auth.value || refreshing.value || !job.value?.job_id) return
  clearTimeout(timer); refreshing.value = true
  const id = job.value.job_id, ownEpoch = epoch, token = ++refreshToken
  try {
    const data = await getJob(id)
    if (!mounted || auth.value || token !== refreshToken || ownEpoch !== epoch || job.value?.job_id !== id) return
    if (!validJob(data) || data.job_id !== id) throw new Error('解释任务响应不完整或任务类型不匹配')
    job.value = data; error.value = ''
    if (data.status === 'success') void loadOutputs()
  } catch (err) { if (mounted && token === refreshToken && ownEpoch === epoch) error.value = message(err) }
  finally {
    if (mounted && token === refreshToken && ownEpoch === epoch) {
      refreshing.value = false
      if (!auth.value && running.value) timer = setTimeout(refreshJob, 1500)
    }
  }
}
async function restoreJob() {
  if (!mounted || auth.value || restoring.value || job.value) return
  restoring.value = true
  const token = ++restoreToken, ownEpoch = epoch
  try {
    const data = await getJobs({ kind: 'explain', size: 1 })
    if (!mounted || auth.value || token !== restoreToken || ownEpoch !== epoch || job.value) return
    if (!Array.isArray(data?.items)) throw new Error('解释历史响应不完整')
    const latest = data.items.find(validJob)
    if (latest) { job.value = latest; await refreshJob() }
  } catch (err) { if (mounted && token === restoreToken) error.value = message(err) }
  finally { if (mounted) restoring.value = false }
}
async function retry() {
  if (busy.value || auth.value || job.value?.status !== 'failed') return
  busy.value = true; error.value = ''
  const id = job.value.job_id
  resetOutputs(); restoreToken++
  const ownEpoch = epoch
  try {
    const data = await retryJob(id)
    if (!mounted || auth.value || ownEpoch !== epoch || job.value?.job_id !== id) return
    if (data?.job_id !== id || !['queued', 'running', 'success', 'failed'].includes(data.status)) throw new Error('重试任务响应不完整')
    job.value = { ...job.value, ...data }; await refreshJob()
  } catch (err) { if (mounted && ownEpoch === epoch) error.value = message(err) }
  finally { if (mounted) busy.value = false }
}
async function cancel() {
  if (busy.value || auth.value || !running.value) return
  busy.value = true; error.value = ''
  const id = job.value.job_id
  resetOutputs(); restoreToken++
  const ownEpoch = epoch
  try {
    const data = await cancelJob(id)
    if (!mounted || auth.value || ownEpoch !== epoch || job.value?.job_id !== id) return
    if (data?.job_id !== id || data.status !== 'cancelled') throw new Error('取消任务响应不完整')
    job.value = { ...job.value, ...data }
  } catch (err) { if (mounted && ownEpoch === epoch) { error.value = message(err); if (!auth.value) void refreshJob() } }
  finally { if (mounted) busy.value = false }
}
async function download(name) {
  if (busy.value || auth.value || downloading.value || !registeredOutputs.value.some(item => item.name === name)) return
  downloading.value = true
  const id = job.value.job_id, ownEpoch = epoch
  try {
    const blob = await fetchExplainOutput(id, name)
    if (!mounted || auth.value || ownEpoch !== epoch || job.value?.job_id !== id) return
    const url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { if (mounted && ownEpoch === epoch) error.value = message(err) }
  finally { if (mounted) downloading.value = false }
}
onMounted(() => { void loadMetadata(); void loadInputs(); void loadSources(); void restoreJob() })
onUnmounted(() => { mounted = false; restoreToken++; resetOutputs() })
</script>

<style scoped>
.explain { min-width: 0; max-width: 100%; font-family: var(--el-font-family), sans-serif; color: var(--el-text-color-primary); }
.panel { min-width: 0; border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2 { margin: 0 0 16px; font-size: var(--el-font-size-base); font-family: var(--el-font-family), sans-serif; } h3 { margin: 18px 0 12px; font-size: var(--el-font-size-base); }
.hint { color: var(--el-text-color-secondary); font-size: var(--el-font-size-small); line-height: 1.65; overflow-wrap: anywhere; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label { display: flex; flex-direction: column; gap: 8px; min-width: 0; font-size: var(--el-font-size-base); }
input:not([type="checkbox"]), select, textarea { box-sizing: border-box; width: 100%; min-width: 0; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input[type="checkbox"] { accent-color: var(--el-color-primary); } textarea { resize: vertical; }
input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible, .table-scroll:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; min-width: 0; } .actions .el-button { margin-left: 0; max-width: 100%; white-space: normal; height: auto; min-height: 32px; }
.checkbox { display: inline-flex; align-items: center; gap: 8px; font-size: var(--el-font-size-base); }
.techniques, .output-list { list-style: none; padding: 0; } .techniques > li { padding: 12px 0; border-bottom: 1px solid var(--el-border-color-lighter); min-width: 0; }
summary { cursor: pointer; padding: 10px 0; font-size: var(--el-font-size-small); } .file-list { padding-left: 20px; }
.mono, code, table { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: var(--el-font-size-extra-small); font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.comparison-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.comparison-card { min-width: 0; padding: 12px; border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); }
.comparison-card h3 { margin-top: 0; } .comparison-card code { display: block; margin-top: 6px; }
.table-scroll { min-width: 0; max-width: 100%; overflow-x: auto; } table { width: 100%; border-collapse: collapse; white-space: nowrap; }
th, td { padding: 10px; text-align: left; border: 1px solid var(--el-border-color-light); } th { background: var(--el-fill-color-light); }
.bar-track { position: relative; width: 140px; height: 12px; margin-bottom: 5px; background: var(--el-fill-color-lighter); }
.bar-track::after { content: ''; position: absolute; left: 50%; top: -2px; bottom: -2px; border-left: 1px solid var(--el-text-color-secondary); }
.contribution-bar { position: absolute; top: 0; height: 100%; background: var(--el-text-color-placeholder); }
.contribution-bar.increase { background: var(--el-color-success); } .contribution-bar.decrease { background: var(--el-color-danger); }
figure { min-width: 0; margin: 20px 0; } img { display: block; max-width: 100%; width: 100%; height: auto; } figcaption { color: var(--el-text-color-secondary); }
.output-list li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); min-width: 0; }
.output-list li div { min-width: 0; overflow-wrap: anywhere; } .output-list code { display: block; margin-top: 6px; } .output-list .el-button { flex-shrink: 0; margin-left: 0; }
@media (max-width: 640px) { .fields, .comparison-grid { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .comparison-card { padding: 10px; } }
</style>
