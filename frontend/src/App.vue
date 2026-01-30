<template>
  <el-container class="page">
    <el-header class="header">
      <div class="title">JXC Manage</div>
      <div class="sub">进销存系统</div>
    </el-header>
    <el-main class="main">
      <el-card class="card">
        <template #header>
          <div class="card-title">登录</div>
        </template>

        <el-form :model="form" label-width="80px">
          <el-form-item label="用户名">
            <el-input v-model="form.username" placeholder="admin" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.password" type="password" placeholder="admin123" show-password />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="onLogin">登录</el-button>
            <el-button @click="onLogout" v-if="user">退出</el-button>
          </el-form-item>
        </el-form>

        <el-alert v-if="error" type="error" :closable="false" :title="error" />
        <el-alert v-if="user" type="success" :closable="false" :title="`已登录：${user.username} (${user.role})`" />
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { login, getMe } from './api'

const form = ref({ username: 'admin', password: 'admin123' })
const loading = ref(false)
const error = ref('')
const user = ref<{ id: number; username: string; role: string } | null>(null)

const loadMe = async () => {
  try {
    user.value = await getMe()
  } catch {
    user.value = null
  }
}

const onLogin = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await login(form.value.username, form.value.password)
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    await loadMe()
    ElMessage.success('登录成功')
  } catch (err: any) {
    error.value = err?.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}

const onLogout = () => {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  user.value = null
  ElMessage.info('已退出')
}

onMounted(() => {
  if (localStorage.getItem('access_token')) {
    loadMe()
  }
})
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f6f7fb 0%, #eef1f6 100%);
}
.header {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 24px 32px;
}
.title {
  font-size: 22px;
  font-weight: 700;
}
.sub {
  color: #666;
  margin-top: 4px;
}
.main {
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 32px;
}
.card {
  width: 420px;
  max-width: 92vw;
}
.card-title {
  font-weight: 600;
}
</style>
