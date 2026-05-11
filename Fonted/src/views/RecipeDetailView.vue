<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'
import { getRecipeEmoji, getFirstImage } from '../utils/recipe'
import NutritionCard from '../components/NutritionCard.vue'
import TasteBars from '../components/TasteBars.vue'
import MaterialsList from '../components/MaterialsList.vue'
import SeasoningsList from '../components/SeasoningsList.vue'
import StepsList from '../components/StepsList.vue'
import AllergenAlert from '../components/AllergenAlert.vue'

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
    let res
    // 已登录用户尝试获取完整详情（包含可能封禁的食谱）
    if (authStore.isLoggedIn) {
      try {
        res = await axios.get(`/api/recipes/${id}/detail`, {
          headers: { Authorization: `Bearer ${authStore.token}` }
        })
      } catch (e: any) {
        // 如果是封禁的食谱403错误，则尝试获取公开版本
        if (e.response?.status === 403) {
          res = await axios.get(`/api/recipes/${id}`)
        } else {
          throw e
        }
      }
    } else {
      res = await axios.get(`/api/recipes/${id}`)
    }
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

function getFirstImageLocal(): string | null {
  return getFirstImage(recipe.value)
}

// 转换逻辑已移至子组件中
</script>

<template>
  <div class="recipe-detail" v-if="recipe">

    <div class="recipe-header">
      <div class="recipe-emoji-large">
        <img v-if="getFirstImageLocal()" :src="getFirstImageLocal()" :alt="recipe.name" class="cover-img" loading="lazy" />
        <span v-else>{{ getRecipeEmoji(recipe.name) }}</span>
      </div>
      <div class="recipe-title">
        <h1>{{ recipe.name }}</h1>
        <div class="recipe-tags">
          <span v-if="recipe.is_halal" class="tag halal">清真</span>
          <span class="tag cuisine">{{ recipe.cuisine }}</span>
          <span class="tag method">{{ recipe.method }}</span>
        </div>
        <p class="source">
          <template v-if="recipe.source === '系统'">来源: 系统</template>
          <template v-else-if="recipe.source_avatar_url">
            <img :src="recipe.source_avatar_url" class="source-avatar" loading="lazy" />
            来源: {{ recipe.source }}
          </template>
          <template v-else-if="recipe.source">来源: {{ recipe.source }}</template>
          <template v-else>来源: 用户</template>
        </p>
        <!-- 收藏按钮 -->
        <button class="btn-favorite" @click="toggleFavorite" :class="{ favorited: isFavorited }">
          {{ isFavorited ? '❤️ 已收藏' : '🤍 收藏' }}
        </button>
      </div>
    </div>

    <NutritionCard
      :carbohydrate="recipe.carbohydrate"
      :protein="recipe.protein"
      :fat="recipe.fat"
    />

    <TasteBars v-if="recipe.taste" :taste="recipe.taste" />

    <MaterialsList :materials="recipe.materials" />
    <SeasoningsList :seasonings="recipe.seasonings" />
    <StepsList :steps="recipe.steps" />

    <AllergenAlert v-if="recipe.allergens?.length" :allergens="recipe.allergens" />
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
  display: flex;
  align-items: center;
  justify-content: center;
  width: 200px;
  height: 200px;
  border-radius: 16px;
  overflow: hidden;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
}

.recipe-emoji-large .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
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
  display: flex;
  align-items: center;
  gap: 0.3rem;
}

.source .source-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  object-fit: cover;
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
}
</style>
