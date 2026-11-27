<template>
  <div
    v-if="items.length"
    class="file-grid"
  >
    <article
      v-for="item in items"
      :key="item.name"
      class="file-card"
    >
      <span class="file-kind">{{ kindOf(item.name) }}</span>
      <div class="file-copy">
        <strong>{{ item.label || prettyName(item.name) }}</strong>
        <small>{{ item.meta || item.name }}</small>
      </div>
      <el-dropdown
        v-if="item.formats?.length"
        :disabled="item.disabled"
        @command="ext => $emit('download', chooseFormat(item, ext))"
      >
        <el-button
          size="small"
          :data-testid="item.testid"
          :disabled="item.disabled"
        >
          下载
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="format in item.formats"
              :key="format.ext"
              :command="format.ext"
            >
              {{ format.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button
        v-else-if="item.download !== false"
        size="small"
        :data-testid="item.testid"
        :disabled="item.disabled"
        @click="$emit('download', item)"
      >
        下载
      </el-button>
    </article>
  </div>
  <div
    v-else
    class="ui-empty file-empty"
  >
    <strong>暂无结果文件</strong>
    <p>任务完成并生成产物后，结果文件会自动出现在这里。</p>
  </div>
</template>

<script setup>
defineOptions({ name: 'OutputFiles' })
defineProps({
  items: { type: Array, default: () => [] }
})
defineEmits(['download'])

function chooseFormat (item, ext) {
  const format = (item.formats || []).find(entry => entry.ext === ext)
  return { ...item, name: format?.name || item.name, format: ext }
}

function extension (name) {
  const match = String(name || '').match(/\.([a-z0-9]+)$/i)
  return match ? match[1].toLowerCase() : ''
}

function kindOf (name) {
  const ext = extension(name)
  if (ext === 'manifest' || name.endsWith('.manifest.json')) return '说明'
  if (ext === 'png') return '图表'
  if (ext === 'xlsx') return 'XLSX'
  if (ext === 'csv') return 'CSV'
  if (ext === 'json') return '数据'
  if (ext === 'zip') return 'ZIP'
  if (ext === 'md') return '文档'
  return (ext || '文件').toUpperCase()
}

function prettyName (name) {
  const raw = String(name || '')
  if (raw.endsWith('.manifest.json')) return '说明文件'
  if (raw.includes('predictions')) return '预测结果'
  if (raw.includes('train_testset')) return '测试集'
  if (raw.includes('clean_dataset')) return '清洗结果'
  if (raw.includes('collected_commits')) return '收集结果'
  if (raw.includes('model_package')) return '模型包'
  if (raw.includes('metrics')) return '评估指标'
  if (raw.includes('confusion')) return '混淆矩阵'
  if (raw.includes('report')) return '评估报告'
  if (raw.includes('evidence')) return '定位证据'
  if (raw.includes('suggestions')) return '修复建议'
  if (raw.includes('localization')) return '定位结果'
  if (raw.includes('compare')) return '模型对比'
  return raw
}
</script>
