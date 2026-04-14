<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const recipe = ref<any>(null)
const loading = ref(true)
const error = ref('')
const isFavorited = ref(false)

// 检查是否已收藏
async function checkFavorite() {
  if (!authStore.isLoggedIn) return
  try {
    const res = await axios.get('/api/users/me/favorites')
    isFavorited.value = res.data.some((f: any) => f.id === recipe.value?.id)
  } catch (e) {
    console.error('检查收藏状态失败', e)
  }
}

// 切换收藏状态
async function toggleFavorite() {
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  const id = Number(route.params.id)
  try {
    if (isFavorited.value) {
      await axios.delete(`/api/users/me/favorites/${id}`)
      isFavorited.value = false
    } else {
      await axios.post(`/api/users/me/favorites/${id}`)
      isFavorited.value = true
    }
  } catch (e) {
    console.error('操作收藏失败', e)
  }
}

onMounted(async () => {
  await authStore.init()
  try {
    const id = Number(route.params.id)
    const res = await axios.get(`/api/recipes/${id}`)
    recipe.value = res.data

    // 设置页面标题
    document.title = `${recipe.value.name} - EATING`

    // 登录用户记录浏览历史
    if (authStore.isLoggedIn) {
      try {
        await axios.post(`/api/users/me/browse/${id}`)
      } catch (e) {
        console.error('记录浏览历史失败', e)
      }
      // 检查是否已收藏
      await checkFavorite()
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '加载失败'
  } finally {
    loading.value = false
  }
})

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

// 转换材料格式：从 {key: value} 转为 {材料名: key, 重量: value}
function parseMaterials(materials: any[]): { 材料名: string; 重量: string }[] {
  if (!materials) return []
  return materials.map(item => {
    const key = Object.keys(item)[0]
    return { 材料名: key, 重量: item[key] }
  })
}

// 转换调料格式
function parseSeasonings(seasonings: any[]): { 调料名: string; 用量: string }[] {
  if (!seasonings) return []
  return seasonings.map(item => {
    const key = Object.keys(item)[0]
    return { 调料名: key, 用量: item[key] }
  })
}

// 转换步骤格式
function parseSteps(steps: any[]): { 步骤: number; 操作: string }[] {
  if (!steps) return []
  return steps.map(item => {
    return { 步骤: item.step || item.步骤, 操作: item.description || item.操作 }
  })
}
</script>

<template>
  <div class="recipe-detail" v-if="recipe">

    <div class="recipe-header">
      <div class="recipe-emoji-large">
        {{ getRecipeEmoji(recipe.name) }}
      </div>
      <div class="recipe-title">
        <h1>{{ recipe.name }}</h1>
        <div class="recipe-tags">
          <span v-if="recipe.is_halal" class="tag halal">清真</span>
          <span class="tag cuisine">{{ recipe.cuisine }}</span>
          <span class="tag method">{{ recipe.method }}</span>
        </div>
        <p class="source">来源: {{ recipe.source }}</p>
        <!-- 收藏按钮 -->
        <button class="btn-favorite" @click="toggleFavorite" :class="{ favorited: isFavorited }">
          {{ isFavorited ? '❤️ 已收藏' : '🤍 收藏' }}
        </button>
      </div>
    </div>

    <div class="nutrition-card">
      <h3>营养成分</h3>
      <div class="nutrition-grid">
        <div class="nutrition-item">
          <span class="value">{{ recipe.carbohydrate || '-' }}</span>
          <span class="label">碳水(g)</span>
        </div>
        <div class="nutrition-item">
          <span class="value">{{ recipe.protein || '-' }}</span>
          <span class="label">蛋白质(g)</span>
        </div>
        <div class="nutrition-item">
          <span class="value">{{ recipe.fat || '-' }}</span>
          <span class="label">脂肪(g)</span>
        </div>
      </div>
    </div>

    <div class="recipe-section">
      <h3>所需材料</h3>
      <div class="materials-list">
        <div v-for="(item, idx) in parseMaterials(recipe.materials)" :key="idx" class="material-item">
          <span class="material-name">{{ item.材料名 }}</span>
          <span class="material-weight">{{ item.重量 }}</span>
        </div>
      </div>
    </div>

    <div class="recipe-section">
      <h3>调味料</h3>
      <div class="seasonings-list">
        <div v-for="(item, idx) in parseSeasonings(recipe.seasonings)" :key="idx" class="seasoning-item">
          <span class="seasoning-name">{{ item.调料名 }}</span>
          <span class="seasoning-amount">{{ item.用量 }}</span>
        </div>
      </div>
    </div>

    <div class="recipe-section">
      <h3>制作步骤</h3>
      <div class="steps-list">
        <div v-for="(step, idx) in parseSteps(recipe.steps)" :key="idx" class="step-item">
          <div class="step-header">
            <h4 class="step-title">{{ step.步骤 }}</h4>
          </div>
          <div class="step-content">
            <p class="step-action">{{ step.操作 }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="recipe-section" v-if="recipe.allergens?.length">
      <h3>过敏提示</h3>
      <div class="allergens">
        <span v-for="a in recipe.allergens" :key="a" class="allergen-tag">{{ a }}</span>
      </div>
      <p class="allergen-disclaimer">本过敏列表仅为提醒，不代表所有过敏源，请结合自身情况排查过敏源。</p>
    </div>
  </div>

  <div v-else-if="loading" class="loading">
    <p>加载中...</p>
  </div>

  <div v-else-if="error" class="error">
    <p>{{ error }}</p>
  </div>
</template>

<style scoped>
.recipe-detail {
  max-width: 800px;
  margin: 0 auto;
}

.recipe-header {
  display: flex;
  gap: 2rem;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.recipe-emoji-large {
  font-size: 6rem;
}

.recipe-title h1 {
  color: #2e7d32;
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}

.recipe-tags {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.tag {
  font-size: 0.8rem;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
}

.tag.halal {
  background: #e3f2fd;
  color: #1976d2;
}

.tag.cuisine {
  background: #fff3e0;
  color: #f57c00;
}

.tag.method {
  background: #e8f5e9;
  color: #388e3c;
}

.source {
  color: #78909c;
  font-size: 0.9rem;
}

.btn-favorite {
  margin-top: 0.5rem;
  background: white;
  border: 2px solid #e0e0e0;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.btn-favorite:hover {
  border-color: #f44336;
}

.btn-favorite.favorited {
  background: #ffebee;
  border-color: #f44336;
  color: #f44336;
}

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

.materials-list, .seasonings-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.8rem;
}

.material-item, .seasoning-item {
  display: flex;
  justify-content: space-between;
  padding: 0.8rem 1rem;
  background: #f5fff5;
  border-radius: 10px;
}

.material-name, .seasoning-name {
  color: #2e7d32;
  font-weight: 500;
}

.material-weight, .seasoning-amount {
  color: #689f38;
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

.step-content {
  flex: 1;
}

.step-time {
  color: #f57c00;
  font-size: 0.85rem;
  margin-bottom: 0.3rem;
}

.step-action {
  color: #37474f;
  line-height: 1.6;
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

.loading {
  text-align: center;
  padding: 4rem;
  color: #78909c;
}

.error {
  text-align: center;
  padding: 4rem;
  color: #d32f2f;
}

@media (max-width: 600px) {
  .recipe-header {
    flex-direction: column;
    text-align: center;
  }

  .materials-list, .seasonings-list {
    grid-template-columns: 1fr;
  }
}
</style>
