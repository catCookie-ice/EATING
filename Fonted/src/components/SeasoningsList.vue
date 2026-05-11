<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  seasonings: any[]
}>()

const items = computed(() => {
  if (!props.seasonings) return []
  return props.seasonings.map((item: any) => {
    const key = Object.keys(item)[0]
    return { 调料名: key, 用量: item[key] }
  })
})
</script>

<template>
  <div class="recipe-section">
    <h3>调味料</h3>
    <div class="list-grid">
      <div v-for="(item, idx) in items" :key="idx" class="list-item">
        <span class="item-name">{{ item.调料名 }}</span>
        <span class="item-weight">{{ item.用量 }}</span>
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

.list-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.8rem;
}

.list-item {
  display: flex;
  justify-content: space-between;
  padding: 0.8rem 1rem;
  background: #f5fff5;
  border-radius: 10px;
}

.item-name {
  color: #2e7d32;
  font-weight: 500;
}

.item-weight {
  color: #689f38;
}

@media (max-width: 600px) {
  .list-grid {
    grid-template-columns: 1fr;
  }
}
</style>
