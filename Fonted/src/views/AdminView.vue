<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'
import { INGREDIENT_CATEGORIES, CUISINES, METHODS } from '../config/constants'

const router = useRouter()
const authStore = useAuthStore()

// 0级管理员 - 超级管理员
const isSuperAdmin = computed(() => authStore.adminLevel === 0)
// 1级管理员 - 普通管理员
const isNormalAdmin = computed(() => authStore.adminLevel === 1)

const activeTab = ref('pending')
const pendingTab = ref('pending') // pending(申请公开) / appealing(申请解封)

// 待审核数据
const pendingRecipes = ref<any[]>([])
const appealingRecipes = ref<any[]>([])
const loading = ref(false)
const pendingLoaded = ref(false)
const appealingLoaded = ref(false)
const usersLoaded = ref(false)
const recipesLoaded = ref(false)
const ingredientsLoaded = ref(false)

// 管理员列表（仅0级可见）
const admins = ref<any[]>([])

// 用户管理数据
const users = ref<any[]>([])
const userSearchQuery = ref('')
const showUserForm = ref(false)
const editingUser = ref<any>(null)

// 食谱管理数据
const allRecipes = ref<any[]>([])
const recipeSearchQuery = ref('')

// 食材管理数据
const ingredients = ref<any[]>([])
const showIngredientForm = ref(false)
const editingIngredient = ref<any>(null)
const ingredientCategories = INGREDIENT_CATEGORIES
const cuisineOptions = CUISINES
const methodOptions = METHODS

// 食谱表单
const showRecipeForm = ref(false)
const editingRecipeId = ref<number | null>(null)
const autoCalculateNutrition = ref(false)
const editingRecipeData = ref<any>(null)  // 保存正在编辑的食谱数据

// 判断是否在编辑系统食谱
const isEditingSystemRecipe = computed(() => {
  return editingRecipeData.value && !editingRecipeData.value.creator_account
})

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
  taste: { sour: 0.2, sweet: 0.2, bitter: 0.2, spicy: 0.2, salty: 0.2 },
  pictures_url: [] as string[]
})
let savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
const defaultTaste = { sour: 0.2, sweet: 0.2, bitter: 0.2, spicy: 0.2, salty: 0.2 }
const tasteDimensions = [
  { key: 'sour', label: '酸' },
  { key: 'sweet', label: '甜' },
  { key: 'bitter', label: '苦' },
  { key: 'spicy', label: '辣' },
  { key: 'salty', label: '咸' },
]

function updateTaste(key: string, value: string) {
  const numVal = parseFloat(value)
  if (isNaN(numVal)) return
  ;(recipeForm.value.taste as any)[key] = numVal
  // 自动归一化，使总和为1
  const taste = recipeForm.value.taste as any
  const total = Object.keys(taste).reduce((sum: number, k: string) => sum + (Number(taste[k]) || 0), 0)
  if (total > 0 && Math.abs(total - 1) > 0.001) {
    for (const k of Object.keys(taste)) {
      taste[k] = Math.round(((taste[k] / total) + Number.EPSILON) * 100) / 100
    }
  }
}

// 封面上传相关
const recipeCoverPreview = ref('')
const recipeCoverFile = ref<File | null>(null)
const uploadingRecipeCover = ref(false)

// 标签输入
const newAllergen = ref('')
const newVitamin = ref('')
const newMineral = ref('')

// 表单
const showAdminForm = ref(false)
const newAdmin = ref({
  password: '',
  permission_duration_days: 30
})
const formError = ref('')

// 用户表单
const userForm = ref({
  nickname: '',
  gender: '私密',
  age: null as number | null,
  is_halal: false,
  allergens: ''
})

// 食材表单
const ingredientForm = ref({
  name: '',
  carbohydrate: 0,
  protein: 0,
  fat: 0,
  category: '蔬菜',
  is_halal: false,
  is_allergen: false,
  vitamins: '',
  minerals: '',
  picture_url: ''
})
let savedIngredientForm = JSON.parse(JSON.stringify(ingredientForm.value))

// 封面上传相关
const ingredientCoverPreview = ref('')
const ingredientCoverFile = ref<File | null>(null)
const uploadingIngredientCover = ref(false)

// 防抖 & 进度条
const isSubmitting = ref(false)
const showProgress = ref(false)
const progressPercent = ref(0)
const progressMessage = ref('')

// 用于标记是否意外关闭（点击弹窗外部）
let isAccidentalClose: boolean = false

// 剪贴板解析结果
const clipboardData = ref<{type: 'recipe' | 'ingredient' | null, data: any}>({type: null, data: null})

// 从localStorage加载草稿
function loadDrafts() {
  try {
    const recipeDraft = localStorage.getItem('recipe_draft')
    if (recipeDraft) {
      savedRecipeForm = JSON.parse(recipeDraft)
    }
    const ingredientDraft = localStorage.getItem('ingredient_draft')
    if (ingredientDraft) {
      savedIngredientForm = JSON.parse(ingredientDraft)
    }
  } catch (e) {
    console.error('加载草稿失败', e)
  }
}

// 解析剪贴板中的JSON数据（仅在对应页面检测）
async function parseClipboard() {
  // 根据当前tab决定检查什么类型
  const currentTab = activeTab.value
  if (currentTab !== 'recipes' && currentTab !== 'ingredients') {
    clipboardData.value = {type: null, data: null}
    return false
  }

  try {
    const text = await navigator.clipboard.readText()
    const data = JSON.parse(text)

    // 食谱页面：只检测食谱格式
    if (currentTab === 'recipes') {
      if (data.name && data.materials && Array.isArray(data.materials) && data.seasonings) {
        clipboardData.value = {type: 'recipe', data}
        return true
      }
    }
    // 食材页面：只检测食材格式
    else if (currentTab === 'ingredients') {
      if (data.name && Array.isArray(data.name) && data.category !== undefined) {
        clipboardData.value = {type: 'ingredient', data}
        return true
      }
    }
  } catch (e) {
    // 不是有效JSON，忽略
  }
  clipboardData.value = {type: null, data: null}
  return false
}

// 应用剪贴板数据到表单
async function applyClipboardData() {
  if (clipboardData.value.type === 'ingredient' && clipboardData.value.data) {
    const d = clipboardData.value.data
    ingredientForm.value = {
      name: Array.isArray(d.name) ? d.name.join(', ') : d.name,
      carbohydrate: d.carbohydrate || 0,
      protein: d.protein || 0,
      fat: d.fat || 0,
      category: d.category || '蔬菜',
      is_halal: d.is_halal || false,
      is_allergen: d.is_allergen || false,
      vitamins: d.vitamins?.join(', ') || '',
      minerals: d.minerals?.join(', ') || ''
    }
    showIngredientForm.value = true
  } else if (clipboardData.value.type === 'recipe' && clipboardData.value.data) {
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

    // 使用Object.assign保持响应式
    Object.assign(recipeForm.value, {
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
      minerals: d.minerals || []
    })
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

onMounted(async () => {
  // 先初始化认证状态，等待完成
  await authStore.init()
  console.log('AdminView: init完成, isLoggedIn=', authStore.isLoggedIn, 'isAdmin=', authStore.isAdmin, 'adminLevel=', authStore.adminLevel)
  if (!authStore.isLoggedIn || !authStore.isAdmin) {
    router.push('/login')
    return
  }
  // 加载草稿
  loadDrafts()
  await fetchData()
})

// 监听食谱弹窗关闭，意外关闭时自动保存草稿
watch(showRecipeForm, (newVal) => {
  if (!newVal && isAccidentalClose && recipeForm.value.name) {
    savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
    localStorage.setItem('recipe_draft', JSON.stringify(savedRecipeForm))
  }
  isAccidentalClose = false
})

// 监听食材弹窗关闭，意外关闭时自动保存草稿
watch(showIngredientForm, (newVal) => {
  if (!newVal && isAccidentalClose && ingredientForm.value.name) {
    savedIngredientForm = JSON.parse(JSON.stringify(ingredientForm.value))
    localStorage.setItem('ingredient_draft', JSON.stringify(savedIngredientForm))
  }
  isAccidentalClose = false
})

async function loadPendingRecipes() {
  if (pendingLoaded.value) return
  const token = authStore.token
  if (!token) return
  try {
    const res = await axios.get('/api/recipes/pending', {
      headers: { Authorization: `Bearer ${token}` }
    })
    pendingRecipes.value = res.data
    pendingLoaded.value = true
  } catch (e: any) {
    console.error('加载申请公开失败', e)
  }
}

async function loadAppealingRecipes() {
  if (appealingLoaded.value) return
  const token = authStore.token
  if (!token) return
  try {
    const res = await axios.get('/api/recipes/appealing', {
      headers: { Authorization: `Bearer ${token}` }
    })
    appealingRecipes.value = res.data
    appealingLoaded.value = true
  } catch (e: any) {
    console.error('加载申请解封失败', e)
  }
}

async function loadUsers() {
  if (usersLoaded.value) return
  const token = authStore.token
  if (!token) return
  try {
    const res = await axios.get('/api/admins/users', {
      headers: { Authorization: `Bearer ${token}` }
    })
    users.value = res.data
    usersLoaded.value = true
  } catch (e: any) {
    console.error('加载用户失败', e)
  }
}

async function loadAllRecipes() {
  if (recipesLoaded.value) return
  const token = authStore.token
  if (!token) return
  try {
    const res = await axios.get('/api/recipes/all', {
      headers: { Authorization: `Bearer ${token}` }
    })
    allRecipes.value = res.data
    recipesLoaded.value = true
  } catch (e: any) {
    console.error('加载食谱失败', e)
  }
}

async function loadIngredients() {
  if (ingredientsLoaded.value) return
  const token = authStore.token
  if (!token) return
  try {
    const res = await axios.get('/api/ingredients/', {
      headers: { Authorization: `Bearer ${token}` }
    })
    ingredients.value = res.data.items
    ingredientsLoaded.value = true
  } catch (e: any) {
    console.error('加载食材失败', e)
  }
}

async function fetchData() {
  loading.value = true
  console.log('fetchData开始')

  const token = authStore.token

  // 0级管理员只获取管理员列表
  if (isSuperAdmin.value) {
    try {
      const adminRes = await axios.get('/api/admins/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      admins.value = adminRes.data
      console.log('管理员列表长度:', admins.value.length)
    } catch (e: any) {
      console.log('获取管理员列表错误:', e.response?.status, e.response?.data)
    }
    // 加载知识库列表
    try {
      const kbRes = await axios.get('/api/admins/knowledge-base/list', {
        headers: { Authorization: `Bearer ${token}` }
      })
      kbList.value = kbRes.data.bases || []
      kbActive.value = kbRes.data.active || null
    } catch (e: any) {
      console.log('获取知识库列表错误:', e.response?.status, e.response?.data)
    }
    loading.value = false
    return
  }

}

// ========== 用户管理 ==========
const filteredUsers = computed(() => {
  if (!userSearchQuery.value) return users.value
  const query = userSearchQuery.value.toLowerCase()
  return users.value.filter(u =>
    u.nickname?.toLowerCase().includes(query) ||
    u.account?.includes(query)
  )
})

function openUserEdit(user: any) {
  editingUser.value = user
  userForm.value = {
    nickname: user.nickname || '',
    gender: user.gender || '私密',
    age: user.age || null,
    is_halal: user.is_halal || false,
    allergens: user.allergens?.join(', ') || ''
  }
  showUserForm.value = true
}

async function saveUser() {
  try {
    const data: any = {
      nickname: userForm.value.nickname,
      gender: userForm.value.gender,
      age: userForm.value.age,
      is_halal: userForm.value.is_halal,
      allergens: userForm.value.allergens ? userForm.value.allergens.split(',').map(s => s.trim()).filter(Boolean) : []
    }
    await axios.put(`/api/users/${editingUser.value.account}`, data, { headers: { Authorization: `Bearer ${authStore.token}` } })
    alert('用户信息已更新')
    showUserForm.value = false
    editingUser.value = null
    // 刷新列表
    const res = await axios.get('/api/admins/users', { headers: { Authorization: `Bearer ${authStore.token}` } })
    users.value = res.data
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function freezeUser(account: string) {
  if (!confirm(`确定要冻结用户 ${account} 吗？`)) return
  try {
    await axios.post(`/api/users/${account}/freeze`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    alert('用户已冻结')
    // 刷新列表
    const res = await axios.get('/api/admins/users', { headers: { Authorization: `Bearer ${authStore.token}` } })
    users.value = res.data
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

async function unfreezeUser(account: string) {
  if (!confirm(`确定要解冻用户 ${account} 吗？`)) return
  try {
    await axios.post(`/api/users/${account}/unfreeze`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    alert('用户已解冻')
    // 刷新列表
    const res = await axios.get('/api/admins/users', { headers: { Authorization: `Bearer ${authStore.token}` } })
    users.value = res.data
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// ========== 食谱管理 ==========
const filteredRecipes = computed(() => {
  // 管理员可见：系统食谱（可编辑）+ 用户公开的食谱（只能设私密）
  const recipes = allRecipes.value.filter(r => !r.creator_account || r.status === 'public')
  if (!recipeSearchQuery.value) return recipes
  const query = recipeSearchQuery.value.toLowerCase()
  return recipes.filter(r =>
    r.name?.toLowerCase().includes(query) ||
    r.cuisine?.toLowerCase().includes(query)
  )
})

// 判断食谱是否可编辑（系统食谱）
const isEditable = (recipe: any) => {
  return !recipe.creator_account
}

async function deleteRecipe(id: number) {
  if (!confirm('确定要删除这个食谱吗？')) return
  try {
    await axios.delete(`/api/recipes/${id}`, { headers: { Authorization: `Bearer ${authStore.token}` } })
    allRecipes.value = allRecipes.value.filter(r => r.id !== id)
    alert('食谱已删除')
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

async function toggleRecipeVisibility(id: number, currentStatus: string) {
  try {
    // 管理员封禁用户食谱
    const newStatus = currentStatus === 'public' ? 'banned' : 'public'
    await axios.put(`/api/recipes/${id}/visibility`, { status: newStatus }, { headers: { Authorization: `Bearer ${authStore.token}` } })
    // 刷新列表
    const res = await axios.get('/api/recipes/all', { headers: { Authorization: `Bearer ${authStore.token}` } })
    allRecipes.value = res.data
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// ========== 食材管理 ==========
function openIngredientCreate(restoreDraft: boolean = true) {
  editingIngredient.value = null
  // 尝试解析剪贴板
  parseClipboard()

  // 如果有保存的草稿且需要恢复
  if (restoreDraft && savedIngredientForm.name) {
    ingredientForm.value = JSON.parse(JSON.stringify(savedIngredientForm))
    // 清除草稿
    savedIngredientForm = {
      name: '',
      carbohydrate: 0,
      protein: 0,
      fat: 0,
      category: '蔬菜',
      is_halal: false,
      is_allergen: false,
      vitamins: '',
      minerals: ''
    }
    localStorage.removeItem('ingredient_draft')
  } else {
    ingredientForm.value = {
      name: '',
      carbohydrate: 0,
      protein: 0,
      fat: 0,
      category: '蔬菜',
      is_halal: false,
      is_allergen: false,
      vitamins: '',
      minerals: ''
    }
  }
  showIngredientForm.value = true
}

function openIngredientEdit(ing: any) {
  editingIngredient.value = ing
  ingredientForm.value = {
    name: Array.isArray(ing.name) ? ing.name.join(', ') : ing.name,
    carbohydrate: ing.carbohydrate || 0,
    protein: ing.protein || 0,
    fat: ing.fat || 0,
    category: ing.category || '蔬菜',
    is_halal: ing.is_halal || false,
    is_allergen: ing.is_allergen || false,
    vitamins: ing.vitamins?.join(', ') || '',
    minerals: ing.minerals?.join(', ') || '',
    picture_url: ing.picture_url || ''
  }
  ingredientCoverPreview.value = ing.picture_url || ''
  showIngredientForm.value = true
}

// 上传食材封面图片
async function uploadIngredientCover(file: File) {
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  uploadingIngredientCover.value = true
  try {
    const res = await axios.post('/api/upload/cover', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ingredientForm.value.picture_url = res.data.url
    ingredientCoverPreview.value = ''
    ingredientCoverFile.value = null
  } catch (e: any) {
    alert(e.response?.data?.detail || '封面上传失败')
  } finally {
    uploadingIngredientCover.value = false
  }
}

// 选择封面图片并直接上传
async function onIngredientCoverSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    const formData = new FormData()
    formData.append('file', file)
    uploadingIngredientCover.value = true
    try {
      const res = await axios.post('/api/upload/cover', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ingredientForm.value.picture_url = res.data.url
    } catch (e: any) {
      alert(e.response?.data?.detail || '封面上传失败')
    } finally {
      uploadingIngredientCover.value = false
      target.value = ''
    }
  }
}

// 删除封面
function removeIngredientCover() {
  ingredientForm.value.picture_url = ''
}

async function saveIngredient() {
  try {
    const data: any = {
      name: ingredientForm.value.name.split(',').map(s => s.trim()).filter(Boolean),
      carbohydrate: ingredientForm.value.carbohydrate,
      protein: ingredientForm.value.protein,
      fat: ingredientForm.value.fat,
      category: ingredientForm.value.category,
      is_halal: ingredientForm.value.is_halal,
      is_allergen: ingredientForm.value.is_allergen,
      vitamins: ingredientForm.value.vitamins ? ingredientForm.value.vitamins.split(',').map(s => s.trim()).filter(Boolean) : [],
      minerals: ingredientForm.value.minerals ? ingredientForm.value.minerals.split(',').map(s => s.trim()).filter(Boolean) : [],
      picture_url: ingredientForm.value.picture_url
    }

    if (editingIngredient.value) {
      // 更新
      await axios.put(`/api/ingredients/${editingIngredient.value.id}`, data, { headers: { Authorization: `Bearer ${authStore.token}` } })
      alert('食材已更新')
    } else {
      // 创建
      await axios.post('/api/ingredients/', data, { headers: { Authorization: `Bearer ${authStore.token}` } })
      alert('食材已创建')
      // 创建成功后清除草稿
      savedIngredientForm = {
        name: '',
        carbohydrate: 0,
        protein: 0,
        fat: 0,
        category: '蔬菜',
        is_halal: false,
        is_allergen: false,
        vitamins: '',
        minerals: '',
        picture_url: ''
      }
      localStorage.removeItem('ingredient_draft')
    }

    showIngredientForm.value = false
    editingIngredient.value = null

    // 刷新列表
    const res = await axios.get('/api/ingredients/', { headers: { Authorization: `Bearer ${authStore.token}` } })
    ingredients.value = res.data.items
  } catch (e: any) {
    alert(e.response?.data?.detail || '保存失败')
  }
}

async function deleteIngredient(id: number) {
  if (!confirm('确定要删除这个食材吗？')) return
  try {
    await axios.delete(`/api/ingredients/${id}`, { headers: { Authorization: `Bearer ${authStore.token}` } })
    ingredients.value = ingredients.value.filter(i => i.id !== id)
    alert('食材已删除')
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

function saveIngredientDraft() {
  savedIngredientForm = JSON.parse(JSON.stringify(ingredientForm.value))
  localStorage.setItem('ingredient_draft', JSON.stringify(savedIngredientForm))
  alert('草稿已保存')
  showIngredientForm.value = false
}

// ========== 食谱管理 - 新增食谱 ==========
function openRecipeCreate(recipe?: any, restoreDraft: boolean = true) {
  console.log('openRecipeCreate called, recipe:', recipe, 'restoreDraft:', restoreDraft)
  editingRecipeId.value = recipe?.id || null
  editingRecipeData.value = recipe || null  // 保存完整的食谱数据

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
      taste: recipe.taste || { ...defaultTaste },
      pictures_url: recipe.pictures_url || []
    }
  } else {
    // 新建模式：如果有保存的数据且需要恢复
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
        taste: { ...defaultTaste },
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
        minerals: [],
        taste: { ...defaultTaste },
        pictures_url: []
      }
    }
  }
  showRecipeForm.value = true
}


function closeRecipeForm(save: boolean = false) {
  if (save) {
    savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
    // 保存到localStorage
    localStorage.setItem('recipe_draft', JSON.stringify(savedRecipeForm))
    alert('草稿已保存')
  } else {
    // 清除草稿
    localStorage.removeItem('recipe_draft')
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
  }
  showRecipeForm.value = false
}

function resetRecipeForm() {
  recipeForm.value = {
    name: '',
    cuisine: '川菜',
    difficulty: 5,
    method: '炒',
    steps: [{ step: '第1步', description: '' }],
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
  savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))
}

// 添加步骤/材料/调料行
function addStep() {
  recipeForm.value.steps.push({ step: `第${recipeForm.value.steps.length + 1}步`, description: '' })
}

function addMaterial() {
  recipeForm.value.materials.push({ name: '', amount: '' })
}

function addSeasoning() {
  recipeForm.value.seasonings.push({ name: '', amount: '' })
}

// 删除步骤/材料/调料行
function removeStep(index: number) {
  if (recipeForm.value.steps.length > 1) {
    recipeForm.value.steps.splice(index, 1)
    // 重新编号
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

// 添加标签
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

// 上传食谱封面图片
async function uploadRecipeCover(file: File) {
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  uploadingRecipeCover.value = true
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
    uploadingRecipeCover.value = false
  }
}

// 选择封面图片并直接上传
async function onRecipeCoverSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    const formData = new FormData()
    formData.append('file', file)
    uploadingRecipeCover.value = true
    try {
      const res = await axios.post('/api/upload/cover', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      recipeForm.value.pictures_url.push(res.data.url)
    } catch (e: any) {
      alert(e.response?.data?.detail || '封面上传失败')
    } finally {
      uploadingRecipeCover.value = false
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

// 进度模拟（在单次HTTP请求中模拟多个阶段）
function startProgressSimulation(): number {
  showProgress.value = true
  progressPercent.value = 0
  progressMessage.value = '正在创建食谱...'

  const stages = [
    { at: 15, msg: '正在保存食谱...' },
    { at: 35, msg: '正在分析食材...' },
    { at: 55, msg: '正在通过AI补充食材信息...' },
    { at: 80, msg: '正在计算营养成分...' },
  ]

  let stageIdx = 0
  return window.setInterval(() => {
    // 到达阶段阈值时更新消息
    if (stageIdx < stages.length && progressPercent.value >= stages[stageIdx].at) {
      progressMessage.value = stages[stageIdx].msg
      stageIdx++
    }
    // 缓慢逼近 95%，不达到 100%（等请求真正完成才跳到 100）
    if (progressPercent.value < 95) {
      const step = Math.max(0.3, (95 - progressPercent.value) / 30)
      progressPercent.value = Math.min(95, progressPercent.value + step)
    }
  }, 400)
}

async function saveRecipe() {
  // 防抖：防止重复提交
  if (isSubmitting.value) return
  isSubmitting.value = true

  let progressTimer: number | null = null
  try {
    // 解析材料
    const materials: any[] = []
    for (const m of recipeForm.value.materials) {
      if (m.name?.trim()) {
        const materialObj: any = {}
        materialObj[m.name.trim()] = m.amount || '适量'
        materials.push(materialObj)
      }
    }

    // 解析调料
    const seasonings: any[] = []
    for (const s of recipeForm.value.seasonings) {
      if (s.name?.trim()) {
        const seasoningObj: any = {}
        seasoningObj[s.name.trim()] = s.amount || '适量'
        seasonings.push(seasoningObj)
      }
    }

    // 解析步骤
    const steps: any[] = []
    for (let i = 0; i < recipeForm.value.steps.length; i++) {
      const s = recipeForm.value.steps[i]
      if (s.description?.trim()) {
        const stepKey = typeof s.step === 'number' ? `第${s.step}步` : String(s.step).trim()
        steps.push({
          step: stepKey,
          description: s.description.trim()
        })
      }
    }

    // 营养计算：根据食材自动计算
    let carb = 0, protein = 0, fat = 0
    if (autoCalculateNutrition.value) {
      for (const m of materials) {
        const materialName = Object.keys(m)[0]
        const amountStr = Object.values(m)[0] as string
        const amount = parseFloat(amountStr.replace(/[^0-9.]/g, '')) || 100

        for (const ing of ingredients.value) {
          const ingNames = ing.name || []
          if (Array.isArray(ingNames) && ingNames.includes(materialName)) {
            const ratio = amount / 500
            carb += (ing.carbohydrate || 0) * ratio
            protein += (ing.protein || 0) * ratio
            fat += (ing.fat || 0) * ratio
            break
          }
        }
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
      carbohydrate: autoCalculateNutrition.value ? Math.round(carb * 100) / 100 : recipeForm.value.carbohydrate,
      protein: autoCalculateNutrition.value ? Math.round(protein * 100) / 100 : recipeForm.value.protein,
      fat: autoCalculateNutrition.value ? Math.round(fat * 100) / 100 : recipeForm.value.fat,
      is_halal: recipeForm.value.is_halal,
      allergens: recipeForm.value.allergens,
      vitamins: recipeForm.value.vitamins,
      minerals: recipeForm.value.minerals,
      taste: recipeForm.value.taste,
      status: 'public',
      pictures_url: recipeForm.value.pictures_url
    }

    const token = authStore.token

    // 开始进度模拟（在实际请求发出前）
    progressTimer = startProgressSimulation()

    if (editingRecipeId.value) {
      await axios.put(`/api/recipes/${editingRecipeId.value}`, data, { headers: { Authorization: `Bearer ${token}` } })
      alert('食谱已更新')
    } else {
      await axios.post('/api/recipes/', data, { headers: { Authorization: `Bearer ${token}` } })
      alert('食谱已创建')
    }

    // 完成
    progressPercent.value = 100
    progressMessage.value = '完成'

    // 清空草稿（只在创建后清空）
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

    // 刷新列表
    const res = await axios.get('/api/recipes/all', { headers: { Authorization: `Bearer ${authStore.token}` } })
    allRecipes.value = res.data
  } catch (e: any) {
    progressPercent.value = 0
    progressMessage.value = ''
    if (!e.response) {
      alert('网络错误: ' + e.message)
    } else {
      alert(e.response?.data?.detail || '保存失败')
    }
  } finally {
    isSubmitting.value = false
    if (progressTimer !== null) clearInterval(progressTimer)
    setTimeout(() => { showProgress.value = false }, 800)
  }
}

// ========== 审核操作 ==========
async function approveRecipe(id: number) {
  try {
    await axios.post(`/api/recipes/${id}/approve`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    pendingRecipes.value = pendingRecipes.value.filter(r => r.id !== id)
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

async function rejectRecipe(id: number) {
  try {
    await axios.post(`/api/recipes/${id}/reject`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    pendingRecipes.value = pendingRecipes.value.filter(r => r.id !== id)
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

async function approveUnban(id: number) {
  try {
    await axios.post(`/api/recipes/${id}/unban-approve`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    appealingRecipes.value = appealingRecipes.value.filter(r => r.id !== id)
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

async function rejectUnban(id: number) {
  try {
    await axios.post(`/api/recipes/${id}/unban-reject`, {}, { headers: { Authorization: `Bearer ${authStore.token}` } })
    appealingRecipes.value = appealingRecipes.value.filter(r => r.id !== id)
  } catch (e: any) {
    alert(e.response?.data?.detail || '操作失败')
  }
}

// ========== 管理员管理 ==========
async function createAdmin() {
  formError.value = ''
  if (!newAdmin.value.password) {
    formError.value = '请填写密码'
    return
  }

  console.log('创建管理员: password=', newAdmin.value.password, 'days=', newAdmin.value.permission_duration_days)
  try {
    const res = await axios.post('/api/admins/ctadmin', {
      password: newAdmin.value.password,
      permission_duration_days: newAdmin.value.permission_duration_days
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    console.log('创建成功:', res.data)
    const newAccount = res.data.account
    await navigator.clipboard.writeText(newAccount)
    alert(`管理员创建成功！\n账号: ${newAccount}\n(已复制到剪贴板)`)
    showAdminForm.value = false
    newAdmin.value = { password: '', permission_duration_days: 30 }
    // 刷新列表
    const listRes = await axios.get('/api/admins/', { headers: { Authorization: `Bearer ${authStore.token}` } })
    admins.value = listRes.data
  } catch (e: any) {
    console.error('创建失败:', e.response?.status, e.response?.data)
    formError.value = e.response?.data?.detail || '创建失败'
  }
}

async function deleteAdmin(account: string) {
  if (!confirm(`确定要删除管理员 ${account} 吗？`)) return

  try {
    await axios.delete(`/api/admins/${account}`, { headers: { Authorization: `Bearer ${authStore.token}` } })
    admins.value = admins.value.filter(a => a.account !== account)
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

// ========== 工具函数 ==========
function getRecipeEmoji(name: string): string {
  const emojiMap: Record<string, string> = {
    '炒': '🍳', '煮': '🍲', '蒸': '🥟', '炸': '🍟', '烤': '🍕',
    '焖': '🍚', '凉拌': '🥗', '汤': '🍜', '面': '🍜', '默认': '🍽️'
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

function getIngredientImage(ing: any): string | null {
  if (ing.picture_url) {
    return ing.picture_url
  }
  return null
}

function getIngredientEmoji(category: string): string {
  const emojiMap: Record<string, string> = {
    '蔬菜': '🥬', '水果': '🍎', '肉类': '🥩', '蛋类': '🥚',
    '奶制品': '🥛', '谷物': '🌾', '豆类': '🫘', '坚果': '🥜',
    '海鲜': '🦐', '其他': '🍽️'
  }
  return emojiMap[category] || emojiMap['其他']
}

function openRecipeDetail(id: number) {
  window.open(`/recipes/${id}`, '_blank')
}

function openIngredientDetail(id: number) {
  window.open(`/ingredients/${id}`, '_blank')
}

function logout() {
  authStore.logout()
  router.push('/')
}

async function getalladmins() {
  try {
    const res = await axios.get('/api/admins/', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    admins.value = res.data
    console.log('管理员列表:', admins.value)
  } catch (e: any) {
    alert(e.response?.data?.detail || '获取管理员列表失败')
  }
}

// ========== 知识库管理 ==========
const kbList = ref<any[]>([])
const kbActive = ref<any>(null)
const kbLoading = ref(false)

async function loadKbList() {
  kbLoading.value = true
  try {
    const res = await axios.get('/api/admins/knowledge-base/list', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    kbList.value = res.data.bases || []
    kbActive.value = res.data.active || null
  } catch (e: any) {
    console.error('加载知识库列表失败', e)
    alert(e.response?.data?.detail || '加载知识库列表失败')
  } finally {
    kbLoading.value = false
  }
}

const kbUploading = ref(false)
const kbUploadError = ref('')

async function uploadKb(file: File) {
  kbUploadError.value = ''
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'txt') {
    kbUploadError.value = '仅支持 .txt 文件'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    kbUploadError.value = '文件大小不能超过 10MB'
    return
  }

  kbUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await axios.post('/api/admins/knowledge-base/upload', formData, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'multipart/form-data',
      },
    })
    alert(`知识库「${res.data.name}」上传成功（${res.data.records_count} 条记录）`)
    await loadKbList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '上传失败')
  } finally {
    kbUploading.value = false
  }
}

function triggerKbUpload() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.txt'
  input.onchange = async () => {
    const file = input.files?.[0]
    if (file) await uploadKb(file)
  }
  input.click()
}

async function activateKb(name: string) {
  try {
    const res = await axios.post('/api/admins/knowledge-base/activate',
      { name },
      { headers: { Authorization: `Bearer ${authStore.token}` } },
    )
    alert(res.data.message)
    await loadKbList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '激活失败')
  }
}

async function deleteKb(name: string) {
  if (!confirm(`确定要删除知识库「${name}」吗？\n此操作不可恢复。`)) return
  try {
    const res = await axios.delete(`/api/admins/knowledge-base/${encodeURIComponent(name)}`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    alert(res.data.message)
    await loadKbList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '删除失败')
  }
}

const kbRebuilding = ref(false)

async function rebuildKb() {
  if (!confirm('确定要重新构建当前知识库的向量索引吗？')) return
  kbRebuilding.value = true
  try {
    const res = await axios.post('/api/admins/knowledge-base/rebuild', {}, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    alert(res.data.message)
    await loadKbList()
  } catch (e: any) {
    alert(e.response?.data?.detail || '重建失败')
  } finally {
    kbRebuilding.value = false
  }
}
</script>

<template>
  <div class="admin-page">
    <!-- 剪贴板提示 -->
    <div v-if="clipboardData.type" class="clipboard-toast">
      <div class="clipboard-content">
        <span>检测到{{ clipboardData.type === 'ingredient' ? '食材' : '食谱' }}数据，是否导入？</span>
        <div class="clipboard-actions">
          <button class="btn-confirm" @click="applyClipboardData">导入</button>
          <button class="btn-cancel" @click="dismissClipboard">忽略</button>
        </div>
      </div>
    </div>

    <div class="admin-header">
      <div class="header-info">
        <h1>管理中心</h1>
        <p>管理员: {{ authStore.account }} ({{ isSuperAdmin ? '超级管理员' : '普通管理员' }})</p>
      </div>
    </div>

    <!-- 0级管理员：管理员管理 -->
    <div v-if="isSuperAdmin" class="admin-section">
      <div class="section-header">
        <h2>管理员管理</h2>
        <button class="btn-add" @click="showAdminForm = true">+ 创建管理员</button>
        <button class="btn-confirm" @click="getalladmins">确认管理员</button>
      </div>

      <!-- 创建管理员表单 -->
      <div v-if="showAdminForm" class="create-form">
        <h3>创建新管理员</h3>
        <div class="form-row">
          <input v-model="newAdmin.password" type="password" placeholder="密码" />
          <input v-model.number="newAdmin.permission_duration_days" type="number" placeholder="权限天数" min="1" max="365" style="width: 100px" />
          <button class="btn-confirm" @click="createAdmin">创建</button>
          <button class="btn-cancel" @click="showAdminForm = false">取消</button>
        </div>
        <p v-if="formError" class="error">{{ formError }}</p>
      </div>

      <!-- 管理员列表 -->
      <div class="admin-list">
        <div v-for="admin in admins" :key="admin.account" class="admin-item">
          <span class="admin-account">{{ admin.account }}</span>
          <span class="admin-level">Lv.{{ admin.level }}</span>
          <button
            v-if="admin.level !== 0"
            class="btn-delete"
            @click="deleteAdmin(admin.account)"
          >删除</button>
        </div>
      </div>
    </div>

    <!-- 0级管理员：知识库管理 -->
    <div v-if="isSuperAdmin" class="admin-section">
      <div class="section-header">
        <h2>知识库管理</h2>
        <div style="display: flex; gap: 8px;">
          <button class="btn-add" :disabled="kbLoading" @click="loadKbList()" style="background: #78909c;">
            {{ kbLoading ? '加载中...' : '刷新' }}
          </button>
          <button class="btn-add" :disabled="kbUploading" @click="triggerKbUpload()">
            {{ kbUploading ? '上传中...' : '+ 上传知识库' }}
          </button>
        </div>
      </div>

      <!-- 当前激活的知识库 -->
      <div v-if="kbActive" class="kb-active-info">
        <span class="kb-active-label">当前激活：</span>
        <span class="kb-active-name">{{ kbActive.name }}</span>
        <span class="kb-active-count">{{ kbActive.records_count || '?' }} 条记录</span>
      </div>

      <!-- 上传错误提示 -->
      <p v-if="kbUploadError" class="error">{{ kbUploadError }}</p>

      <!-- 知识库列表 -->
      <div v-if="kbLoading" class="empty">加载中...</div>
      <div v-else-if="kbList.length === 0" class="empty">暂无知识库</div>
      <div v-else class="admin-list">
        <div v-for="kb in kbList" :key="kb.name" class="kb-item">
          <div class="kb-info">
            <span class="kb-name">{{ kb.name }}</span>
            <span v-if="kb.is_default" class="kb-tag tag-default">默认</span>
            <span v-if="kb.is_active" class="kb-tag tag-active">当前</span>
            <span v-else class="kb-tag tag-inactive">未激活</span>
            <span class="kb-meta">{{ kb.is_default ? '内置知识库' : '上传的知识库' }}</span>
          </div>
          <div class="kb-actions">
            <button
              v-if="!kb.is_active"
              class="btn-approve"
              style="flex: 0; padding: 6px 14px;"
              @click="activateKb(kb.name)"
            >激活</button>
            <button
              v-if="!kb.is_default"
              class="btn-delete"
              style="flex: 0;"
              @click="deleteKb(kb.name)"
            >删除</button>
          </div>
        </div>
      </div>

      <!-- 重建索引 -->
      <div class="kb-rebuild-section">
        <button
          class="btn-rebuild"
          :disabled="kbRebuilding"
          @click="rebuildKb()"
        >{{ kbRebuilding ? '重建中...' : '🔄 重建向量索引' }}</button>
        <span class="kb-hint">当知识库文件更新后，需重建索引使变更生效</span>
      </div>
    </div>

    <!-- 1级管理员功能区 -->
    <div v-if="isNormalAdmin" class="admin-tabs">
      <button
        :class="['tab', { active: activeTab === 'pending' }]"
        @click="activeTab = 'pending'; loadPendingRecipes(); loadAppealingRecipes()"
      >
        待审核食谱
        <span v-if="pendingRecipes.length + appealingRecipes.length" class="badge">{{ pendingRecipes.length + appealingRecipes.length }}</span>
      </button>
      <button
        :class="['tab', { active: activeTab === 'users' }]"
        @click="activeTab = 'users'; loadUsers()"
      >
        用户管理
      </button>
      <button
        :class="['tab', { active: activeTab === 'recipes' }]"
        @click="activeTab = 'recipes'; loadAllRecipes()"
      >
        食谱管理
      </button>
      <button
        :class="['tab', { active: activeTab === 'ingredients' }]"
        @click="activeTab = 'ingredients'; loadIngredients()"
      >
        食材管理
      </button>
    </div>

    <!-- 待审核食谱 -->
    <div v-if="isNormalAdmin && activeTab === 'pending'" class="admin-tabs">
      <button :class="['tab', { active: pendingTab === 'pending' }]" @click="pendingTab = 'pending'">
        申请公开
        <span v-if="pendingRecipes.length" class="badge">{{ pendingRecipes.length }}</span>
      </button>
      <button :class="['tab', { active: pendingTab === 'appealing' }]" @click="pendingTab = 'appealing'">
        申请解封
        <span v-if="appealingRecipes.length" class="badge">{{ appealingRecipes.length }}</span>
      </button>
    </div>
    <div v-if="isNormalAdmin && activeTab === 'pending' && pendingTab === 'pending'" class="admin-content">
      <h2>申请公开食谱</h2>
      <div v-if="pendingRecipes.length === 0" class="empty">
        暂无申请公开的食谱
      </div>
      <div v-else class="recipe-grid">
        <div v-for="recipe in pendingRecipes" :key="recipe.id" class="recipe-card">
          <div class="recipe-image" @click="openRecipeDetail(recipe.id)">
            <img v-if="getRecipeFirstImage(recipe)" :src="getRecipeFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
            <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h3>{{ recipe.name }}</h3>
            <p class="meta">来源: {{ recipe.source }}</p>
            <div class="actions">
              <button class="btn-approve" @click="approveRecipe(recipe.id)">通过</button>
              <button class="btn-reject" @click="rejectRecipe(recipe.id)">拒绝</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 申请解封食谱 -->
    <div v-if="isNormalAdmin && activeTab === 'pending' && pendingTab === 'appealing'" class="admin-content">
      <h2>申请解封食谱</h2>
      <div v-if="appealingRecipes.length === 0" class="empty">
        暂无申请解封的食谱
      </div>
      <div v-else class="recipe-grid">
        <div v-for="recipe in appealingRecipes" :key="recipe.id" class="recipe-card">
          <div class="recipe-image" @click="openRecipeDetail(recipe.id)">
            <img v-if="getRecipeFirstImage(recipe)" :src="getRecipeFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
            <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h3>{{ recipe.name }}</h3>
            <p class="meta">来源: {{ recipe.source }}</p>
            <div class="actions">
              <button class="btn-approve" @click="approveUnban(recipe.id)">解封</button>
              <button class="btn-reject" @click="rejectUnban(recipe.id)">拒绝</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 用户管理 -->
    <div v-if="isNormalAdmin && activeTab === 'users'" class="admin-content">
      <h2>用户管理</h2>

      <!-- 搜索 -->
      <div class="search-box">
        <input
          v-model="userSearchQuery"
          type="text"
          placeholder="搜索用户..."
        />
      </div>

      <!-- 用户列表 -->
      <div v-if="filteredUsers.length === 0" class="empty">
        暂无用户
      </div>
      <div v-else class="user-list">
        <div v-for="user in filteredUsers" :key="user.id" class="user-item">
          <div class="user-info">
            <span class="user-account">{{ user.account }}</span>
            <span class="user-nickname">{{ user.nickname }}</span>
            <span class="user-gender">{{ user.gender }}</span>
            <span v-if="user.is_halal" class="tag halal">清真</span>
          </div>
          <div class="user-actions">
            <button class="btn-edit" @click="openUserEdit(user)">编辑</button>
            <button v-if="user.status !== '冻结'" class="btn-freeze" @click="freezeUser(user.account)">冻结</button>
            <button v-else class="btn-unfreeze" @click="unfreezeUser(user.account)">解冻</button>
          </div>
        </div>
      </div>

      <!-- 编辑用户弹窗 -->
      <div v-if="showUserForm" class="modal-overlay" @click="isAccidentalClose = true; showUserForm = false">
        <div class="modal" @click.stop>
          <h3>编辑用户 - {{ editingUser?.account }}</h3>
          <div class="form-group">
            <label>昵称</label>
            <input v-model="userForm.nickname" type="text" />
          </div>
          <div class="form-group">
            <label>性别</label>
            <select v-model="userForm.gender">
              <option value="男">男</option>
              <option value="女">女</option>
              <option value="私密">私密</option>
            </select>
          </div>
          <div class="form-group">
            <label>年龄</label>
            <input v-model="userForm.age" type="number" />
          </div>
          <div class="form-group">
            <label>
              <input v-model="userForm.is_halal" type="checkbox" />
              清真
            </label>
          </div>
          <div class="form-group">
            <label>过敏源（逗号分隔）</label>
            <input v-model="userForm.allergens" type="text" placeholder="如: 花生, 虾" />
          </div>
          <div class="modal-actions">
            <button class="btn-confirm" @click="saveUser">保存</button>
            <button class="btn-cancel" @click="showUserForm = false">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 食谱管理 -->
    <div v-if="isNormalAdmin && activeTab === 'recipes'" class="admin-content">
      <div class="section-header">
        <h2>食谱管理</h2>
        <button class="btn-add" @click="openRecipeCreate(null, false)">+ 添加食谱</button>
      </div>

      <!-- 搜索 -->
      <div class="search-box">
        <input
          v-model="recipeSearchQuery"
          type="text"
          placeholder="搜索食谱..."
        />
      </div>

      <!-- 食谱列表 -->
      <div v-if="filteredRecipes.length === 0" class="empty">
        暂无食谱
      </div>
      <div v-else class="recipe-grid">
        <div v-for="recipe in filteredRecipes" :key="recipe.id" class="recipe-card">
          <div class="recipe-image" @click="openRecipeDetail(recipe.id)">
            <img v-if="getRecipeFirstImage(recipe)" :src="getRecipeFirstImage(recipe)" :alt="recipe.name" class="cover-img" loading="lazy" />
            <span v-else class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h3>{{ recipe.name }}</h3>
            <p class="meta">菜系: {{ recipe.cuisine }}</p>
            <p v-if="recipe.creator_account" class="meta">用户创建</p>
            <span class="status" :class="{ public: recipe.status === 'public', banned: recipe.status === 'banned', pending: recipe.status === 'pending', appealing: recipe.status === 'appealing' }">
              {{ recipe.status === 'banned' ? '已封禁' : (recipe.status === 'public' ? '已公开' : (recipe.status === 'appealing' ? '申请解封' : '申请公开')) }}
            </span>
            <div class="actions">
              <!-- 系统食谱：可编辑、可删除、可设私密 -->
              <template v-if="isEditable(recipe)">
                <button class="btn-edit" @click="openRecipeCreate(recipe)">编辑</button>
                <button class="btn-toggle" @click="toggleRecipeVisibility(recipe.id, recipe.status)">
                  {{ recipe.status === 'public' ? '设为私密' : '设为公开' }}
                </button>
                <button class="btn-delete-small" @click="deleteRecipe(recipe.id)">删除</button>
              </template>
              <!-- 用户食谱：显示食谱状态，可封禁 -->
              <template v-else>
                <button v-if="recipe.status === 'public'" class="btn-toggle" @click="toggleRecipeVisibility(recipe.id, recipe.status)">
                  封禁
                </button>
                <button v-if="recipe.status === 'pending'" class="btn-toggle" @click="approveRecipe(recipe.id)">通过</button>
                <button v-if="recipe.status === 'pending'" class="btn-reject" @click="rejectRecipe(recipe.id)">拒绝</button>
                <button v-if="recipe.status === 'appealing'" class="btn-toggle" @click="approveUnban(recipe.id)">解封</button>
                <button v-if="recipe.status === 'appealing'" class="btn-reject" @click="rejectUnban(recipe.id)">拒绝</button>
              </template>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 食材管理 -->
    <div v-if="isNormalAdmin && activeTab === 'ingredients'" class="admin-content">
      <div class="section-header">
        <h2>食材管理</h2>
        <button class="btn-add" @click="openIngredientCreate(false)">+ 添加食材</button>
      </div>

      <!-- 食材列表 -->
      <div v-if="ingredients.length === 0" class="empty">
        暂无食材
      </div>
      <div v-else class="ingredient-list">
        <div v-for="ing in ingredients" :key="ing.id" class="ingredient-item">
          <div class="ingredient-image">
            <img v-if="getIngredientImage(ing)" :src="getIngredientImage(ing)" :alt="Array.isArray(ing.name) ? ing.name[0] : ing.name" class="cover-img" loading="lazy" />
            <span v-else class="ingredient-emoji">{{ getIngredientEmoji(ing.category) }}</span>
          </div>
          <div class="ingredient-info" @click="openIngredientDetail(ing.id)">
            <span class="ingredient-name">{{ Array.isArray(ing.name) ? ing.name.join(', ') : ing.name }}</span>
            <span class="ingredient-category">{{ ing.category }}</span>
            <span class="ingredient-nutrition">
              碳水{{ ing.carbohydrate }}g 蛋白{{ ing.protein }}g 脂肪{{ ing.fat }}g
            </span>
            <span v-if="ing.is_halal" class="tag halal">清真</span>
            <span v-if="ing.is_allergen" class="tag allergen">易过敏</span>
          </div>
          <div class="ingredient-actions">
            <button class="btn-edit" @click="openIngredientEdit(ing)">编辑</button>
            <button class="btn-delete-small" @click="deleteIngredient(ing.id)">删除</button>
          </div>
        </div>
      </div>

      <!-- 食材表单弹窗 -->
      <div v-if="showIngredientForm" class="modal-overlay" @click="isAccidentalClose = true; showIngredientForm = false">
        <div class="modal" @click.stop>
          <h3>{{ editingIngredient ? '编辑食材' : (savedIngredientForm.name ? '继续填写食材' : '添加食材') }}</h3>
          <div v-if="savedIngredientForm.name && !editingIngredient" style="margin-bottom: 1rem;">
            <button class="btn-add" @click="openIngredientCreate()">
              继续填写 →
            </button>
          </div>
          <div class="form-group">
            <label>食材名称（逗号分隔）</label>
            <input v-model="ingredientForm.name" type="text" placeholder="如: 西红柿, 番茄" />
          </div>
          <div class="form-group">
            <label>分类</label>
            <select v-model="ingredientForm.category">
              <option v-for="c in ingredientCategories" :key="c" :value="c">{{ c }}</option>
            </select>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>碳水(g)</label>
              <input v-model.number="ingredientForm.carbohydrate" type="number" step="0.1" />
            </div>
            <div class="form-group">
              <label>蛋白质(g)</label>
              <input v-model.number="ingredientForm.protein" type="number" step="0.1" />
            </div>
            <div class="form-group">
              <label>脂肪(g)</label>
              <input v-model.number="ingredientForm.fat" type="number" step="0.1" />
            </div>
          </div>
          <div class="form-group">
            <label>
              <input v-model="ingredientForm.is_halal" type="checkbox" />
              清真
            </label>
            <label>
              <input v-model="ingredientForm.is_allergen" type="checkbox" />
              易过敏
            </label>
          </div>
          <div class="form-group">
            <label>维生素（逗号分隔）</label>
            <input v-model="ingredientForm.vitamins" type="text" placeholder="如: 维生素C, 维生素A" />
          </div>
          <div class="form-group">
            <label>封面图片</label>
            <div class="cover-upload-area">
              <div v-if="ingredientForm.picture_url" class="cover-preview-item">
                <img :src="ingredientForm.picture_url" alt="封面" loading="lazy" />
                <button class="btn-remove-cover" @click="removeIngredientCover">×</button>
              </div>
              <div v-else class="cover-input-wrapper">
                <input type="file" accept="image/*" @change="onIngredientCoverSelect" id="ingredient-cover-input" style="display: none;" />
                <label for="ingredient-cover-input" class="cover-input-label">
                  <span v-if="uploadingIngredientCover">上传中...</span>
                  <span v-else>+ 添加封面</span>
                </label>
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>矿物质（逗号分隔）</label>
            <input v-model="ingredientForm.minerals" type="text" placeholder="如: 钙, 铁" />
          </div>
          <div class="modal-actions">
            <button class="btn-confirm" @click="saveIngredient">保存</button>
            <button class="btn-save-draft" @click="saveIngredientDraft">保存草稿</button>
            <button class="btn-cancel" @click="showIngredientForm = false">取消</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 食谱表单弹窗 -->
    <div v-if="showRecipeForm" class="modal-overlay" @click="isAccidentalClose = true; showRecipeForm = false">
      <div class="modal" @click.stop style="max-width: 700px; max-height: 90vh; overflow-y: auto;">
        <h3>添加食谱</h3>
        <div v-if="savedRecipeForm.name" style="margin-bottom: 1rem;">
          <button class="btn-add" @click="openRecipeCreate()">
            继续填写 →
          </button>
        </div>
        <div class="form-group">
          <label>食谱名称 *</label>
          <input v-model="recipeForm.name" type="text" placeholder="如: 红烧肉" />
        </div>

        <div class="form-group">
          <label>封面图片 <span v-if="!isEditingSystemRecipe" class="form-hint">(用户食谱不可修改封面)</span></label>
          <div class="cover-upload-area" v-if="isEditingSystemRecipe">
            <div v-if="recipeForm.pictures_url && recipeForm.pictures_url.length > 0" class="cover-list">
              <div v-for="(url, idx) in recipeForm.pictures_url" :key="idx" class="cover-item">
                <img :src="url" alt="封面" loading="lazy" />
                <button class="btn-remove-cover" @click="removeRecipeCover(idx)">×</button>
              </div>
            </div>
            <div v-if="!recipeForm.pictures_url || recipeForm.pictures_url.length < 3" class="cover-input-wrapper">
              <input type="file" accept="image/*" @change="onRecipeCoverSelect" id="recipe-cover-input-admin" style="display: none;" />
              <label for="recipe-cover-input-admin" class="cover-input-label">
                <span v-if="uploadingRecipeCover">上传中...</span>
                <span v-else>+ 添加封面</span>
              </label>
            </div>
            <p class="form-hint">最多3张封面图片</p>
          </div>
          <div v-else class="cover-display-only">
            <div v-if="recipeForm.pictures_url && recipeForm.pictures_url.length > 0" class="cover-list">
              <div v-for="(url, idx) in recipeForm.pictures_url" :key="idx" class="cover-item">
                <img :src="url" alt="封面" loading="lazy" />
              </div>
            </div>
            <p v-else class="form-hint">无封面图片</p>
          </div>
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

        <!-- 所需材料 -->
        <div class="form-group">
          <label>所需材料</label>
          <div v-for="(m, idx) in recipeForm.materials" :key="'m'+idx" class="line-input">
            <input v-model="m.name" placeholder="食材名" />
            <input v-model="m.amount" placeholder="用量" style="width: 100px;" />
            <button v-if="recipeForm.materials.length > 1" class="btn-remove" @click="removeMaterial(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addMaterial">+</button>
        </div>

        <!-- 所需调料 -->
        <div class="form-group">
          <label>所需调料</label>
          <div v-for="(s, idx) in recipeForm.seasonings" :key="'s'+idx" class="line-input">
            <input v-model="s.name" placeholder="调料名" />
            <input v-model="s.amount" placeholder="用量" style="width: 100px;" />
            <button v-if="recipeForm.seasonings.length > 1" class="btn-remove" @click="removeSeasoning(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addSeasoning">+</button>
        </div>

        <!-- 制作步骤 -->
        <div class="form-group">
          <label>制作步骤</label>
          <div v-for="(st, idx) in recipeForm.steps" :key="'st'+idx" class="line-input">
            <input v-model="st.step" placeholder="步骤名+时间，如:第一步 10分钟" style="flex: 1;" />
            <input v-model="st.description" placeholder="具体步骤" style="flex: 2;" />
            <button v-if="recipeForm.steps.length > 1" class="btn-remove" @click="removeStep(idx)">×</button>
          </div>
          <button class="btn-add-row" @click="addStep">+</button>
        </div>

        <!-- 营养物质（自动计算） -->
        <div class="form-group">
          <label>
            <input v-model="autoCalculateNutrition" type="checkbox" />
            自动计算营养物质（根据食材和用量计算）
          </label>
        </div>
        <div v-if="!autoCalculateNutrition" class="form-row">
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
          <label>
            <input v-model="recipeForm.is_halal" type="checkbox" />
            清真
          </label>
        </div>

        <div class="form-group">
          <label>口味占比</label>
          <div class="taste-sliders">
            <div class="taste-row" v-for="dim in tasteDimensions" :key="dim.key">
              <span class="taste-label">{{ dim.label }}</span>
              <input type="range" min="0" max="1" step="0.05" :value="recipeForm.taste[dim.key]" @input="updateTaste(dim.key, ($event.target as HTMLInputElement).value)" />
              <span class="taste-value">{{ (recipeForm.taste[dim.key] * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>

        <!-- 过敏食材 -->
        <div class="form-group">
          <label>过敏食材</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.allergens" :key="tag" class="tag-item">
              {{ tag }}
              <span class="tag-remove" @click="removeTag('allergens', tag)">×</span>
            </span>
            <input v-model="newAllergen" placeholder="输入后回车添加" @keyup.enter="addAllergen" style="flex: 1;" />
            <button class="btn-add-tag" @click="addAllergen">+</button>
          </div>
        </div>

        <!-- 维生素 -->
        <div class="form-group">
          <label>维生素</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.vitamins" :key="tag" class="tag-item">
              {{ tag }}
              <span class="tag-remove" @click="removeTag('vitamins', tag)">×</span>
            </span>
            <input v-model="newVitamin" placeholder="输入后回车添加" @keyup.enter="addVitamin" style="flex: 1;" />
            <button class="btn-add-tag" @click="addVitamin">+</button>
          </div>
        </div>

        <!-- 矿物质 -->
        <div class="form-group">
          <label>矿物质</label>
          <div class="tag-input">
            <span v-for="tag in recipeForm.minerals" :key="tag" class="tag-item">
              {{ tag }}
              <span class="tag-remove" @click="removeTag('minerals', tag)">×</span>
            </span>
            <input v-model="newMineral" placeholder="输入后回车添加" @keyup.enter="addMineral" style="flex: 1;" />
            <button class="btn-add-tag" @click="addMineral">+</button>
          </div>
        </div>

        <!-- 维生素 -->
        <div class="form-group">
          <label>维生素</label>
          <div class="tag-list">
            <span v-for="tag in recipeForm.vitamins" :key="tag" class="tag-item">
              {{ tag }}
              <span class="tag-remove" @click="removeTag('vitamins', tag)">×</span>
            </span>
          </div>
        </div>

        <!-- 矿物质 -->
        <div class="form-group">
          <label>矿物质</label>
          <div class="tag-list">
            <span v-for="tag in recipeForm.minerals" :key="tag" class="tag-item">
              {{ tag }}
              <span class="tag-remove" @click="removeTag('minerals', tag)">×</span>
            </span>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-confirm" :disabled="isSubmitting" @click="async () => { await saveRecipe(); closeRecipeForm(false) }">{{ isSubmitting ? '提交中...' : '创建' }}</button>
          <button class="btn-save-draft" @click="closeRecipeForm(true)">保存草稿</button>
          <button class="btn-cancel" @click="closeRecipeForm(false)">取消</button>
        </div>
      </div>
    </div>

    <!-- 0级管理员提示 -->
    <div v-if="isSuperAdmin" class="admin-tip">
      <p>超级管理员权限：可管理管理员账号和知识库</p>
      <p>食谱、食材、用户管理请使用1级管理员账号</p>
    </div>
  </div>

  <!-- 创建/保存进度条 -->
  <div v-if="showProgress" class="modal-overlay">
    <div class="progress-modal">
      <h3>{{ progressMessage }}</h3>
      <div class="progress-bar-track">
        <div class="progress-bar-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <p class="progress-percent">{{ Math.round(progressPercent) }}%</p>
    </div>
  </div>
</template>

<style scoped>
/* 封面上传样式 */
.cover-upload-area {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.cover-preview-item {
  position: relative;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
}

.cover-preview-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cover-display-only {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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

.admin-page {
  max-width: 1200px;
  margin: 0 auto;
}

.admin-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-info h1 {
  color: #2e7d32;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.header-info p {
  color: #78909c;
}

.btn-logout {
  padding: 0.6rem 1.2rem;
  border: none;
  background: #ffebee;
  color: #f44336;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-logout:hover {
  background: #ffcdd2;
}

/* 通用区块 */
.admin-section {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.section-header h2 {
  color: #2e7d32;
  font-size: 1.3rem;
}

.btn-add {
  padding: 0.5rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

/* 表单 */
.create-form {
  background: #f5f5f5;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.create-form h3 {
  font-size: 1rem;
  margin-bottom: 0.8rem;
  color: #37474f;
}

.form-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.form-row input,
.form-row select {
  flex: 1;
  min-width: 150px;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
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

.form-group input,
.form-group select {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
}

.form-group input[type="checkbox"] {
  width: auto;
  margin-right: 0.5rem;
}

.btn-confirm {
  padding: 0.6rem 1rem;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-cancel {
  padding: 0.6rem 1rem;
  background: #e0e0e0;
  color: #666;
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

.error {
  color: #f44336;
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

/* 管理员列表 */
.admin-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.admin-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.8rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.admin-account {
  flex: 1;
  font-weight: 500;
}

.admin-level {
  color: #78909c;
  font-size: 0.9rem;
}

.btn-delete {
  padding: 0.3rem 0.8rem;
  background: #ffebee;
  color: #f44336;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

/* Tabs */
.admin-tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

/* Nav Cards */
.admin-nav-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  padding: 2rem;
}

.nav-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2rem;
  background: white;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.nav-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
}

.nav-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.nav-text {
  font-size: 1.1rem;
  font-weight: 500;
  color: #333;
}

.nav-desc {
  font-size: 0.8rem;
  color: #78909c;
  margin-top: 0.25rem;
}

.tab {
  padding: 0.8rem 1.5rem;
  border: none;
  background: white;
  border-radius: 12px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #78909c;
}

.tab:hover {
  background: #e8f5e9;
}

.tab.active {
  background: #4caf50;
  color: white;
}

.badge {
  background: #f44336;
  color: white;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
  font-size: 0.75rem;
}

/* Content */
.admin-content {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.admin-content h2 {
  color: #2e7d32;
  margin-bottom: 1.5rem;
}

.search-box {
  margin-bottom: 1.5rem;
}

.search-box input {
  width: 100%;
  padding: 0.8rem 1rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  font-size: 1rem;
}

.search-box input:focus {
  outline: none;
  border-color: #4caf50;
}

.empty {
  text-align: center;
  padding: 3rem;
  color: #78909c;
}

/* 食谱网格 */
.recipe-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
}

.recipe-card {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
}

.recipe-image {
  height: 120px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden; 
  cursor: pointer;
}

.recipe-emoji {
  font-size: 3rem;
}

.recipe-info {
  padding: 1rem;
}

.recipe-info h3 {
  color: #2e7d32;
  font-size: 1rem;
  margin-bottom: 0.3rem;
}

.recipe-info .meta {
  font-size: 0.8rem;
  color: #78909c;
  margin-bottom: 0.5rem;
}

.status {
  font-size: 0.75rem;
  color: #78909c;
  display: inline-block;
  margin-bottom: 0.5rem;
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

.actions {
  display: flex;
  gap: 0.5rem;
}

.btn-approve, .btn-reject {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.3s ease;
}

.btn-approve {
  background: #4caf50;
  color: white;
}

.btn-approve:hover {
  background: #43a047;
}

.btn-reject {
  background: #ffebee;
  color: #f44336;
}

.btn-reject:hover {
  background: #ffcdd2;
}

.btn-toggle {
  flex: 1;
  padding: 0.4rem;
  border: 1px solid #4caf50;
  background: white;
  color: #4caf50;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-reject {
  flex: 1;
  padding: 0.4rem;
  border: 1px solid #f44336;
  background: white;
  color: #f44336;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}

.btn-delete-small {
  flex: 1;
  padding: 0.4rem;
  background: #ffebee;
  color: #f44336;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.8rem;
}

/* 用户列表 */
.user-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.user-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.user-account {
  font-weight: 500;
  color: #2e7d32;
}

.user-nickname {
  color: #37474f;
}

.user-gender {
  color: #78909c;
  font-size: 0.85rem;
}

.user-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-edit {
  padding: 0.4rem 0.8rem;
  background: #e3f2fd;
  color: #1976d2;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-freeze {
  padding: 0.4rem 0.8rem;
  background: #fff3e0;
  color: #f57c00;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-unfreeze {
  padding: 0.4rem 0.8rem;
  background: #e8f5e9;
  color: #4caf50;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

/* 标签 */
.tag {
  font-size: 0.7rem;
  padding: 0.2rem 0.5rem;
  border-radius: 10px;
}

.tag.halal {
  background: #e3f2fd;
  color: #1976d2;
}

.tag.allergen {
  background: #ffebee;
  color: #d32f2f;
}

/* 食材列表 */
.ingredient-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.ingredient-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 8px;
}

.ingredient-image {
  width: 60px;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  flex-shrink: 0;
}

.ingredient-image .cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ingredient-image .ingredient-emoji {
  font-size: 1.8rem;
}

.ingredient-info {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  cursor: pointer;
  flex: 1;
}

.ingredient-name {
  font-weight: 500;
  color: #2e7d32;
}

.ingredient-category {
  color: #689f38;
  background: #e8f5e9;
  padding: 0.2rem 0.6rem;
  border-radius: 10px;
  font-size: 0.8rem;
}

.ingredient-nutrition {
  color: #78909c;
  font-size: 0.8rem;
}

.ingredient-actions {
  display: flex;
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

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

/* 提示 */
.admin-tip {
  margin-top: 2rem;
  padding: 1.5rem;
  background: #fff3e0;
  border-radius: 12px;
  text-align: center;
}

.admin-tip p {
  color: #f57c00;
  margin: 0.3rem 0;
}

/* 响应式 */
@media (max-width: 768px) {
  .recipe-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .admin-tabs {
    flex-wrap: wrap;
  }

  .user-item,
  .ingredient-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .user-actions,
  .ingredient-actions {
    margin-top: 0.5rem;
  }
}

/* 行输入框样式 */
.line-input {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
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
  font-size: 1rem;
}

.btn-add-row {
  background: #e8f5e9;
  color: #4caf50;
  border: 1px dashed #4caf50;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.9rem;
  margin-top: 0.3rem;
}

.btn-add-row:hover {
  background: #c8e6c9;
}

/* 标签输入样式 */
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

.tag-input input:focus {
  outline: none;
  border-color: #4caf50;
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

.tag-remove:hover {
  color: #d32f2f;
}

.btn-add-tag {
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0.4rem 0.8rem;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-add-tag:hover {
  background: #43a047;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

@media (max-width: 600px) {
  .line-input {
    grid-template-columns: 1fr;
  }
}

.taste-sliders {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.taste-row {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.taste-label {
  min-width: 2rem;
  font-size: 0.9rem;
  color: #555;
  text-align: center;
}

.taste-row input[type="range"] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  background: #e0e0e0;
  border-radius: 3px;
  outline: none;
}

.taste-row input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #4caf50;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
}

.taste-value {
  min-width: 3rem;
  font-size: 0.85rem;
  color: #666;
  text-align: right;
}

/* 进度条弹窗 */
.progress-modal {
  background: white;
  border-radius: 16px;
  padding: 2.5rem 3rem;
  text-align: center;
  min-width: 360px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}

.progress-modal h3 {
  color: #2e7d32;
  margin-bottom: 1.5rem;
  font-size: 1.1rem;
}

.progress-bar-track {
  width: 100%;
  height: 12px;
  background: #e8f5e9;
  border-radius: 6px;
  overflow: hidden;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #4caf50, #66bb6a);
  border-radius: 6px;
  transition: width 0.3s ease;
}

.progress-percent {
  margin-top: 0.8rem;
  color: #78909c;
  font-size: 0.9rem;
}

/* === 知识库管理 === */
.kb-active-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: #e8f5e9;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.kb-active-label {
  color: #555;
}

.kb-active-name {
  font-weight: 600;
  color: #2e7d32;
}

.kb-active-count {
  color: #78909c;
  font-size: 0.85rem;
  margin-left: auto;
}

.kb-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 12px 14px;
  background: #f9f9f9;
  border-radius: 8px;
  transition: background 0.2s;
}

.kb-item:hover {
  background: #f0fdf4;
}

.kb-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  flex: 1;
}

.kb-name {
  font-weight: 500;
  color: #2e7d32;
}

.kb-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.kb-tag.tag-default {
  background: #e3f2fd;
  color: #1976d2;
}

.kb-tag.tag-active {
  background: #e8f5e9;
  color: #2e7d32;
}

.kb-tag.tag-inactive {
  background: #f5f5f5;
  color: #9e9e9e;
}

.kb-meta {
  font-size: 0.8rem;
  color: #9e9e9e;
}

.kb-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.kb-rebuild-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-rebuild {
  padding: 8px 16px;
  background: #fff3e0;
  color: #e65100;
  border: 1px solid #ffe0b2;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: all 0.2s;
}

.btn-rebuild:hover {
  background: #ffe0b2;
}

.btn-rebuild:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kb-hint {
  font-size: 0.8rem;
  color: #9e9e9e;
}

@media (max-width: 600px) {
  .kb-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .kb-actions {
    margin-top: 6px;
    align-self: flex-end;
  }

  .kb-rebuild-section {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>