<script setup lang="ts">
defineProps<{
  allergens: string[]
}>()
</script>

<template>
  <div class="recipe-section">
    <h3>过敏提示</h3>
    <div class="allergens">
      <span v-for="a in allergens" :key="a" class="allergen-tag">{{ a }}</span>
    </div>
    <p class="allergen-disclaimer">本过敏列表仅为提醒，不代表所有过敏源，请结合自身情况排查过敏源。</p>
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

.allergens {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.allergen-tag {
  background: #ffebee;
  color: #d32f2f;
  padding: 0.4rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.allergen-disclaimer {
  margin-top: 0.8rem;
  font-size: 0.8rem;
  color: #78909c;
  font-style: italic;
}
</style>
