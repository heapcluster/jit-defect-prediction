<template>
  <div>
    <PageHint text="用人工确认的标签评估预测质量，并按 F1 最优点校准阈值 —— 改完立即生效。">
      <el-radio-group
        v-model="labelSource"
        size="small"
        @change="load"
      >
        <el-radio-button value="manual">
          人工标签
        </el-radio-button>
        <el-radio-button value="szz">
          SZZ 对照
        </el-radio-button>
      </el-radio-group>
      <el-button
        size="small"
        type="primary"
        :loading="calibrating"
        @click="calibrate"
      >
        按标签校准
      </el-button>
      <el-button
        size="small"
        :loading="loading"
        @click="load"
      >
        刷新
      </el-button>
    </PageHint>

    <div class="stats">
      <StatCard
        label="精确率"
        :value="pct(quality.precision)"
        hint="判高风险的里有多少真缺陷"
      />
      <StatCard
        label="召回率"
        :value="pct(quality.recall)"
        hint="真缺陷里被捞出来多少"
      />
      <StatCard
        label="F1"
        :value="num(quality.f1)"
        hint="精确率与召回率的调和平均"
      />
      <StatCard
        label="误拦率"
        :value="pct(quality.false_discovery_rate)"
        hint="判高风险的里有多少其实不是缺陷（=1−精确率）"
      />
      <StatCard
        label="评估样本"
        :value="`${quality.evaluated}/${quality.labeled_total}`"
        hint="已比对 / 已标记"
      />
    </div>

    <el-alert
      v-if="!loading && quality.evaluated === 0"
      type="info"
      :closable="false"
      class="mb"
    >
      {{ labelSource === 'szz'
        ? 'SZZ 自动标签对照视图：只有 SZZ 标签且已有预测的提交才计入，结论不能作为验收依据。'
        : '还没有可评估的样本：先到「风险列表」打开几条提交，标记是否真的引入缺陷。' }}
    </el-alert>

    <div class="grid">
      <el-card shadow="never">
        <template #header>
          混淆矩阵（阈值 {{ quality.threshold }}）
        </template>
        <div class="matrix">
          <div class="cell">
            <b class="hit">{{ quality.tp }}</b>
            <span>真缺陷 · 判高</span>
          </div>
          <div class="cell">
            <b class="miss">{{ quality.fn }}</b>
            <span>真缺陷 · 漏判</span>
          </div>
          <div class="cell">
            <b class="false">{{ quality.fp }}</b>
            <span>非缺陷 · 误判</span>
          </div>
          <div class="cell">
            <b class="safe">{{ quality.tn }}</b>
            <span>非缺陷 · 判低</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          阈值
        </template>
        <div class="row">
          <span>当前高风险</span><b>{{ cfg.high_risk_threshold }}</b>
        </div>
        <div class="row">
          <span>当前中风险</span><b>{{ cfg.mid_risk_threshold }}</b>
        </div>
        <div class="row">
          <span>标签推荐</span><b>{{ quality.recommended_threshold ?? '样本不足' }}</b>
        </div>
        <el-button
          size="small"
          :disabled="quality.recommended_threshold == null"
          :loading="applying"
          @click="applyRecommended"
        >
          应用推荐阈值
        </el-button>
        <!-- 校准结果就地说明，不再单独占一张卡（它是一次性事件，刷新后已无意义） -->
        <p
          v-if="calibration && !calibration.applied"
          class="note"
        >
          {{ reasonText }}
        </p>
        <p
          v-else-if="calibration"
          class="note"
        >
          已校准：阈值 {{ calibration.before.threshold }} → <b>{{ calibration.after.threshold }}</b>，F1
          {{ num(calibration.before.f1) }} → <b>{{ num(calibration.after.f1) }}</b>
        </p>
        <p
          v-else
          class="note"
        >
          改完立即生效，同时影响风险等级与 PR 门禁。
        </p>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { getQuality, postCalibrate, getConfig, putConfig } from '../api'
import { ElMessage } from 'element-plus'
import { errText } from '../utils/errors'
import StatCard from '../components/StatCard.vue'
import PageHint from '../components/PageHint.vue'

const quality = reactive({
  model_name: null,
  threshold: 0.5,
  label_source: 'manual',
  labeled_total: 0,
  evaluated: 0,
  tp: 0,
  fp: 0,
  tn: 0,
  fn: 0,
  precision: null,
  recall: null,
  f1: null,
  false_discovery_rate: null,
  recommended_threshold: null
})
// manual = 人工标签（ground truth）；szz = 自动标签对照视图，不参与验收
const labelSource = ref('manual')
const cfg = reactive({ high_risk_threshold: null, mid_risk_threshold: null })
const calibration = ref(null)
const loading = ref(false)
const calibrating = ref(false)
const applying = ref(false)

function pct(v) {
  return v == null ? '—' : `${(v * 100).toFixed(1)}%`
}
function num(v) {
  return v == null ? '—' : Number(v).toFixed(2)
}

const reasonText = computed(() => {
  const reason = calibration.value?.reason
  if (reason === 'insufficient_labels') {
    return '样本不足（可评估少于 2 条，或标签只有单一类别），阈值未改动。'
  }
  if (reason === 'no_improvement') return '当前阈值已是 F1 最优点，无需调整。'
  if (reason === 'no_model') return '库内还没有模型预测，无法校准。'
  return '阈值未改动。'
})

async function load() {
  loading.value = true
  try {
    const [q, c] = await Promise.all([
      getQuality({ label_source: labelSource.value }),
      getConfig()
    ])
    Object.assign(quality, q)
    Object.assign(cfg, c)
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    loading.value = false
  }
}

async function calibrate() {
  calibrating.value = true
  try {
    calibration.value = await postCalibrate(null)
    ElMessage.success(
      calibration.value.applied ? '已按标签校准并生效' : '未改动阈值'
    )
    await load()
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    calibrating.value = false
  }
}

async function applyRecommended() {
  const high = quality.recommended_threshold
  if (high == null) return
  applying.value = true
  try {
    // mid 必须 <= high：取原 mid 与推荐值的较小者
    const mid = Math.min(cfg.mid_risk_threshold ?? 0, high)
    Object.assign(cfg, await putConfig(high, mid))
    ElMessage.success('阈值已更新并生效')
    await load()
  } catch (e) {
    ElMessage.error(errText(e))
  } finally {
    applying.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.mb {
  margin-bottom: 12px;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.cell {
  border: 1px solid #eef0f4;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  background: #fafbfc;
}
.cell b {
  font-size: 22px;
  font-family: monospace;
}
.cell span {
  font-size: 12px;
  color: #7c838c;
}
.hit {
  color: #4e9b68;
}
.miss {
  color: #d9484a;
}
.false {
  color: #d98a2b;
}
.safe {
  color: #6b7280;
}
.row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #f2f4f7;
  font-size: 13px;
}
.row:last-of-type {
  margin-bottom: 10px;
}
.note {
  margin: 10px 0 0;
  color: #9aa1ab;
  font-size: 12px;
  line-height: 1.6;
}

</style>
