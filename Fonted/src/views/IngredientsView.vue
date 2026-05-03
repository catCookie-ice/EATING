<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'

const ingredients = ref<any[]>([])
const loading = ref(false)

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchQuery = ref('')
const selectedCategory = ref('')

const categories = ["肉", "蛋", "蔬菜", "水果","奶制品","谷物",'豆类', '坚果',"海鲜","其他"]

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

async function fetchIngredients() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (selectedCategory.value) params.category = selectedCategory.value

    const res = await axios.get('/api/ingredients/', { params })
    ingredients.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// 分类筛选变更时，重置到第一页并重新请求
watch(selectedCategory, () => {
  page.value = 1
  fetchIngredients()
})

onMounted(fetchIngredients)

// 客户端搜索过滤（在当前页数据中搜索名称）
const filteredIngredients = computed(() => {
  if (!searchQuery.value) return ingredients.value
  return ingredients.value.filter(i => {
    const names = Array.isArray(i.name) ? i.name : [i.name]
    return names.some((n: string) => n.includes(searchQuery.value))
  })
})

function getIngredientEmoji(category: string): string {
  const emojiMap: Record<string, string> = {
    '蔬菜': '🥬', '水果': '🍎', '肉': '🥩', '蛋': '🥚',
    '奶制品': '🥛', '谷物': '🌾', '豆类': '🫘', '坚果': '🥜',
    '海鲜': '🦐', '其他': '🍽️'
  }
  return emojiMap[category] || emojiMap['其他']
}

function goToIngredient(id: number) {
  window.open(`/ingredients/${id}`, '_blank')
}

function getFirstImage(item: any): string | null {
  if (item.picture_url) {
    return item.picture_url
  }
  return null
}

function prevPage() {
  if (page.value > 1) {
    page.value--
    fetchIngredients()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    fetchIngredients()
  }
}

function goToPage(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    fetchIngredients()
  }
}
</script>

<template>
  <div class="ingredients-page">
    <div class="page-header">
      <h1>食材库</h1>
      <p>了解每种食材的营养价值</p>
    </div>

    <div class="filters">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索食材..."
        />
      </div>
      <div class="filter-group">
        <select v-model="selectedCategory">
          <option value="">全部分类</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
      </div>
    </div>

    <div class="ingredient-grid">
      <div
        v-for="item in filteredIngredients"
        :key="item.id"
        class="ingredient-card"
        @click="goToIngredient(item.id)"
      >
        <div class="ingredient-image">
          <img v-if="getFirstImage(item)" :src="getFirstImage(item)" :alt="Array.isArray(item.name) ? item.name[0] : item.name" class="cover-img" loading="lazy" />
          <span v-else class="ingredient-emoji">{{ getIngredientEmoji(item.category) }}</span>
        </div>
        <div class="ingredient-info">
          <h3>{{ Array.isArray(item.name) ? item.name.join(', ') : item.name }}</h3>
          <span class="category">{{ item.category }}</span>
          <div class="nutrition-brief">
            <span>碳水 {{ item.carbohydrate }}g</span>
            <span>蛋白 {{ item.protein }}g</span>
            <span>脂肪 {{ item.fat }}g</span>
          </div>
          <div class="ingredient-tags">
            <span v-if="item.is_halal" class="tag halal">清真</span>
            <span v-if="item.is_allergen" class="tag allergen">易过敏</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="filteredIngredients.length === 0 && !loading" class="empty-state">
      <span class="empty-icon">🥬</span>
      <p>暂无食材</p>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button class="page-btn" :disabled="page <= 1" @click="prevPage">上一页</button>
      <button
        v-for="p in totalPages"
        :key="p"
        class="page-btn"
        :class="{ active: p === page }"
        @click="goToPage(p)"
      >{{ p }}</button>
      <button class="page-btn" :disabled="page >= totalPages" @click="nextPage">下一页</button>
      <span class="page-info">共 {{ total }} 条</span>
    </div>
  </div>
</template>

<style scoped>
.page-header {
  text-align: center;
  margin-bottom: 2rem;
}

.page-header h1 {
  color: #2e7d32;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.page-header p {
  color: #689f38;
}

.filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.search-box {
  flex: 1;
  min-width: 200px;
}

.search-box input {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
}

.search-box input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.filter-group select {
  padding: 0.8rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  cursor: pointer;
}

.ingredient-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
}

.ingredient-card {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
}

.ingredient-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(76, 175, 80, 0.2);
}

.ingredient-image {
  height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
  overflow: hidden;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 12px;
}

.ingredient-image .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ingredient-emoji {
  font-size: 3rem;
}

.ingredient-info h3 {
  color: #2e7d32;
  font-size: 1rem;
  margin-bottom: 0.3rem;
}

.category {
  display: inline-block;
  font-size: 0.8rem;
  color: #689f38;
  background: #e8f5e9;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  margin-bottom: 0.8rem;
}

.nutrition-brief {
  display: flex;
  gap: 0.8rem;
  font-size: 0.8rem;
  color: #78909c;
  margin-bottom: 0.8rem;
}

.ingredient-tags {
  display: flex;
  gap: 0.3rem;
}

.tag {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
}

.tag.halal {
  background: #e3f2fd;
  color: #1976d2;
}

.tag.allergen {
  background: #ffebee;
  color: #d32f2f;
}

.empty-state {
  text-align: center;
  padding: 4rem;
  color: #78909c;
}

.empty-icon {
  font-size: 4rem;
  display: block;
  margin-bottom: 1rem;
}

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

@media (max-width: 1024px) {
  .ingredient-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .ingredient-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
