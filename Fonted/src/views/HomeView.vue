<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { holidayConfigs } from '../config/holidays'

const router = useRouter()
const featuredRecipes = ref<any[]>([])

onMounted(async () => {
  const res = await axios.get('/api/recipes/', { params: { limit: 6 } })
  featuredRecipes.value = res.data
})

function goToRecipe(id: number) {
  window.open(`/recipes/${id}`, '_blank')
}

// 检查是否有匹配的节日配置
const holidayContent = computed(() => {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const today = `${month}-${day}`

  const match = holidayConfigs.find(h => h.time === today)
  return match?.content || ''
})

// 解析内容中的链接，返回片段数组
interface ContentPart {
  type: 'text' | 'link'
  text: string
  url?: string
}

function parseContent(content: string): ContentPart[] {
  const parts: ContentPart[] = []
  const regex = /\[([^\]]+)\]\(([^)]+)\)/g
  let lastIndex = 0
  let match

  while ((match = regex.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        text: content.slice(lastIndex, match.index)
      })
    }
    parts.push({
      type: 'link',
      text: match[1],
      url: match[2]
    })
    lastIndex = regex.lastIndex
  }

  if (lastIndex < content.length) {
    parts.push({
      type: 'text',
      text: content.slice(lastIndex)
    })
  }

  return parts
}

const contentParts = computed(() => parseContent(holidayContent.value))
const hasHoliday = computed(() => !!holidayContent.value)

function handleLinkClick(url: string) {
  router.push(url)
}
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">
          人生难以把握<br />
          <span class="highlight">美食妙手自成</span>
        </h1>
        <p class="hero-subtitle">
          <template v-if="hasHoliday">
            <template v-for="(part, idx) in contentParts" :key="idx">
              <a
                v-if="part.type === 'link'"
                class="holiday-link"
                @click="handleLinkClick(part.url!)"
              >
                {{ part.text }}
              </a>
              <span v-else>{{ part.text }}</span>
            </template>
          </template>
          <template v-else>
            精选食谱，营养食材，让每一餐都充满幸福感
          </template>
        </p>
        <div class="hero-buttons">
          <button class="btn-primary" @click="router.push('/recipes')">探索食谱</button>
          <button class="btn-secondary" @click="router.push('/ingredients')">查看食材</button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="floating-card card-1">🥗 轻食沙拉</div>
        <div class="floating-card card-2">🍲 营养汤品</div>
        <div class="floating-card card-3">🍜 美味主食</div>
      </div>
    </section>

    <section class="intro">
      <div class="divider-line">
        <span class="line"></span>
        <span class="divider-text">EATING</span>
        <span class="line"></span>
      </div>
    </section>

    <section class="featured">
      <h2 class="section-title">热门食谱</h2>
      <div class="recipe-grid">
        <div
          v-for="recipe in featuredRecipes"
          :key="recipe.id"
          class="recipe-card"
          @click="goToRecipe(recipe.id)"
        >
          <div class="recipe-image">
            <span class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h3>{{ recipe.name }}</h3>
            <p class="recipe-meta">
              <span v-if="recipe.cuisine">{{ recipe.cuisine }}</span>
              <span class="difficulty">难度 {{ recipe.difficulty }}/10</span>
            </p>
            <div class="recipe-tags">
              <span v-if="recipe.is_halal" class="tag halal">清真</span>
              <span class="tag method">{{ recipe.method || '家常' }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script lang="ts">
function getRecipeEmoji(name: string): string {
  const emojiMap: Record<string, string> = {
    '炒': '🍳',
    '煮': '🍲',
    '蒸': '🥟',
    '炸': '🍟',
    '烤': '🍕',
    '焖': '🍚',
    '凉拌': '🥗',
    '沙拉': '🥗',
    '汤': '🍜',
    '面': '🍜',
    '饭': '🍚',
    '肉': '🥩',
    '鱼': '🐟',
    '鸡': '🍗',
    '蔬': '🥬',
    '甜': '🍰',
    '默认': '🍽️'
  }
  for (const key in emojiMap) {
    if (name.includes(key)) return emojiMap[key]
  }
  return emojiMap['默认']
}
</script>

<style scoped>
.home {
  padding-bottom: 2rem;
}

.hero {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3rem;
  align-items: center;
  padding: 3rem 0;
}

.intro {
  padding: 0.5rem 0;
  text-align: center;
  margin-bottom: 2rem;
}

.divider-line {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  gap: 1.5rem;
}

.line {
  flex: 1;
  height: 2px;
  background: #2e7d32;
  max-width: 40%;
}

.divider-text {
  color: #2e7d32;
  font-size: 3rem;
  font-weight: 700;
  letter-spacing: 0.5em;
  white-space: nowrap;
}

.hero-content {
  animation: fadeInUp 0.6s ease-out;
}

.hero-title {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1.2;
  color: #1b5e20;
  margin-bottom: 1rem;
}

.hero-title .highlight {
  background: linear-gradient(135deg, #4caf50, #8bc34a);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.1rem;
  color: #558b2f;
  margin-bottom: 2rem;
  line-height: 1.8;
}

.hero-subtitle .holiday-link {
  color: #2e7d32;
  font-weight: 600;
  text-decoration: underline;
  text-decoration-color: #8bc34a;
  text-underline-offset: 3px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.hero-subtitle .holiday-link:hover {
  color: #1b5e20;
  text-decoration-color: #4caf50;
}

.hero-buttons {
  display: flex;
  gap: 1rem;
}

.btn-primary {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(76, 175, 80, 0.4);
}

.btn-secondary {
  background: white;
  color: #43a047;
  border: 2px solid #43a047;
  padding: 0.8rem 2rem;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: rgba(76, 175, 80, 0.1);
}

.hero-visual {
  position: relative;
  height: 300px;
  animation: fadeInRight 0.8s ease-out;
}

.floating-card {
  position: absolute;
  background: white;
  padding: 1rem 1.5rem;
  border-radius: 16px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
  font-weight: 600;
  color: #2e7d32;
  animation: float 3s ease-in-out infinite;
}

.card-1 {
  top: 20px;
  left: 20px;
  animation-delay: 0s;
}

.card-2 {
  top: 100px;
  right: 40px;
  animation-delay: 0.5s;
}

.card-3 {
  bottom: 20px;
  left: 60px;
  animation-delay: 1s;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.features {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2rem;
  padding: 3rem 0;
}

.feature {
  background: white;
  padding: 2rem;
  border-radius: 20px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
  transition: all 0.3s ease;
}

.feature:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 30px rgba(76, 175, 80, 0.2);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature h3 {
  color: #2e7d32;
  margin-bottom: 0.5rem;
}

.feature p {
  color: #689f38;
  font-size: 0.9rem;
}

.section-title {
  font-size: 1.8rem;
  color: #2e7d32;
  text-align: center;
  margin-bottom: 2rem;
  position: relative;
}

.section-title::after {
  content: '';
  display: block;
  width: 60px;
  height: 3px;
  background: linear-gradient(90deg, #4caf50, #8bc34a);
  margin: 0.5rem auto;
  border-radius: 2px;
}

.recipe-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
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
  height: 150px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.recipe-emoji {
  font-size: 4rem;
}

.recipe-info {
  padding: 1rem;
}

.recipe-info h3 {
  color: #2e7d32;
  font-size: 1.1rem;
  margin-bottom: 0.5rem;
}

.recipe-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  color: #78909c;
  margin-bottom: 0.5rem;
}

.recipe-tags {
  display: flex;
  gap: 0.5rem;
}

.tag {
  font-size: 0.75rem;
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
}

.tag.halal {
  background: #e3f2fd;
  color: #1976d2;
}

.tag.method {
  background: #fff3e0;
  color: #f57c00;
}

@media (max-width: 768px) {
  .hero {
    grid-template-columns: 1fr;
    text-align: center;
  }

  .hero-visual {
    display: none;
  }

  .recipe-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
