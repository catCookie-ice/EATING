<script setup lang="ts">
import { RouterView, RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from './stores'
import { computed, onMounted } from 'vue'
import { watch } from 'vue'

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

// 使用 computed 确保响应式
const isAdmin = computed(() => auth.isAdmin)
const isSuperAdmin = computed(() => auth.adminLevel === 0)
const isNormalAdmin = computed(() => auth.adminLevel === 1)

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
      <header class="header" v-if="!hideNav">
        <div class="logo">
          <span class="logo-icon">🍽️</span>
          <span class="logo-text">EATING</span>
        </div>

        <!-- 用户导航 -->
        <nav class="nav" v-if="!isAdmin">
          <RouterLink to="/" class="nav-link">首页</RouterLink>
          <RouterLink to="/recipes" class="nav-link">食谱</RouterLink>
          <RouterLink to="/ingredients" class="nav-link">食材</RouterLink>
          <RouterLink v-if="auth.isLoggedIn" to="/profile" class="nav-link">我的</RouterLink>
          <RouterLink v-else to="/login" class="nav-link">登录</RouterLink>
        </nav>

        <!-- 管理员导航 -->
        <nav class="nav" v-else>
          <RouterLink to="/profile" class="nav-link">个人中心</RouterLink>
          <RouterLink to="/admin" class="nav-link">管理后台</RouterLink>
          <a @click="auth.logout()" class="nav-link logout">退出</a>
        </nav>
      </header>
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

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 20px rgba(76, 175, 80, 0.15);
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.logo-icon {
  font-size: 1.8rem;
}

.logo-text {
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, #43a047, #2e7d32);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.nav {
  display: flex;
  gap: 1.5rem;
}

.nav-link {
  color: #2e7d32;
  text-decoration: none;
  font-weight: 500;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.nav-link:hover {
  background: rgba(76, 175, 80, 0.1);
}

.nav-link.router-link-active {
  background: #4caf50;
  color: white;
}

.nav-link.logout {
  color: #f44336;
}

.nav-link.logout:hover {
  background: rgba(244, 67, 54, 0.1);
}

.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}
</style>
