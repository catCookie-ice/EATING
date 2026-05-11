import { createApp } from 'vue'
import { createPinia } from 'pinia'
import axios from 'axios'
import router from './router'
import './style.css'
import App from './App.vue'

// 全局 axios 配置
axios.defaults.timeout = 15000  // 15s 超时，避免请求卡死

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
