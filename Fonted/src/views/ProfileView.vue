<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

const myRecipes = ref<any[]>([])
const userInfo = ref<any>({})
const showRecipeForm = ref(false)
const editingRecipeId = ref<number | null>(null)

// 头像相关
const showAvatarModal = ref(false)
const avatarPreview = ref('')
const avatarFile = ref<File | null>(null)
const uploadingAvatar = ref(false)

// 是否是管理员
const isAdmin = computed(() => authStore.isAdmin)

// 食谱表单
const recipeForm = ref({
  name: '',
  cuisine: '川菜',
  difficulty: 5,
  method: '炒',
  steps: [{ step: '第一步', description: '' }],
  materials: [{ name: '', amount: '' }],
  seasonings: [{ name: '', amount: '' }],
  carbohydrate: 0,
  protein: 0,
  fat: 0,
  is_halal: false,
  allergens: [] as string[],
  vitamins: [] as string[],
  minerals: [] as string[],
  pictures_url: [] as string[]
})
let savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))

// 用于标记是否意外关闭（点击弹窗外部）
let isAccidentalClose = false

// 剪贴板数据
const clipboardData = ref<{type: 'recipe' | null, data: any}>({type: null, data: null})

const cuisineOptions = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "东北菜", "西北菜","家常菜","西餐", "日料", "韩餐", "东南亚菜", "家常菜","其他"
    ]
const methodOptions = ['炒', '煮', '蒸', '炸', '烤', '焖', '凉拌', '卤', '煎', '腌', '其他']
const newTag = ref('')
const tagType = ref<'allergens' | 'vitamins' | 'minerals'>('allergens')
const newAllergen = ref('')
const newVitamin = ref('')
const newMineral = ref('')

// 封面上传相关
const recipeCoverPreview = ref('')
const recipeCoverFile = ref<File | null>(null)
const uploadingCover = ref(false)

onMounted(async () => {
  await authStore.init()
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  // 复用 authStore 中的用户信息
  userInfo.value = authStore.userInfo || {
    account: authStore.account,
    nickname: authStore.nickname,
    avatar_url: authStore.avatarUrl
  }
  // 加载草稿
  loadDrafts()
  // 仅普通用户需要获取自己的食谱
  if (!isAdmin.value) {
    const res = await axios.get('/api/recipes/my')
    myRecipes.value = res.data
  }
})

// 加载草稿
function loadDrafts() {
  try {
    const draft = localStorage.getItem('recipe_draft')
    if (draft) {
      savedRecipeForm = JSON.parse(draft)
    }
  } catch (e) {
    console.error('加载草稿失败', e)
  }
}

// 监听弹窗关闭，意外关闭时自动保存草稿
watch(showRecipeForm, (newVal) => {
  if (!newVal && isAccidentalClose && recipeForm.value.name) {
    savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
    localStorage.setItem('recipe_draft', JSON.stringify(savedRecipeForm))
  }
  isAccidentalClose = false
})

// 关闭食谱表单
function closeRecipeForm() {
  showRecipeForm.value = false
  // 清除草稿
  clearRecipeDraft()
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

function getRecipeFirstImage(recipe: any): string | null {
  if (recipe.pictures_url && Array.isArray(recipe.pictures_url) && recipe.pictures_url.length > 0) {
    return recipe.pictures_url[0]
  }
  return null
}

function goToAdmin() {
  router.push('/admin')
}

function handleLogout() {
  authStore.logout()
  router.push('/Login')
}

// 头像点击处理
function onAvatarClick() {
  avatarPreview.value = userInfo.value.avatar_url || ''
  showAvatarModal.value = true
}

// 关闭头像弹窗
function closeAvatarModal() {
  showAvatarModal.value = false
  avatarFile.value = null
  avatarPreview.value = ''
}

// 解析剪贴板中的JSON数据
async function parseClipboard() {
  // 只在食谱弹窗打开时检测
  if (!showRecipeForm.value) {
    clipboardData.value = {type: null, data: null}
    return false
  }

  try {
    const text = await navigator.clipboard.readText()
    const data = JSON.parse(text)

    // 检测食谱格式
    if (data.name && data.materials && Array.isArray(data.materials) && data.seasonings) {
      clipboardData.value = {type: 'recipe', data}
      return true
    }
  } catch (e) {
    // 不是有效JSON，忽略
  }
  clipboardData.value = {type: null, data: null}
  return false
}

// 应用剪贴板数据到表单
async function applyClipboardData() {
  if (clipboardData.value.type === 'recipe' && clipboardData.value.data) {
    const d = clipboardData.value.data

    // 转换materials格式
    const materials = d.materials?.map((m: any) => {
      const key = Object.keys(m)[0]
      return {name: key, amount: Object.values(m)[0]}
    }) || []

    // 转换seasonings格式
    const seasonings = d.seasonings?.map((s: any) => {
      const key = Object.keys(s)[0]
      return {name: key, amount: Object.values(s)[0]}
    }) || []

    // 转换steps格式
    const steps = d.steps?.map((s: any) => ({
      step: s.step || '',
      description: s.description || ''
    })) || []

    recipeForm.value = {
      name: d.name || '',
      cuisine: d.cuisine || '川菜',
      difficulty: d.difficulty || 5,
      method: d.method || '炒',
      steps: steps.length ? steps : [{step: '第一步', description: ''}],
      materials: materials.length ? materials : [{name: '', amount: ''}],
      seasonings: seasonings.length ? seasonings : [{name: '', amount: ''}],
      carbohydrate: d.carbohydrate || 0,
      protein: d.protein || 0,
      fat: d.fat || 0,
      is_halal: d.is_halal || false,
      allergens: d.allergens || [],
      vitamins: d.vitamins || [],
      minerals: d.minerals || [],
      pictures_url: []
    }
    showRecipeForm.value = true
  }

  // 导入后清空剪贴板内容
  try {
    await navigator.clipboard.writeText('')
  } catch (e) {
    // 忽略剪贴板写入错误
  }

  clipboardData.value = {type: null, data: null}
}

function dismissClipboard() {
  clipboardData.value = {type: null, data: null}
}

// 选择新头像文件
function onAvatarFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files && input.files[0]) {
    const file = input.files[0]
    // 检查文件类型
    if (!['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'].includes(file.type)) {
      alert('请选择图片文件 (jpeg/png/gif/webp/bmp)')
      return
    }
    // 检查文件大小 (最大5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert('图片大小不能超过5MB')
      return
    }
    avatarFile.value = file
    // 生成预览
    const reader = new FileReader()
    reader.onload = (e) => {
      avatarPreview.value = e.target?.result as string
    }
    reader.readAsDataURL(file)
  }
}

// 上传新头像
async function uploadAvatar() {
  if (!avatarFile.value) {
    alert('请先选择图片文件')
    return
  }
  uploadingAvatar.value = true
  try {
    const formData = new FormData()
    formData.append('file', avatarFile.value)

    const res = await axios.post('/api/upload/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })

    // 更新用户头像
    await axios.put('/api/users/me', { avatar_url: res.data.url })

    // 刷新用户信息
    const userRes = await axios.get('/api/users/me')
    userInfo.value = userRes.data
    // 同时更新 authStore 中的用户信息
    authStore.userInfo = userRes.data
    authStore.avatarUrl = userRes.data.avatar_url

    alert('头像更新成功')
    closeAvatarModal()
  } catch (e: any) {
    alert(e.response?.data?.detail || '上传失败')
  } finally {
    uploadingAvatar.value = false
  }
}

function openMyRecipeCreate(recipe?: any, restoreDraft: boolean = true) {
  editingRecipeId.value = recipe?.id || null
  // 尝试解析剪贴板（异步但不阻塞）
  parseClipboard()

  if (recipe) {
    // 编辑模式：填充现有数据
    const materials = (recipe.materials || []).map((m: any) => {
      const name = Object.keys(m)[0]
      return { name, amount: Object.values(m)[0] }
    })
    const seasonings = (recipe.seasonings || []).map((s: any) => {
      const name = Object.keys(s)[0]
      return { name, amount: Object.values(s)[0] }
    })
    const steps = (recipe.steps || []).map((s: any) => ({
      step: s.step || s.步骤 || '',
      description: s.description || s.操作 || ''
    }))

    recipeForm.value = {
      name: recipe.name || '',
      cuisine: recipe.cuisine || '川菜',
      difficulty: recipe.difficulty || 5,
      method: recipe.method || '炒',
      steps: steps.length ? steps : [{ step: '第一步', description: '' }],
      materials: materials.length ? materials : [{ name: '', amount: '' }],
      seasonings: seasonings.length ? seasonings : [{ name: '', amount: '' }],
      carbohydrate: recipe.carbohydrate || 0,
      protein: recipe.protein || 0,
      fat: recipe.fat || 0,
      is_halal: recipe.is_halal || false,
      allergens: recipe.allergens || [],
      vitamins: recipe.vitamins || [],
      minerals: recipe.minerals || [],
      pictures_url: recipe.pictures_url || []
    }
  } else {
    // 新建模式：如果有保存的草稿且需要恢复
    if (restoreDraft && savedRecipeForm.name) {
      recipeForm.value = JSON.parse(JSON.stringify(savedRecipeForm))
      // 清除草稿
      savedRecipeForm = {
        name: '',
        cuisine: '川菜',
        difficulty: 5,
        method: '炒',
        steps: [{ step: '第一步', description: '' }],
        materials: [{ name: '', amount: '' }],
        seasonings: [{ name: '', amount: '' }],
        carbohydrate: 0,
        protein: 0,
        fat: 0,
        is_halal: false,
        allergens: [],
        vitamins: [],
        minerals: [],
        pictures_url: []
      }
      localStorage.removeItem('recipe_draft')
    } else {
      recipeForm.value = {
        name: '',
        cuisine: '川菜',
        difficulty: 5,
        method: '炒',
        steps: [{ step: '第一步', description: '' }],
        materials: [{ name: '', amount: '' }],
        seasonings: [{ name: '', amount: '' }],
        carbohydrate: 0,
        protein: 0,
        fat: 0,
        is_halal: false,
        allergens: [],
        vitamins: [],
        minerals: []
      }
    }
  }
  showRecipeForm.value = true

  // 尝试解析剪贴板
  parseClipboard()
}

function addStep() {
  recipeForm.value.steps.push({ step: `第${recipeForm.value.steps.length + 1}步`, description: '' })
}

function addMaterial() {
  recipeForm.value.materials.push({ name: '', amount: '' })
}

function addSeasoning() {
  recipeForm.value.seasonings.push({ name: '', amount: '' })
}

function removeStep(index: number) {
  if (recipeForm.value.steps.length > 1) {
    recipeForm.value.steps.splice(index, 1)
    recipeForm.value.steps.forEach((s, i) => s.step = `第${i + 1}步`)
  }
}

function removeMaterial(index: number) {
  if (recipeForm.value.materials.length > 1) {
    recipeForm.value.materials.splice(index, 1)
  }
}

function removeSeasoning(index: number) {
  if (recipeForm.value.seasonings.length > 1) {
    recipeForm.value.seasonings.splice(index, 1)
  }
}

function addTag() {
  // 保留旧方法的空实现以避免错误
}

function addAllergen() {
  if (!newAllergen.value.trim()) return
  if (!recipeForm.value.allergens.includes(newAllergen.value.trim())) {
    recipeForm.value.allergens.push(newAllergen.value.trim())
  }
  newAllergen.value = ''
}

function addVitamin() {
  if (!newVitamin.value.trim()) return
  if (!recipeForm.value.vitamins.includes(newVitamin.value.trim())) {
    recipeForm.value.vitamins.push(newVitamin.value.trim())
  }
  newVitamin.value = ''
}

function addMineral() {
  if (!newMineral.value.trim()) return
  if (!recipeForm.value.minerals.includes(newMineral.value.trim())) {
    recipeForm.value.minerals.push(newMineral.value.trim())
  }
  newMineral.value = ''
}

// 上传封面图片
async function uploadRecipeCover(file: File) {
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  uploadingCover.value = true
  try {
    const res = await axios.post('/api/upload/cover', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    recipeForm.value.pictures_url.push(res.data.url)
    recipeCoverPreview.value = ''
    recipeCoverFile.value = null
  } catch (e: any) {
    alert(e.response?.data?.detail || '封面上传失败')
  } finally {
    uploadingCover.value = false
  }
}

// 选择封面图片并直接上传
async function onRecipeCoverSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    const formData = new FormData()
    formData.append('file', file)
    uploadingCover.value = true
    try {
      const res = await axios.post('/api/upload/cover', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      recipeForm.value.pictures_url.push(res.data.url)
    } catch (e: any) {
      alert(e.response?.data?.detail || '封面上传失败')
    } finally {
      uploadingCover.value = false
      // 清空input，以便再次选择同一文件
      target.value = ''
    }
  }
}

// 删除封面
function removeRecipeCover(index: number) {
  recipeForm.value.pictures_url.splice(index, 1)
}

function removeTag(type: 'allergens' | 'vitamins' | 'minerals', tag: string) {
  if (type === 'allergens') {
    recipeForm.value.allergens = recipeForm.value.allergens.filter(t => t !== tag)
  } else if (type === 'vitamins') {
    recipeForm.value.vitamins = recipeForm.value.vitamins.filter(t => t !== tag)
  } else {
    recipeForm.value.minerals = recipeForm.value.minerals.filter(t => t !== tag)
  }
}

async function saveMyRecipe() {
  try {
    const materials: any[] = []
    for (const m of recipeForm.value.materials) {
      if (m.name?.trim()) {
        materials.push({ [m.name.trim()]: m.amount || '适量' })
      }
    }

    const seasonings: any[] = []
    for (const s of recipeForm.value.seasonings) {
      if (s.name?.trim()) {
        seasonings.push({ [s.name.trim()]: s.amount || '适量' })
      }
    }

    const steps: any[] = []
    for (let i = 0; i < recipeForm.value.steps.length; i++) {
      const s = recipeForm.value.steps[i]
      if (s.description?.trim()) {
        // step 可能是数字或字符串，需要转换为字符串
        const stepKey = typeof s.step === 'number' ? `第${s.step}步` : String(s.step).trim()
        steps.push({
          step: stepKey,
          description: s.description.trim()
        })
      }
    }

    const data: any = {
      name: recipeForm.value.name,
      cuisine: recipeForm.value.cuisine,
      difficulty: recipeForm.value.difficulty,
      method: recipeForm.value.method,
      materials,
      seasonings,
      steps,
      carbohydrate: recipeForm.value.carbohydrate,
      protein: recipeForm.value.protein,
      fat: recipeForm.value.fat,
      is_halal: recipeForm.value.is_halal,
      allergens: recipeForm.value.allergens,
      vitamins: recipeForm.value.vitamins,
      minerals: recipeForm.value.minerals,
      pictures_url: recipeForm.value.pictures_url
    }

    if (editingRecipeId.value) {
      // 编辑模式
      await axios.put(`/api/recipes/my/${editingRecipeId.value}`, data)
      alert('食谱已更新')
    } else {
      // 新建模式
      await axios.post('/api/recipes/my', data)
      alert('食谱创建成功')
    }

    // 成功后清除草稿
    savedRecipeForm = {
      name: '',
      cuisine: '川菜',
      difficulty: 5,
      method: '炒',
      steps: [{ step: '第一步', description: '' }],
      materials: [{ name: '', amount: '' }],
      seasonings: [{ name: '', amount: '' }],
      carbohydrate: 0,
      protein: 0,
      fat: 0,
      is_halal: false,
      allergens: [],
      vitamins: [],
      minerals: [],
      pictures_url: []
    }
    localStorage.removeItem('recipe_draft')

    showRecipeForm.value = false
    editingRecipeId.value = null

    // 刷新列表
    const res = await axios.get('/api/recipes/my')
    myRecipes.value = res.data
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

// 保存草稿
function saveRecipeDraft() {
  savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
  localStorage.setItem('recipe_draft', JSON.stringify(savedRecipeForm))
  alert('草稿已保存')
  showRecipeForm.value = false
}

// 清除草稿
function clearRecipeDraft() {
  savedRecipeForm = {
    name: '',
    cuisine: '川菜',
    difficulty: 5,
    method: '炒',
    steps: [{ step: '第一步', description: '' }],
    materials: [{ name: '', amount: '' }],
    seasonings: [{ name: '', amount: '' }],
    carbohydrate: 0,
    protein: 0,
    fat: 0,
    is_halal: false,
    allergens: [],
    vitamins: [],
    minerals: [],
    pictures_url: []
  }
  localStorage.removeItem('recipe_draft')
}

function goToFavorites() {
  router.push('/profile/favorites')
}

function goToBrowseHistory() {
  router.push('/profile/browse-history')
}

async function shareRecipe(recipeId: number) {
  const recipe = myRecipes.value.find(r => r.id === recipeId)
  if (!recipe) return

  if (recipe.status === 'pending' || recipe.status === 'appealing') {
    alert('食谱已在审核中，请等待管理员审核')
    return
  }

  try {
    await axios.put(`/api/recipes/my/${recipeId}/share`)
    const res = await axios.get('/api/recipes/my')
    myRecipes.value = res.data
    alert('食谱已提交审核，请等待管理员通过')
  } catch (e: any) {
    alert(e.response?.data?.detail || '分享失败')
  }
}

async function applyUnban(recipeId: number) {
  try {
    await axios.put(`/api/recipes/${recipeId}/unban`)
    const res = await axios.get('/api/recipes/my')
    myRecipes.value = res.data
    alert('已申请解封，请等待管理员审核')
  } catch (e: any) {
    alert(e.response?.data?.detail || '申请解封失败')
  }
}

async function deleteMyRecipe(recipeId: number) {
  if (!confirm('确定要删除这个食谱吗？')) return
  try {
    await axios.delete(`/api/recipes/my/${recipeId}`)
    myRecipes.value = myRecipes.value.filter(r => r.id !== recipeId)
    alert('食谱已删除')
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  }
}
</script>

<template>
  <div class="profile-page">
    <!-- 剪贴板提示 -->
    <div v-if="clipboardData.type" class="clipboard-toast">
      <div class="clipboard-content">
        <span>检测到食谱数据，是否导入？</span>
        <div class="clipboard-actions">
          <button class="btn-confirm" @click="applyClipboardData">导入</button>
          <button class="btn-cancel" @click="dismissClipboard">忽略</button>
        </div>
      </div>
    </div>

    <!-- 头像弹窗 -->
    <div v-if="showAvatarModal" class="modal-overlay" @click="closeAvatarModal">
      <div class="modal avatar-modal" @click.stop>
        <h3>更换头像</h3>
        <div class="avatar-preview">
          <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" />
          <div v-else class="avatar-placeholder">暂无头像</div>
        </div>
        <div class="avatar-upload">
          <label class="upload-label">
            <input type="file" accept="image/jpeg,image/png,image/gif,image/webp,image/bmp" @change="onAvatarFileChange" hidden />
            选择图片
          </label>
          <p class="upload-tip">支持 jpeg/png/gif/webp/bmp，最大5MB</p>
        </div>
        <div class="modal-actions">
          <button class="btn-confirm" @click="uploadAvatar" :disabled="!avatarFile || uploadingAvatar">
            {{ uploadingAvatar ? '上传中...' : '保存' }}
          </button>
          <button class="btn-cancel" @click="closeAvatarModal">取消</button>
        </div>
      </div>
    </div>

    <div class="profile-card">
      <div class="profile-header">
        <div class="avatar" @click="onAvatarClick" title="点击更换头像">
          <img v-if="userInfo.avatar_url" :src="userInfo.avatar_url" alt="头像" class="avatar-img" />
          <span v-else class="avatar-emoji">👤</span>
        </div>
        <div class="user-info">
          <h2>{{ isAdmin ? authStore.account : (authStore.nickname || authStore.account) }}</h2>
          <p v-if="authStore.isAdmin" class="admin-badge">管理员 Lv.{{ authStore.adminLevel }}</p>
          <p v-else class="user-badge">普通用户</p>
        </div>
      </div>

      <!-- 管理员快捷入口 -->
      <div v-if="isAdmin" class="admin-quick-link">
        <button class="btn-admin" @click="goToAdmin">进入管理后台</button>
      </div>

      <div v-if="!isAdmin" class="profile-quick-links">
        <button class="btn-link" @click="goToFavorites">
          <span class="icon">❤️</span>
          <span>我的收藏</span>
        </button>
        <button class="btn-link" @click="goToBrowseHistory">
          <span class="icon">👀</span>
          <span>浏览记录</span>
        </button>
      </div>

      <div class="profile-actions">
        <button class="btn-logout" @click="handleLogout">退出登录</button>
      </div>
    </div>

    <!-- 普通用户：我的食谱 -->
    <div v-if="!isAdmin" class="my-recipes">
      <div class="section-header">
        <h3>我的食谱</h3>
        <button class="btn-add" @click="openMyRecipeCreate">+ 创建食谱</button>
      </div>
      <div class="recipe-grid" v-if="myRecipes.length">
        <div
          v-for="recipe in myRecipes"
          :key="recipe.id"
          class="recipe-card"
        >
          <div class="recipe-image" @click="goToRecipe(recipe.id)">
            <img v-if="getRecipeFirstImage(recipe)" :src="getRecipeFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
            <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h4>{{ recipe.name }}</h4>
            <span class="status" :class="{ public: recipe.status === 'public', banned: recipe.status === 'banned', pending: recipe.status === 'pending', appealing: recipe.status === 'appealing' }">
              {{ recipe.status === 'banned' ? '已封禁' : (recipe.status === 'public' ? '已公开' : (recipe.status === 'private' ? '私密' : (recipe.status === 'appealing' ? '申请解封' : '申请公开'))) }}
            </span>
          </div>
          <div class="recipe-actions">
            <button class="btn-share" v-if="recipe.status === 'private'" @click.stop="shareRecipe(recipe.id)">分享</button>
            <button class="btn-share" v-if="recipe.status === 'banned'" @click.stop="applyUnban(recipe.id)">申请解封</button>
            <button class="btn-edit" @click.stop="openMyRecipeCreate(recipe)">编辑</button>
            <button class="btn-delete" @click.stop="deleteMyRecipe(recipe.id)">删除</button>
          </div>
        </div>
      </div>
      <div v-else class="empty">
        <p>还没有创建过食谱</p>
      </div>
    </div>

    <!-- 新增食谱弹窗 -->
    <div v-if="showRecipeForm" class="modal-overlay" @click="isAccidentalClose = true; showRecipeForm = false">
      <div class="modal" @click.stop style="max-width: 700px; max-height: 90vh; overflow-y: auto;">
        <h3>{{ editingRecipeId ? '编辑食谱' : '创建食谱' }}</h3>
        <div v-if="savedRecipeForm.name && !editingRecipeId" style="margin-bottom: 1rem;">
          <button class="btn-add" @click="openMyRecipeCreate()">
            继续填写 →
          </button>
        </div>
        <div class="form-group">
          <label>食谱名称 *</label>
          <input v-model="recipeForm.name" type="text" placeholder="如: 红烧肉" />
        </div>

        <div class="form-group">
          <label>封面图片</label>
          <div class="cover-upload-area">
            <div v-if="recipeForm.pictures_url && recipeForm.pictures_url.length > 0" class="cover-list">
              <div v-for="(url, idx) in recipeForm.pictures_url" :key="idx" class="cover-item">
                <img :src="url" alt="封面" loading="lazy" />
                <button class="btn-remove-cover" @click="removeRecipeCover(idx)">×</button>
              </div>
            </div>
            <div v-if="!recipeForm.pictures_url || recipeForm.pictures_url.length < 3" class="cover-input-wrapper">
              <input type="file" accept="image/*" @change="onRecipeCoverSelect" id="recipe-cover-input" style="display: none;" />
              <label for="recipe-cover-input" class="cover-input-label">
                <span v-if="uploadingCover">上传中...</span>
                <span v-else>+ 添加封面</span>
              </label>
            </div>
          </div>
          <p class="form-hint">最多3张封面图片</p>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>菜系</label>
            <select v-model="recipeForm.cuisine">
              <option v-for="c in cuisineOptions" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>烹饪方式</label>
            <select v-model="recipeForm.method">
              <option v-for="m in methodOptions" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>难度(1-10)</label>
            <input v-model.number="recipeForm.difficulty" type="number" min="1" max="10" />
          </div>
        </div>

        <div class="form-group">
          <label>所需材料</label>
          <div v-for="(m, idx) in recipeForm.materials" :key="'m'+idx" class="line-input">
            <input v-model="m.name" placeholder="食材名" />
            <input v-model="m.amount" placeholder="用量" style="width: 100px;" />
            <button v-if="recipeForm.materials.length > 1" class="btn-remove" @click="removeMaterial(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addMaterial">+</button>
        </div>

        <div class="form-group">
          <label>所需调料</label>
          <div v-for="(s, idx) in recipeForm.seasonings" :key="'s'+idx" class="line-input">
            <input v-model="s.name" placeholder="调料名" />
            <input v-model="s.amount" placeholder="用量" style="width: 100px;" />
            <button v-if="recipeForm.seasonings.length > 1" class="btn-remove" @click="removeSeasoning(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addSeasoning">+</button>
        </div>

        <div class="form-group">
          <label>制作步骤</label>
          <div v-for="(st, idx) in recipeForm.steps" :key="'st'+idx" class="line-input">
            <input v-model="st.step" placeholder="步骤名+时间" style="flex: 1;" />
            <input v-model="st.description" placeholder="具体步骤" style="flex: 2;" />
            <button v-if="recipeForm.steps.length > 1" class="btn-remove" @click="removeStep(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addStep">+</button>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label>碳水(g)</label>
            <input v-model.number="recipeForm.carbohydrate" type="number" step="0.1" />
          </div>
          <div class="form-group">
            <label>蛋白质(g)</label>
            <input v-model.number="recipeForm.protein" type="number" step="0.1" />
          </div>
          <div class="form-group">
            <label>脂肪(g)</label>
            <input v-model.number="recipeForm.fat" type="number" step="0.1" />
          </div>
        </div>

        <div class="form-group">
          <label class="checkbox-label"><input v-model="recipeForm.is_halal" type="checkbox" /> 清真</label>
        </div>

        <div class="form-group">
          <label>过敏食材</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.allergens" :key="tag" class="tag-item">{{ tag }}<span class="tag-remove" @click="removeTag('allergens', tag)">×</span></span>
            <input v-model="newAllergen" placeholder="输入后回车添加" @keyup.enter="addAllergen" style="flex: 1;" />
            <button class="btn-add-tag" @click="addAllergen">+</button>
          </div>
        </div>

        <div class="form-group">
          <label>维生素</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.vitamins" :key="tag" class="tag-item">{{ tag }}<span class="tag-remove" @click="removeTag('vitamins', tag)">×</span></span>
            <input v-model="newVitamin" placeholder="输入后回车添加" @keyup.enter="addVitamin" style="flex: 1;" />
            <button class="btn-add-tag" @click="addVitamin">+</button>
          </div>
        </div>

        <div class="form-group">
          <label>矿物质</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.minerals" :key="tag" class="tag-item">{{ tag }}<span class="tag-remove" @click="removeTag('minerals', tag)">×</span></span>
            <input v-model="newMineral" placeholder="输入后回车添加" @keyup.enter="addMineral" style="flex: 1;" />
            <button class="btn-add-tag" @click="addMineral">+</button>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-confirm" @click="saveMyRecipe">{{ editingRecipeId ? '保存修改' : '创建食谱' }}</button>
          <button class="btn-save-draft" @click="saveRecipeDraft">保存草稿</button>
          <button class="btn-cancel" @click="closeRecipeForm">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 800px;
  margin: 0 auto;
}

/* 封面上传样式 */
.cover-upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.cover-list {
  display: flex;
  gap: 10px;
}

.cover-item {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
}

.cover-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.btn-remove-cover {
  position: absolute;
  top: 2px;
  right: 2px;
  background: rgba(0, 0, 0, 0.6);
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
}

.cover-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cover-input-label {
  width: 80px;
  height: 80px;
  border: 2px dashed #ccc;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #999;
  font-size: 0.8rem;
  overflow: hidden;
}

.cover-input-label:hover {
  border-color: #4caf50;
  color: #4caf50;
}

.cover-preview-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.btn-confirm-cover {
  padding: 6px 12px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-confirm-cover:disabled {
  background: #ccc;
}

.form-hint {
  font-size: 0.8rem;
  color: #999;
  margin-top: 4px;
}

/* 剪贴板提示 */
.clipboard-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  background: #4caf50;
  color: white;
  padding: 0.6rem 1rem;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
  font-size: 0.9rem;
}

.clipboard-content {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.clipboard-actions {
  display: flex;
  gap: 0.4rem;
}

.clipboard-actions .btn-confirm {
  background: white;
  color: #4caf50;
  padding: 0.3rem 0.8rem;
  font-size: 0.85rem;
}

.clipboard-actions .btn-cancel {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  padding: 0.3rem 0.8rem;
  font-size: 0.85rem;
}

/* 头像弹窗 */
.avatar-modal {
  text-align: center;
}

.avatar-preview {
  width: 150px;
  height: 150px;
  margin: 1rem auto;
  border-radius: 50%;
  overflow: hidden;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  color: #999;
  font-size: 3rem;
}

.avatar-upload {
  margin: 1rem 0;
}

.upload-label {
  display: inline-block;
  padding: 0.6rem 1.2rem;
  background: #4caf50;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.3s;
}

.upload-label:hover {
  background: #43a047;
}

.upload-tip {
  font-size: 0.8rem;
  color: #999;
  margin-top: 0.5rem;
}

/* 头像弹窗样式在 profile-page 下方 */

/* 行输入框 */
.line-input {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.line-input input {
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
}

.line-input input:focus {
  outline: none;
  border-color: #4caf50;
}

.btn-remove {
  background: #ffebee;
  color: #f44336;
  border: none;
  border-radius: 4px;
  width: 28px;
  height: 28px;
  cursor: pointer;
}

.btn-add-row {
  background: #e8f5e9;
  color: #4caf50;
  border: 1px dashed #4caf50;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  margin-top: 0.3rem;
}

/* 标签输入 */
.tag-input {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  padding: 0.5rem;
  background: #f9f9f9;
  border-radius: 6px;
}

.tag-input input,
.tag-input select {
  padding: 0.4rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.85rem;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.3rem 0.6rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.tag-remove {
  cursor: pointer;
  color: #f44336;
  font-weight: bold;
}

.btn-add-tag {
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal h3 {
  color: #2e7d32;
  margin-bottom: 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.3rem;
  color: #37474f;
  font-size: 0.9rem;
}

.checkbox-label {
  display: flex !important;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-label input {
  width: auto !important;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.form-row {
  display: flex;
  gap: 0.5rem;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.btn-confirm {
  padding: 0.6rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-save-draft {
  padding: 0.6rem 1rem;
  background: #fff3e0;
  color: #f57c00;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-save-draft:hover {
  background: #ffe0b2;
}

.btn-cancel {
  padding: 0.6rem 1rem;
  background: #e0e0e0;
  color: #666;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.profile-card {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.avatar {
  width: 80px;
  height: 80px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.avatar .avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar .avatar-emoji {
  font-size: 2.5rem;
}

.user-info h2 {
  color: #2e7d32;
  margin-bottom: 0.3rem;
}

.admin-badge {
  display: inline-block;
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.user-badge {
  display: inline-block;
  background: #e3f2fd;
  color: #1976d2;
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
}

.admin-quick-link {
  margin-bottom: 1rem;
}

.btn-admin {
  width: 100%;
  padding: 0.8rem;
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-admin:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.profile-quick-links {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}

.btn-link {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.8rem;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
  font-weight: 500;
  color: #333;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-link:hover {
  border-color: #4caf50;
  color: #2e7d32;
}

.btn-link .icon {
  font-size: 1.2rem;
}

.profile-actions {
  display: flex;
  gap: 1rem;
}

.btn-logout {
  background: #ffebee;
  color: #d32f2f;
  border: none;
  padding: 0.8rem 1.5rem;
  border-radius: 12px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.btn-logout:hover {
  background: #ffcdd2;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h3 {
  color: #2e7d32;
  margin: 0;
}

.btn-add {
  padding: 0.5rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.my-recipes h3 {
  color: #2e7d32;
  margin-bottom: 1rem;
}

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
  overflow: hidden; 
  justify-content: center;
}

.recipe-emoji {
  font-size: 2.5rem;
}

.recipe-info {
  padding: 0.8rem;
}

.recipe-actions {
  padding: 0 0.8rem 0.8rem;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.recipe-actions button {
  flex: 1;
  min-width: 60px;
  padding: 0.4rem;
  border: none;
  border-radius: 6px;
  font-size: 0.8rem;
  cursor: pointer;
}

.btn-share {
  background: #fff3e0;
  color: #f57c00;
}

.btn-share:hover {
  background: #ffe0b2;
}

.btn-edit {
  background: #e8f5e9;
  color: #2e7d32;
}

.btn-edit:hover {
  background: #c8e6c9;
}

.btn-delete {
  background: #ffebee;
  color: #d32f2f;
}

.btn-delete:hover {
  background: #ffcdd2;
}

.recipe-info h4 {
  color: #2e7d32;
  font-size: 0.9rem;
  margin-bottom: 0.3rem;
}

.status {
  font-size: 0.75rem;
  color: #78909c;
}

.status.public {
  color: #4caf50;
}

.status.banned {
  color: #f44336;
}

.status.pending {
  color: #ff9800;
}

.status.appealing {
  color: #9c27b0;
}

.empty {
  text-align: center;
  padding: 2rem;
  color: #78909c;
  background: white;
  border-radius: 12px;
}

@media (max-width: 600px) {
  .recipe-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
