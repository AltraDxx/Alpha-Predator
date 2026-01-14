<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import Dashboard from './components/Dashboard.vue'
import SettingsPanel from './components/SettingsPanel.vue'

const isLoading = ref(true)
const apiStatus = ref<'connecting' | 'connected' | 'error'>('connecting')
const currentLlmProvider = ref<string>('')
const currentTime = ref(new Date().toLocaleTimeString('zh-CN'))

// 时间更新定时器
let timeInterval: ReturnType<typeof setInterval> | null = null

function updateTime() {
  currentTime.value = new Date().toLocaleTimeString('zh-CN')
}

async function loadProviderInfo() {
  try {
    const response = await fetch('/api/config/providers')
    if (response.ok) {
      const data = await response.json()
      currentLlmProvider.value = data.current || ''
    }
  } catch {
    // 忽略错误，保持默认值
  }
}

async function checkHealth() {
  try {
    const response = await fetch('/health')
    if (response.ok) {
      apiStatus.value = 'connected'
      // 健康检查通过后加载提供商信息
      await loadProviderInfo()
    } else {
      apiStatus.value = 'error'
    }
  } catch {
    apiStatus.value = 'error'
  }
}

async function onConfigured() {
  // 配置完成后重新加载状态
  await checkHealth()
}

onMounted(async () => {
  await checkHealth()
  isLoading.value = false
  // 启动时间更新定时器
  timeInterval = setInterval(updateTime, 1000)
})

onUnmounted(() => {
  // 清理定时器
  if (timeInterval) {
    clearInterval(timeInterval)
  }
})
</script>

<template>
  <div class="app">
    <!-- 顶部导航栏 -->
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">⚡</span>
          <span class="logo-text">QuantumAlpha</span>
        </div>
        <span class="version-badge">v0.1.0</span>
      </div>
      
      <div class="header-center">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            type="text" 
            placeholder="搜索股票代码或快捷命令 (Ctrl+K)"
            class="search-input"
          />
        </div>
      </div>
      
      <div class="header-right">
        <div class="status-indicator" :class="apiStatus">
          <span class="status-dot"></span>
          <span class="status-text">
            {{ apiStatus === 'connected' ? 'API 已连接' : 
               apiStatus === 'connecting' ? '连接中...' : 'API 离线' }}
          </span>
        </div>
        <div class="time-display">
          {{ currentTime }}
        </div>
        <SettingsPanel @configured="onConfigured" />
      </div>
    </header>
    
    <!-- 主内容区 -->
    <main class="main">
      <Dashboard v-if="!isLoading" :api-status="apiStatus" :current-llm-provider="currentLlmProvider" />
      <div v-else class="loading-container">
        <div class="loading-spinner"></div>
        <p>正在加载系统...</p>
      </div>
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  background: var(--primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.version-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg-card);
  border-radius: 9999px;
  color: var(--text-muted);
}

.header-center {
  flex: 1;
  max-width: 500px;
  margin: 0 24px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius);
  transition: var(--transition);
}

.search-box:focus-within {
  border-color: var(--primary-color);
}

.search-icon {
  font-size: 14px;
  opacity: 0.6;
}

.search-input {
  flex: 1;
  background: none;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  outline: none;
}

.search-input::placeholder {
  color: var(--text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
}

.status-indicator.connected {
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}

.status-indicator.connecting {
  background: rgba(245, 158, 11, 0.15);
  color: var(--warning);
}

.status-indicator.error {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-indicator.connecting .status-dot {
  animation: pulse 1.5s infinite;
}

.time-display {
  font-size: 14px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.main {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 60vh;
  gap: 16px;
  color: var(--text-secondary);
}
</style>
