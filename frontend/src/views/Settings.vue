<template>
  <section class="settings">
    <div class="section-heading">
      <h2>用户配置</h2>
      <span>唯一配置源：user_config</span>
    </div>
    <p class="hint">
      当前固定 Token 模式写入 global；恢复默认删除当前作用域配置，由后端回退 global / factory。
      保存后风险展示重新分档，不改写已有 risk_score，不自动重新预测。
    </p>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
      class="notice"
    >
      <el-button
        v-if="readFailed"
        data-testid="retry-config"
        :disabled="busy"
        @click="refresh"
      >
        重试
      </el-button>
    </el-alert>
    <el-skeleton
      v-if="!initialized && busy"
      :rows="6"
      animated
    />
    <template v-if="initialized">
      <el-alert
        title="阈值校验：0 < risk_mid_threshold < risk_high_threshold < 1；decision_threshold 仅供后续预测 / 评估运行使用。primary_metric 必须属于 metrics_selected。最终校验由后端完成。"
        type="info"
        :closable="false"
        class="notice"
      />
      <el-form
        label-position="top"
        :disabled="busy || unauthorized"
        @submit.prevent="save"
      >
        <el-tabs v-model="activeGroup">
          <el-tab-pane
            v-for="group in groups"
            :key="group"
            :name="group"
            :label="group === 'global' ? '全局' : group"
          >
            <p
              v-if="group === 'clean' || group === 'train'"
              class="hint"
            >
              目前仅支持空模板 {}；非空模板须等待对应操作/算法注册表实现。
            </p>
            <div class="field-grid">
              <el-form-item
                v-for="field in fields.filter(item => item.group === group)"
                :key="field.key"
                :label="field.label"
                :for="inputId(field.key)"
                :data-config-key="field.key"
                :error="validation[field.key]"
                class="config-field"
              >
                <div class="field-body">
                  <code class="config-key">{{ field.key }}</code>
                  <el-select
                    v-if="Array.isArray(field.choices)"
                    :id="inputId(field.key)"
                    v-model="draft[field.key]"
                    :aria-label="field.label"
                    :multiple="field.value_type === 'list'"
                    :disabled="field.choices.length === 0"
                    filterable
                    class="editor"
                  >
                    <el-option
                      v-for="choice in field.choices"
                      :key="String(choice)"
                      :label="choice === '' ? '不指定（由后端回退）' : String(choice)"
                      :value="choice"
                    />
                  </el-select>
                  <el-input-number
                    v-else-if="field.value_type === 'float' || field.value_type === 'int'"
                    :id="inputId(field.key)"
                    v-model="draft[field.key]"
                    :aria-label="field.label"
                    :step="field.value_type === 'int' ? 1 : 0.01"
                    controls-position="right"
                    class="editor"
                  />
                  <el-switch
                    v-else-if="field.value_type === 'bool'"
                    :id="inputId(field.key)"
                    v-model="draft[field.key]"
                    :aria-label="field.label"
                  />
                  <el-input
                    v-else
                    :id="inputId(field.key)"
                    v-model="draft[field.key]"
                    :aria-label="field.label"
                    :type="isJson(field) ? 'textarea' : 'text'"
                    :rows="isJson(field) ? 5 : undefined"
                    :spellcheck="false"
                    class="editor"
                  />
                  <p
                    v-if="isJson(field)"
                    class="hint json-hint"
                  >
                    JSON {{ field.value_type === 'object' ? '对象' : '数组' }}编辑器
                  </p>
                  <div class="field-footer">
                    <span class="source">
                      来源：<el-tag size="small">{{ field.source }}</el-tag>
                    </span>
                    <el-button
                      data-testid="reset-config"
                      size="small"
                      :aria-label="`恢复默认：${field.label}`"
                      :disabled="busy || unauthorized || readFailed || field.source === 'factory'"
                      @click="resetField(field.key)"
                    >
                      恢复默认
                    </el-button>
                  </div>
                  <time
                    v-if="field.updated_at"
                    class="hint updated-at"
                  >{{ field.updated_at }}</time>
                </div>
              </el-form-item>
            </div>
          </el-tab-pane>
        </el-tabs>
        <div class="actions">
          <el-button
            data-testid="save-config"
            type="primary"
            native-type="submit"
            :disabled="busy || unauthorized || readFailed"
            :loading="saving"
          >
            保存修改
          </el-button>
          <span
            role="status"
            aria-live="polite"
            class="hint"
          >{{ status }}</span>
        </div>
      </el-form>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { deleteConfigKey, putConfig } from '../api'
import { applyConfiguration, configuration, loadConfiguration } from '../utils/thresholds'

defineOptions({ name: 'ConfigurationSettings' })

const draft = reactive({})
const baseline = reactive({})
const validation = reactive({})
const activeGroup = ref('')
const initialized = ref(false)
const busy = ref(false)
const saving = ref(false)
const unauthorized = ref(false)
const readFailed = ref(false)
const error = ref('')
const status = ref('')
const sensitiveKey = /secret|password|passwd|credential|token|api[_.-]?key|llm[_.-]?key|connection[_.-]?string/i

function hasSensitiveValue(value) {
  if (!value || typeof value !== 'object') return false
  return Object.entries(value).some(([key, nested]) => sensitiveKey.test(key) || hasSensitiveValue(nested))
}

const fields = computed(() => configuration.items.flatMap(item => {
  const meta = configuration.schema[item.config_key]
  if (!meta || sensitiveKey.test(item.config_key) || hasSensitiveValue(item.value)) return []
  return [{ ...meta, ...item, key: item.config_key }]
}))
const groups = computed(() => {
  const values = [...new Set(fields.value.map(field => field.group))]
  return values.includes('global') ? ['global', ...values.filter(group => group !== 'global')] : values
})
const inputId = key => `config-${key}`
const isJson = field => !Array.isArray(field.choices) && (field.value_type === 'object' || field.value_type === 'list')
const copy = value => JSON.parse(JSON.stringify(value))
const encode = (field, value) => isJson(field) ? JSON.stringify(value, null, 2) : copy(value)
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b)

function parse(field) {
  const value = isJson(field) ? JSON.parse(draft[field.key]) : draft[field.key]
  if (field.value_type === 'object' && (value === null || typeof value !== 'object' || Array.isArray(value))) {
    throw new Error('须为 JSON 对象')
  }
  if (field.value_type === 'list' && !Array.isArray(value)) throw new Error('须为 JSON 数组')
  if (hasSensitiveValue(value)) throw new Error('配置不能包含敏感字段')
  return value
}

function isChanged(field) {
  try { return !equal(parse(field), baseline[field.key]) } catch { return true }
}

// 重读来源时保留其他字段的未提交草稿；已确认字段只使用响应值回填。
function fill(confirmedKeys = []) {
  for (const field of fields.value) {
    const keep = Object.hasOwn(baseline, field.key) && !confirmedKeys.includes(field.key) && isChanged(field)
    baseline[field.key] = copy(field.value)
    if (!keep) draft[field.key] = encode(field, field.value)
  }
  if (!groups.value.includes(activeGroup.value)) activeGroup.value = groups.value[0] || ''
  initialized.value = true
}

function showError(caught) {
  error.value = caught.detail || caught.message || '配置请求失败'
  if (caught.code === 40100) unauthorized.value = true
}

async function read() {
  readFailed.value = false
  try {
    await loadConfiguration()
    fill()
    unauthorized.value = false
  } catch (caught) {
    readFailed.value = true
    showError(caught)
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
  for (const field of fields.value) {
    try {
      const value = parse(field)
      if (!equal(value, baseline[field.key])) items.push({ config_key: field.key, value })
    } catch (caught) {
      validation[field.key] = isJson(field) && caught instanceof SyntaxError ? 'JSON 格式无效' : caught.message
      activeGroup.value = field.group
    }
  }
  if (Object.keys(validation).length) {
    error.value = '请修正字段错误；整批尚未提交'
    return
  }
  if (!items.length) {
    status.value = '没有修改，无需保存'
    return
  }
  busy.value = true
  saving.value = true
  try {
    const confirmed = await putConfig(items)
    await applyConfiguration(confirmed)
    fill(confirmed.items.map(item => item.config_key))
    status.value = '已保存，后续操作使用新配置'
    await read()
  } catch (caught) {
    showError(caught)
  } finally {
    saving.value = false
    busy.value = false
  }
}

async function resetField(key) {
  const field = fields.value.find(item => item.key === key)
  if (busy.value || unauthorized.value || readFailed.value || field?.source === 'factory') return
  busy.value = true
  error.value = ''
  status.value = ''
  try {
    const confirmed = await deleteConfigKey(key)
    await applyConfiguration({ items: [{
      ...configuration.items.find(item => item.config_key === key),
      config_key: confirmed.config_key,
      value: confirmed.value,
      source: confirmed.fallback_source,
      updated_at: null
    }] })
    fill([key])
    delete validation[key]
    status.value = `已恢复默认，回退来源：${confirmed.fallback_source}`
    await read()
  } catch (caught) {
    showError(caught)
  } finally {
    busy.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.settings {
  max-width: 1120px;
  min-width: 0;
  margin: 0 auto;
}
.section-heading {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.section-heading h2 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.section-heading span,
.hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  line-height: 1.65;
  overflow-wrap: anywhere;
}
.notice {
  margin: 12px 0;
  overflow-wrap: anywhere;
}
.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  padding: 4px 0;
}
.config-field {
  min-width: 0;
  margin: 0;
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
}
.field-body,
.editor {
  width: 100%;
  min-width: 0;
}
.config-key {
  display: block;
  margin-bottom: 10px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.json-hint {
  margin: 4px 0;
}
.field-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-top: 12px;
}
.source {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.updated-at {
  display: block;
  margin-top: 4px;
}
.actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
:deep(.el-form-item__content),
:deep(.el-tabs__content) {
  min-width: 0;
}
:deep(.el-form-item__error) {
  position: static;
}
@media (max-width: 640px) {
  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }
  .config-field {
    padding: 12px;
  }
}
</style>
