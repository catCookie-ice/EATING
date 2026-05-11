<script setup lang="ts">
import { getRecipeEmoji, getFirstImage } from '../utils/recipe'

const props = defineProps<{
  recipe: any
}>()

const emit = defineEmits<{
  click: [id: number]
}>()
</script>

<template>
  <div class="recipe-card" @click="emit('click', recipe.id)">
    <div class="recipe-image">
      <img
        v-if="getFirstImage(recipe)"
        :src="getFirstImage(recipe)"
        :alt="recipe.name"
        class="cover-img"
        loading="lazy"
      />
      <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
    </div>
    <div class="recipe-info">
      <h3>{{ recipe.name }}</h3>
      <div class="recipe-meta">
        <span>{{ recipe.cuisine || '家常' }}</span>
        <span class="difficulty">难度 {{ recipe.difficulty }}/10</span>
      </div>
      <div class="recipe-tags">
        <span v-if="recipe.is_halal" class="tag halal">清真</span>
        <span class="tag method">{{ recipe.method || '家常' }}</span>
        <span v-if="recipe.source === '系统'" class="tag official">官方</span>
        <span v-else-if="recipe.source" class="tag user-source">
          <img
            v-if="recipe.source_avatar_url"
            :src="recipe.source_avatar_url"
            class="source-avatar"
            loading="lazy"
          />
          {{ recipe.source }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
  justify-content: center;
  overflow: hidden;
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
</style>
