<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AnalysisFlow from './AnalysisFlow.vue'
import PortfolioManager from './PortfolioManager.vue'
const props = defineProps<{
  apiStatus: 'connecting' | 'connected' | 'error'
  currentLlmProvider?: string
}>()

// LLM 提供商名称映射
const llmProviderName = computed(() => {
  const nameMap: Record<string, string> = {
    'google': 'Gemini',
    'openai': 'ChatGPT',
    'qwen': '通义千问',
    'custom': '自定义',
  }
  return nameMap[props.currentLlmProvider || ''] || props.currentLlmProvider || '未配置'
})

// 数据源名称
const dataSourceName = computed(() => {
  // 检查是否配置了 Tushare API Key
  const tushareKey = localStorage.getItem('tushare_api_key')
  return tushareKey ? 'Tushare' : 'AkShare'
})

// 风险偏好名称
const riskPreference = ref('balanced')
const riskPreferenceName = computed(() => {
  const nameMap: Record<string, string> = {
    'aggressive': '激进型',
    'balanced': '平衡型',
    'conservative': '保守型',
  }
  return nameMap[riskPreference.value] || '平衡型'
})

// 状态
const activeTab = ref<'alpha' | 'diagnose' | 'portfolio'>('alpha')
const isDiagnosing = ref(false)
const stockCode = ref('')

// 实时市场数据
interface MarketIndex {
  name: string
  code: string
  price: number
  change_pct: number
}
const marketIndices = ref<MarketIndex[]>([])
const isLoadingMarket = ref(false)

// 判断是否在交易时间内
function isMarketOpen(): boolean {
  const now = new Date()
  const day = now.getDay() // 0=周日, 6=周六
  
  // 周末不开盘
  if (day === 0 || day === 6) return false
  
  const hours = now.getHours()
  const minutes = now.getMinutes()
  const time = hours * 100 + minutes
  
  // 上午 9:30-11:30, 下午 13:00-15:00
  return (time >= 930 && time <= 1130) || (time >= 1300 && time <= 1500)
}

// 获取市场状态描述
const marketStatus = computed(() => {
  const now = new Date()
  const day = now.getDay()
  
  if (day === 0 || day === 6) return '休市'
  
  const hours = now.getHours()
  const minutes = now.getMinutes()
  const time = hours * 100 + minutes
  
  if (time < 930) return '未开盘'
  if (time <= 1130) return '交易中'
  if (time < 1300) return '午休'
  if (time <= 1500) return '交易中'
  return '已收盘'
})

// 获取实时行情
async function loadMarketData() {
  isLoadingMarket.value = true
  try {
    const response = await fetch('/api/market/realtime')
    const data = await response.json()
    if (data.success && data.data) {
      marketIndices.value = data.data
    }
  } catch (error) {
    console.error('获取实时行情失败:', error)
  } finally {
    isLoadingMarket.value = false
  }
}

// 页面加载时获取行情
onMounted(() => {
  // 首次加载
  loadMarketData()
  
  // 只在交易时间内每30秒刷新
  setInterval(() => {
    if (isMarketOpen()) {
      loadMarketData()
    }
  }, 30000)
  
  // 加载风险偏好
  const savedRisk = localStorage.getItem('riskPreference')
  if (savedRisk) {
    riskPreference.value = savedRisk
  }
})

// 错误提示
const errorMessage = ref<{
  type: 'error' | 'warning' | 'info'
  title: string
  message: string
  details?: string
} | null>(null)

// 分析结果
const diagnoseResult = ref<{
  stock: { ts_code: string; name: string; industry: string }
  content: string
  signal: { direction: string; strength: string; score: number; reasons: string[] } | null
} | null>(null)

// 显示错误提示
function showError(type: 'error' | 'warning' | 'info', title: string, message: string, details?: string) {
  errorMessage.value = { type, title, message, details }
  // 10秒后自动关闭
  setTimeout(() => {
    if (errorMessage.value?.title === title) {
      errorMessage.value = null
    }
  }, 10000)
}

function closeError() {
  errorMessage.value = null
}

// 解析 API 错误
function parseApiError(data: any, defaultMessage: string): { title: string; message: string; details?: string } {
  // 检查是否是 API 配额问题
  if (data?.detail && typeof data.detail === 'string') {
    const detail = data.detail
    
    // Gemini 配额错误
    if (detail.includes('429') || detail.includes('quota') || detail.includes('exceeded')) {
      return {
        title: '🚫 API 配额已用尽',
        message: 'Gemini API 免费配额已达到限制。',
        details: '解决方案：\n1. 等待配额重置（通常每日重置）\n2. 升级到 Google Cloud 付费计划\n3. 在 .env 中配置 OpenAI API Key 并切换提供商'
      }
    }
    
    // Tushare 权限错误
    if (detail.includes('没有接口访问权限') || detail.includes('tushare.pro')) {
      return {
        title: '🔒 数据源权限不足',
        message: 'Tushare 账户积分不足，无法访问此数据接口。',
        details: '解决方案：\n1. 访问 tushare.pro 登录您的账户\n2. 通过完成任务积累积分\n3. 或升级到付费会员获取更多权限'
      }
    }
    
    // 其他 API 错误
    return {
      title: '⚠️ 请求失败',
      message: detail.substring(0, 200),
      details: detail.length > 200 ? detail : undefined
    }
  }
  
  // 检查是否返回了 success: false
  if (data?.success === false && data?.content) {
    // 检查内容中是否包含错误信息
    const content = data.content as string
    if (content.includes('429') || content.includes('quota')) {
      return {
        title: '🚫 API 配额已用尽',
        message: 'LLM 服务配额不足',
        details: content.substring(0, 500)
      }
    }
  }
  
  return {
    title: '❌ 操作失败',
    message: defaultMessage
  }
}

// API 调用 - Alpha 分析
// API 调用 - 个股诊疗
async function runDiagnose() {
  if (!stockCode.value.trim()) {
    showError('info', '💡 请输入股票代码', '格式示例：000001.SZ（深市）或 600519.SH（沪市）')
    return
  }
  if (props.apiStatus !== 'connected') {
    showError('warning', '⚠️ 服务未连接', '请先启动 API 服务')
    return
  }
  
  errorMessage.value = null
  isDiagnosing.value = true
  
  try {
    // 先尝试快速扫描
    const scanResponse = await fetch(`/api/stock/scan?ts_code=${stockCode.value}`)
    const scanData = await scanResponse.json()
    
    if (!scanResponse.ok) {
      const error = parseApiError(scanData, '快速扫描失败，请检查股票代码格式')
      showError('error', error.title, error.message, error.details)
      return
    }
    
    // 然后深度诊疗
    const diagnoseResponse = await fetch('/api/stock/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ts_code: stockCode.value })
    })
    const diagnoseData = await diagnoseResponse.json()
    
    if (!diagnoseResponse.ok || diagnoseData.success === false) {
      const error = parseApiError(diagnoseData, '个股诊疗失败')
      showError('error', error.title, error.message, error.details)
      return
    }
    
    diagnoseResult.value = {
      stock: diagnoseData.stock,
      content: diagnoseData.content,
      signal: scanData.signal || diagnoseData.signal
    }
    
  } catch (error: any) {
    console.error('诊疗失败:', error)
    showError('error', '❌ 网络错误', '无法连接到 API 服务', error?.message)
  } finally {
    isDiagnosing.value = false
  }
}

// 格式化 Markdown（使用 marked 库正确渲染表格）
import { marked } from 'marked'

// 配置 marked
marked.setOptions({
  breaks: true,  // 支持换行
  gfm: true,     // 支持 GitHub 风格 Markdown
})

function formatMarkdown(text: string): string {
  if (!text) return ''
  try {
    return marked(text) as string
  } catch (e) {
    // 降级到简单替换
    return text
      .replace(/^### (.*$)/gm, '<h3>$1</h3>')
      .replace(/^## (.*$)/gm, '<h2>$1</h2>')
      .replace(/^# (.*$)/gm, '<h1>$1</h1>')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>')
  }
}
</script>

<template>
  <div class="dashboard">
    <!-- 错误提示 Toast -->
    <Transition name="toast">
      <div v-if="errorMessage" class="toast-container">
        <div class="toast" :class="'toast-' + errorMessage.type">
          <div class="toast-header">
            <span class="toast-title">{{ errorMessage.title }}</span>
            <button class="toast-close" @click="closeError">✕</button>
          </div>
          <p class="toast-message">{{ errorMessage.message }}</p>
          <div v-if="errorMessage.details" class="toast-details">
            <pre>{{ errorMessage.details }}</pre>
          </div>
        </div>
      </div>
    </Transition>
    
    <!-- 左侧面板：功能入口 -->
    <aside class="sidebar">
      <div class="sidebar-section">
        <h3 class="section-title">功能模块</h3>
        <nav class="nav-menu">
          <button 
            class="nav-item" 
            :class="{ active: activeTab === 'alpha' }"
            @click="activeTab = 'alpha'"
          >
            <span class="nav-icon">🎯</span>
            <span class="nav-text">Alpha Predator</span>
            <span class="nav-desc">全市场策略分析</span>
          </button>
          <button 
            class="nav-item"
            :class="{ active: activeTab === 'diagnose' }"
            @click="activeTab = 'diagnose'"
          >
            <span class="nav-icon">🔬</span>
            <span class="nav-text">Deep Dive</span>
            <span class="nav-desc">个股深度诊疗</span>
          </button>
          <button 
            class="nav-item"
            :class="{ active: activeTab === 'portfolio' }"
            @click="activeTab = 'portfolio'"
          >
            <span class="nav-icon">💼</span>
            <span class="nav-text">持仓管理</span>
            <span class="nav-desc">管理我的持仓</span>
          </button>
        </nav>
      </div>
      
      <div class="sidebar-section">
        <h3 class="section-title">系统状态</h3>
        <div class="status-list">
          <div class="status-item">
            <span class="status-label">LLM 引擎</span>
            <span class="badge badge-success">{{ llmProviderName }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">数据源</span>
            <span class="badge" :class="dataSourceName === 'AkShare' ? 'badge-info' : 'badge-warning'">{{ dataSourceName }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">风险偏好</span>
            <span class="badge badge-primary">{{ riskPreferenceName }}</span>
          </div>
          <div class="status-item">
            <span class="status-label">市场状态</span>
            <span class="badge" :class="marketStatus === '交易中' ? 'badge-success' : 'badge-muted'">{{ marketStatus }}</span>
          </div>
        </div>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="content">
      <!-- Alpha Predator - 分步分析流程 -->
      <div v-if="activeTab === 'alpha'" class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">🎯 Alpha Predator</h2>
            <p class="panel-desc">全市场阿尔法捕获引擎 - 智能策略分析与推送</p>
          </div>
        </div>
        
        <div v-if="apiStatus !== 'connected'" class="alert alert-warning">
          ⚠️ API 服务未连接。请先运行：<code>uvicorn src.api.main:app --reload --port 8000</code>
        </div>
        
        <AnalysisFlow v-else />
      </div>
      
      <!-- Deep Dive -->
      <div v-if="activeTab === 'diagnose'" class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">🔬 Deep Dive Diagnostic</h2>
            <p class="panel-desc">个股深度诊疗 - 多维度体检与评级</p>
          </div>
        </div>
        
        <div class="diagnose-input">
          <input 
            v-model="stockCode"
            type="text" 
            class="input"
            placeholder="输入股票代码（如：000001.SZ、600519.SH）"
            @keyup.enter="runDiagnose"
          />
          <button 
            class="btn btn-primary"
            @click="runDiagnose"
            :disabled="isDiagnosing || apiStatus !== 'connected'"
          >
            <span v-if="isDiagnosing" class="loading-spinner"></span>
            {{ isDiagnosing ? '诊疗中...' : '开始诊疗' }}
          </button>
        </div>
        
        <div v-if="apiStatus !== 'connected'" class="alert alert-warning">
          ⚠️ API 服务未连接
        </div>
        
        <div v-else-if="!diagnoseResult" class="empty-state">
          <div class="empty-icon">🩺</div>
          <h3>输入股票代码开始诊疗</h3>
          <p>系统将为您提供多因子评分、技术形态分析和 Buy/Hold/Sell 评级</p>
        </div>
        
        <div v-else class="diagnose-result animate-slide-in">
          <div class="stock-header">
            <div class="stock-info">
              <h3>{{ diagnoseResult.stock.name }}</h3>
              <span class="stock-code">{{ diagnoseResult.stock.ts_code }}</span>
              <span class="stock-industry">{{ diagnoseResult.stock.industry }}</span>
            </div>
            <div 
              class="signal-badge"
              :class="'signal-' + (diagnoseResult.signal?.direction || 'hold')"
            >
              {{ (diagnoseResult.signal?.direction || 'HOLD').toUpperCase() }}
            </div>
          </div>
          
          <div v-if="diagnoseResult.signal" class="signal-details">
            <div class="signal-score">
              <span class="score-label">综合评分</span>
              <span class="score-value" :class="diagnoseResult.signal.direction">
                {{ diagnoseResult.signal.score }}
              </span>
            </div>
            <div class="signal-strength">
              <span class="strength-label">信号强度</span>
              <span class="strength-value">{{ diagnoseResult.signal.strength }}</span>
            </div>
          </div>
          
          <div class="report-content" v-html="formatMarkdown(diagnoseResult.content)"></div>
        </div>
      </div>

      <!-- 持仓管理 -->
      <div v-if="activeTab === 'portfolio'" class="panel">
        <div class="panel-header">
          <div>
            <h2 class="panel-title">💼 持仓管理</h2>
            <p class="panel-subtitle">记录和管理您的持仓，支持实时盈亏分析</p>
          </div>
        </div>
        <PortfolioManager />
      </div>
    </main>
    
    <!-- 右侧面板：实时信息 -->
    <aside class="info-panel">
      <div class="info-section">
        <h3 class="section-title">
          📈 市场概览
          <button v-if="!isLoadingMarket" class="refresh-btn" @click="loadMarketData">🔄</button>
          <span v-else class="loading-spinner-small"></span>
        </h3>
        <div class="market-card">
          <div v-if="marketIndices.length === 0" class="market-empty">
            暂无数据，点击刷新
          </div>
          <div 
            v-for="index in marketIndices" 
            :key="index.code" 
            class="market-item"
          >
            <span class="market-name">{{ index.name }}</span>
            <span 
              class="market-value" 
              :class="index.change_pct >= 0 ? 'up' : 'down'"
            >
              {{ index.price.toLocaleString('zh-CN', { minimumFractionDigits: 2 }) }}
            </span>
            <span 
              class="market-change" 
              :class="index.change_pct >= 0 ? 'up' : 'down'"
            >
              {{ index.change_pct >= 0 ? '+' : '' }}{{ index.change_pct.toFixed(2) }}%
            </span>
          </div>
        </div>
      </div>
      
      <div class="info-section">
        <h3 class="section-title">💡 使用提示</h3>
        <div class="tips-list">
          <div class="tip-item">
            <span class="tip-icon">1️⃣</span>
            <span>启动 API：<code>uvicorn src.api.main:app --reload</code></span>
          </div>
          <div class="tip-item">
            <span class="tip-icon">2️⃣</span>
            <span>配置有效的 Gemini API Key</span>
          </div>
          <div class="tip-item">
            <span class="tip-icon">3️⃣</span>
            <span>确保 Tushare 积分充足</span>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
.dashboard {
  display: grid;
  grid-template-columns: 280px 1fr 300px;
  gap: 24px;
  min-height: calc(100vh - 80px);
}

/* 左侧边栏 */
.sidebar {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.sidebar-section {
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 20px;
  border: 1px solid var(--border-color);
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 16px;
}

.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 14px 16px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: var(--transition);
  text-align: left;
}

.nav-item:hover {
  background: var(--bg-hover);
  border-color: var(--border-color);
}

.nav-item.active {
  background: rgba(102, 126, 234, 0.15);
  border-color: var(--primary-color);
}

.nav-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.nav-text {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.nav-desc {
  font-size: 12px;
  color: var(--text-muted);
}

.quick-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--primary-gradient);
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
}

.action-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow);
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.status-label {
  font-size: 13px;
  color: var(--text-secondary);
}

.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 500;
  background: var(--bg-tertiary);
  color: var(--text-secondary);
}

.badge-success {
  background: rgba(34, 197, 94, 0.15);
  color: #22c55e;
}

.badge-warning {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.badge-info {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.badge-primary {
  background: rgba(139, 92, 246, 0.15);
  color: #8b5cf6;
}

.badge-muted {
  background: rgba(113, 113, 122, 0.15);
  color: #a1a1aa;
}

/* 主内容区 */
.content {
  display: flex;
  flex-direction: column;
}

.panel {
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 24px;
  border: 1px solid var(--border-color);
  flex: 1;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.panel-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 8px;
}

.panel-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

.diagnose-input {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}

.diagnose-input .input {
  flex: 1;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-state h3 {
  font-size: 18px;
  margin-bottom: 8px;
}

.empty-state p {
  color: var(--text-secondary);
  max-width: 400px;
}

.alert {
  padding: 16px 20px;
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
}

.alert-warning {
  background: rgba(245, 158, 11, 0.15);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: var(--warning);
}

.alert code {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.report-card, .diagnose-result {
  background: var(--bg-secondary);
  border-radius: var(--radius);
  padding: 24px;
  border: 1px solid var(--border-color);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color);
}

.report-header h3 {
  font-size: 18px;
}

.report-time {
  font-size: 12px;
  color: var(--text-muted);
}

.report-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.report-content :deep(h1),
.report-content :deep(h2),
.report-content :deep(h3) {
  color: var(--text-primary);
  margin: 20px 0 12px;
}

.report-content :deep(strong) {
  color: var(--text-primary);
}

/* Markdown 表格样式 */
.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 13px;
}

.report-content :deep(th),
.report-content :deep(td) {
  padding: 10px 12px;
  text-align: left;
  border: 1px solid var(--border-color);
}

.report-content :deep(th) {
  background: var(--bg-tertiary);
  color: var(--text-primary);
  font-weight: 600;
}

.report-content :deep(tr:nth-child(even)) {
  background: rgba(255, 255, 255, 0.02);
}

.report-content :deep(tr:hover) {
  background: rgba(139, 92, 246, 0.1);
}

/* Markdown 列表样式 */
.report-content :deep(ul),
.report-content :deep(ol) {
  padding-left: 24px;
  margin: 12px 0;
}

.report-content :deep(li) {
  margin: 6px 0;
}

/* Markdown 代码样式 */
.report-content :deep(code) {
  background: rgba(0, 0, 0, 0.3);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: var(--primary-color);
}

.report-content :deep(pre) {
  background: var(--bg-tertiary);
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
}

.stock-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stock-info h3 {
  font-size: 22px;
  margin-bottom: 8px;
}

.stock-code {
  font-size: 14px;
  color: var(--primary-color);
  margin-right: 12px;
}

.stock-industry {
  font-size: 13px;
  color: var(--text-muted);
  padding: 2px 10px;
  background: var(--bg-card);
  border-radius: 9999px;
}

.signal-badge {
  font-size: 18px;
  font-weight: 700;
  padding: 12px 24px;
  border-radius: var(--radius-sm);
}

.signal-badge.signal-buy {
  background: rgba(16, 185, 129, 0.2);
  color: var(--buy-color);
}

.signal-badge.signal-sell {
  background: rgba(239, 68, 68, 0.2);
  color: var(--sell-color);
}

.signal-badge.signal-hold {
  background: rgba(245, 158, 11, 0.2);
  color: var(--hold-color);
}

.signal-details {
  display: flex;
  gap: 40px;
  padding: 16px;
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  margin-bottom: 20px;
}

.signal-score, .signal-strength {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.score-label, .strength-label {
  font-size: 12px;
  color: var(--text-muted);
}

.score-value {
  font-size: 28px;
  font-weight: 700;
}

.score-value.buy { color: var(--buy-color); }
.score-value.sell { color: var(--sell-color); }
.score-value.hold { color: var(--hold-color); }

.strength-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  text-transform: capitalize;
}

/* 右侧信息面板 */
.info-panel {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.info-section {
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 20px;
  border: 1px solid var(--border-color);
}

.market-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.market-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.market-name {
  font-size: 13px;
  color: var(--text-secondary);
}

.market-value {
  font-size: 16px;
  font-weight: 600;
}

.market-value.up { color: var(--buy-color); }
.market-value.down { color: var(--sell-color); }

.market-change {
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.market-change.up {
  background: rgba(16, 185, 129, 0.15);
  color: var(--buy-color);
}

.market-change.down {
  background: rgba(239, 68, 68, 0.15);
  color: var(--sell-color);
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tip-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.tip-item code {
  font-size: 11px;
  background: var(--bg-secondary);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--primary-color);
}

/* Toast 错误提示 */
.toast-container {
  position: fixed;
  top: 80px;
  right: 24px;
  z-index: 1000;
  max-width: 420px;
  animation: slideIn 0.3s ease-out;
}

.toast {
  background: var(--bg-card);
  border-radius: var(--radius);
  padding: 16px 20px;
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-lg);
}

.toast-error {
  border-color: var(--danger);
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, var(--bg-card) 100%);
}

.toast-warning {
  border-color: var(--warning);
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, var(--bg-card) 100%);
}

.toast-info {
  border-color: var(--info);
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, var(--bg-card) 100%);
}

.toast-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.toast-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.toast-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 14px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: var(--transition);
}

.toast-close:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.toast-message {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0;
  line-height: 1.5;
}

.toast-details {
  margin-top: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  overflow-x: auto;
}

.toast-details pre {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: pre-wrap;
  font-family: 'SF Mono', Monaco, monospace;
}

/* Toast 动画 */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100px);
}

/* 响应式 */
@media (max-width: 1200px) {
  .dashboard {
    grid-template-columns: 240px 1fr;
  }
  .info-panel {
    display: none;
  }
}

.refresh-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.7;
  transition: all 0.2s;
  margin-left: 8px;
}

.refresh-btn:hover {
  opacity: 1;
  transform: rotate(180deg);
}

.loading-spinner-small {
  display: inline-block;
  width: 12px;
  height: 12px;
  border: 2px solid var(--text-muted);
  border-top-color: var(--primary-color);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-left: 8px;
}

.market-empty {
  text-align: center;
  padding: 20px;
  color: var(--text-muted);
  font-size: 13px;
}

.section-title {
  display: flex;
  align-items: center;
}

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
  .sidebar {
    display: none;
  }
}
</style>
