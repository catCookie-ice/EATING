<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

// 0级管理员 - 超级管理员
const isSuperAdmin = computed(() => authStore.adminLevel === 0)
// 1级管理员 - 普通管理员
const isNormalAdmin = computed(() => authStore.adminLevel === 1)

const activeTab = ref('pending')

// 待审核数据
const pendingRecipes = ref<any[]>([])
const loading = ref(false)

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
const ingredientCategories = ['蔬菜', '水果', '肉类', '蛋类', '奶制品', '谷物', '豆类', '坚果', '海鲜', '其他']
const cuisineOptions = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "东北菜", "西北菜","家常菜","西餐", "日料", "韩餐", "东南亚菜", "家常菜","其他"
    ]
const methodOptions = ["蒸", "煮", "炸", "炒", "焖", "拌", "卤", "烤", "煎", "腌","炖", "其他"]

// 食谱表单
const showRecipeForm = ref(false)
const editingRecipeId = ref<number | null>(null)
const autoCalculateNutrition = ref(false)
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
  minerals: [] as string[]
})
let savedRecipeForm = JSON.parse(JSON.stringify(recipeForm.value))

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
  minerals: ''
})
let savedIngredientForm = JSON.parse(JSON.stringify(ingredientForm.value))

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
    loading.value = false
    return
  }

  // 1级管理员获取所有数据
  if (isNormalAdmin.value) {
    try {
      // 待审核食谱
      const res = await axios.get('/api/recipes/pending', {
        headers: { Authorization: `Bearer ${token}` }
      })
      pendingRecipes.value = res.data
      console.log('待审核食谱:', pendingRecipes.value.length)

      // 用户列表
      console.log('获取用户列表...')
      const userRes = await axios.get('/api/admins/users', {
        headers: { Authorization: `Bearer ${token}` }
      })
      users.value = userRes.data
      console.log('用户列表:', users.value.length)

      // 食谱列表
      console.log('获取食谱列表...')
      const recipeRes = await axios.get('/api/recipes/all', {
        headers: { Authorization: `Bearer ${token}` }
      })
      allRecipes.value = recipeRes.data
      console.log('食谱列表:', allRecipes.value.length)

      // 食材列表
      console.log('获取食材列表...')
      const ingRes = await axios.get('/api/ingredients/', {
        headers: { Authorization: `Bearer ${token}` }
      })
      ingredients.value = ingRes.data
      console.log('食材列表:', ingredients.value.length)
    } catch (e: any) {
      console.error('fetchData错误:', e.response?.status, e.response?.data)
    }
  }

  loading.value = false
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
  if (!recipeSearchQuery.value) return allRecipes.value
  const query = recipeSearchQuery.value.toLowerCase()
  return allRecipes.value.filter(r =>
    r.name?.toLowerCase().includes(query) ||
    r.cuisine?.toLowerCase().includes(query)
  )
})

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

async function toggleRecipeVisibility(id: number, currentStatus: boolean) {
  try {
    await axios.put(`/api/recipes/${id}/visibility`, { is_public: !currentStatus }, { headers: { Authorization: `Bearer ${authStore.token}` } })
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
    minerals: ing.minerals?.join(', ') || ''
  }
  showIngredientForm.value = true
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
      minerals: ingredientForm.value.minerals ? ingredientForm.value.minerals.split(',').map(s => s.trim()).filter(Boolean) : []
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
        minerals: ''
      }
      localStorage.removeItem('ingredient_draft')
    }

    showIngredientForm.value = false
    editingIngredient.value = null

    // 刷新列表
    const res = await axios.get('/api/ingredients/', { headers: { Authorization: `Bearer ${authStore.token}` } })
    ingredients.value = res.data
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
      minerals: recipe.minerals || []
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
        minerals: []
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
      minerals: []
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
    minerals: []
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

function removeTag(type: 'allergens' | 'vitamins' | 'minerals', tag: string) {
  if (type === 'allergens') {
    recipeForm.value.allergens = recipeForm.value.allergens.filter(t => t !== tag)
  } else if (type === 'vitamins') {
    recipeForm.value.vitamins = recipeForm.value.vitamins.filter(t => t !== tag)
  } else {
    recipeForm.value.minerals = recipeForm.value.minerals.filter(t => t !== tag)
  }
}

async function saveRecipe() {
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
        // step 可能是数字或字符串，需要转换为字符串
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
      // 遍历食谱中的食材，从食材库获取营养数据并根据用量计算
      for (const m of materials) {
        const materialName = Object.keys(m)[0]
        const amountStr = Object.values(m)[0] as string
        // 尝试提取数字用量（单位：g）
        const amount = parseFloat(amountStr.replace(/[^0-9.]/g, '')) || 100 // 默认100g

        // 查找食材
        for (const ing of ingredients.value) {
          const ingNames = ing.name || []
          if (Array.isArray(ingNames) && ingNames.includes(materialName)) {
            // 按比例计算（以500g为基准）
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
      status: 'public'
    }

    const token = authStore.token

    if (editingRecipeId.value) {
      // 更新模式
      await axios.put(`/api/recipes/${editingRecipeId.value}`, data, { headers: { Authorization: `Bearer ${token}` } })
      alert('食谱已更新')
    } else {
      // 创建新食谱
      await axios.post('/api/recipes/', data, { headers: { Authorization: `Bearer ${token}` } })
      alert('食谱已创建')
    }

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
      minerals: []
    }
    localStorage.removeItem('recipe_draft')

    showRecipeForm.value = false

    // 刷新列表
    const res = await axios.get('/api/recipes/all', { headers: { Authorization: `Bearer ${authStore.token}` } })
    allRecipes.value = res.data
  } catch (e: any) {
    // 检查是否是网络错误
    if (!e.response) {
      alert('网络错误: ' + e.message)
    } else {
      alert(e.response?.data?.detail || '保存失败')
    }
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
      <button class="btn-logout" @click="logout">退出登录</button>
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

    <!-- 1级管理员功能区 -->
    <div v-if="isNormalAdmin" class="admin-tabs">
      <button
        :class="['tab', { active: activeTab === 'pending' }]"
        @click="activeTab = 'pending'"
      >
        待审核食谱
        <span v-if="pendingRecipes.length" class="badge">{{ pendingRecipes.length }}</span>
      </button>
      <button
        :class="['tab', { active: activeTab === 'users' }]"
        @click="activeTab = 'users'"
      >
        用户管理
      </button>
      <button
        :class="['tab', { active: activeTab === 'recipes' }]"
        @click="activeTab = 'recipes'"
      >
        食谱管理
      </button>
      <button
        :class="['tab', { active: activeTab === 'ingredients' }]"
        @click="activeTab = 'ingredients'"
      >
        食材管理
      </button>
    </div>

    <!-- 待审核食谱 -->
    <div v-if="isNormalAdmin && activeTab === 'pending'" class="admin-content">
      <h2>待审核食谱</h2>
      <div v-if="pendingRecipes.length === 0" class="empty">
        暂无待审核的食谱
      </div>
      <div v-else class="recipe-grid">
        <div v-for="recipe in pendingRecipes" :key="recipe.id" class="recipe-card">
          <div class="recipe-image" @click="openRecipeDetail(recipe.id)">
            <span class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
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
            <span class="recipe-emoji">{{ getRecipeEmoji(recipe.name) }}</span>
          </div>
          <div class="recipe-info">
            <h3>{{ recipe.name }}</h3>
            <p class="meta">菜系: {{ recipe.cuisine }}</p>
            <span class="status" :class="{ public: recipe.is_public }">
              {{ recipe.is_public ? '已公开' : '私密' }}
            </span>
            <div class="actions">
              <button class="btn-edit" @click="openRecipeCreate(recipe)">编辑</button>
              <button class="btn-toggle" @click="toggleRecipeVisibility(recipe.id, recipe.is_public)">
                {{ recipe.is_public ? '设为私密' : '设为公开' }}
              </button>
              <button class="btn-delete-small" @click="deleteRecipe(recipe.id)">删除</button>
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
          <button class="btn-confirm" @click="async () => { await saveRecipe(); closeRecipeForm(false) }">创建</button>
          <button class="btn-save-draft" @click="closeRecipeForm(true)">保存草稿</button>
          <button class="btn-cancel" @click="closeRecipeForm(false)">取消</button>
        </div>
      </div>
    </div>

    <!-- 0级管理员提示 -->
    <div v-if="isSuperAdmin" class="admin-tip">
      <p>超级管理员权限：仅可管理管理员账号</p>
      <p>食谱、食材、用户管理请使用1级管理员账号</p>
    </div>
  </div>
</template>

<style scoped>
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
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #f9f9f9;
  border-radius: 8px;
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
</style>