<template>
  <section class="localization">
    <p class="hint">
      定位工具：必须提供预测 CSV / XLSX，可选解释表格及 companion manifest。内容由服务端按 §3.4 识别；不导入展示库，不修改仓库。
    </p>
    <el-alert
      v-if="error || auth"
      :title="auth ? '鉴权失败，请检查部署环境中的 API Key；写入与下载已停用' : error"
      type="error"
      :closable="false"
      show-icon
    />

    <section
      class="panel"
      aria-labelledby="localization-input-title"
    >
      <h2 id="localization-input-title">
        定位输入与范围
      </h2>
      <div class="fields">
        <label for="localization-repo">仓库来源 repo_source<input
          id="localization-repo"
          v-model="draft.repo_source"
          :disabled="locked"
          placeholder="允许根目录内的仓库路径 / 支持的仓库 URL"
        ></label>
        <label for="localization-commit">提交 40 位 hash（可选定位范围；浏览源码必填）<input
          id="localization-commit"
          v-model="draft.commit_hash"
          :disabled="locked"
        ></label>
        <label for="localization-model">模型名（可选过滤，不自动预测）<input
          id="localization-model"
          v-model="draft.model_name"
          :disabled="locked"
        ></label>
        <label for="localization-dataset">数据集（仅补充仓库来源）<select
          id="localization-dataset"
          v-model="draft.dataset_id"
          :disabled="locked || inputsLoading"
          @change="selectDataset"
        ><option value="">不使用数据集</option><option
          v-for="item in datasets"
          :key="item.dataset_id"
          :value="item.dataset_id"
        >{{ item.name || item.dataset_id }}</option></select></label>
        <label
          class="span-all"
          for="localization-files"
        >预测（必需）+ 解释（可选）+ manifest<input
          id="localization-files"
          type="file"
          multiple
          accept=".csv,.xlsx,.json"
          :disabled="locked"
          @change="selectFiles"
        ></label>
      </div>
      <p
        v-if="inputsLoading"
        role="status"
        class="hint"
      >
        读取数据集…
      </p>
      <div
        v-if="inputsError"
        class="actions"
      >
        <p
          role="alert"
          class="hint"
        >
          {{ inputsError }}
        </p><el-button
          :disabled="auth || inputsLoading"
          @click="loadInputs"
        >
          重试数据集
        </el-button>
      </div>
      <p class="hint">
        本地允许根目录（服务端配置）：{{ allowRoots.length ? allowRoots.join(' · ') : metadataReady ? '未配置本地根目录' : '尚未确认' }}
      </p>
      <ul class="file-list mono">
        <li
          v-for="item in files"
          :key="`${item.role}/${item.file.name}`"
        >
          {{ roleLabel(item.role) }} · {{ item.file.name }} · {{ item.file.size }} bytes <el-button
            size="small"
            :disabled="locked"
            @click="removeFile(item)"
          >
            移除
          </el-button>
        </li>
      </ul>
      <div class="fields">
        <label for="localization-source-artifact">预测 / 解释输入产物库<select
          id="localization-source-artifact"
          v-model="selectedArtifact"
          :disabled="locked || artifactsLoading"
        ><option value="">选择已登记 CSV / XLSX</option><option
          v-for="item in artifacts"
          :key="item.value"
          :value="item.value"
        >{{ item.kind }} · {{ item.name }} · {{ item.job_id }}</option></select></label>
        <div class="actions">
          <el-button
            data-testid="localization-use-artifact"
            :disabled="locked || !selectedArtifact || artifactsLoading"
            @click="useArtifact"
          >
            使用文件及已登记 manifest
          </el-button><el-button
            data-testid="localization-retry-artifacts"
            :disabled="auth || artifactsLoading"
            @click="loadArtifacts"
          >
            刷新 / 重试产物库
          </el-button>
        </div>
      </div>
      <p
        v-if="artifactsLoading"
        class="hint"
        role="status"
      >
        读取输入产物库…
      </p>
      <p
        v-if="artifactsError"
        data-testid="localization-artifact-error"
        class="hint"
        role="alert"
      >
        {{ artifactsError }}
      </p>
    </section>

    <section
      class="panel"
      aria-labelledby="localization-config-title"
    >
      <h2 id="localization-config-title">
        定位参数
      </h2>
      <p
        v-if="metadataLoading"
        class="hint"
        role="status"
      >
        读取生效配置…
      </p>
      <div
        v-if="metadataError"
        class="actions"
      >
        <p role="alert">
          {{ metadataError }}
        </p><el-button
          data-testid="localization-retry-metadata"
          :disabled="auth || metadataLoading"
          @click="loadMetadata(true)"
        >
          重试配置元数据
        </el-button>
      </div>
      <div class="fields">
        <label
          class="span-all"
          for="localization-weights"
        >weights（嵌套 JSON，初值来自服务端；允许部分权重覆盖）<textarea
          id="localization-weights"
          v-model="draft.weights"
          class="mono"
          rows="9"
          :disabled="locked || !metadataReady"
        /></label>
        <label for="localization-top-files">Top 文件数<input
          id="localization-top-files"
          v-model="draft.top_files"
          type="number"
          min="1"
          max="1000"
          step="1"
          :disabled="locked || !metadataReady"
        ></label>
        <label for="localization-top-lines">Top 行数<input
          id="localization-top-lines"
          v-model="draft.top_lines"
          type="number"
          min="1"
          max="1000"
          step="1"
          :disabled="locked || !metadataReady"
        ></label>
        <label for="localization-file-size">file_size_max（字节）<input
          id="localization-file-size"
          v-model="draft.file_size_max"
          type="number"
          min="1"
          step="1"
          :disabled="locked || !metadataReady"
        ></label>
        <label for="localization-format">输出格式<select
          id="localization-format"
          v-model="draft.format"
          :disabled="locked"
        ><option value="csv">CSV</option><option value="xlsx">XLSX</option></select></label>
      </div>
      <fieldset :disabled="locked || !metadataReady">
        <legend>建议来源 suggestion_sources</legend><label
          v-for="name in suggestionChoices"
          :key="name"
          class="checkbox"
          :for="`localization-source-${name}`"
        ><input
          :id="`localization-source-${name}`"
          v-model="draft.suggestion_sources"
          type="checkbox"
          :value="name"
        >{{ name }}</label>
      </fieldset>
      <label
        class="checkbox"
        for="localization-patch"
      ><input
        id="localization-patch"
        v-model="draft.patch_preview"
        type="checkbox"
        :disabled="locked"
      >请求 patch_preview（可能没有可靠 diff；不会应用补丁）</label>
      <p class="hint">
        单批最多 20 个预测目标，服务端最多读取 5000 行；结果可能截断。行可疑度是定位启发式评分，不是训练得到的行级概率。
      </p>
      <div class="actions">
        <el-button
          id="localization-run"
          data-testid="localization-run"
          type="primary"
          :loading="running"
          :disabled="locked || !canRun"
          @click="submit"
        >
          运行定位（同步）
        </el-button><el-button
          data-testid="localization-save-defaults"
          :loading="saving"
          :disabled="locked || !metadataReady"
          @click="saveDefaults"
        >
          保存当前定位默认值
        </el-button><span class="hint">{{ configMessage }}</span>
      </div>
      <p
        v-if="running || outputLoading"
        role="status"
        class="hint"
      >
        {{ outputLoading ? '读取完整证据 JSON；确认后才替换结果…' : '正在请求同步定位服务…' }}
      </p>
      <div
        v-if="outputError"
        class="actions"
      >
        <p role="alert">
          {{ outputError }} 新结果尚未确认，保留此前结果与输入。
        </p><el-button
          data-testid="localization-retry-output"
          :disabled="locked || !pending"
          @click="retryOutput"
        >
          重试读取本次产物
        </el-button>
      </div>
    </section>

    <section
      class="panel source-panel"
      aria-labelledby="localization-source-title"
    >
      <h2 id="localization-source-title">
        原始提交 diff / 提交版本全文
      </h2>
      <p class="hint">
        只读 Git 提交版本，不读取当前工作树。可在定位前独立浏览；定位成功后浏览固定的结果版本，修改输入草稿不会切换它。
      </p>
      <div class="actions">
        <el-button
          id="localization-source-browse"
          data-testid="localization-source-browse"
          :disabled="auth || !canBrowse"
          @click="browseSource"
        >
          浏览源码 / 重试目录
        </el-button>
        <label
          v-if="resultHashes.length"
          for="localization-result-commit"
        >结果提交<select
          id="localization-result-commit"
          v-model="resultHash"
          :disabled="auth || running || outputLoading"
          @change="browseSource"
        ><option
          v-for="hash in resultHashes"
          :key="hash"
          :value="hash"
        >{{ hash }}</option></select></label>
        <label for="localization-source-mode">显示<select
          id="localization-source-mode"
          v-model="sourceMode"
        ><option value="file">提交版本全文</option><option value="diff">原始提交 diff</option></select></label>
      </div>
      <p
        v-if="source"
        data-testid="localization-source-version"
        class="mono version"
      >
        {{ source.repo_source || source.dataset_id }} · {{ source.commit_hash }}
      </p>
      <p
        v-else
        class="hint"
      >
        请填写仓库和提交 40 位 hash 后浏览；不默认使用 HEAD。
      </p>
      <p
        v-if="commitPredictions.length"
        data-testid="localization-source-risk"
        class="hint"
      >
        提交风险（预测原始 risk_score，非行可疑度）：<span
          v-for="(prediction, index) in commitPredictions"
          :key="index"
          class="mono"
        >{{ prediction.model_name }} {{ score(prediction.risk_score) }} · {{ prediction.model_version }} / {{ prediction.feature_version }} </span>
      </p>
      <template v-if="sourceMode === 'diff'">
        <p class="hint">
          下面是输入证据中的原始提交 unified diff，不是建议修复补丁。
        </p>
        <pre
          v-if="originalDiff !== null"
          data-testid="localization-original-diff"
          class="code-scroll original-diff"
        >{{ originalDiff }}</pre>
        <p
          v-else
          class="hint"
        >
          该版本暂无原始 diff 证据；可浏览提交版本全文。
        </p>
      </template>
      <div
        v-else
        class="source-layout"
      >
        <aside
          class="source-tree"
          aria-label="提交目录"
        >
          <label for="localization-source-search">路径子串搜索<input
            id="localization-source-search"
            v-model="search"
            :disabled="auth || !source"
            @keyup.enter="loadTree(treePath)"
          ></label>
          <div class="actions tree-actions">
            <el-button
              size="small"
              data-testid="localization-source-search"
              :disabled="auth || !source"
              @click="loadTree(treePath)"
            >
              搜索
            </el-button><el-button
              size="small"
              data-testid="localization-tree-back"
              :disabled="auth || !source || !treePath"
              @click="loadTree(parentPath(treePath))"
            >
              上一级
            </el-button><el-button
              size="small"
              data-testid="localization-tree-root"
              :disabled="auth || !source"
              @click="loadTree('')"
            >
              根目录
            </el-button>
          </div>
          <p class="mono version">
            /{{ treePath }}
          </p>
          <p
            v-if="treeLoading"
            role="status"
            class="hint"
          >
            读取目录…
          </p>
          <p
            v-if="treeError"
            role="alert"
            class="hint"
          >
            {{ treeError }}
          </p>
          <p
            v-if="treeData?.truncated"
            class="hint"
          >
            目录结果截断，请缩小路径 / 搜索范围。
          </p>
          <p
            v-if="treeData?.skipped?.length"
            class="hint"
          >
            已跳过：{{ displayJSON(treeData.skipped) }}
          </p>
          <ul class="tree-list">
            <li
              v-for="entry in treeData?.entries || []"
              :key="entry.path"
            >
              <button
                type="button"
                :data-testid="`localization-entry-${entry.path}`"
                :disabled="auth"
                :class="{ selected: filePath === entry.path }"
                @click="selectEntry(entry)"
              >
                <span class="hint">{{ entry.type === 'tree' ? '目录' : '文件' }}</span> {{ entry.name }} <span class="hint">{{ entry.size != null ? `${entry.size} bytes` : '' }}</span>
              </button>
            </li>
          </ul>
          <p
            v-if="source && treeData && !treeLoading && !treeData.entries.length"
            class="hint"
          >
            暂无匹配路径。
          </p>
        </aside>
        <article
          class="source-file"
          aria-label="只读提交源码"
        >
          <p
            v-if="filePath"
            class="mono version"
          >
            {{ filePath }}
          </p>
          <p
            v-if="fileLoading"
            role="status"
            class="hint"
          >
            读取提交版本文件…
          </p>
          <div
            v-if="fileError"
            class="actions"
          >
            <p role="alert">
              {{ fileError }}
            </p><el-button
              data-testid="localization-retry-file"
              :disabled="auth"
              @click="loadFile(filePath, requestedStart)"
            >
              重试文件
            </el-button>
          </div>
          <p
            v-if="fileData && fileData.status !== 'ok'"
            data-testid="localization-file-empty"
            class="hint"
          >
            {{ fileData.status }} · {{ fileData.reason || '该版本无可显示文本' }} · {{ fileData.size_bytes ?? '未知' }} bytes
          </p>
          <p
            v-if="!fileData && !fileLoading && !fileError"
            class="hint"
          >
            选择目录中的文件；二进制、超限或不存在文件不会显示伪造内容。
          </p>
          <template v-if="fileData?.status === 'ok'">
            <div class="actions pagination">
              <el-button
                data-testid="localization-prev-page"
                :disabled="auth || fileLoading || fileData.start_line <= 1"
                @click="loadFile(filePath, Math.max(1, fileData.start_line - PAGE_SIZE))"
              >
                上 200 行
              </el-button><el-button
                data-testid="localization-next-page"
                :disabled="auth || fileLoading || fileData.end_line >= fileData.total_lines"
                @click="loadFile(filePath, fileData.end_line + 1)"
              >
                下 200 行
              </el-button><span class="hint">{{ fileData.start_line }}–{{ fileData.end_line }} / {{ fileData.total_lines }} 行 · {{ fileData.encoding }} · {{ fileData.size_bytes }} bytes</span>
            </div>
            <div class="actions jump">
              <label for="localization-jump-line">跳转行<input
                id="localization-jump-line"
                v-model="jumpLine"
                type="number"
                min="1"
                :max="fileData.total_lines"
                step="1"
                :disabled="auth || fileLoading"
                @keyup.enter="jump"
              ></label><el-button
                data-testid="localization-jump"
                :disabled="auth || fileLoading"
                @click="jump"
              >
                跳转
              </el-button><span
                v-if="jumpError"
                class="hint"
                role="alert"
              >{{ jumpError }}</span>
            </div>
            <div
              data-testid="localization-code"
              class="code-scroll"
              tabindex="0"
              aria-label="带行号的提交版本全文"
            >
              <div
                v-for="line in sourceLines"
                :key="line.number"
                :data-testid="`localization-line-${line.number}`"
                class="code-line"
                :class="{ suspicious: lineMarks.has(line.number), 'jump-target': Number(jumpLine) === line.number }"
              >
                <span class="line-number">{{ line.number }}</span><span class="badge-slot"><button
                  v-if="lineMarks.has(line.number)"
                  class="suspicion-badge"
                  type="button"
                  :aria-label="`查看第 ${line.number} 行定位证据`"
                  @click="openEvidence(lineMarks.get(line.number))"
                >#{{ lineMarks.get(line.number).rank }} · {{ score(lineMarks.get(line.number).suspicion) }}</button></span><code>{{ line.text }}</code>
              </div>
            </div>
          </template>
        </article>
      </div>
    </section>

    <section
      v-if="result"
      data-testid="localization-result"
      class="panel"
      aria-labelledby="localization-result-title"
    >
      <h2 id="localization-result-title">
        已确认定位结果 · {{ result.accepted.job_id }}
      </h2>
      <p
        data-testid="localization-summary"
        class="hint"
      >
        提交 {{ result.document.summary.commits }} · 定位行 {{ result.document.summary.localized_rows }} · 行级 {{ result.document.summary.line_rows }} · 提交级回退 {{ result.document.summary.commit_rows }} · 证据不足 {{ result.document.summary.insufficient_count }} · {{ result.document.summary.truncated ? '结果截断（20 目标 / 5000 行上限）' : '未截断' }} · 建议来源 {{ result.document.summary.suggestion_sources?.join(', ') }}
      </p>
      <p class="hint">
        缺失解释会标记 missing_explanation；无可靠行证据时仅提交级回退，不虚构行号。
      </p>
      <pre
        v-if="insufficiencies.length"
        class="reason-text hint"
      >{{ displayJSON(insufficiencies) }}</pre>
      <h3>前 20 行 canonical 定位数据（完整行保存在证据 JSON，用于所有页高亮）</h3>
      <div
        class="table-scroll"
        tabindex="0"
        aria-label="定位结果前二十行"
      >
        <table>
          <thead><tr><th>提交</th><th>路径</th><th>行号</th><th>可疑度</th><th>排名</th><th>级别 / 证据</th></tr></thead><tbody>
            <tr
              v-for="(row, index) in result.document.rows.slice(0, 20)"
              :key="index"
              data-testid="localization-row"
            >
              <td>{{ row.commit_hash }}</td><td>{{ row.file_path }}</td><td>{{ row.level === 'line' ? row.line_number : '' }}</td><td>{{ score(row.suspicion) }}</td><td>{{ row.rank }}</td><td>
                <el-button
                  size="small"
                  @click="openEvidence(row)"
                >
                  {{ row.level === 'commit' ? '提交级回退' : '行级' }} · 证据
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p
        v-if="!result.document.rows.length"
        class="hint"
      >
        暂无定位行，请查看证据不足与完整产物。
      </p>
      <section
        data-testid="localization-suggestions"
        aria-labelledby="localization-suggestions-title"
      >
        <h3 id="localization-suggestions-title">
          修复建议（文本，只读）
        </h3><pre class="suggestions-text">{{ result.accepted.suggestions }}</pre><p
          v-for="(heading, index) in suggestionHeadings"
          :key="index"
          data-testid="localization-suggestion-part"
          class="hint"
        >
          {{ heading }}
        </p>
      </section>
      <p
        v-if="result.document.summary.patch_reason || result.accepted.summary.patch_reason"
        class="hint"
      >
        {{ result.document.summary.patch_reason || result.accepted.summary.patch_reason }}：没有可靠修复补丁，仅提供建议；patch_preview=true 不保证生成 diff。
      </p>
      <h3>已登记产物</h3><ul
        data-testid="localization-output-list"
        class="output-list"
      >
        <li
          v-for="output in result.accepted.outputs"
          :key="output.name"
        >
          <div class="mono">
            {{ output.name }}<code>SHA256 {{ output.sha256 || output.sha || '未提供' }} · {{ output.size_bytes ?? output.size ?? '未提供' }} bytes</code>
          </div><el-button
            size="small"
            :data-testid="`localization-download-${output.name}`"
            :disabled="locked || downloading"
            @click="download(output.name)"
          >
            下载
          </el-button>
        </li>
      </ul>
    </section>
    <p
      v-else
      data-testid="localization-result-empty"
      class="hint"
    >
      暂无已确认定位结果；源码浏览无需预测文件。
    </p>

    <el-drawer
      v-model="evidenceOpen"
      title="定位证据（原始输入 / 启发式）"
      size="min(560px, 100vw)"
    >
      <section
        v-if="selectedEvidence"
        data-testid="localization-evidence-pane"
        class="evidence-pane"
      >
        <p class="hint">
          prediction / raw risk 与行可疑度分开；包含解释上下文、hunk / code、history、insufficiencies。
        </p><h3>canonical 行与解析 evidence_json</h3><pre>{{ displayJSON(selectedEvidence.row) }}</pre><pre>{{ displayJSON(selectedEvidence.parsed) }}</pre><h3>提交与文件完整证据</h3><pre>{{ displayJSON(selectedEvidence.commit) }}</pre>
      </section>
    </el-drawer>
  </section>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { getSourceTree, getSourceFile, runLocalize, fetchLocalizeOutput, getJobs, getDatasets, fetchPredictOutput, fetchExplainOutput, putConfigKey } from '../api'
import { configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'LocalizationView' })
const route = useRoute(), PAGE_SIZE = 200
const queryString = value => typeof value === 'string' ? value : ''
const draft = reactive({ repo_source: '', dataset_id: '', commit_hash: queryString(route.query.commit_hash), model_name: queryString(route.query.model_name), weights: '', top_files: '', top_lines: '', file_size_max: '', suggestion_sources: [], patch_preview: true, format: 'csv' })
const files = ref([]), datasets = ref([]), artifacts = ref([]), selectedArtifact = ref('')
const metadataReady = ref(false), metadataLoading = ref(false), metadataError = ref(''), allowRoots = ref([]), suggestionChoices = ref([])
const inputsLoading = ref(false), inputsError = ref(''), artifactsLoading = ref(false), artifactsError = ref('')
const running = ref(false), saving = ref(false), usingArtifact = ref(false), auth = ref(false), error = ref(''), configMessage = ref('')
const outputLoading = ref(false), outputError = ref(''), pending = ref(null), result = ref(null), downloading = ref(false)
const source = ref(null), treeData = ref(null), treePath = ref(''), treeLoading = ref(false), treeError = ref(''), search = ref('')
const filePath = ref(''), fileData = ref(null), fileLoading = ref(false), fileError = ref(''), requestedStart = ref(1), jumpLine = ref(''), jumpError = ref(''), sourceMode = ref('file'), resultHash = ref('')
const evidenceOpen = ref(false), selectedEvidence = ref(null)
let mounted = true, treeEpoch = 0, fileEpoch = 0, outputEpoch = 0, defaultsInitialized = false
const locked = computed(() => auth.value || running.value || saving.value || usingArtifact.value || outputLoading.value)
const hasPredictions = computed(() => files.value.some(item => item.role === 'predictions'))
const canRun = computed(() => metadataReady.value && !metadataError.value && hasPredictions.value && Boolean(draft.repo_source.trim() || draft.dataset_id))
const resultHashes = computed(() => [...new Set((result.value?.document.rows || []).map(row => row.commit_hash).filter(Boolean))])
const canBrowse = computed(() => result.value ? Boolean(resultHash.value && (result.value.config.repo_source || result.value.config.dataset_id)) : Boolean(draft.commit_hash.trim() && (draft.repo_source.trim() || draft.dataset_id)))
const commitEvidence = computed(() => source.value && result.value ? result.value.document.evidence[source.value.commit_hash] : null)
const originalDiff = computed(() => typeof commitEvidence.value?.diff === 'string' ? commitEvidence.value.diff : null)
const commitPredictions = computed(() => (commitEvidence.value?.predictions || []).map(item => item.prediction).filter(Boolean))
const insufficiencies = computed(() => Object.entries(result.value?.document.evidence || {}).flatMap(([hash, entry]) => [
  ...(entry.insufficiencies || []).map(reason => ({ commit_hash: hash, reason })),
  ...(entry.predictions || []).flatMap(item => (item.insufficiencies || []).map(reason => ({ commit_hash: hash, model_name: item.prediction?.model_name, reason })))
]))
const suggestionHeadings = computed(() => (result.value?.accepted.suggestions || '').split('\n').filter(line => /^##\s+/.test(line)))
const sourceLines = computed(() => {
  if (fileData.value?.status !== 'ok' || fileData.value.total_lines === 0) return []
  return fileData.value.content.split('\n').slice(0, Math.max(0, fileData.value.end_line - fileData.value.start_line + 1)).map((text, index) => ({ number: fileData.value.start_line + index, text }))
})
const lineMarks = computed(() => {
  const marks = new Map()
  if (!source.value || !result.value) return marks
  const submitted = result.value.config
  if ((submitted.repo_source || submitted.dataset_id) !== (source.value.repo_source || source.value.dataset_id)) return marks
  for (const row of result.value.document.rows) {
    if (row.level !== 'line' || row.commit_hash !== source.value.commit_hash || row.file_path !== filePath.value || !Number.isInteger(row.line_number) || !numeric(row.suspicion)) continue
    const previous = marks.get(row.line_number)
    if (!previous || row.suspicion > previous.suspicion) marks.set(row.line_number, row)
  }
  return marks
})
const numeric = value => typeof value === 'number' && Number.isFinite(value)
const score = value => numeric(value) ? value.toFixed(6) : ''
const displayJSON = value => JSON.stringify(value, null, 2)
const roleLabel = role => ({ predictions: '预测（必需）', explanation: '解释（可选）', manifest: 'manifest' })[role]
const parentPath = path => path.split('/').slice(0, -1).join('/')
const tableFile = name => /\.(csv|xlsx)$/i.test(name)
const companionNames = name => { const stem = name.replace(/\.[^.]+$/, ''); return [`${stem}.manifest.json`, `${name}.manifest.json`, `${stem}_manifest.json`] }
function knownRole(name) {
  if (/^(?:pred(?:[_.-]|$)|predict)/i.test(name)) return 'predictions'
  if (/^explain/i.test(name)) return 'explanation'
  return null
}
function message(err) {
  if (err.code === 40100 || err.response?.status === 401) { auth.value = true; return '鉴权失败，请检查部署环境中的 API Key' }
  if (err.code === 40001) return `40001 参数错误：${err.detail || err.message}（请检查 repo_source / commit_hash / 输入文件）`
  if (err.code === 50000 || err.response?.status >= 500) return '服务异常，请稍后重试'
  return err.detail || err.message || '请求失败，请重试'
}
function removeFile(item) {
  if (locked.value) return
  files.value = files.value.filter(other => other !== item && !(item.role !== 'manifest' && companionNames(item.file.name).includes(other.file.name)))
}
function replaceRole(file, role) {
  const previous = files.value.find(item => item.role === role)
  if (previous) removeFileUnconditionally(previous)
  files.value.push({ file, role })
}
function removeFileUnconditionally(item) {
  files.value = files.value.filter(other => other !== item && !companionNames(item.file.name).includes(other.file.name))
}
function mergeFiles(incoming, forcedRole) {
  for (const file of incoming.filter(item => tableFile(item.name))) {
    const role = forcedRole || knownRole(file.name) || (!files.value.some(item => item.role === 'predictions') ? 'predictions' : !files.value.some(item => item.role === 'explanation') ? 'explanation' : 'predictions')
    replaceRole(file, role)
  }
  for (const file of incoming.filter(item => /\.json$/i.test(item.name))) {
    files.value = files.value.filter(item => item.file.name !== file.name)
    files.value.push({ file, role: 'manifest' })
  }
}
function selectFiles(event) {
  if (locked.value) return
  const incoming = Array.from(event.target.files || []); event.target.value = ''
  if (incoming.some(file => !/\.(csv|xlsx|json)$/i.test(file.name))) { error.value = '仅接受 CSV / XLSX 和 JSON manifest'; return }
  mergeFiles(incoming)
}
function selectDataset() {
  const item = datasets.value.find(entry => entry.dataset_id === draft.dataset_id)
  if (typeof item?.repo_source === 'string') draft.repo_source = item.repo_source
}
function positiveInt(value, name, max = Number.MAX_SAFE_INTEGER) {
  const number = Number(value)
  if (value === '' || !Number.isSafeInteger(number) || number < 1 || number > max) throw new Error(`${name} 必须为 1–${max} 的正整数`)
  return number
}
function validateWeights(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('weights 必须是嵌套对象，数值为非负有限数')
  for (const item of Object.values(value)) {
    if (item && typeof item === 'object' && !Array.isArray(item)) validateWeights(item)
    else if (!numeric(item) || item < 0) throw new Error('weights 必须使用非负有限数')
  }
  return value
}
function businessValues() {
  let weights
  try { weights = JSON.parse(draft.weights) } catch { throw new Error('weights JSON 格式不正确') }
  validateWeights(weights)
  if (!draft.suggestion_sources.length || draft.suggestion_sources.some(item => !suggestionChoices.value.includes(item))) throw new Error('suggestion_sources 至少选择一个服务端支持的来源')
  return { weights, top_n: { files: positiveInt(draft.top_files, 'top_n.files', 1000), lines: positiveInt(draft.top_lines, 'top_n.lines', 1000) }, file_size_max: positiveInt(draft.file_size_max, 'file_size_max'), suggestion_sources: [...draft.suggestion_sources] }
}
function repository(config) { return config.repo_source ? { repo_source: config.repo_source } : { dataset_id: config.dataset_id } }
function snapshot() {
  const config = { ...repository({ repo_source: draft.repo_source.trim(), dataset_id: draft.dataset_id }), ...businessValues(), patch_preview: draft.patch_preview, format: draft.format }
  if (!config.repo_source && !config.dataset_id) throw new Error('40001：需要 repo_source 或 dataset_id')
  if (!hasPredictions.value) throw new Error('40001：需要预测 CSV / XLSX')
  if (!['csv', 'xlsx'].includes(config.format)) throw new Error('format 必须为 csv / xlsx')
  if (draft.commit_hash.trim()) config.commit_hash = draft.commit_hash.trim()
  if (draft.model_name.trim()) config.model_name = draft.model_name.trim()
  return config
}
async function loadMetadata(refresh = false) {
  if (auth.value || metadataLoading.value) return
  metadataLoading.value = true; metadataReady.value = false; metadataError.value = ''
  try {
    if (refresh || !configuration.ready || configuration.error) await loadConfiguration()
    if (!mounted || auth.value) return
    const items = Array.isArray(configuration.items) ? configuration.items : []
    const values = Object.fromEntries(items.map(item => [item.config_key, item.value]))
    const weights = validateWeights(values['localization.weights']), top = values['localization.top_n']
    if (!top || typeof top !== 'object') throw new Error('服务端 localization.top_n 默认值缺失')
    const topFiles = positiveInt(top.files, 'localization.top_n.files', 1000), topLines = positiveInt(top.lines, 'localization.top_n.lines', 1000)
    const fileSize = positiveInt(values['localization.file_size_max'], 'localization.file_size_max')
    const sources = values['localization.suggestion_sources'], roots = values['collect.allow_roots']
    const choices = configuration.schema?.['localization.suggestion_sources']?.choices
    if (!Array.isArray(roots) || roots.some(item => typeof item !== 'string') || !Array.isArray(choices) || !choices.length || choices.some(item => !['template', 'llm', 'history'].includes(item)) || !Array.isArray(sources) || !sources.length || sources.some(item => !choices.includes(item))) throw new Error('服务端配置元数据不完整（allow_roots / suggestion_sources）')
    allowRoots.value = roots; suggestionChoices.value = choices
    if (!defaultsInitialized) {
      draft.weights = JSON.stringify(weights, null, 2); draft.top_files = topFiles; draft.top_lines = topLines; draft.file_size_max = fileSize; draft.suggestion_sources = [...sources]
      defaultsInitialized = true
    }
    metadataReady.value = true
  } catch (err) { if (mounted) metadataError.value = `配置尚未确认：${message(err)}；不会使用前端默认值` }
  finally { if (mounted) metadataLoading.value = false }
}
async function loadInputs() {
  if (auth.value || inputsLoading.value) return
  inputsLoading.value = true; inputsError.value = ''
  try {
    const data = await getDatasets({ size: 100, status: 'ready' })
    if (!mounted || auth.value) return
    if (!Array.isArray(data?.items)) throw new Error('数据集响应结构不完整')
    datasets.value = data.items
  } catch (err) { if (mounted) inputsError.value = message(err) }
  finally { if (mounted) inputsLoading.value = false }
}
async function loadArtifacts() {
  if (auth.value || artifactsLoading.value) return
  artifactsLoading.value = true; artifactsError.value = ''
  try {
    const kinds = ['predict_batch', 'explain']
    const responses = await Promise.all(kinds.map(kind => getJobs({ kind, status: 'success', size: 100 })))
    if (!mounted || auth.value) return
    if (responses.some(data => !Array.isArray(data?.items))) throw new Error('产物库响应结构不完整')
    artifacts.value = responses.flatMap((data, index) => data.items.filter(item => item.kind === kinds[index]).flatMap(item => {
      const outputs = item.output_ref_json?.outputs || item.outputs || []
      return outputs.filter(output => typeof output?.name === 'string' && tableFile(output.name)).map(output => ({ ...output, job_id: item.job_id, kind: item.kind, value: `${item.kind}/${item.job_id}/${output.name}`, companions: outputs.filter(candidate => companionNames(output.name).includes(candidate.name)) }))
    }))
  } catch (err) { if (mounted) artifactsError.value = message(err) }
  finally { if (mounted) artifactsLoading.value = false }
}
async function useArtifact() {
  if (locked.value) return
  const item = artifacts.value.find(entry => entry.value === selectedArtifact.value)
  if (!item) return
  usingArtifact.value = true; error.value = ''
  try {
    const fetcher = item.kind === 'predict_batch' ? fetchPredictOutput : fetchExplainOutput
    const staged = await Promise.all([item, ...item.companions].map(async output => new File([await fetcher(item.job_id, output.name)], output.name)))
    if (mounted && !auth.value) mergeFiles(staged, item.kind === 'predict_batch' ? 'predictions' : 'explanation')
  } catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) usingArtifact.value = false }
}
async function saveDefaults() {
  if (locked.value || !metadataReady.value) return
  saving.value = true; error.value = ''; configMessage.value = ''
  try {
    const values = businessValues()
    for (const [key, value] of Object.entries(values)) {
      await putConfigKey(`localization.${key}`, value)
      if (!mounted || auth.value) return
    }
    await loadConfiguration()
    if (mounted && !auth.value) configMessage.value = '定位默认值已保存并重载；未运行定位'
  } catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) saving.value = false }
}
function canonicalRow(row) {
  return row && typeof row.commit_hash === 'string' && ['line', 'commit'].includes(row.level) && typeof row.evidence_json === 'string' && (row.level === 'commit' ? row.file_path === null && row.line_number === null : typeof row.file_path === 'string' && Number.isInteger(row.line_number) && row.line_number > 0) && numeric(row.suspicion)
}
function validSummary(summary) { return summary && ['commits', 'localized_rows', 'line_rows', 'commit_rows', 'insufficient_count'].every(key => Number.isInteger(summary[key]) && summary[key] >= 0) && typeof summary.truncated === 'boolean' && Array.isArray(summary.suggestion_sources) }
function validateAccepted(data) {
  if (!data || typeof data.job_id !== 'string' || data.status !== 'success' || !validSummary(data.summary) || !Array.isArray(data.outputs) || data.outputs.some(item => typeof item?.name !== 'string') || !Array.isArray(data.localization) || !data.localization.every(canonicalRow) || typeof data.suggestions !== 'string') throw new Error('同步定位响应结构不完整；不支持排队 / 轮询')
}
async function blobJSON(blob) {
  const text = typeof blob.text === 'function' ? await blob.text() : await new Promise((resolve, reject) => {
    const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = () => reject(new Error('证据 JSON 读取失败')); reader.readAsText(blob)
  })
  try { return JSON.parse(text) } catch { throw new Error('证据 JSON 结构 / 格式不正确') }
}
function validateDocument(data) {
  if (!Array.isArray(data?.rows) || !data.rows.every(canonicalRow) || !data.evidence || typeof data.evidence !== 'object' || Array.isArray(data.evidence) || !validSummary(data.summary) || Object.values(data.evidence).some(entry => !entry || typeof entry.diff !== 'string' || !Array.isArray(entry.files) || !Array.isArray(entry.predictions) || !Array.isArray(entry.insufficiencies)) || data.rows.some(row => !data.evidence[row.commit_hash])) throw new Error('完整定位证据 JSON 结构不正确')
}
async function submit() {
  if (locked.value || !canRun.value) return
  running.value = true; error.value = ''; outputError.value = ''; pending.value = null
  const token = ++outputEpoch
  try {
    const config = snapshot(), uploaded = files.value.map(item => item.file)
    const accepted = await runLocalize(config, uploaded)
    if (!mounted || auth.value || token !== outputEpoch) return
    validateAccepted(accepted)
    pending.value = { accepted, config }
    await loadOutput(token)
  } catch (err) { if (mounted && token === outputEpoch) error.value = message(err) }
  finally { if (mounted && token === outputEpoch) running.value = false }
}
async function loadOutput(token) {
  const staged = pending.value
  if (!staged || auth.value || !mounted) return
  outputLoading.value = true; outputError.value = ''
  try {
    const name = `localization_evidence_${staged.accepted.job_id}.json`
    if (!staged.accepted.outputs.some(item => item.name === name)) throw new Error('本次未登记完整证据 JSON，不能确认新结果')
    const document = await fetchLocalizeOutput(staged.accepted.job_id, name).then(blobJSON)
    if (!mounted || auth.value || token !== outputEpoch || pending.value !== staged) return
    validateDocument(document)
    // A synchronous response is not a displayed success until its complete artifact is validated.
    result.value = { ...staged, document }; pending.value = null
    evidenceOpen.value = false; selectedEvidence.value = null
    const hashes = [...new Set(document.rows.map(row => row.commit_hash).filter(Boolean))]
    resultHash.value = hashes.includes(staged.config.commit_hash) ? staged.config.commit_hash : hashes[0] || ''
    if (resultHash.value) setSource({ ...repository(staged.config), commit_hash: resultHash.value })
    else clearSource()
  } catch (err) { if (mounted && token === outputEpoch) outputError.value = message(err) }
  finally { if (mounted && token === outputEpoch) outputLoading.value = false }
}
async function retryOutput() {
  if (locked.value || !pending.value) return
  await loadOutput(++outputEpoch)
}
function clearSource() {
  treeEpoch++; fileEpoch++; source.value = null; treeData.value = null; fileData.value = null; filePath.value = ''; treePath.value = ''; treeLoading.value = false; fileLoading.value = false; treeError.value = ''; fileError.value = ''; jumpError.value = ''; jumpLine.value = ''
}
function setSource(version) {
  clearSource(); source.value = version; search.value = ''; void loadTree('')
}
function browseSource() {
  if (auth.value || !canBrowse.value) return
  const version = result.value ? { ...repository(result.value.config), commit_hash: resultHash.value } : { ...repository({ repo_source: draft.repo_source.trim(), dataset_id: draft.dataset_id }), commit_hash: draft.commit_hash.trim() }
  if (!source.value || JSON.stringify(source.value) !== JSON.stringify(version)) setSource(version)
  else void loadTree(treePath.value)
}
async function loadTree(path = '') {
  if (!source.value || auth.value) return
  const token = ++treeEpoch, version = { ...source.value }, query = search.value
  treePath.value = path; treeData.value = null; treeLoading.value = true; treeError.value = ''
  try {
    const data = await getSourceTree({ ...version, path, ...(query ? { search: query } : {}) })
    if (!mounted || auth.value || token !== treeEpoch) return
    if (!Array.isArray(data?.entries) || typeof data.commit_hash !== 'string' || typeof data.path !== 'string') throw new Error('源码目录响应结构不完整')
    treeData.value = data
  } catch (err) { if (mounted && token === treeEpoch) treeError.value = message(err) }
  finally { if (mounted && token === treeEpoch) treeLoading.value = false }
}
function selectEntry(entry) {
  if (auth.value) return
  if (entry.type === 'tree') void loadTree(entry.path)
  else if (entry.type === 'blob') { sourceMode.value = 'file'; jumpLine.value = ''; jumpError.value = ''; void loadFile(entry.path, 1) }
}
async function loadFile(path, start = 1) {
  if (!source.value || auth.value || !path) return
  const token = ++fileEpoch, version = { ...source.value }
  filePath.value = path; requestedStart.value = start; fileData.value = null; fileLoading.value = true; fileError.value = ''; jumpError.value = ''
  try {
    const data = await getSourceFile({ ...version, path, start_line: start, end_line: start + PAGE_SIZE - 1 })
    if (!mounted || auth.value || token !== fileEpoch) return
    if (!['ok', 'binary', 'too_large', 'not_found'].includes(data?.status) || data.path !== path || typeof data.commit_hash !== 'string' || (data.status === 'ok' && (typeof data.content !== 'string' || !Number.isInteger(data.start_line) || !Number.isInteger(data.end_line) || !Number.isInteger(data.total_lines)))) throw new Error('源码文件响应结构不完整')
    fileData.value = data
  } catch (err) { if (mounted && token === fileEpoch) fileError.value = message(err) }
  finally { if (mounted && token === fileEpoch) fileLoading.value = false }
}
function jump() {
  if (auth.value || fileLoading.value || fileData.value?.status !== 'ok') return
  try {
    const line = positiveInt(jumpLine.value, '跳转行', fileData.value.total_lines)
    void loadFile(filePath.value, Math.floor((line - 1) / PAGE_SIZE) * PAGE_SIZE + 1)
  } catch (err) { jumpError.value = message(err) }
}
function openEvidence(row) {
  let parsed
  try { parsed = JSON.parse(row.evidence_json) } catch { parsed = { reason: 'evidence_json 解析失败', original: row.evidence_json } }
  selectedEvidence.value = { row, parsed, commit: result.value?.document.evidence[row.commit_hash] || null }; evidenceOpen.value = true
}
async function download(name) {
  if (locked.value || downloading.value || !result.value?.accepted.outputs.some(item => item.name === name)) return
  downloading.value = true; error.value = ''
  const current = result.value
  try {
    const blob = await fetchLocalizeOutput(current.accepted.job_id, name)
    if (!mounted || auth.value || result.value !== current) return
    const url = URL.createObjectURL(blob)
    try { const link = document.createElement('a'); link.href = url; link.download = name; link.click() }
    finally { URL.revokeObjectURL(url) }
  } catch (err) { if (mounted) error.value = message(err) }
  finally { if (mounted) downloading.value = false }
}
onMounted(() => { void loadMetadata(); void loadInputs(); void loadArtifacts() })
onUnmounted(() => { mounted = false; outputEpoch++; treeEpoch++; fileEpoch++ })
</script>

<style scoped>
.localization { min-width: 0; max-width: 100%; font-family: var(--el-font-family), sans-serif; color: var(--el-text-color-primary); }
.panel { min-width: 0; border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); padding: 18px; margin: 18px 0; }
h2, h3 { font-size: var(--el-font-size-base); } h2 { margin: 0 0 16px; } h3 { margin: 18px 0 12px; }
.hint { color: var(--el-text-color-secondary); font-size: var(--el-font-size-small); line-height: 1.65; overflow-wrap: anywhere; }
.fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 16px 0; }
.fields label, .source-tree > label { display: flex; flex-direction: column; gap: 8px; min-width: 0; font-size: var(--el-font-size-base); } .span-all { grid-column: 1 / -1; }
input:not([type="checkbox"]), select, textarea { box-sizing: border-box; min-width: 0; max-width: 100%; width: 100%; padding: 8px 10px; font: inherit; background: var(--el-fill-color-blank); color: var(--el-text-color-primary); border: 1px solid var(--el-border-color); border-radius: var(--el-border-radius-base); }
input:disabled, select:disabled, textarea:disabled { background: var(--el-fill-color-light); color: var(--el-text-color-disabled); } textarea { resize: vertical; } input[type="checkbox"] { accent-color: var(--el-color-primary); }
input:focus-visible, select:focus-visible, textarea:focus-visible, button:focus-visible, .code-scroll:focus-visible, .table-scroll:focus-visible { outline: 2px solid var(--el-color-primary); outline-offset: 2px; }
.actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; min-width: 0; } .actions > label { flex: 1 1 180px; min-width: 0; max-width: 100%; }
.actions .el-button, .file-list .el-button { margin-left: 0; max-width: 100%; white-space: normal; height: auto; min-height: 32px; }
.checkbox { display: inline-flex; align-items: center; gap: 8px; margin: 8px 16px 8px 0; font-size: var(--el-font-size-base); } fieldset { min-width: 0; margin: 14px 0; border: 1px solid var(--el-border-color-light); } legend { font-size: var(--el-font-size-small); }
.mono, pre, code, table { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: var(--el-font-size-extra-small); font-variant-numeric: tabular-nums; }
.version, .file-list { overflow-wrap: anywhere; } .file-list { padding-left: 20px; } .file-list li { margin: 8px 0; }
.source-layout { display: grid; grid-template-columns: 240px minmax(0, 1fr); margin-top: 16px; border: 1px solid var(--el-border-color-light); border-radius: var(--el-border-radius-base); min-width: 0; }
.source-tree { min-width: 0; padding: 12px; background: var(--el-fill-color-light); border-right: 1px solid var(--el-border-color-light); } .tree-actions { margin: 10px 0; gap: 6px; }
.tree-list { list-style: none; padding: 0; } .tree-list button { display: block; width: 100%; text-align: left; border: 0; background: transparent; padding: 10px 6px; color: var(--el-text-color-primary); font: inherit; font-size: var(--el-font-size-small); overflow-wrap: anywhere; cursor: pointer; } .tree-list button:hover, .tree-list button.selected { background: var(--el-color-primary-light-9); color: var(--el-color-primary); }
.source-file { min-width: 0; padding: 12px; } .pagination, .jump { margin: 12px 0; } .jump > label { flex: 0 1 140px; }
.code-scroll { min-width: 0; max-width: 100%; overflow: auto; background: var(--el-fill-color-blank); border: 1px solid var(--el-border-color-lighter); }
.code-line { display: flex; min-width: max-content; line-height: 1.9; min-height: 26px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: var(--el-font-size-extra-small); }
.line-number { flex: 0 0 52px; width: 52px; text-align: right; padding-right: 12px; box-sizing: border-box; color: var(--el-text-color-placeholder); background: var(--el-fill-color-light); user-select: none; }
.badge-slot { flex: 0 0 132px; width: 132px; padding: 0 6px; box-sizing: border-box; } .code-line code { white-space: pre; padding-right: 16px; }
.code-line.suspicious { background: var(--el-color-warning-light-9); } .code-line.jump-target { box-shadow: inset 3px 0 var(--el-color-primary); }
.suspicion-badge { color: var(--el-color-warning-dark-2); background: var(--el-color-warning-light-9); border: 1px solid var(--el-color-warning-light-5); border-radius: var(--el-border-radius-small); cursor: pointer; font: inherit; white-space: nowrap; }
.original-diff { padding: 12px; white-space: pre; } .table-scroll { min-width: 0; max-width: 100%; overflow-x: auto; } table { width: 100%; border-collapse: collapse; white-space: nowrap; } th, td { padding: 10px; text-align: left; border: 1px solid var(--el-border-color-light); } th { background: var(--el-fill-color-light); }
.suggestions-text, .reason-text, .evidence-pane pre { white-space: pre-wrap; overflow-wrap: anywhere; min-width: 0; max-width: 100%; } .suggestions-text, .evidence-pane pre { padding: 12px; background: var(--el-fill-color-light); line-height: 1.65; } .evidence-pane { min-width: 0; }
.output-list { padding: 0; list-style: none; } .output-list li { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); min-width: 0; } .output-list li div { min-width: 0; overflow-wrap: anywhere; } .output-list code { display: block; margin-top: 6px; } .output-list .el-button { flex-shrink: 0; margin-left: 0; }
@media (max-width: 640px) { .fields, .source-layout { grid-template-columns: minmax(0, 1fr); } .panel { padding: 14px; } .source-tree { border-right: 0; border-bottom: 1px solid var(--el-border-color-light); } .source-file { padding: 10px; } }
</style>
