<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  steps: any[]
}>()

const items = computed(() => {
  if (!props.steps) return []
  return props.steps.map((item: any) => ({
    step: item.step || item.步骤,
    action: item.description || item.操作
  }))
})
</script>

<template>
  <div class="recipe-section">
    <h3>制作步骤</h3>
    <div class="steps-list">
      <div v-for="(step, idx) in items" :key="idx" class="step-item">
        <div class="step-header">
          <h4 class="step-title">{{ step.step }}</h4>
        </div>
        <div class="step-content">
          <p class="step-action">{{ step.action }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.recipe-section {
  background: white;
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.recipe-section h3 {
  color: #2e7d32;
  margin-bottom: 1rem;
}

.steps-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.step-item {
  padding: 1rem;
  background: #f5fff5;
  border-radius: 12px;
  margin-bottom: 1rem;
}

.step-header {
  border-bottom: 1px solid #c8e6c9;
  padding-bottom: 0.5rem;
  margin-bottom: 0.8rem;
}

.step-title {
  color: #2e7d32;
  font-size: 1.1rem;
  margin: 0;
}

.step-action {
  color: #37474f;
  line-height: 1.6;
}
</style>
