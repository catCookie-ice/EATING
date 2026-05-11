<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useAuthStore } from '../stores'

const auth = useAuthStore()
</script>

<template>
  <header class="header">
    <div class="logo">
      <span class="logo-icon">🍽️</span>
      <span class="logo-text">EATING</span>
    </div>

    <!-- 用户导航 -->
    <nav class="nav" v-if="!auth.isAdmin">
      <RouterLink to="/" class="nav-link">首页</RouterLink>
      <RouterLink to="/recipes" class="nav-link">食谱</RouterLink>
      <RouterLink to="/ingredients" class="nav-link">食材</RouterLink>
      <RouterLink v-if="auth.isLoggedIn" to="/chat" class="nav-link">AI 聊天</RouterLink>
      <RouterLink v-if="auth.isLoggedIn" to="/profile" class="nav-link">我的</RouterLink>
      <RouterLink v-else to="/login" class="nav-link">登录</RouterLink>
    </nav>

    <!-- 管理员导航 -->
    <nav class="nav" v-else>
      <RouterLink to="/admin" class="nav-link">管理后台</RouterLink>
      <a @click="auth.logout()" class="nav-link logout">退出</a>
    </nav>
  </header>
</template>

<style scoped>
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
</style>
