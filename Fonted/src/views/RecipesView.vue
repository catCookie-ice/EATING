<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const recipes = ref<any[]>([])
const loading = ref(false)

const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const searchQuery = ref('')
const selectedCuisine = ref('')
const selectedHalal = ref<boolean | null>(null)

const cuisines = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "东北菜", "西北菜","家常菜","西餐", "日料", "韩餐", "东南亚菜", "家常菜","其他"
    ]

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

function prevPage() {
  if (page.value > 1) {
    page.value--
    fetchRecipes()
  }
}

function nextPage() {
  if (page.value < totalPages.value) {
    page.value++
    fetchRecipes()
  }
}

function goToPage(p: number) {
  if (p >= 1 && p <= totalPages.value) {
    page.value = p
    fetchRecipes()
  }
}

function goToDetail(id: number) {
  window.open(`/recipes/${id}`, '_blank')
}

function getRecipeEmoji(name: string): string {
  const emojiMap: Record<string, string> = {
    '炒': '🍳', '煮': '🍲', '蒸': '🥟', '炸': '🍟', '烤': '🍕',
    '焖': '🍚', '凉拌': '🥗', '沙拉': '🥗', '汤': '🍜', '面': '🍜',
    '饭': '🍚', '肉': '🥩', '鱼': '🐟', '鸡': '🍗', '蔬': '🥬', '默认': '🍽️'
  }
  for (const key in emojiMap) {
    if (name.includes(key)) return emojiMap[key]
  }
  return emojiMap['默认']
}

function getFirstImage(recipe: any): string | null {
  if (recipe.pictures_url && Array.isArray(recipe.pictures_url) && recipe.pictures_url.length > 0) {
    return recipe.pictures_url[0]
  }
  return null
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
      <div
        v-for="recipe in filteredRecipes"
        :key="recipe.id"
        class="recipe-card"
        @click="goToDetail(recipe.id)"
      >
        <div class="recipe-image">
          <img v-if="getFirstImage(recipe)" :src="getFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
          <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
        </div>
        <div class="recipe-info">
          <h3>{{ recipe.name }}</h3>
          <div class="recipe-meta">
            <span class="cuisine">{{ recipe.cuisine || '家常' }}</span>
            <span class="difficulty">难度 {{ recipe.difficulty }}</span>
          </div>
          <div class="recipe-tags">
            <span v-if="recipe.is_halal" class="tag halal">清真</span>
            <span class="tag method">{{ recipe.method || '家常' }}</span>
            <span v-if="recipe.source === '系统'" class="tag official">官方</span>
            <span v-else-if="recipe.source" class="tag user-source">
              <img v-if="recipe.source_avatar_url" :src="recipe.source_avatar_url" class="source-avatar" loading="lazy" />
              {{ recipe.source }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="filteredRecipes.length === 0 && !loading" class="empty-state">
      <span class="empty-icon">🔍</span>
      <p>暂无食谱</p>
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

.recipe-card {
  background: white;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
}

.recipe-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(76, 175, 80, 0.2);
}

.recipe-image {
  height: 140px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  display: flex;
  align-items: center;
  overflow: hidden; 
  justify-content: center;
}

.recipe-image .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.recipe-emoji {
  font-size: 3.5rem;
}

.recipe-info {
  padding: 1rem;
}

.recipe-info h3 {
  color: #2e7d32;
  font-size: 1rem;
  margin-bottom: 0.5rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.recipe-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  color: #78909c;
  margin-bottom: 0.5rem;
}

.recipe-tags {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
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

.tag.method {
  background: #fff3e0;
  color: #f57c00;
}

.tag.official {
  background: #e8f5e9;
  color: #388e3c;
}

.tag.user-source {
  background: #fce4ec;
  color: #c2185b;
  display: flex;
  align-items: center;
  gap: 0.2rem;
}

.tag .source-avatar {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  object-fit: cover;
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
