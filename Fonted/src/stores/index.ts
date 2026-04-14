import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const account = ref(localStorage.getItem('account') || '')
  const isAdmin = ref(false)
  const adminLevel = ref<number | null>(null)
  const nickname = ref('')
  const initialized = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  // 配置axios默认headers
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  async function login(accountVal: string, password: string) {
    const res = await axios.post('/api/auth/login', { account: accountVal, password: password })
    token.value = res.data.access_token
    account.value = res.data.account
    localStorage.setItem('token', token.value)
    localStorage.setItem('account', account.value)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    // 登录后立即验证身份
    await init()
    return res.data
  }

  async function register(data: any) {
    const res = await axios.post('/api/auth/register', data)
    return res.data
  }

  function logout() {
    token.value = ''
    account.value = ''
    isAdmin.value = false
    adminLevel.value = null
    nickname.value = ''
    initialized.value = false
    localStorage.removeItem('token')
    localStorage.removeItem('account')
    delete axios.defaults.headers.common['Authorization']
    router.push('/login')
  }

  async function init() {
    // 防止重复调用
    if (initialized.value) return

    if (token.value) {
      // 设置token到axios headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`

      // 先通过专用接口检查是否是管理员（不会累加 failed_admin_attempts）
      try {
        const checkRes = await axios.get('/api/auth/check-admin')
        if (checkRes.data.is_admin) {
          isAdmin.value = true
          adminLevel.value = checkRes.data.admin_level
          account.value = localStorage.getItem('account') || ''
          nickname.value = ''
          initialized.value = true
          return
        }
        // 不是管理员，继续检查用户
      } catch (e: any) {
        // 检查失败，继续检查用户
      }

      // 尝试获取用户信息
      try {
        const res = await axios.get('/api/users/me')
        isAdmin.value = false
        adminLevel.value = null
        account.value = res.data.account
        nickname.value = res.data.nickname || ''
        initialized.value = true
        return
      } catch (e: any) {
        // 用户信息获取失败，清除登录状态
        console.warn('登录状态已失效', e.response?.data?.detail || e.message)
      }
    }

    // 没有token或登录状态失效
    logout()
    initialized.value = true
  }

  return { token, account, isAdmin, adminLevel, nickname, isLoggedIn, initialized, login, register, logout, init }
})
