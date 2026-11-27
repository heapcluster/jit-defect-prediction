<template>
  <ToolWorkspace
    hide-tabs
    model-value="config"
  >
    <template #config>
      <el-alert
        v-if="error"
        :title="error"
        type="error"
        :closable="false"
        show-icon
        class="notice"
      >
        <el-button
          v-if="readFailed || unauthorized"
          data-testid="retry-config"
          :disabled="busy"
          @click="refresh"
        >
          重试
        </el-button>
      </el-alert>

      <el-form
        v-if="initialized"
        label-position="top"
        :disabled="busy || unauthorized"
        @submit.prevent="save"
      >
        <header class="settings-intro">
          <h2>风险分档阈值</h2>
          <p>
            预测分数达到高风险阈值即标为高风险，介于中、高阈值之间为中风险，低于中风险阈值为低风险。
            保存后立即在数据收集、预测与评估页面生效。
          </p>
        </header>

        <div class="threshold-grid">
          <el-form-item
            label="高风险阈值"
            :for="inputId('risk_high_threshold')"
            :error="validation.risk_high_threshold"
            data-config-key="risk_high_threshold"
            class="threshold-field"
          >
            <el-input-number
              :id="inputId('risk_high_threshold')"
              v-model="draft.risk_high_threshold"
              :min="0.01"
              :max="0.99"
              :step="0.01"
              :precision="2"
              controls-position="right"
              :aria-label="'高风险阈值'"
              class="editor"
            />
            <p class="field-hint">
              分数 ≥ {{ format(draft.risk_high_threshold) }} 判定为高风险
            </p>
          </el-form-item>

          <el-form-item
            label="中风险阈值"
            :for="inputId('risk_mid_threshold')"
            :error="validation.risk_mid_threshold"
            data-config-key="risk_mid_threshold"
            class="threshold-field"
          >
            <el-input-number
              :id="inputId('risk_mid_threshold')"
              v-model="draft.risk_mid_threshold"
              :min="0.01"
              :max="0.99"
              :step="0.01"
              :precision="2"
              controls-position="right"
              :aria-label="'中风险阈值'"
              class="editor"
            />
            <p class="field-hint">
              分数 ≥ {{ format(draft.risk_mid_threshold) }} 且低于高风险阈值时判定为中风险
            </p>
          </el-form-item>
        </div>

        <section
          class="risk-scale"
          aria-label="当前风险区间预览"
        >
          <div class="risk-scale__head">
            <span>当前风险区间</span>
            <span class="risk-scale__note">分数范围 0 – 1</span>
          </div>
          <div class="risk-scale__bar">
            <span
              class="risk-scale__band is-low"
              :style="{ flexGrow: lowWeight }"
            >
              <strong>低风险</strong>
              <small>0 – {{ format(draft.risk_mid_threshold) }}</small>
            </span>
            <span
              class="risk-scale__band is-mid"
              :style="{ flexGrow: midWeight }"
            >
              <strong>中风险</strong>
              <small>{{ format(draft.risk_mid_threshold) }} – {{ format(draft.risk_high_threshold) }}</small>
            </span>
            <span
              class="risk-scale__band is-high"
              :style="{ flexGrow: highWeight }"
            >
              <strong>高风险</strong>
              <small>{{ format(draft.risk_high_threshold) }} – 1</small>
            </span>
          </div>
        </section>

        <div class="settings-footer">
          <el-button
            data-testid="save-config"
            class="run-button"
            type="primary"
            native-type="submit"
            :disabled="busy || unauthorized || readFailed || !changed"
            :loading="saving"
          >
            保存修改
          </el-button>
          <p
            role="status"
            aria-live="polite"
            class="status-line"
          >
            {{ status || (changed ? '修改后点此保存，保存后立即生效' : '当前为已生效设置') }}
          </p>
        </div>
      </el-form>
      <el-skeleton
        v-else
        :rows="4"
        animated
        aria-label="正在读取设置"
      />
    </template>
  </ToolWorkspace>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import ToolWorkspace from '../components/ToolWorkspace.vue'
import { putConfig } from '../api'
import { errText } from '../utils/errors'
import { applyConfiguration, configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'ConfigurationSettings' })

const KEYS = ['risk_high_threshold', 'risk_mid_threshold']
const draft = reactive({ risk_high_threshold: null, risk_mid_threshold: null })
const baseline = reactive({ risk_high_threshold: null, risk_mid_threshold: null })
const validation = reactive({})
const initialized = ref(false)
const busy = ref(false)
const saving = ref(false)
const unauthorized = ref(false)
const readFailed = ref(false)
const error = ref('')
const status = ref('')

const inputId = key => `config-${key}`
const format = value => (typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—')
const parsed = key => {
  const value = draft[key]
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error('请填写 0 到 1 之间的数值')
  if (!(value > 0 && value < 1)) throw new Error('阈值需在 0 到 1 之间')
  return value
}
const changed = computed(() => KEYS.some(key => draft[key] !== baseline[key]))
const lowWeight = computed(() => Math.max(Number(draft.risk_mid_threshold) || 0, 0.02))
const midWeight = computed(() => Math.max((Number(draft.risk_high_threshold) || 0) - (Number(draft.risk_mid_threshold) || 0), 0.02))
const highWeight = computed(() => Math.max(1 - (Number(draft.risk_high_threshold) || 0), 0.02))

function showError(caught) {
  error.value = caught.code === 40400 ? '设置不存在，请刷新后重试'
    : caught.code === 40001 && caught.detail ? `${errText(caught)}：${caught.detail}` : errText(caught)
  if (caught.code === 40100) unauthorized.value = true
}

function fill() {
  for (const key of KEYS) {
    const value = configuration.items.find(item => item.config_key === key)?.value
    if (typeof value === 'number') baseline[key] = value
  }
  draft.risk_high_threshold = baseline.risk_high_threshold
  draft.risk_mid_threshold = baseline.risk_mid_threshold
  initialized.value = true
}

async function read() {
  readFailed.value = false
  try {
    await loadConfiguration()
    fill()
    unauthorized.value = false
    return true
  } catch (caught) {
    readFailed.value = true
    showError(caught)
    return false
  }
}

async function refresh() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  await read()
  busy.value = false
}

async function save() {
  if (busy.value || unauthorized.value || readFailed.value) return
  error.value = ''
  status.value = ''
  for (const key of Object.keys(validation)) delete validation[key]

  const items = []
  for (const key of KEYS) {
    try {
      const value = parsed(key)
      if (value !== baseline[key]) items.push({ config_key: key, value })
    } catch (caught) {
      validation[key] = caught.message
    }
  }
  const high = Number(draft.risk_high_threshold)
  const mid = Number(draft.risk_mid_threshold)
  if (!validation.risk_high_threshold && !validation.risk_mid_threshold && !(mid < high)) {
    validation.risk_mid_threshold = '中风险阈值必须小于高风险阈值'
  }
  if (Object.keys(validation).length) {
    error.value = '请先修正标红项再保存'
    return
  }
  if (!items.length) {
    status.value = '没有需要保存的修改'
    return
  }

  busy.value = true
  saving.value = true
  try {
    const confirmed = await putConfig(items)
    await applyConfiguration(confirmed)
    if (await read()) status.value = '设置已保存，已在所有页面生效'
  } catch (caught) {
    showError(caught)
  } finally {
    saving.value = false
    busy.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.notice {
  margin-bottom: var(--ui-space-4);
  overflow-wrap: anywhere;
}
.settings-intro {
  max-width: 720px;
  margin-bottom: var(--ui-space-5);
}
.settings-intro h2 {
  margin: 0;
  font-size: var(--ui-font-lg);
  font-weight: 650;
  letter-spacing: -0.01em;
}
.settings-intro p {
  margin: var(--ui-space-2) 0 0;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-sm);
  line-height: 1.7;
}
.threshold-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--ui-space-4);
  max-width: 720px;
}
.threshold-field {
  min-width: 0;
  margin: 0;
}
.threshold-field :deep(.el-form-item__label) {
  padding-bottom: 6px;
  color: var(--ui-text);
  font-size: var(--ui-font-sm);
  font-weight: 600;
}
.threshold-field :deep(.el-form-item__content) {
  display: block;
  min-width: 0;
}
.threshold-field :deep(.el-form-item__error) {
  position: static;
  padding-top: 4px;
}
.editor {
  width: 100%;
}
.field-hint {
  margin: 8px 0 0;
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  line-height: 1.55;
}
.risk-scale {
  max-width: 720px;
  margin-top: var(--ui-space-5);
  padding: var(--ui-space-4);
  border: 1px solid var(--ui-border);
  border-radius: var(--ui-radius-lg);
  background: var(--ui-surface-subtle);
}
.risk-scale__head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--ui-space-3);
  margin-bottom: var(--ui-space-3);
  font-size: var(--ui-font-sm);
  font-weight: 600;
}
.risk-scale__note {
  color: var(--ui-text-muted);
  font-size: var(--ui-font-hint);
  font-weight: 400;
}
.risk-scale__bar {
  display: flex;
  gap: 2px;
  height: 52px;
  overflow: hidden;
  border-radius: var(--ui-radius-sm);
}
.risk-scale__band {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  padding: 0 10px;
  color: var(--ui-text);
  font-size: var(--ui-font-hint);
  line-height: 1.3;
  white-space: nowrap;
}
.risk-scale__band strong {
  font-size: var(--ui-font-sm);
  font-weight: 650;
}
.risk-scale__band small {
  color: var(--ui-text-muted);
  font-variant-numeric: tabular-nums;
}
.risk-scale__band.is-low {
  background: var(--ui-success-bg);
  color: var(--ui-success-text);
}
.risk-scale__band.is-mid {
  background: var(--ui-warning-bg);
  color: var(--ui-warning-text);
}
.risk-scale__band.is-high {
  background: var(--ui-danger-bg);
  color: var(--ui-danger-text);
}
.risk-scale__band.is-low small,
.risk-scale__band.is-mid small,
.risk-scale__band.is-high small {
  color: inherit;
  opacity: 0.75;
}
.settings-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--ui-space-3);
  margin-top: var(--ui-space-5);
  padding-top: var(--ui-space-4);
  border-top: 1px solid var(--ui-border);
}
.settings-footer .run-button {
  width: auto;
  min-width: 144px;
}
.settings-footer .status-line {
  margin: 0;
}
@media (max-width: 760px) {
  .threshold-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .settings-footer {
    align-items: stretch;
    flex-direction: column;
  }
  .settings-footer .run-button {
    width: 100%;
  }
  .risk-scale__band small {
    display: none;
  }
}
</style>
