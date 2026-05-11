<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  taste: Record<string, number>
}>()

const items = computed(() => {
  const labels: Record<string, string> = { sour: '酸', sweet: '甜', bitter: '苦', spicy: '辣', salty: '咸' }
  return Object.keys(props.taste).map(key => ({
    label: labels[key] || key,
    value: props.taste[key]
  }))
})
</script>

<template>
  <div class="recipe-section">
    <h3>口味占比</h3>
    <div class="taste-bars">
      <div class="taste-bar-row" v-for="item in items" :key="item.label">
        <span class="taste-bar-label">{{ item.label }}</span>
        <div class="taste-bar-track">
          <div class="taste-bar-fill" :style="{ width: (item.value * 100) + '%' }"></div>
        </div>
        <span class="taste-bar-value">{{ (item.value * 100).toFixed(0) }}%</span>
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

.taste-bars {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.taste-bar-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.taste-bar-label {
  min-width: 2rem;
  font-size: 0.9rem;
  color: #555;
  text-align: center;
}

.taste-bar-track {
  flex: 1;
  height: 10px;
  background: #e0e0e0;
  border-radius: 5px;
  overflow: hidden;
}

.taste-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #81c784);
  border-radius: 5px;
  transition: width 0.3s ease;
}

.taste-bar-value {
  min-width: 3rem;
  font-size: 0.85rem;
  color: #666;
  text-align: right;
}
</style>
