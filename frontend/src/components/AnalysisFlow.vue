<script setup lang="ts">
/**
 * 分步分析流程组件
 * 步骤1: 分析热门板块
 * 步骤2: 用户选择板块
 * 步骤3: 推荐具体股票
 */
import { ref, computed } from 'vue'
import SectorCard from './SectorCard.vue'
import StockRecommendation from './StockRecommendation.vue'

interface Sector {
  name: string
  change_pct: number
  money_flow: number
  hot_level: string
  signal: string
  reason: string
}

interface SectorAnalysis {
  market_summary: string
  market_direction: string
  sectors: Sector[]
  risk_warning: string
  trade_date: string
}

interface StockRec {
  rank: number
  ts_code: string
  name: string
  sector: string
  signal: string
  score: number
  current_price: number
  target_price: number
  stop_loss_price: number
  position_pct: number
  hold_period: string
  entry_timing: string
  reasons: string[]
  risk_factors: string[]
}

interface StockRecommendations {
  analysis_summary: string
  recommendations: StockRec[]
  risk_warning: string
  trade_date: string
  selected_sectors?: string[]
}

// 状态
const currentStep = ref<1 | 2 | 3>(1)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

// 数据
const sectorAnalysis = ref<SectorAnalysis | null>(null)
const selectedSectors = ref<Set<string>>(new Set())
const stockRecommendations = ref<StockRecommendations | null>(null)

// 计算属性
const hasSelectedSectors = computed(() => selectedSectors.value.size > 0)

// 方法
function toggleSector(name: string) {
  if (selectedSectors.value.has(name)) {
    selectedSectors.value.delete(name)
  } else {
    selectedSectors.value.add(name)
  }
  // 触发响应式更新
  selectedSectors.value = new Set(selectedSectors.value)
}

async function analyzeSectors() {
  isLoading.value = true
  errorMessage.value = null
  
  try {
    const response = await fetch('/api/analyze/sectors')
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || '板块分析失败')
    }
    
    sectorAnalysis.value = data
    currentStep.value = 2
    
  } catch (error: any) {
    errorMessage.value = error.message || '请求失败'
  } finally {
    isLoading.value = false
  }
}

async function recommendStocks() {
  if (!hasSelectedSectors.value) {
    errorMessage.value = '请至少选择一个板块'
    return
  }
  
  isLoading.value = true
  errorMessage.value = null
  
  try {
    const response = await fetch('/api/analyze/stocks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sectors: Array.from(selectedSectors.value)
      })
    })
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || '股票推荐失败')
    }
    
    stockRecommendations.value = data
    currentStep.value = 3
    
  } catch (error: any) {
    errorMessage.value = error.message || '请求失败'
  } finally {
    isLoading.value = false
  }
}

function resetFlow() {
  currentStep.value = 1
  sectorAnalysis.value = null
  selectedSectors.value = new Set()
  stockRecommendations.value = null
  errorMessage.value = null
}

function goBack() {
  if (currentStep.value === 3) {
    currentStep.value = 2
    stockRecommendations.value = null
  } else if (currentStep.value === 2) {
    currentStep.value = 1
    sectorAnalysis.value = null
    selectedSectors.value = new Set()
  }
}

function getDirectionClass(direction: string) {
  if (direction === '看多') return 'direction-bullish'
  if (direction === '看空') return 'direction-bearish'
  return 'direction-neutral'
}
</script>

<template>
  <div class="analysis-flow">
    <!-- 进度指示器 -->
    <div class="progress-bar">
      <div class="step" :class="{ active: currentStep >= 1, done: currentStep > 1 }">
        <div class="step-number">1</div>
        <div class="step-label">板块分析</div>
      </div>
      <div class="step-line" :class="{ active: currentStep > 1 }"></div>
      <div class="step" :class="{ active: currentStep >= 2, done: currentStep > 2 }">
        <div class="step-number">2</div>
        <div class="step-label">选择板块</div>
      </div>
      <div class="step-line" :class="{ active: currentStep > 2 }"></div>
      <div class="step" :class="{ active: currentStep >= 3 }">
        <div class="step-number">3</div>
        <div class="step-label">股票推荐</div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="errorMessage" class="error-alert">
      <span>⚠️ {{ errorMessage }}</span>
      <button @click="errorMessage = null">✕</button>
    </div>

    <!-- 步骤1: 开始分析 -->
    <div v-if="currentStep === 1" class="step-content">
      <div class="start-section">
        <div class="start-icon">🎯</div>
        <h2>智能策略分析</h2>
        <p>分析当前市场热门板块，智能推荐值得关注的投资方向</p>
        <button 
          class="btn btn-primary btn-large"
          @click="analyzeSectors"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="loading-spinner"></span>
          {{ isLoading ? '分析中...' : '🔍 开始板块分析' }}
        </button>
      </div>
    </div>

    <!-- 步骤2: 板块选择 -->
    <div v-if="currentStep === 2 && sectorAnalysis" class="step-content">
      <!-- 市场总结 -->
      <div class="market-summary">
        <div class="summary-header">
          <h3>📊 市场概况</h3>
          <span 
            class="direction-badge" 
            :class="getDirectionClass(sectorAnalysis.market_direction)"
          >
            {{ sectorAnalysis.market_direction }}
          </span>
        </div>
        <p class="summary-text">{{ sectorAnalysis.market_summary }}</p>
      </div>

      <!-- 板块列表 -->
      <div class="section-header">
        <h3>🔥 热门板块</h3>
        <span class="selected-count">
          已选择 {{ selectedSectors.size }} 个板块
        </span>
      </div>
      
      <div class="sector-grid">
        <SectorCard
          v-for="sector in sectorAnalysis.sectors"
          :key="sector.name"
          :sector="sector"
          :selected="selectedSectors.has(sector.name)"
          @toggle="toggleSector(sector.name)"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <button class="btn btn-secondary" @click="goBack">
          ← 返回
        </button>
        <button 
          class="btn btn-primary"
          @click="recommendStocks"
          :disabled="!hasSelectedSectors || isLoading"
        >
          <span v-if="isLoading" class="loading-spinner"></span>
          {{ isLoading ? '分析中...' : '获取股票推荐 →' }}
        </button>
      </div>

      <!-- 风险提示 -->
      <div class="risk-warning">
        ⚠️ {{ sectorAnalysis.risk_warning }}
      </div>
    </div>

    <!-- 步骤3: 股票推荐 -->
    <div v-if="currentStep === 3 && stockRecommendations" class="step-content">
      <!-- 分析总结 -->
      <div class="analysis-summary">
        <h3>📈 分析结论</h3>
        <p>{{ stockRecommendations.analysis_summary }}</p>
        <div class="selected-sectors-tags">
          <span 
            v-for="sector in stockRecommendations.selected_sectors" 
            :key="sector"
            class="sector-tag"
          >
            {{ sector }}
          </span>
        </div>
      </div>

      <!-- 推荐股票列表 -->
      <div class="section-header">
        <h3>🎯 推荐股票</h3>
        <span class="rec-count">
          共 {{ stockRecommendations.recommendations.length }} 只
        </span>
      </div>

      <div v-if="stockRecommendations.recommendations.length === 0" class="empty-rec">
        <p>暂无符合条件的股票推荐，请尝试选择其他板块</p>
      </div>

      <div v-else class="stock-grid">
        <StockRecommendation
          v-for="stock in stockRecommendations.recommendations"
          :key="stock.ts_code"
          :stock="stock"
        />
      </div>

      <!-- 操作按钮 -->
      <div class="action-bar">
        <button class="btn btn-secondary" @click="goBack">
          ← 重新选择板块
        </button>
        <button class="btn btn-primary" @click="resetFlow">
          🔄 开始新分析
        </button>
      </div>

      <!-- 风险提示 -->
      <div class="risk-warning">
        ⚠️ {{ stockRecommendations.risk_warning }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.analysis-flow {
  padding: 20px;
}

/* 进度条 */
.progress-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 32px;
  padding: 20px;
  background: var(--bg-secondary, #1e1e2e);
  border-radius: 12px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.step-number {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-secondary, #888);
  transition: all 0.3s ease;
}

.step.active .step-number {
  background: var(--primary-color, #8b5cf6);
  color: white;
}

.step.done .step-number {
  background: #22c55e;
  color: white;
}

.step-label {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
}

.step.active .step-label {
  color: var(--text-primary, #fff);
  font-weight: 500;
}

.step-line {
  width: 80px;
  height: 2px;
  background: var(--bg-tertiary, #2a2a3e);
  margin: 0 16px;
  margin-bottom: 28px;
  transition: background 0.3s ease;
}

.step-line.active {
  background: var(--primary-color, #8b5cf6);
}

/* 错误提示 */
.error-alert {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.2);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  margin-bottom: 20px;
}

.error-alert button {
  background: none;
  border: none;
  color: #ef4444;
  cursor: pointer;
  font-size: 1.2rem;
}

/* 步骤1: 开始 */
.start-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 60px 20px;
}

.start-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.start-section h2 {
  font-size: 1.8rem;
  margin-bottom: 12px;
  color: var(--text-primary, #fff);
}

.start-section p {
  color: var(--text-secondary, #888);
  margin-bottom: 32px;
  max-width: 400px;
}

/* 市场总结 */
.market-summary {
  background: var(--bg-secondary, #1e1e2e);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.summary-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.direction-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.direction-bullish {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.direction-bearish {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.direction-neutral {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
}

.summary-text {
  color: var(--text-secondary, #888);
  line-height: 1.6;
  margin: 0;
}

/* 板块列表 */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.section-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.selected-count, .rec-count {
  font-size: 0.85rem;
  color: var(--primary-color, #8b5cf6);
}

.sector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

/* 股票列表 */
.analysis-summary {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), transparent);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 24px;
}

.analysis-summary h3 {
  margin: 0 0 12px;
  font-size: 1.1rem;
}

.analysis-summary p {
  color: var(--text-secondary, #888);
  line-height: 1.6;
  margin: 0 0 12px;
}

.selected-sectors-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.sector-tag {
  padding: 4px 12px;
  background: var(--bg-tertiary, #2a2a3e);
  border-radius: 20px;
  font-size: 0.8rem;
  color: var(--text-secondary, #888);
}

.stock-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  margin-bottom: 24px;
}

.empty-rec {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary, #888);
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}

/* 风险提示 */
.risk-warning {
  padding: 12px 16px;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 8px;
  font-size: 0.85rem;
  color: #eab308;
}

/* 按钮 */
.btn {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-primary, #fff);
  border: 1px solid var(--border-color, #333);
}

.btn-secondary:hover {
  background: var(--bg-hover, #333);
}

.btn-large {
  padding: 16px 32px;
  font-size: 1.1rem;
}

/* 加载动画 */
.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
