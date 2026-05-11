<script setup lang="ts">
import { RouterView, useRoute } from 'vue-router'
import { useAuthStore } from './stores'
import { computed, onMounted } from 'vue'
import { watch } from 'vue'
import NavBar from './components/NavBar.vue'

const auth = useAuthStore()
const route = useRoute()

// 监听路由变化，当跳转到login时立即标记为已初始化
watch(() => route.path, (newPath) => {
  if (newPath === '/login') {
    auth.initialized = true
  }
}, { immediate: true })

onMounted(() => {
  if (route.path !== '/login') {
    auth.init()
  }
})

// 判断是否应该隐藏导航栏（详情页）
const hideNav = computed(() => {
  const path = route.path
  return path.startsWith('/recipes/') || path.startsWith('/ingredients/')
})

// login页面不需要等待初始化
const showLoading = computed(() => {
  // login页面直接不显示loading
  if (route.path === '/login') return false
  // 没有token也不需要等待
  if (!auth.token) return false
  // 需要认证但未初始化
  return !auth.initialized
})
</script>

<template>
  <div class="app-container">
    <!-- Loading 状态：只在需要认证的页面显示 -->
    <div v-if="showLoading" class="loading-container">
      <div class="loading">加载中...</div>
    </div>

    <template v-else>
      <!-- 导航栏：详情页隐藏 -->
      <NavBar v-if="!hideNav" />
      <main class="main">
        <RouterView />
      </main>
    </template>
  </div>
</template>

<style scoped>
.app-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5fff5 0%, #e8f5e9 50%, #c8e6c9 100%);
}

.loading-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading {
  color: #4caf50;
  font-size: 1.2rem;
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}
</style>
