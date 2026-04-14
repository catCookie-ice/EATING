<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const router = useRouter()
const ingredient = ref<any>(null)
const relatedRecipes = ref<any[]>([])
const loading = ref(true)
const activeTab = ref('nutrition')

onMounted(async () => {
  const id = Number(route.params.id)
  // 获取食材详情
  const res = await axios.get(`/api/ingredients/${id}`)
  ingredient.value = res.data
  document.title = `${Array.isArray(ingredient.value.name) ? ingredient.value.name.join(', ') : ingredient.value.name} - EATING`

  // 获取使用该食材的食谱
  try {
    const recipesRes = await axios.get(`/api/recipes-search/by-ingredient?ingredient_id=${id}`)
    relatedRecipes.value = recipesRes.data
  } catch (e) {
    console.error('获取相关食谱失败', e)
  }

  loading.value = false
})

function getIngredientEmoji(category: string): string {
  const emojiMap: Record<string, string> = {
    '蔬菜': '🥬', '水果': '🍎', '肉类': '🥩', '蛋类': '🥚',
    '奶制品': '🥛', '谷物': '🌾', '豆类': '🫘', '坚果': '🥜',
    '海鲜': '🦐', '其他': '🍽️'
  }
  return emojiMap[category] || emojiMap['其他']
}

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
</script>

<template>
  <div class="ingredient-detail" v-if="ingredient">
    <div class="ingredient-header">
      <div class="ingredient-emoji-large">
        {{ getIngredientEmoji(ingredient.category) }}
      </div>
      <div class="ingredient-title">
        <h1>{{ Array.isArray(ingredient.name) ? ingredient.name.join(', ') : ingredient.name }}</h1>
        <span class="category-tag">{{ ingredient.category }}</span>
        <div class="ingredient-tags">
          <span v-if="ingredient.is_halal" class="tag halal">清真</span>
          <span v-if="ingredient.is_allergen" class="tag allergen">易过敏</span>
        </div>
      </div>
    </div>

    <!-- 选项卡 -->
    <div class="tabs">
      <button class="tab" :class="{ active: activeTab === 'nutrition' }" @click="activeTab = 'nutrition'">
        营养成分
      </button>
      <button class="tab" :class="{ active: activeTab === 'recipes' }" @click="activeTab = 'recipes'">
        食谱 ({{ relatedRecipes.length }})
      </button>
    </div>

    <!-- 营养成分内容 -->
    <div v-if="activeTab === 'nutrition'" class="tab-content">
      <div class="nutrition-card">
        <h3>营养成分（每500g）</h3>
        <div class="nutrition-grid">
          <div class="nutrition-item">
            <span class="value">{{ ingredient.carbohydrate }}</span>
            <span class="label">碳水(g)</span>
          </div>
          <div class="nutrition-item">
            <span class="value">{{ ingredient.protein }}</span>
            <span class="label">蛋白质(g)</span>
          </div>
          <div class="nutrition-item">
            <span class="value">{{ ingredient.fat }}</span>
            <span class="label">脂肪(g)</span>
          </div>
        </div>
      </div>

      <div class="detail-section" v-if="ingredient.vitamins?.length">
        <h3>维生素</h3>
        <div class="tag-list">
          <span v-for="v in ingredient.vitamins" :key="v" class="tag vitamin">{{ v }}</span>
        </div>
      </div>

      <div class="detail-section" v-if="ingredient.minerals?.length">
        <h3>矿物质</h3>
        <div class="tag-list">
          <span v-for="m in ingredient.minerals" :key="m" class="tag mineral">{{ m }}</span>
        </div>
      </div>
    </div>

    <!-- 食谱内容 -->
    <div v-if="activeTab === 'recipes'" class="tab-content">
      <div v-if="relatedRecipes.length" class="recipe-grid">
        <div
          v-for="recipe in relatedRecipes"
          :key="recipe.id"
          class="recipe-card"
          @click="goToRecipe(recipe.id)"
        >
          <div class="recipe-image">
            <span class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h4>{{ recipe.name }}</h4>
            <div class="recipe-tags">
              <span class="tag">难度 {{ recipe.difficulty }}</span>
              <span class="tag cuisine">{{ recipe.cuisine }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty">
        <p>暂无使用该食材的食谱</p>
      </div>
    </div>
  </div>

  <div v-else-if="!loading" class="not-found">
    <p>食材未找到</p>
  </div>

  <div v-else class="loading">
    <p>加载中...</p>
  </div>
</template>

<style scoped>
.ingredient-detail {
  max-width: 800px;
  margin: 0 auto;
}

.ingredient-header {
  display: flex;
  gap: 2rem;
  align-items: center;
  margin-bottom: 2rem;
  padding: 2rem;
  background: white;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.ingredient-emoji-large {
  font-size: 6rem;
}

.ingredient-title h1 {
  color: #2e7d32;
  font-size: 1.8rem;
  margin-bottom: 0.5rem;
}

.category-tag {
  display: inline-block;
  background: #e8f5e9;
  color: #388e3c;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.9rem;
}

.ingredient-tags {
  margin-top: 0.8rem;
}

.tag {
  font-size: 0.8rem;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  margin-right: 0.5rem;
}

.tag.halal {
  background: #e3f2fd;
  color: #1976d2;
}

.tag.allergen {
  background: #ffebee;
  color: #d32f2f;
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

.detail-section {
  background: white;
  border-radius: 20px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.detail-section h3 {
  color: #2e7d32;
  margin-bottom: 1rem;
}

.tag-list {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag.vitamin {
  background: #fff3e0;
  color: #f57c00;
}

.tag.mineral {
  background: #e3f2fd;
  color: #1976d2;
}

.not-found, .loading {
  text-align: center;
  padding: 4rem;
  color: #78909c;
}

/* 选项卡样式 */
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.tab {
  flex: 1;
  padding: 0.8rem;
  background: white;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab:hover {
  background: #e8f5e9;
}

.tab.active {
  background: #4caf50;
  color: white;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 食谱卡片样式 */
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

.recipe-tags .tag {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 8px;
  background: #f5f5f5;
  color: #666;
}

.recipe-tags .tag.cuisine {
  background: #fff3e0;
  color: #f57c00;
}

.empty {
  text-align: center;
  padding: 3rem;
  background: white;
  border-radius: 12px;
  color: #78909c;
}
</style>
