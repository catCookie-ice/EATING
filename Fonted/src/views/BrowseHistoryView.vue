<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

const browseHistory = ref<any[]>([])
const loading = ref(true)

onMounted(async () => {
  await authStore.init()
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  try {
    const res = await axios.get('/api/users/me')
    const history = res.data.browse_history || []
    // 获取每个食谱的详情
    const recipesPromises = history.map(async (h: any) => {
      try {
        const recipeRes = await axios.get(`/api/recipes/${h.recipe_id}`)
        return {
          ...recipeRes.data,
          浏览时间: h.浏览时间
        }
      } catch {
        return null
      }
    })
    const recipes = await Promise.all(recipesPromises)
    browseHistory.value = recipes.filter(r => r !== null)
  } catch (e) {
    console.error('获取浏览记录失败', e)
  } finally {
    loading.value = false
  }
})

function goToRecipe(id: number) {
  window.open(`/recipes/${id}`, '_blank')
}

function getRecipeEmoji(name: string): string {
  const emojiMap: Record<string, string> = {
    '炒': '🍳', '煮': '🍲', '蒸': '🥟', '炸': '🍟', '烤': '🍕',
    '焖': '🍚', '凉拌': '🥗', '沙拉': '🥗', '汤': '🍜', '默认': '🍽️'
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

function formatTime(timeStr: string): string {
  if (!timeStr) return ''
  const date = new Date(timeStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const hours = Math.floor(diff / (1000 * 60 * 60 * 24))
  if (hours < 1) return '刚刚'
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return timeStr.split('T')[0]
}

function goBack() {
  router.push('/profile')
}
</script>

<template>
  <div class="browse-history-page">
    <div class="page-header">
      <button class="btn-back" @click="goBack">← 返回</button>
      <h2>浏览记录</h2>
    </div>

    <div class="recipe-grid" v-if="browseHistory.length && !loading">
      <div
        v-for="recipe in browseHistory"
        :key="recipe.id"
        class="recipe-card"
        @click="goToRecipe(recipe.id)"
      >
        <div class="recipe-image">
          <img v-if="getFirstImage(recipe)" :src="getFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
          <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
        </div>
        <div class="recipe-info">
          <h4>{{ recipe.name }}</h4>
          <div class="recipe-tags">
            <span class="tag difficulty">难度 {{ recipe.difficulty }}</span>
            <span class="tag cuisine">{{ recipe.cuisine }}</span>
            <span v-if="recipe.source === '系统'" class="tag official">官方</span>
            <span v-else-if="recipe.source" class="tag user-source">
              <img v-if="recipe.source_avatar_url" :src="recipe.source_avatar_url" class="source-avatar" loading="lazy" />
              {{ recipe.source }}
            </span>
          </div>
          <p class="browse-time">{{ formatTime(recipe.浏览时间) }}</p>
        </div>
      </div>
    </div>

    <div v-else-if="loading" class="loading">
      <p>加载中...</p>
    </div>

    <div v-else class="empty">
      <p>还没有浏览过任何食谱</p>
      <button class="btn-explore" @click="router.push('/recipes')">去逛逛</button>
    </div>
  </div>
</template>

<style scoped>
.browse-history-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.btn-back {
  background: #f5f5f5;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #333;
}

.btn-back:hover {
  background: #e0e0e0;
}

.page-header h2 {
  color: #2e7d32;
}

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.recipe-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
}

.recipe-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.2);
}

.recipe-image {
  height: 100px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.recipe-image .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.recipe-emoji {
  font-size: 2.5rem;
}

.recipe-info {
  padding: 0.8rem;
}

.recipe-info h4 {
  color: #2e7d32;
  font-size: 0.9rem;
  margin-bottom: 0.3rem;
}

.recipe-tags {
  display: flex;
  gap: 0.3rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  background: #f5f5f5;
  color: #666;
}

.tag.cuisine {
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
  width: 14px;
  height: 14px;
  border-radius: 50%;
  object-fit: cover;
}

.browse-time {
  font-size: 0.75rem;
  color: #999;
  margin-top: 0.3rem;
}

.loading {
  text-align: center;
  padding: 4rem;
  color: #78909c;
}

.empty {
  text-align: center;
  padding: 4rem;
  background: white;
  border-radius: 12px;
  color: #78909c;
}

.empty p {
  margin-bottom: 1rem;
}

.btn-explore {
  background: #4caf50;
  color: white;
  border: none;
  padding: 0.8rem 1.5rem;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 500;
}

.btn-explore:hover {
  background: #43a047;
}

@media (max-width: 600px) {
  .recipe-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>