<script setup lang="ts">
defineProps<{
  page: number
  totalPages: number
  total: number
}>()

const emit = defineEmits<{
  pageChange: [page: number]
}>()
</script>

<template>
  <div v-if="totalPages > 1" class="pagination">
    <button
      class="page-btn"
      :disabled="page <= 1"
      @click="emit('pageChange', page - 1)"
    >上一页</button>
    <button
      v-for="p in totalPages"
      :key="p"
      class="page-btn"
      :class="{ active: p === page }"
      @click="emit('pageChange', p)"
    >{{ p }}</button>
    <button
      class="page-btn"
      :disabled="page >= totalPages"
      @click="emit('pageChange', page + 1)"
    >下一页</button>
    <span class="page-info">共 {{ total }} 条</span>
  </div>
</template>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  margin-top: 2rem;
  flex-wrap: wrap;
}

.page-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  background: white;
  color: #2e7d32;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled):not(.active) {
  border-color: #4caf50;
  background: #e8f5e9;
}

.page-btn.active {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border-color: #2e7d32;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  margin-left: 0.5rem;
  color: #78909c;
  font-size: 0.85rem;
}
</style>
