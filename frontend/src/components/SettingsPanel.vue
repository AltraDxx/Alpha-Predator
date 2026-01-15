<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'

const emit = defineEmits<{
  (e: 'configured'): void
}>()

const isOpen = ref(false)
const isLoading = ref(false)
const selectedProvider = ref('qwen')
const apiKey = ref('')
const message = ref<{ type: 'success' | 'error', text: string } | null>(null)

const providers = ref<Array<{id: string, name: string, configured: boolean}>>([])
const currentProvider = ref('')

// Tushare 配置
const tushareApiKey = ref('')
const tushareConfigured = ref(false)

async function loadProviders() {
  try {
    const response = await fetch('/api/config/providers')
    const data = await response.json()
    providers.value = data.providers
    currentProvider.value = data.current
  } catch (e) {
    console.error('获取配置失败:', e)
  }
  // 检查 Tushare 配置
  const savedTushare = localStorage.getItem('tushare_api_key')
  tushareConfigured.value = !!savedTushare
}

// 判断当前选择的提供商是否已配置
const isSelectedProviderConfigured = computed(() => {
  const provider = providers.value.find(p => p.id === selectedProvider.value)
  return provider?.configured ?? false
})

// 动态 placeholder
const apiKeyPlaceholder = computed(() => {
  if (isSelectedProviderConfigured.value) {
    return '••••••••••••（已配置，输入新 Key 可覆盖）'
  }
  return '输入你的 API Key'
})

// 切换提供商时清空输入
watch(selectedProvider, () => {
  apiKey.value = ''
  message.value = null
})

async function saveApiKey() {
  // 如果已配置且用户没有输入新 Key，提示用户
  if (!apiKey.value.trim()) {
    if (isSelectedProviderConfigured.value) {
      message.value = { type: 'error', text: '请输入新的 API Key 以覆盖现有配置' }
    } else {
      message.value = { type: 'error', text: '请输入 API Key' }
    }
    return
  }
  
  isLoading.value = true
  message.value = null
  
  try {
    // 配置 API Key
    const configResponse = await fetch('/api/config/apikey', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        provider: selectedProvider.value,
        api_key: apiKey.value,
      })
    })
    
    const configData = await configResponse.json()
    
    if (!configResponse.ok) {
      throw new Error(configData.detail || '配置失败')
    }
    
    // 切换到该提供商
    await fetch('/api/llm/switch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider: selectedProvider.value })
    })
    
    message.value = { type: 'success', text: `${configData.message}，已切换为默认提供商` }
    apiKey.value = ''
    
    // 重新加载配置
    await loadProviders()
    
    // 3秒后关闭弹窗并清除消息
    setTimeout(() => {
      message.value = null
      emit('configured')
      isOpen.value = false
    }, 2000)
    
  } catch (e: any) {
    message.value = { type: 'error', text: e.message || '配置失败' }
    // 错误消息5秒后自动消失
    setTimeout(() => {
      message.value = null
    }, 5000)
  } finally {
    isLoading.value = false
  }
}

// Tushare 保存
function saveTushareKey() {
  if (tushareApiKey.value.trim()) {
    localStorage.setItem('tushare_api_key', tushareApiKey.value.trim())
    tushareConfigured.value = true
    tushareApiKey.value = ''
    message.value = { type: 'success', text: 'Tushare Token 已保存' }
    setTimeout(() => { message.value = null }, 3000)
  }
}

// Tushare 清除
function clearTushareKey() {
  localStorage.removeItem('tushare_api_key')
  tushareConfigured.value = false
  message.value = { type: 'success', text: '已切换回 AkShare' }
  setTimeout(() => { message.value = null }, 3000)
}

onMounted(() => {
  loadProviders()
})
</script>

<template>
  <div class="settings-widget">
    <button class="settings-btn" @click="isOpen = true; loadProviders()" title="API 设置">
      ⚙️
    </button>
    
    <!-- 设置弹窗 -->
    <Transition name="modal">
      <div v-if="isOpen" class="modal-overlay" @click.self="isOpen = false">
        <div class="modal">
          <div class="modal-header">
            <h3>🔧 API 配置</h3>
            <button class="close-btn" @click="isOpen = false">✕</button>
          </div>
          
          <div class="modal-body">
            <p class="modal-desc">配置 LLM API Key 以启用分析功能</p>
            
            <!-- 当前状态 -->
            <div class="providers-status">
              <h4>服务状态</h4>
              <div class="provider-list">
                <div 
                  v-for="p in providers" 
                  :key="p.id"
                  class="provider-item"
                  :class="{ active: p.id === currentProvider }"
                >
                  <span class="provider-name">{{ p.name }}</span>
                  <span v-if="p.configured" class="status-dot configured">✓</span>
                  <span v-else class="status-dot unconfigured">✗</span>
                </div>
              </div>
            </div>
            
            <!-- 配置表单 -->
            <div class="config-form">
              <h4>配置新的 API Key</h4>
              
              <div class="form-group">
                <label>选择服务商</label>
                <select v-model="selectedProvider" class="select-input">
                  <option value="qwen">阿里通义千问 (推荐)</option>
                  <option value="google">Google Gemini</option>
                  <option value="openai">OpenAI ChatGPT</option>
                </select>
              </div>
              
              <div class="form-group">
                <label>API Key</label>
                <input 
                  v-model="apiKey"
                  type="password"
                  class="input"
                  :placeholder="apiKeyPlaceholder"
                />
              </div>
              
              <div v-if="message" class="message" :class="message.type">
                {{ message.text }}
              </div>
              
              <button 
                class="btn btn-primary save-btn"
                @click="saveApiKey"
                :disabled="isLoading"
              >
                {{ isLoading ? '配置中...' : '保存并启用' }}
              </button>
            </div>
            
            <div class="help-text">
              <p>💡 获取 API Key：</p>
              <ul>
                <li><a href="https://dashscope.console.aliyun.com/" target="_blank">通义千问 (DashScope)</a></li>
                <li><a href="https://aistudio.google.com/app/apikey" target="_blank">Google Gemini</a></li>
                <li><a href="https://platform.openai.com/api-keys" target="_blank">OpenAI</a></li>
              </ul>
            </div>

            <!-- Tushare 配置 -->
            <div class="config-form tushare-section">
              <h4>📈 Tushare 数据源（可选）</h4>
              <p class="section-desc">配置后可获取更全面的基本面数据，未配置则使用 AkShare</p>
              <div class="form-group">
                <input 
                  v-model="tushareApiKey"
                  type="password"
                  class="input"
                  :placeholder="tushareConfigured ? '••••••••（已配置）' : '输入 Tushare Token'"
                />
              </div>
              <div class="btn-row">
                <button 
                  class="btn btn-secondary btn-sm"
                  @click="saveTushareKey"
                >
                  {{ tushareConfigured ? '更新' : '保存' }}
                </button>
                <button 
                  v-if="tushareConfigured"
                  class="btn btn-danger btn-sm"
                  @click="clearTushareKey"
                >
                  清除
                </button>
                <span v-if="tushareConfigured" class="status-hint">✅ 已配置，数据源为 Tushare</span>
                <span v-else class="status-hint">使用 AkShare 免费数据源</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.settings-widget {
  position: relative;
}

.settings-btn {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  cursor: pointer;
  font-size: 16px;
  transition: var(--transition);
}

.settings-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-color);
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 18px;
  padding: 4px 8px;
}

.close-btn:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: 24px;
}

.modal-desc {
  color: var(--text-secondary);
  margin-bottom: 20px;
}

.providers-status {
  margin-bottom: 24px;
}

.providers-status h4,
.config-form h4 {
  font-size: 13px;
  color: var(--text-muted);
  text-transform: uppercase;
  margin-bottom: 12px;
}

.provider-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  border: 1px solid transparent;
}

.provider-item.active {
  border-color: var(--primary-color);
  background: rgba(102, 126, 234, 0.1);
}

.provider-name {
  font-size: 14px;
}

.status-dot {
  font-size: 14px;
  font-weight: bold;
}

.status-dot.configured {
  color: var(--success);
}

.status-dot.unconfigured {
  color: var(--text-muted);
}

.config-form {
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.select-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 14px;
}

.select-input:focus {
  outline: none;
  border-color: var(--primary-color);
}

.message {
  padding: 12px;
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 14px;
}

.message.success {
  background: rgba(16, 185, 129, 0.15);
  color: var(--success);
}

.message.error {
  background: rgba(239, 68, 68, 0.15);
  color: var(--danger);
}

.save-btn {
  width: 100%;
}

.help-text {
  padding: 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--text-secondary);
}

.help-text p {
  margin-bottom: 8px;
}

.help-text ul {
  margin: 0;
  padding-left: 20px;
}

.help-text li {
  margin-bottom: 4px;
}

.help-text a {
  color: var(--primary-color);
  text-decoration: none;
}

.help-text a:hover {
  text-decoration: underline;
}

/* 动画 */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal,
.modal-leave-to .modal {
  transform: scale(0.95);
}

/* Tushare 区域 */
.tushare-section {
  border-top: 1px solid var(--border-color);
  padding-top: 20px;
  margin-top: 20px;
}

.section-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.btn-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-danger {
  background: #ef4444;
  color: white;
  border: none;
}

.btn-danger:hover {
  background: #dc2626;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 13px;
}

.status-hint {
  font-size: 12px;
  color: var(--text-muted);
}
</style>
