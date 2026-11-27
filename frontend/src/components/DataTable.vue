<template>
  <div class="ui-table-wrap data-table">
    <table
      class="ui-table"
      :data-testid="testId"
    >
      <thead>
        <tr>
          <th
            v-for="column in columns"
            :key="column.key"
            :style="column.width ? { width: column.width } : undefined"
            :class="{ 'is-numeric': column.align === 'right' }"
          >
            {{ column.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(row, index) in rows"
          :key="rowKey ? row[rowKey] : index"
          :class="{ 'data-table__row--clickable': clickable }"
          :data-testid="rowTestId"
          :tabindex="clickable ? 0 : undefined"
          @click="clickable && $emit('row-click', row)"
          @keydown.enter="clickable && $emit('row-click', row)"
          @keydown.space.prevent="clickable && $emit('row-click', row)"
        >
          <td
            v-for="column in columns"
            :key="column.key"
            :class="{
              'is-numeric': column.align === 'right',
              'data-table__cell--mono': column.mono
            }"
          >
            <slot
              :name="`cell.${column.key}`"
              :row="row"
              :value="row[column.key]"
              :index="index"
            >
              {{ display(row[column.key]) }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <p
      v-if="!rows.length"
      class="ui-empty data-table__empty"
    >
      {{ empty }}
    </p>
  </div>
</template>

<script setup>
defineOptions({ name: 'DataTable' })
defineProps({
  columns: { type: Array, required: true },
  rows: { type: Array, default: () => [] },
  empty: { type: String, default: '暂无数据' },
  rowKey: { type: String, default: '' },
  clickable: { type: Boolean, default: false },
  testId: { type: String, default: undefined },
  rowTestId: { type: String, default: undefined }
})
defineEmits(['row-click'])

function display(value) {
  if (value == null || value === '') return '—'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return value
}
</script>

<style scoped>
.data-table__row--clickable {
  cursor: pointer;
}
.data-table__row--clickable:hover,
.data-table__row--clickable:focus-visible {
  background: var(--ui-primary-soft);
}
.data-table__row--clickable:focus-visible {
  outline: 2px solid var(--ui-primary);
  outline-offset: -2px;
}
.is-numeric {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
