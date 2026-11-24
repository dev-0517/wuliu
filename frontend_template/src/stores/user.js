import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useUserStore = defineStore('user', () => {
  const profile = ref(null)
  async function loadProfile() { profile.value = await api.get('/profile') }
  async function authenticate(mode, form) {
    const data = await api.post(`/auth/${mode}`, form)
    sessionStorage.setItem('huanuo_token', data.token)
    profile.value = data.user
  }
  async function logout() {
    await api.post('/auth/logout')
    sessionStorage.removeItem('huanuo_token')
    profile.value = null
  }
  return { profile, loadProfile, authenticate, logout }
})
