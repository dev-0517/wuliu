<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import bgUrl from '../assets/login-bg.jpg'

const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const data = await api.post('/auth/login', { username: username.value, password: password.value })
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    router.push('/')
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page" :style="{ backgroundImage: `url(${bgUrl})` }">
    <h1 class="login-title">智慧物流全球通</h1>

    <form class="login-form" @submit.prevent="submit">
      <input v-model="username" class="login-input" placeholder="输入您的账户" autocomplete="username" />
      <input v-model="password" class="login-input" type="password" placeholder="输入您的密码" autocomplete="current-password" />
      <p v-if="error" class="login-err">{{ error }}</p>
      <button class="login-btn" :disabled="loading">
        {{ loading ? '登录中…' : '登录' }}
      </button>
    </form>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  background-size: cover;
  background-position: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.login-title {
  margin: 9vh 0 0;
  font-size: 40px;
  font-weight: 700;
  letter-spacing: 10px;
  color: #fff;
  text-shadow: 0 2px 14px rgba(0, 0, 0, .45);
}

.login-form {
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  width: min(340px, 86vw);
  padding: 30px 0 8vh;
}

.login-input {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 22px;
  background: #fff;
  text-align: center;
  font-size: 14px;
  color: #333;
  box-shadow: 0 2px 10px rgba(0, 0, 0, .18);
}

.login-input::placeholder { color: #9ca3af; }
.login-input:focus { outline: 2px solid rgba(37, 99, 235, .55); }

.login-btn {
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 22px;
  background: #2563eb;
  color: #fff;
  font-size: 15px;
  letter-spacing: 6px;
  cursor: pointer;
  box-shadow: 0 2px 10px rgba(0, 0, 0, .18);
}

.login-btn:hover { background: #1d4ed8; }
.login-btn:disabled { opacity: .6; cursor: not-allowed; }

.login-err {
  margin: 0;
  color: #fff;
  font-size: 13px;
  background: rgba(220, 38, 38, .85);
  border-radius: 14px;
  padding: 6px 16px;
}
</style>
