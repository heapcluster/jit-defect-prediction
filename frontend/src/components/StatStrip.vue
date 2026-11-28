<template>
  <div class="stats">
    <div v-for="item in items" :key="item.label" class="stat">
      <div class="stat-label">{{ item.label }}</div>
      <div class="stat-value" :class="item.tone">
        {{ item.value ?? '—' }}
        <span v-if="item.unit" class="unit">{{ item.unit }}</span>
      </div>
      <div v-if="item.hint" class="stat-hint">{{ item.hint }}</div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] }
})
</script>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.stat {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 13px 15px;
  box-shadow: var(--shadow-sm);
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 600;
}

.stat-value {
  margin-top: 6px;
  font-size: 22px;
  font-weight: 750;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
}

.stat-value.primary {
  color: var(--primary-strong);
}

.stat-value.accent {
  color: var(--accent);
}

.stat-value.danger {
  color: var(--danger);
}

.unit {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-soft);
  margin-left: 2px;
}

.stat-hint {
  margin-top: 4px;
  font-size: 11.5px;
  color: var(--text-soft);
}
</style>
