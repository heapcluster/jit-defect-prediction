<template>
  <section class="section-card" :class="{ disabled }">
    <header class="card-head">
      <div class="head-main">
        <span v-if="index" class="step-no">{{ index }}</span>
        <div>
          <h2>{{ title }}</h2>
          <p v-if="description" class="desc">{{ description }}</p>
        </div>
      </div>
      <div class="head-aside">
        <slot name="aside" />
      </div>
    </header>
    <div class="card-body">
      <slot />
    </div>
    <footer v-if="$slots.footer" class="card-foot">
      <slot name="footer" />
    </footer>
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
  index: { type: String, default: '' },
  disabled: { type: Boolean, default: false }
})
</script>

<style scoped>
.section-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow 0.2s ease, opacity 0.2s ease;
}

.section-card:hover {
  box-shadow: var(--shadow);
}

.section-card.disabled {
  opacity: 0.55;
}

.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, #fbfdff, #ffffff);
}

.head-main {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 0;
}

.step-no {
  font-family: var(--mono);
  font-size: 11.5px;
  font-weight: 700;
  color: var(--primary-strong);
  background: var(--primary-soft);
  border: 1px solid rgba(15, 118, 110, 0.16);
  padding: 4px 8px;
  border-radius: 8px;
  margin-top: 1px;
  white-space: nowrap;
}

h2 {
  font-size: 15.5px;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.desc {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12.5px;
  line-height: 1.55;
}

.head-aside {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.card-body {
  padding: 20px;
}

.card-foot {
  padding: 14px 20px;
  border-top: 1px solid var(--border);
  background: var(--surface-muted);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .card-head {
    flex-direction: column;
  }

  .card-body {
    padding: 16px;
  }
}
</style>
