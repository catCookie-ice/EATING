import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import router from '../router'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const isAdmin = ref(false)
  const adminLevel = ref<number | null>(null)
  const nickname = ref('')
  const avatarUrl = ref<string | null>(null)
  const userInfo = ref<any>(null)  // 完整用户信息
  const initialized = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  // 从token中解析account（JWT payload中的sub字段）
  function getAccountFromToken(): string {
    try {
      const payload = token.value.split('.')[1]
      if (payload) {
        const decoded = JSON.parse(atob(payload))
        return decoded.sub || ''
      }
    } catch (e) {
      console.error('解析token失败', e)
    }
    return ''
  }

  // 响应式account（从token解析）
  const account = computed(() => getAccountFromToken())

  // 配置axios默认headers
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  async function login(accountVal: string, password: string) {
    const res = await axios.post('/api/auth/login', { account: accountVal, password: password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    // 登录后强制重新初始化（可能之前已经 initialized，需强制刷新身份）
    await init(true)
    return res.data
  }

  async function register(data: any) {
    const res = await axios.post('/api/auth/register', data)
    return res.data
  }

  function logout() {
    // 清除所有用户状态
    token.value = ''
    isAdmin.value = false
    adminLevel.value = null
    nickname.value = ''
    avatarUrl.value = null
    userInfo.value = null

    // 标记为已初始化（退出后需要重新初始化）
    initialized.value = false

    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
    router.push('/login')
  }

  async function init(force: boolean = false) {
    // 防止重复调用（除非强制刷新）
    if (initialized.value && !force) return

    if (token.value) {
      // 设置token到axios headers
      axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`

      // 先通过专用接口检查是否是管理员（不会累加 failed_admin_attempts）
      try {
        const checkRes = await axios.get('/api/auth/check-admin')
        if (checkRes.data.is_admin) {
          isAdmin.value = true
          adminLevel.value = checkRes.data.admin_level
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
        nickname.value = res.data.nickname || ''
        avatarUrl.value = res.data.avatar_url || null
        userInfo.value = res.data  // 保存完整用户信息
        initialized.value = true
        return
      } catch (e: any) {
        // 用户信息获取失败，清除登录状态
        console.warn('登录状态已失效', e.response?.data?.detail || e.message)
      }
    }

    // 没有token，设置已初始化状态（不自动登出，避免循环）
    if (!token.value) {
      initialized.value = true
      return
    }

    // 有token但登录状态失效
    logout()
    initialized.value = true
  }

  return { token, account, isAdmin, adminLevel, nickname, avatarUrl, userInfo, isLoggedIn, initialized, login, register, logout, init }
})
