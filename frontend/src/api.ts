import axios from 'axios'

const apiBase = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

export const api = axios.create({
  baseURL: apiBase,
  timeout: 10000
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export type LoginResponse = {
  access_token: string
  refresh_token: string
  token_type: string
}

export async function login(username: string, password: string) {
  const res = await api.post<LoginResponse>('/api/auth/login', { username, password })
  return res.data
}

export async function getMe() {
  const res = await api.get('/api/auth/me')
  return res.data as { id: number; username: string; role: string }
}
