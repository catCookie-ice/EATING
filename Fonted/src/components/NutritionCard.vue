<script setup lang="ts">
defineProps<{
  carbohydrate?: number | null
  protein?: number | null
  fat?: number | null
}>()
</script>

<template>
  <div class="nutrition-card">
    <h3>营养成分</h3>
    <div class="nutrition-grid">
      <div class="nutrition-item">
        <span class="value">{{ carbohydrate ?? '-' }}</span>
        <span class="label">碳水(g)</span>
      </div>
      <div class="nutrition-item">
        <span class="value">{{ protein ?? '-' }}</span>
        <span class="label">蛋白质(g)</span>
      </div>
      <div class="nutrition-item">
        <span class="value">{{ fat ?? '-' }}</span>
        <span class="label">脂肪(g)</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nutrition-card {
  background: white;
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.nutrition-card h3 {
  color: #2e7d32;
  margin-bottom: 1rem;
}

.nutrition-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.nutrition-item {
  text-align: center;
  padding: 1rem;
  background: #f5fff5;
  border-radius: 12px;
}

.nutrition-item .value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #43a047;
}

.nutrition-item .label {
  color: #689f38;
  font-size: 0.85rem;
}
</style>
