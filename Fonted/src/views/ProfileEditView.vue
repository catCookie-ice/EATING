<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const success = ref('')

const form = ref({
  nickname: '',
  gender: '私密' as string,
  age: null as number | null,
  taste: { sour: 0.2, sweet: 0.2, bitter: 0.2, spicy: 0.2, salty: 0.2 },
})

// 邮箱换绑
const hasEmail = ref(false)
const maskedEmail = ref('')
const verifiedToken = ref('')
const isVerified = ref(false)
const newContact = ref('')
const showVerifyModal = ref(false)
const verifyMethod = ref<'code' | 'password' | null>(null)
const verifyCode = ref('')
const verifyPassword = ref('')
const verifyCooldown = ref(0)
const verifyLoading = ref(false)
const verifyError = ref('')
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const tasteDimensions = [
  { key: 'sour', label: '酸' },
  { key: 'sweet', label: '甜' },
  { key: 'bitter', label: '苦' },
  { key: 'spicy', label: '辣' },
  { key: 'salty', label: '咸' },
]

const genderOptions = ['男', '女', '私密']

onMounted(async () => {
  await authStore.init()
  if (!authStore.isLoggedIn) {
    router.push('/login')
    return
  }
  loading.value = true
  try {
    const res = await axios.get('/api/users/me')
    form.value.nickname = res.data.nickname || ''
    form.value.gender = res.data.gender || '私密'
    form.value.age = res.data.age || null
    if (res.data.taste) {
      form.value.taste = { ...form.value.taste, ...res.data.taste }
    }
    // 通过 me_edit 接口获取邮箱信息（脱敏显示）
    try {
      const editRes = await axios.get('/api/users/me_edit')
      hasEmail.value = !!editRes.data.email
      maskedEmail.value = editRes.data.email || ''
    } catch {
      hasEmail.value = false
      maskedEmail.value = ''
    }
  } catch (e: any) {
    error.value = '加载用户信息失败'
  } finally {
    loading.value = false
  }
})

function updateTaste(key: string, value: string) {
  const numVal = parseFloat(value)
  if (isNaN(numVal)) return
  const taste = form.value.taste as any
  taste[key] = numVal
  const total = Object.keys(taste).reduce((sum: number, k: string) => sum + (Number(taste[k]) || 0), 0)
  if (total > 0 && Math.abs(total - 1) > 0.001) {
    for (const k of Object.keys(taste)) {
      taste[k] = Math.round(((taste[k] / total) + Number.EPSILON) * 100) / 100
    }
  }
}

async function handleSaveProfile() {
  error.value = ''
  success.value = ''
  saving.value = true
  try {
    const data: any = {
      nickname: form.value.nickname,
      gender: form.value.gender,
      taste: form.value.taste,
    }
    if (form.value.age !== null) {
      data.age = form.value.age
    }
    await axios.put('/api/users/me', data)
    success.value = '个人信息已更新'
    authStore.userInfo = null
    await authStore.init(true)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '保存失败'
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/profile')
}

// ===== 换绑邮箱 =====

function openVerifyModal() {
  showVerifyModal.value = true
  verifyMethod.value = null
  verifyCode.value = ''
  verifyPassword.value = ''
  verifyError.value = ''
  verifyCooldown.value = 0
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}

function closeVerifyModal() {
  showVerifyModal.value = false
  if (cooldownTimer) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}

function startCooldown() {
  verifyCooldown.value = 60
  if (cooldownTimer) clearInterval(cooldownTimer)
  cooldownTimer = setInterval(() => {
    verifyCooldown.value--
    if (verifyCooldown.value <= 0) {
      if (cooldownTimer) {
        clearInterval(cooldownTimer)
        cooldownTimer = null
      }
    }
  }, 1000)
}

async function handleSendCode() {
  verifyError.value = ''
  verifyLoading.value = true
  try {
    await axios.post('/api/auth/change-email/send-code', {})
    startCooldown()
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || '发送验证码失败'
  } finally {
    verifyLoading.value = false
  }
}

async function handleVerifyCode() {
  verifyError.value = ''
  verifyLoading.value = true
  try {
    const res = await axios.post('/api/auth/change-email/verify-code', {
      code: verifyCode.value
    })
    verifiedToken.value = res.data.verified_token
    isVerified.value = true
    closeVerifyModal()
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || '验证码错误'
  } finally {
    verifyLoading.value = false
  }
}

async function handleVerifyPassword() {
  verifyError.value = ''
  verifyLoading.value = true
  try {
    const res = await axios.post('/api/auth/change-email/verify-password', {
      password: verifyPassword.value
    })
    verifiedToken.value = res.data.verified_token
    isVerified.value = true
    closeVerifyModal()
  } catch (e: any) {
    verifyError.value = e.response?.data?.detail || '密码错误'
  } finally {
    verifyLoading.value = false
  }
}

async function handleUpdateEmail() {
  error.value = ''
  success.value = ''
  if (!newContact.value.trim()) {
    error.value = '请输入新的联系方式'
    return
  }
  saving.value = true
  try {
    await axios.post('/api/auth/change-email/update', {
      new_contact: newContact.value.trim(),
      verified_token: verifiedToken.value
    })
    success.value = '邮箱已更新'
    isVerified.value = false
    verifiedToken.value = ''
    newContact.value = ''
    hasEmail.value = true
  } catch (e: any) {
    error.value = e.response?.data?.detail || '邮箱更新失败'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="edit-page">
    <div class="edit-card">
      <div class="edit-header">
        <button class="btn-back" @click="goBack">← 返回</button>
        <h2>编辑个人资料</h2>
      </div>

      <div v-if="loading" class="loading">加载中...</div>

      <form v-else @submit.prevent="handleSaveProfile" class="edit-form">
        <!-- 昵称 -->
        <div class="form-group">
          <label>昵称</label>
          <input v-model="form.nickname" type="text" placeholder="请输入昵称" required />
        </div>

        <!-- 性别 -->
        <div class="form-group">
          <label>性别</label>
          <div class="gender-options">
            <button
              v-for="g in genderOptions"
              :key="g"
              type="button"
              :class="['gender-btn', { active: form.gender === g }]"
              @click="form.gender = g"
            >{{ g }}</button>
          </div>
        </div>

        <!-- 年龄 -->
        <div class="form-group">
          <label>年龄</label>
          <input v-model.number="form.age" type="number" min="1" max="150" placeholder="请输入年龄" />
        </div>

        <!-- 口味偏好 -->
        <div class="form-group">
          <label>口味偏好</label>
          <div class="taste-sliders">
            <div class="taste-row" v-for="dim in tasteDimensions" :key="dim.key">
              <span class="taste-label">{{ dim.label }}</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                :value="(form.taste as any)[dim.key]"
                @input="updateTaste(dim.key, ($event.target as HTMLInputElement).value)"
              />
              <span class="taste-value">{{ ((form.taste as any)[dim.key] * 100).toFixed(0) }}%</span>
            </div>
          </div>
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>
        <div v-if="success" class="success-message">{{ success }}</div>

        <div class="form-actions">
          <button type="submit" class="btn-save" :disabled="saving">
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
          <button type="button" class="btn-cancel" @click="goBack">取消</button>
        </div>
      </form>

      <!-- 邮箱换绑区域（与主表单独立） -->
      <div class="email-section">
        <h3>邮箱绑定</h3>
        <div class="email-status">
          <span class="status-dot" :class="{ bound: hasEmail }"></span>
          <span v-if="hasEmail">{{ maskedEmail }}</span>
          <span v-else>未绑定邮箱</span>
          <button class="btn-verify" @click="openVerifyModal">验证</button>
        </div>

        <!-- 验证通过后显示新邮箱输入 -->
        <div v-if="isVerified" class="new-email-form">
          <div class="form-group">
            <label>新邮箱</label>
            <input v-model="newContact" type="text" placeholder="请输入新的邮箱地址" />
          </div>
          <button class="btn-bind" :disabled="saving || !newContact.trim()" @click="handleUpdateEmail">
            {{ saving ? '处理中...' : '确认换绑' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 验证弹窗 -->
    <div v-if="showVerifyModal" class="modal-overlay">
      <div class="modal verify-modal">

        <!-- 选择验证方式 -->
        <template v-if="!verifyMethod">
          <h3>验证身份</h3>
          <p class="modal-desc">请选择验证方式</p>
          <div class="verify-options">
            <button class="verify-option" @click="verifyMethod = 'code'">
              <span class="verify-icon">📧</span>
              <span class="verify-text">原邮箱可用</span>
              <span class="verify-sub">通过邮箱验证码验证</span>
            </button>
            <button class="verify-option" @click="verifyMethod = 'password'">
              <span class="verify-icon">🔑</span>
              <span class="verify-text">原邮箱不可用</span>
              <span class="verify-sub">通过密码验证</span>
            </button>
          </div>
          <button class="btn-cancel verify-cancel" @click="closeVerifyModal">取消</button>
        </template>

        <!-- 邮箱验证码方式 -->
        <template v-if="verifyMethod === 'code'">
          <h3>邮箱验证</h3>
          <p class="modal-desc">验证码将发送至您当前绑定的邮箱</p>
          <button
            class="btn-send-code"
            :disabled="verifyCooldown > 0 || verifyLoading"
            @click="handleSendCode"
          >
            {{ verifyCooldown > 0 ? `重新发送(${verifyCooldown}s)` : '发送验证码' }}
          </button>
          <div class="form-group" style="margin-top: 1rem;">
            <label>验证码</label>
            <input v-model="verifyCode" type="text" maxlength="4" placeholder="输入4位验证码" />
          </div>
          <div v-if="verifyError" class="error-message">{{ verifyError }}</div>
          <div class="modal-actions">
            <button class="btn-confirm" :disabled="verifyLoading || verifyCode.length !== 4" @click="handleVerifyCode">
              {{ verifyLoading ? '验证中...' : '确认' }}
            </button>
            <button class="btn-cancel" @click="verifyMethod = null">返回</button>
          </div>
        </template>

        <!-- 密码方式 -->
        <template v-if="verifyMethod === 'password'">
          <h3>密码验证</h3>
          <p class="modal-desc">请输入您的当前密码</p>
          <div class="form-group">
            <label>密码</label>
            <input v-model="verifyPassword" type="password" placeholder="请输入当前密码" />
          </div>
          <div v-if="verifyError" class="error-message">{{ verifyError }}</div>
          <div class="modal-actions">
            <button class="btn-confirm" :disabled="verifyLoading || !verifyPassword" @click="handleVerifyPassword">
              {{ verifyLoading ? '验证中...' : '确认' }}
            </button>
            <button class="btn-cancel" @click="verifyMethod = null">返回</button>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.edit-page {
  max-width: 600px;
  margin: 0 auto;
  padding: 2rem 1rem;
}

.edit-card {
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 20px rgba(76, 175, 80, 0.1);
}

.edit-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.edit-header h2 {
  color: #2e7d32;
  font-size: 1.4rem;
  margin: 0;
}

.btn-back {
  background: none;
  border: none;
  color: #4caf50;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.3rem 0.5rem;
  border-radius: 6px;
  transition: background 0.2s;
}

.btn-back:hover {
  background: #e8f5e9;
}

.loading {
  text-align: center;
  color: #78909c;
  padding: 2rem;
}

.edit-form {
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.form-group label {
  color: #37474f;
  font-size: 0.9rem;
  font-weight: 500;
}

.form-group input {
  padding: 0.7rem 0.9rem;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.gender-options {
  display: flex;
  gap: 0.5rem;
}

.gender-btn {
  flex: 1;
  padding: 0.6rem;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  background: white;
  color: #666;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.gender-btn:hover {
  border-color: #81c784;
}

.gender-btn.active {
  border-color: #4caf50;
  background: #e8f5e9;
  color: #2e7d32;
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

.error-message {
  color: #d32f2f;
  font-size: 0.85rem;
  text-align: center;
  padding: 0.5rem;
  background: #ffebee;
  border-radius: 8px;
}

.success-message {
  color: #2e7d32;
  font-size: 0.85rem;
  text-align: center;
  padding: 0.5rem;
  background: #e8f5e9;
  border-radius: 8px;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 0.5rem;
}

.btn-save {
  flex: 1;
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-save:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-cancel {
  flex: 1;
  background: #e0e0e0;
  color: #666;
  border: none;
  padding: 0.8rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-cancel:hover {
  background: #d0d0d0;
}

/* 邮箱换绑区域 */
.email-section {
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e0e0e0;
}

.email-section h3 {
  color: #2e7d32;
  font-size: 1.1rem;
  margin: 0 0 1rem;
}

.email-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: #555;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #e0e0e0;
}

.status-dot.bound {
  background: #4caf50;
}

.btn-verify {
  margin-left: auto;
  background: #e8f5e9;
  color: #2e7d32;
  border: none;
  padding: 0.4rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-verify:hover {
  background: #c8e6c9;
}

.new-email-form {
  margin-top: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.btn-bind {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.7rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-bind:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.btn-bind:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 验证弹窗 */
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
  border-radius: 20px;
  padding: 2rem;
  width: 90%;
  max-width: 400px;
  animation: modalIn 0.3s ease;
}

@keyframes modalIn {
  from { opacity: 0; transform: scale(0.9); }
  to { opacity: 1; transform: scale(1); }
}

.modal h3 {
  color: #2e7d32;
  font-size: 1.3rem;
  margin-bottom: 0.5rem;
}

.modal-desc {
  color: #78909c;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.verify-options {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin: 1rem 0;
}

.verify-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.3rem;
  padding: 1.2rem;
  border: 2px solid #e0e0e0;
  border-radius: 12px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
}

.verify-option:hover {
  border-color: #4caf50;
  background: #f1f8e9;
}

.verify-icon {
  font-size: 1.8rem;
}

.verify-text {
  font-size: 1rem;
  font-weight: 600;
  color: #333;
}

.verify-sub {
  font-size: 0.8rem;
  color: #999;
}

.verify-cancel {
  margin-top: 0.5rem;
}

.btn-send-code {
  width: 100%;
  padding: 0.7rem;
  background: #e8f5e9;
  color: #2e7d32;
  border: 2px solid #4caf50;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-send-code:hover:not(:disabled) {
  background: #c8e6c9;
}

.btn-send-code:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-actions {
  display: flex;
  gap: 0.8rem;
  margin-top: 1rem;
}

.btn-confirm {
  flex: 1;
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.7rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
}

.btn-confirm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 600px) {
  .edit-page {
    padding: 1rem 0.5rem;
  }
  .edit-card {
    padding: 1.5rem;
  }
}
</style>
