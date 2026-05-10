<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores'
import axios from 'axios'


const router = useRouter()
const auth = useAuthStore()

const isLogin = ref(true)
const account = ref('')
const password = ref('')
const confirmed = ref(false)
const showConfirm = ref(false)
const nickname = ref('')
const contact = ref('')
const agreedToTerms = ref(false)
const showTermsModal = ref(false)
const error = ref('')
const loading = ref(false)
const generatedAccount = ref('')
const showAccountModal = ref(false)

// 找回密码
const showForgotModal = ref(false)
const forgotStep = ref(0)
const forgotAccount = ref('')
const forgotEmailKey = ref('')
const forgotMaskedEmail = ref('')
const forgotCode = ref('')
const forgotNewPassword = ref('')
const forgotConfirmPassword = ref('')
const forgotResetToken = ref('')
const forgotCooldown = ref(0)
const forgotError = ref('')
const forgotLoading = ref(false)
let forgotCooldownTimer: ReturnType<typeof setInterval> | null = null

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    if (isLogin.value) {
      const result = await auth.login(account.value, password.value)
      
      if (result.must_reset_password) {
        router.push('/profile')
      } else if (result.is_admin) {
        // const sureAdmin = await axios.get('/api/admin/is_admin')
        // if(!sureAdmin.data.is_admin){
        //   error.value = '身份异常，无法登录'
        //   loading.value = false
        //   return
        // }
        router.push('/admin')
      } else {
        router.push('/')
      }
    } else {
      // 注册时，如果还没显示确认区域，则显示
      if (!showConfirm.value) {
        showConfirm.value = true
        loading.value = false
        return
      }

      // 确认密码
      if (!confirmed.value) {
        error.value = '请确认密码正确'
        loading.value = false
        return
      }

      // 检查是否同意用户须知
      if (!agreedToTerms.value) {
        error.value = '请阅读并同意用户须知'
        loading.value = false
        return
      }

      const result = await auth.register({
        nickname: nickname.value,
        password: password.value,
        contact: contact.value || undefined
      })
      // 注册成功，显示生成的账号
      generatedAccount.value = result.account
      showAccountModal.value = true
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  } finally {
    loading.value = false
  }
}

function closeModal() {
  showAccountModal.value = false
  // 自动切换到登录
  isLogin.value = true
  account.value = generatedAccount.value
  generatedAccount.value = ''
  // 重置注册表单
  nickname.value = ''
  password.value = ''
  confirmed.value = false
  showConfirm.value = false
}

// 切换到注册时重置表单
function switchToRegister() {
  isLogin.value = false
  nickname.value = ''
  password.value = ''
  confirmed.value = false
  showConfirm.value = false
  error.value = ''
}

// 切换到登录时重置表单
function switchToLogin() {
  isLogin.value = true
  account.value = ''
  password.value = ''
  error.value = ''
}

// ===== 找回密码 =====
async function handleGetEmailInfo() {
  forgotError.value = ''
  forgotLoading.value = true
  try {
    const res = await axios.get(`/api/auth/forgot-password/${forgotAccount.value}`)
    forgotEmailKey.value = res.data.email_key
    forgotMaskedEmail.value = res.data.masked_email
    forgotStep.value = 1
  } catch (e: any) {
    forgotError.value = e.response?.data?.detail || '获取验证信息失败'
  } finally {
    forgotLoading.value = false
  }
}

async function handleConfirmEmail() {
  forgotError.value = ''
  forgotLoading.value = true
  try {
    await axios.post('/api/auth/forgot-password/confirm-email', {
      account: forgotAccount.value
    })
    forgotStep.value = 2
    handleSendCode()
  } catch (e: any) {
    forgotError.value = e.response?.data?.detail || '确认邮箱失败'
    forgotLoading.value = false
  }
}

async function handleSendCode() {
  forgotError.value = ''
  forgotLoading.value = true
  try {
    await axios.post('/api/auth/forgot-password/send-code', {
      account: forgotAccount.value
    })
    startForgotCooldown()
  } catch (e: any) {
    forgotError.value = e.response?.data?.detail || '发送验证码失败'
  } finally {
    forgotLoading.value = false
  }
}

async function handleVerifyCode() {
  forgotError.value = ''
  forgotLoading.value = true
  try {
    const res = await axios.post('/api/auth/forgot-password/verify-code', {
      account: forgotAccount.value,
      code: forgotCode.value
    })
    forgotResetToken.value = res.data.reset_token
    forgotStep.value = 3
  } catch (e: any) {
    forgotError.value = e.response?.data?.detail || '验证码错误'
  } finally {
    forgotLoading.value = false
  }
}

async function handleResetPassword() {
  forgotError.value = ''
  if (forgotNewPassword.value.length < 6) {
    forgotError.value = '密码长度至少6位'
    return
  }
  if (forgotNewPassword.value !== forgotConfirmPassword.value) {
    forgotError.value = '两次密码输入不一致'
    return
  }
  forgotLoading.value = true
  try {
    await axios.post('/api/auth/forgot-password/reset', {
      account: forgotAccount.value,
      new_password: forgotNewPassword.value,
      reset_token: forgotResetToken.value
    })
    forgotStep.value = 4
  } catch (e: any) {
    forgotError.value = e.response?.data?.detail || '密码重置失败'
  } finally {
    forgotLoading.value = false
  }
}

function startForgotCooldown() {
  forgotCooldown.value = 60
  if (forgotCooldownTimer) clearInterval(forgotCooldownTimer)
  forgotCooldownTimer = setInterval(() => {
    forgotCooldown.value--
    if (forgotCooldown.value <= 0) {
      if (forgotCooldownTimer) {
        clearInterval(forgotCooldownTimer)
        forgotCooldownTimer = null
      }
    }
  }, 1000)
}

function openForgotModal() {
  showForgotModal.value = true
  forgotStep.value = 0
  forgotAccount.value = account.value
  forgotEmailKey.value = ''
  forgotMaskedEmail.value = ''
  forgotCode.value = ''
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
  forgotResetToken.value = ''
  forgotCooldown.value = 0
  forgotError.value = ''
  forgotLoading.value = false
  if (forgotCooldownTimer) {
    clearInterval(forgotCooldownTimer)
    forgotCooldownTimer = null
  }
}

function goBackForgotStep() {
  forgotError.value = ''
  if (forgotStep.value === 1) {
    forgotStep.value = 0
  } else if (forgotStep.value === 2) {
    forgotStep.value = 1
  } else if (forgotStep.value === 3) {
    forgotStep.value = 2
  }
}

function closeForgotModal() {
  showForgotModal.value = false
  forgotStep.value = 0
  forgotAccount.value = ''
  forgotEmailKey.value = ''
  forgotMaskedEmail.value = ''
  forgotCode.value = ''
  forgotNewPassword.value = ''
  forgotConfirmPassword.value = ''
  forgotResetToken.value = ''
  forgotCooldown.value = 0
  forgotError.value = ''
  if (forgotCooldownTimer) {
    clearInterval(forgotCooldownTimer)
    forgotCooldownTimer = null
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-container">
      <!-- 左侧介绍 -->
      <div class="login-side">
        <div class="side-content">
          <span class="side-emoji">🍽️</span>
          <h2 class="side-title">
            {{ isLogin ? '事已至此，先吃饭吧' : '努力加餐饭' }}
          </h2>
          <p class="side-desc">
            {{ isLogin ? '登录账号，发现更多美味食谱' : '创建账号，开启您的美食之旅' }}
          </p>
          <div class="side-decoration">
            <div class="decoration-item">🥗</div>
            <div class="decoration-item">🍲</div>
            <div class="decoration-item">🍜</div>
          </div>
        </div>
      </div>

      <!-- 右侧表单 -->
      <div class="login-form-side">
        <div class="form-card">
          <h1>{{ isLogin ? '欢迎回来' : '创建账号' }}</h1>
          <p class="form-desc">{{ isLogin ? '登录您的EATING账号' : '填写以下信息完成注册' }}</p>

          <form @submit.prevent="handleSubmit" class="form">
            <!-- 登录：账号 -->
            <div class="form-group" v-if="isLogin">
              <label>账号</label>
              <input
                v-model="account"
                type="text"
                placeholder="请输入账号"
                required
              />
            </div>

            <!-- 注册：昵称 -->
            <div class="form-group" v-if="!isLogin">
              <label>昵称</label>
              <input
                v-model="nickname"
                type="text"
                placeholder="请输入昵称"
                required
              />
            </div>

            <!-- 密码 -->
            <div class="form-group">
              <label>密码</label>
              <input
                v-model="password"
                type="password"
                :placeholder="isLogin ? '请输入密码' : '请设置登录密码'"
                required
              />
              <a v-if="isLogin" class="forgot-link" @click="openForgotModal">找回密码？</a>
            </div>

            <!-- 注册：确认密码（按钮触发后显示） -->
            <div class="form-group confirm-group" v-if="!isLogin && showConfirm">
              <div class="confirm-wrapper">
                <div class="confirm-info">
                  <span class="confirm-label">确认密码：</span>
                  <span class="confirm-password">{{ password }}</span>
                </div>
                <label class="confirm-checkbox">
                  <input type="checkbox" v-model="confirmed" />
                  <span class="checkbox-label">确认密码正确</span>
                </label>
              </div>
            </div>

            <!-- 注册：联系方式 -->
            <div class="form-group" v-if="!isLogin">
              <label>联系方式（可选）</label>
              <input
                v-model="contact"
                type="text"
                placeholder="邮箱或手机号"
              />
            </div>

            <!-- 注册：用户须知 -->
            <div class="form-group" v-if="!isLogin">
              <label class="terms-checkbox">
                <input type="checkbox" v-model="agreedToTerms" />
                <span class="checkbox-text">
                  我已阅读并同意
                  <a href="#" @click.prevent="showTermsModal = true">《用户须知》</a>
                </span>
              </label>
            </div>

            <div v-if="error" class="error-message">{{ error }}</div>

            <button type="submit" class="submit-btn" :disabled="loading">
              {{ loading ? '处理中...' : (isLogin ? '登录' : (showConfirm ? '确认注册' : '下一步')) }}
            </button>
          </form>

          <div class="switch-mode">
            <span>{{ isLogin ? '还没有账号？' : '已有账号？' }}</span>
            <a @click="isLogin ? switchToRegister() : switchToLogin()" class="switch-link">
              {{ isLogin ? '立即注册' : '立即登录' }}
            </a>
          </div>
        </div>
      </div>
    </div>

    <!-- 账号显示弹窗 -->
    <div v-if="showAccountModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal">
        <div class="modal-icon">🎉</div>
        <h3>注册成功！</h3>
        <p class="modal-desc">您的账号已生成，请牢记：</p>
        <div class="account-display">{{ generatedAccount }}</div>
        <p class="modal-tip">登录后可查看详情</p>
        <button class="modal-btn" @click="closeModal">知道了，去登录</button>
      </div>
    </div>

    <!-- 用户须知弹窗 -->
    <div v-if="showTermsModal" class="modal-overlay" @click.self="showTermsModal = false">
      <div class="modal" style="max-width: 500px;">
        <h3>用户须知</h3>
        <div class="terms-content">
          <p>本项目中的过敏列表仅起到提醒作用，<strong>不可作为医学判断标准</strong>，仅表达部分观点，列举部分过敏源，实际请务必结合自身情况，仔细排查过敏源。</p>
          <p>若您出现了过敏反应，请及时就医，我们将诚信为你感到担忧，祝您早日康复，但本项目声明不对此负责。</p>
        </div>
        <button class="modal-btn" @click="showTermsModal = false">我已阅读</button>
      </div>
    </div>

    <!-- 找回密码弹窗 -->
    <div v-if="showForgotModal" class="modal-overlay">
      <div class="modal forgot-modal">
        <button class="modal-close" @click="closeForgotModal">&times;</button>

        <!-- Step 0: 输入账号 -->
        <template v-if="forgotStep === 0">
          <div class="modal-icon">🔑</div>
          <h3>找回密码</h3>
          <p class="modal-desc">输入您的账号，我们将验证您的身份</p>
          <div class="forgot-form">
            <div class="form-group">
              <label>账号</label>
              <input
                v-model="forgotAccount"
                type="text"
                placeholder="请输入账号"
                required
              />
            </div>
            <div v-if="forgotError" class="error-message">{{ forgotError }}</div>
            <button class="forgot-btn" :disabled="forgotLoading || !forgotAccount" @click="handleGetEmailInfo">
              {{ forgotLoading ? '验证中...' : '获取验证信息' }}
            </button>
          </div>
        </template>

        <!-- Step 1: 确认邮箱 -->
        <template v-if="forgotStep === 1">
          <div class="modal-icon">📧</div>
          <h3>确认邮箱</h3>
          <p class="modal-desc">您的邮箱前四位为：</p>
          <div class="email-key-display">{{ forgotEmailKey }}</div>
          <p class="modal-desc" style="margin-top: 0.5rem;">
            脱敏邮箱：<span class="masked-email">{{ forgotMaskedEmail }}</span>
          </p>
          <p class="modal-tip">确认这是您的邮箱吗？</p>
          <div v-if="forgotError" class="error-message">{{ forgotError }}</div>
          <div class="forgot-actions">
            <button class="forgot-btn-secondary" @click="goBackForgotStep">返回</button>
            <button class="forgot-btn" :disabled="forgotLoading" @click="handleConfirmEmail">
              {{ forgotLoading ? '确认中...' : '确认是我的邮箱' }}
            </button>
          </div>
        </template>

        <!-- Step 2: 验证码 -->
        <template v-if="forgotStep === 2">
          <div class="modal-icon">✉️</div>
          <h3>验证码已发送</h3>
          <p class="modal-desc">验证码已发送至您的邮箱，请在1分钟内查收</p>
          <div class="forgot-form">
            <div class="form-group">
              <label>验证码</label>
              <input
                v-model="forgotCode"
                type="text"
                maxlength="4"
                placeholder="请输入4位验证码"
              />
            </div>
            <div class="send-code-row">
              <button
                class="forgot-btn-secondary send-code-btn"
                :disabled="forgotCooldown > 0 || forgotLoading"
                @click="handleSendCode"
              >
                {{ forgotCooldown > 0 ? `重新发送(${forgotCooldown}s)` : '发送验证码' }}
              </button>
            </div>
            <div v-if="forgotError" class="error-message">{{ forgotError }}</div>
            <button class="forgot-btn" :disabled="forgotLoading || forgotCode.length !== 4" @click="handleVerifyCode">
              {{ forgotLoading ? '验证中...' : '确认验证码' }}
            </button>
          </div>
          <button class="forgot-link-btn" @click="goBackForgotStep">返回上一步</button>
        </template>

        <!-- Step 3: 重置密码 -->
        <template v-if="forgotStep === 3">
          <div class="modal-icon">🔒</div>
          <h3>重置密码</h3>
          <p class="modal-desc">请输入您的新密码</p>
          <div class="forgot-form">
            <div class="form-group">
              <label>新密码</label>
              <input
                v-model="forgotNewPassword"
                type="password"
                placeholder="至少6位密码"
              />
            </div>
            <div class="form-group">
              <label>确认密码</label>
              <input
                v-model="forgotConfirmPassword"
                type="password"
                placeholder="再次输入新密码"
              />
            </div>
            <div v-if="forgotError" class="error-message">{{ forgotError }}</div>
            <button class="forgot-btn" :disabled="forgotLoading || !forgotNewPassword || !forgotConfirmPassword" @click="handleResetPassword">
              {{ forgotLoading ? '重置中...' : '重置密码' }}
            </button>
          </div>
        </template>

        <!-- Step 4: 成功 -->
        <template v-if="forgotStep === 4">
          <div class="modal-icon">✅</div>
          <h3>密码已重置</h3>
          <p class="modal-desc">您的密码已成功修改，请使用新密码登录</p>
          <button class="forgot-btn" @click="closeForgotModal">完成</button>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: calc(100vh - 200px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
}

.login-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  max-width: 900px;
  width: 100%;
  background: white;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(76, 175, 80, 0.15);
}

/* 左侧 */
.login-side {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  padding: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.side-content {
  text-align: center;
  color: white;
}

.side-emoji {
  font-size: 4rem;
  display: block;
  margin-bottom: 1.5rem;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.side-title {
  font-size: 1.8rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  line-height: 1.3;
}

.side-desc {
  opacity: 0.9;
  font-size: 0.95rem;
}

.side-decoration {
  margin-top: 2rem;
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.decoration-item {
  font-size: 2rem;
  opacity: 0.7;
}

/* 右侧 */
.login-form-side {
  padding: 3rem;
}

.form-card {
  max-width: 360px;
  margin: 0 auto;
}

.form-card h1 {
  color: #2e7d32;
  font-size: 1.6rem;
  margin-bottom: 0.5rem;
}

.form-desc {
  color: #78909c;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
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

/* 确认密码区域 */
.confirm-group {
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.confirm-wrapper {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.confirm-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.confirm-label {
  font-size: 0.8rem;
  color: #78909c;
}

.confirm-password {
  font-size: 0.85rem;
  color: #43a047;
  font-weight: 500;
}

.confirm-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  padding: 0.4rem 0;
}

.confirm-checkbox input {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-label {
  font-size: 0.85rem;
  color: #37474f;
}

.error-message {
  color: #d32f2f;
  font-size: 0.85rem;
  text-align: center;
  padding: 0.5rem;
  background: #ffebee;
  border-radius: 8px;
}

.terms-checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.terms-checkbox input {
  width: auto;
}

.checkbox-text {
  font-size: 0.85rem;
  color: #666;
}

.checkbox-text a {
  color: #1976d2;
  text-decoration: none;
}

.terms-content {
  max-height: 300px;
  overflow-y: auto;
  padding: 1rem;
  background: #f5f5f5;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.terms-content p {
  font-size: 0.9rem;
  color: #666;
  line-height: 1.6;
  margin-bottom: 1rem;
}

.terms-content strong {
  color: #d32f2f;
}

.submit-btn {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.9rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 0.5rem;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.switch-mode {
  text-align: center;
  margin-top: 1.5rem;
  color: #78909c;
  font-size: 0.9rem;
}

.switch-link {
  color: #4caf50;
  font-weight: 600;
  cursor: pointer;
  margin-left: 0.5rem;
}

.switch-link:hover {
  text-decoration: underline;
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
  padding: 2rem;
  border-radius: 20px;
  text-align: center;
  max-width: 360px;
  animation: modalIn 0.3s ease;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.modal h3 {
  color: #2e7d32;
  font-size: 1.4rem;
  margin-bottom: 0.5rem;
}

.modal-desc {
  color: #78909c;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.account-display {
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 1.8rem;
  font-weight: 700;
  padding: 1rem;
  border-radius: 12px;
  letter-spacing: 4px;
  margin-bottom: 0.5rem;
}

.modal-tip {
  color: #78909c;
  font-size: 0.8rem;
  margin-bottom: 1.5rem;
}

.modal-btn {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.8rem 2rem;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.modal-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

/* 找回密码链接 */
.forgot-link {
  display: block;
  text-align: right;
  font-size: 0.8rem;
  color: #1976d2;
  cursor: pointer;
  margin-top: 0.3rem;
  text-decoration: none;
}

.forgot-link:hover {
  text-decoration: underline;
}

/* 找回密码弹窗 */
.forgot-modal {
  max-width: 400px;
  position: relative;
}

.modal-close {
  position: absolute;
  top: 0.5rem;
  right: 1rem;
  font-size: 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  padding: 0.25rem 0.5rem;
  line-height: 1;
}

.modal-close:hover {
  color: #333;
}

.forgot-form {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  margin-top: 1rem;
}

.forgot-btn {
  background: linear-gradient(135deg, #43a047, #2e7d32);
  color: white;
  border: none;
  padding: 0.8rem;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
}

.forgot-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
}

.forgot-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.forgot-btn-secondary {
  background: white;
  color: #43a047;
  border: 2px solid #43a047;
  padding: 0.7rem 1.2rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.forgot-btn-secondary:hover:not(:disabled) {
  background: #e8f5e9;
}

.forgot-btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.forgot-link-btn {
  background: none;
  border: none;
  color: #1976d2;
  font-size: 0.85rem;
  cursor: pointer;
  margin-top: 1rem;
  text-decoration: underline;
  display: block;
  width: 100%;
  text-align: center;
}

.forgot-actions {
  display: flex;
  gap: 0.8rem;
  margin-top: 1rem;
}

.forgot-actions .forgot-btn,
.forgot-actions .forgot-btn-secondary {
  flex: 1;
}

.email-key-display {
  background: #e8f5e9;
  color: #2e7d32;
  font-size: 2rem;
  font-weight: 700;
  padding: 0.8rem 1.5rem;
  border-radius: 12px;
  letter-spacing: 6px;
  display: inline-block;
  margin: 0.5rem 0;
}

.masked-email {
  color: #43a047;
  font-weight: 600;
}

.send-code-row {
  display: flex;
  justify-content: center;
}

.send-code-btn {
  width: 100%;
}

@media (max-width: 768px) {
  .login-container {
    grid-template-columns: 1fr;
  }

  .login-side {
    padding: 2rem;
  }

  .side-title {
    font-size: 1.4rem;
  }

  .login-form-side {
    padding: 2rem;
  }
}
</style>
