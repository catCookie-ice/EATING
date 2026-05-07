import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import router from '../router'

// 本地缓存 key 前缀
const CACHE_PREFIX = 'user_cache_'
const CACHE_NICKNAME_KEY = CACHE_PREFIX + 'nickname'
const CACHE_ACCOUNT_KEY = CACHE_PREFIX + 'account'
const CACHE_AVATAR_KEY = CACHE_PREFIX + 'avatar'

function saveUserCache(nickname: string, account: string, avatarUrl: string | null) {
  localStorage.setItem(CACHE_NICKNAME_KEY, nickname)
  localStorage.setItem(CACHE_ACCOUNT_KEY, account)
  localStorage.setItem(CACHE_AVATAR_KEY, avatarUrl || '')
}

function clearUserCache() {
  localStorage.removeItem(CACHE_NICKNAME_KEY)
  localStorage.removeItem(CACHE_ACCOUNT_KEY)
  localStorage.removeItem(CACHE_AVATAR_KEY)
}

function loadUserCache(): { nickname: string; account: string; avatarUrl: string } | null {
  const cachedNickname = localStorage.getItem(CACHE_NICKNAME_KEY)
  const cachedAccount = localStorage.getItem(CACHE_ACCOUNT_KEY)
  if (!cachedNickname && !cachedAccount) return null
  return {
    nickname: cachedNickname || '',
    account: cachedAccount || '',
    avatarUrl: localStorage.getItem(CACHE_AVATAR_KEY) || '',
  }
}

// axios 响应拦截器（只注册一次）：检测携带 token 的请求返回 401 时自动清除登录态
let interceptorRegistered = false

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const isAdmin = ref(false)
  const adminLevel = ref<number | null>(null)
  const nickname = ref('')
  const avatarUrl = ref<string | null>(null)
  const userInfo = ref<any>(null)  // 完整用户信息
  const initialized = ref(false)

  const isLoggedIn = computed(() => !!token.value)

  // account 从 localStorage 读取（登录时存入，不再解析 token）
  const account = ref(localStorage.getItem(CACHE_ACCOUNT_KEY) || '')

  // 配置axios默认headers
  if (token.value) {
    axios.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  // 注册 401 响应拦截器（全局只执行一次）
  if (!interceptorRegistered) {
    interceptorRegistered = true
    axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // 登录接口本身会返回 401（账号密码错误），不处理
        if (error.response?.status === 401 && error.config?.url !== '/api/auth/login') {
          const authHeader = error.config?.headers?.Authorization
          if (authHeader && authHeader.startsWith('Bearer ')) {
            clearUserCache()
            localStorage.removeItem('token')
            delete axios.defaults.headers.common['Authorization']
            router.push('/login')
          }
        }
        return Promise.reject(error)
      }
    )
  }

  async function login(accountVal: string, password: string) {
    const res = await axios.post('/api/auth/login', { account: accountVal, password: password })
    token.value = res.data.access_token
    account.value = res.data.account || accountVal
    localStorage.setItem('token', token.value)
    localStorage.setItem(CACHE_ACCOUNT_KEY, account.value)
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
    account.value = ''
    isAdmin.value = false
    adminLevel.value = null
    nickname.value = ''
    avatarUrl.value = null
    userInfo.value = null

    // 标记为未初始化，下次需要重新 init
    initialized.value = false

    // 清除本地缓存
    clearUserCache()

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

      // 先从本地缓存读取（优先显示，提升体验）
      const cache = loadUserCache()
      if (cache) {
        nickname.value = cache.nickname
        avatarUrl.value = cache.avatarUrl || null
      }

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

        // API成功返回后，刷新本地缓存
        saveUserCache(nickname.value, account.value, avatarUrl.value)

        initialized.value = true
        return
      } catch (e: any) {
        // 用户信息获取失败，清除登录状态（拦截器可能已处理）
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
