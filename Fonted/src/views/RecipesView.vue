<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import RecipeCard from '../components/RecipeCard.vue'
import Pagination from '../components/Pagination.vue'
import { CUISINES } from '../config/constants'

const router = useRouter()
const recipes = ref<any[]>([])
const loading = ref(false)

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchQuery = ref('')
const selectedCuisine = ref('')
const selectedHalal = ref<boolean | null>(null)

const cuisines = CUISINES

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

async function fetchRecipes() {
  loading.value = true
  try {
    const params: Record<string, any> = { page: page.value, page_size: pageSize.value }
    if (selectedCuisine.value) params.cuisine = selectedCuisine.value
    if (selectedHalal.value !== null) params.is_halal = selectedHalal.value

    const res = await axios.get('/api/recipes/', { params })
    recipes.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

// 菜系/清真筛选变更时，重置到第一页并重新请求
watch([selectedCuisine, selectedHalal], () => {
  page.value = 1
  fetchRecipes()
})

onMounted(fetchRecipes)

// 客户端搜索过滤（在当前页数据中搜索）
const filteredRecipes = computed(() => {
  if (!searchQuery.value) return recipes.value
  return recipes.value.filter(r => r.name.includes(searchQuery.value))
})

function goToPage(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    fetchRecipes()
  }
}

function goToDetail(id: number) {
  window.open(`/recipes/${id}`, '_blank')
}
</script>

<template>
  <div class="recipes-page">
    <div class="page-header">
      <h1>食谱列表</h1>
      <p>发现美味健康的食谱</p>
    </div>

    <div class="filters">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索食谱..."
        />
      </div>
      <div class="filter-group">
        <select v-model="selectedCuisine">
          <option value="">全部菜系</option>
          <option v-for="c in cuisines" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="selectedHalal">
          <option :value="null">全部</option>
          <option :value="true">清真</option>
          <option :value="false">非清真</option>
        </select>
      </div>
    </div>

    <div class="recipe-grid">
      <RecipeCard
        v-for="recipe in filteredRecipes"
        :key="recipe.id"
        :recipe="recipe"
        @click="goToDetail"
      />
    </div>

    <div v-if="filteredRecipes.length === 0 && !loading" class="empty-state">
      <span class="empty-icon">🔍</span>
      <p>暂无食谱</p>
    </div>

    <!-- 分页 -->
    <Pagination
      v-if="totalPages > 1"
      :page="page"
      :total-pages="totalPages"
      :total="total"
      @page-change="goToPage"
    />
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
  transition: all 0.3s ease;
}

.search-box input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.filter-group {
  display: flex;
  gap: 0.5rem;
}

.filter-group select {
  padding: 0.8rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  background: white;
  cursor: pointer;
}

.filter-group select:focus {
  outline: none;
  border-color: #4caf50;
}

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 1.5rem;
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

@media (max-width: 1024px) {
  .recipe-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 768px) {
  .recipe-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
