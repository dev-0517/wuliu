<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import bgUrl from '../assets/login-bg.jpg'

const router = useRouter()
const mode = ref('login') // login | register
const username = ref('')
const password = ref('')
const confirm = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!username.value.trim() || !password.value) {
    error.value = '请输入账户和密码'
    return
  }
  if (mode.value === 'register' && password.value !== confirm.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  loading.value = true
  try {
    const path = mode.value === 'login' ? '/auth/login' : '/auth/register'
    const data = await api.post(path, { username: username.value.trim(), password: password.value })
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
      <input id="acc" v-model="username" class="login-input" placeholder="输入您的账户" autocomplete="username" />
      <input id="pwd" v-model="password" class="login-input" type="password" placeholder="输入您的密码" autocomplete="current-password" />
      <input v-if="mode === 'register'" v-model="confirm" class="login-input" type="password" placeholder="再次输入密码" autocomplete="new-password" />
      <p v-if="error" class="login-err">{{ error }}</p>
      <button class="login-btn" :disabled="loading">
        {{ loading ? '提交中…' : mode === 'login' ? '登 录' : '注 册' }}
      </button>
      <p class="login-switch">
        <span>{{ mode === 'login' ? '还没有账号？' : '已有账号？' }}</span>
        <a @click.prevent="mode = mode === 'login' ? 'register' : 'login'; error = ''">
          {{ mode === 'login' ? '立即注册' : '去登录' }}
        </a>
      </p>
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
  padding: 30px 0 6vh;
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

.login-switch {
  margin: 0;
  font-size: 13px;
  color: #fff;
  text-shadow: 0 1px 6px rgba(0, 0, 0, .4);
}

.login-switch a {
  color: #fff;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
  margin-left: 4px;
}
</style>
