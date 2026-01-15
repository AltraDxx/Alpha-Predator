<script setup lang="ts">
/**
 * 持仓管理组件
 * 支持添加、修改、删除持仓，自动保存到 localStorage
 */
import { ref, computed, onMounted, watch } from 'vue'

interface Position {
  ts_code: string
  name: string
  quantity: number
  cost_price: number
  current_price?: number
  profit?: number
  profit_pct?: number
  weight?: number
}

interface Portfolio {
  total_capital: number
  positions: Position[]
}

// 状态
const portfolio = ref<Portfolio>({
  total_capital: 100000,
  positions: []
})

const isEditing = ref(false)
const editingIndex = ref<number | null>(null)
const isLoading = ref(false)
const isLookingUp = ref(false)
const isDiagnosing = ref(false)
const diagnosisResult = ref<string | null>(null)

// 表单
const formData = ref({
  ts_code: '',
  name: '',
  quantity: 100,
  cost_price: 0
})

// 计算属性
const totalMarketValue = computed(() => {
  return portfolio.value.positions.reduce((sum, pos) => {
    return sum + pos.quantity * pos.cost_price
  }, 0)
})

const totalProfit = computed(() => {
  return portfolio.value.positions.reduce((sum, pos) => {
    return sum + (pos.profit || 0)
  }, 0)
})

// 可用资金
const availableCapital = computed(() => {
  return portfolio.value.total_capital - totalMarketValue.value
})

// 判断是否在交易时间内
function isMarketOpen(): boolean {
  const now = new Date()
  const day = now.getDay()
  if (day === 0 || day === 6) return false
  
  const time = now.getHours() * 100 + now.getMinutes()
  return (time >= 930 && time <= 1130) || (time >= 1300 && time <= 1500)
}

// 初始化：从 localStorage 加载
onMounted(() => {
  const saved = localStorage.getItem('portfolio')
  if (saved) {
    try {
      portfolio.value = JSON.parse(saved)
    } catch (e) {
      console.error('加载持仓数据失败', e)
    }
  }
  // 只在交易时间刷新行情
  if (isMarketOpen()) {
    refreshQuotes()
  }
})

// 监听变化，自动保存
watch(portfolio, (newVal) => {
  localStorage.setItem('portfolio', JSON.stringify(newVal))
}, { deep: true })

// 股票代码自动识别
async function lookupStock() {
  const code = formData.value.ts_code.trim()
  if (!code || code.length < 6) return
  
  isLookingUp.value = true
  try {
    const response = await fetch(`/api/stock/info?code=${code}`)
    const data = await response.json()
    if (data.success && data.data) {
      formData.value.ts_code = data.data.ts_code
      formData.value.name = data.data.name
    }
  } catch (e) {
    console.error('查询股票失败', e)
  } finally {
    isLookingUp.value = false
  }
}

// 刷新实时行情
async function refreshQuotes() {
  if (portfolio.value.positions.length === 0) return
  
  isLoading.value = true
  try {
    for (const pos of portfolio.value.positions) {
      try {
        const response = await fetch(`/api/stock/quote?ts_code=${pos.ts_code}`)
        if (response.ok) {
          const data = await response.json()
          if (data.success && data.data) {
            pos.current_price = data.data.price
            pos.name = data.data.name || pos.name
            const currentPrice = pos.current_price || pos.cost_price
            pos.profit = (currentPrice - pos.cost_price) * pos.quantity
            pos.profit_pct = pos.cost_price > 0 
              ? ((currentPrice / pos.cost_price) - 1) * 100 
              : 0
          }
        }
      } catch (e) {
        console.error(`获取 ${pos.ts_code} 行情失败`)
      }
    }
    updateWeights()
  } finally {
    isLoading.value = false
  }
}

// 更新仓位占比
function updateWeights() {
  const total = portfolio.value.total_capital
  for (const pos of portfolio.value.positions) {
    const value = pos.quantity * pos.cost_price
    pos.weight = total > 0 ? (value / total) * 100 : 0
  }
}

// 股数加减
function adjustQuantity(delta: number) {
  const newQty = formData.value.quantity + delta
  if (newQty >= 100) {
    formData.value.quantity = newQty
  }
}

// 校验股数为100的整数倍
function validateQuantity() {
  if (formData.value.quantity < 100) {
    formData.value.quantity = 100
  } else if (formData.value.quantity % 100 !== 0) {
    formData.value.quantity = Math.round(formData.value.quantity / 100) * 100
  }
}

// 添加/编辑持仓
function savePosition() {
  // 验证
  if (!formData.value.ts_code) {
    alert('请输入股票代码')
    return
  }
  if (formData.value.quantity <= 0 || formData.value.quantity % 100 !== 0) {
    alert('持仓数量必须是100的正整数倍')
    return
  }
  if (formData.value.cost_price <= 0) {
    alert('请输入有效的成本价')
    return
  }
  
  const position: Position = {
    ts_code: formData.value.ts_code.toUpperCase(),
    name: formData.value.name || formData.value.ts_code,
    quantity: formData.value.quantity,
    cost_price: formData.value.cost_price
  }
  
  if (editingIndex.value !== null) {
    portfolio.value.positions[editingIndex.value] = position
  } else {
    portfolio.value.positions.push(position)
  }
  
  resetForm()
  updateWeights()
}

// 编辑持仓
function editPosition(index: number) {
  const pos = portfolio.value.positions[index]
  if (!pos) return
  formData.value = {
    ts_code: pos.ts_code,
    name: pos.name,
    quantity: pos.quantity,
    cost_price: pos.cost_price
  }
  editingIndex.value = index
  isEditing.value = true
}

// 删除持仓
function deletePosition(index: number) {
  if (confirm('确定要删除这条持仓记录吗？')) {
    portfolio.value.positions.splice(index, 1)
    updateWeights()
  }
}

// 重置表单
function resetForm() {
  formData.value = {
    ts_code: '',
    name: '',
    quantity: 100,
    cost_price: 0
  }
  editingIndex.value = null
  isEditing.value = false
}

// 格式化数字
function formatNumber(num: number, decimals = 2): string {
  return num.toLocaleString('zh-CN', { 
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals 
  })
}

// 格式化百分比
function formatPercent(num: number): string {
  const sign = num >= 0 ? '+' : ''
  return sign + num.toFixed(2) + '%'
}

// 持仓诊断
async function diagnosePortfolio() {
  if (portfolio.value.positions.length === 0) {
    alert('请先添加持仓')
    return
  }
  
  isDiagnosing.value = true
  diagnosisResult.value = null
  
  try {
    const response = await fetch('/api/user/portfolio/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        total_capital: portfolio.value.total_capital,
        positions: portfolio.value.positions
      })
    })
    const data = await response.json()
    
    if (data.success) {
      diagnosisResult.value = data.diagnosis
    } else {
      alert('诊断失败: ' + (data.error || '未知错误'))
    }
  } catch (e) {
    console.error('诊断失败', e)
    alert('诊断请求失败')
  } finally {
    isDiagnosing.value = false
  }
}
</script>

<template>
  <div class="portfolio-manager">
    <div class="section-header">
      <h2>📊 我的持仓</h2>
      <div class="header-actions">
        <button class="btn btn-primary btn-sm" @click="diagnosePortfolio" :disabled="isDiagnosing || portfolio.positions.length === 0">
          {{ isDiagnosing ? '诊断中...' : '🩺 每日诊断' }}
        </button>
        <button class="btn btn-secondary btn-sm" @click="refreshQuotes" :disabled="isLoading">
          {{ isLoading ? '刷新中...' : '🔄 刷新行情' }}
        </button>
      </div>
    </div>

    <!-- 总资金设置 -->
    <div class="capital-section">
      <label>总投入资金：</label>
      <div class="capital-input">
        <span class="currency">¥</span>
        <input 
          type="number" 
          v-model.number="portfolio.total_capital" 
          min="0"
          step="10000"
        />
      </div>
      <div class="capital-stats">
        <span>持仓市值: ¥{{ formatNumber(totalMarketValue) }}</span>
        <span class="available">可用: ¥{{ formatNumber(availableCapital) }}</span>
        <span :class="totalProfit >= 0 ? 'profit' : 'loss'">
          盈亏: {{ totalProfit >= 0 ? '+' : '' }}¥{{ formatNumber(totalProfit) }}
        </span>
      </div>
    </div>

    <!-- 添加/编辑表单 -->
    <div class="add-form">
      <div class="form-row-inline">
        <div class="form-group">
          <label>股票代码</label>
          <div class="code-input-wrapper">
            <input 
              type="text" 
              v-model="formData.ts_code" 
              placeholder="6位代码"
              @blur="lookupStock"
              maxlength="10"
              class="input-sm"
            />
            <span v-if="isLookingUp" class="lookup-loading">...</span>
          </div>
        </div>
        
        <div class="form-group">
          <label>股票名称</label>
          <input 
            type="text" 
            v-model="formData.name" 
            placeholder="自动识别"
            readonly
            class="readonly-input input-sm"
          />
        </div>
        
        <div class="form-group">
          <label>数量</label>
          <div class="quantity-control">
            <button class="qty-btn" @click="adjustQuantity(-100)" :disabled="formData.quantity <= 100">−</button>
            <input 
              type="text"
              :value="formData.quantity"
              @change="formData.quantity = parseInt(($event.target as HTMLInputElement).value) || 100; validateQuantity()"
              class="qty-input"
            />
            <button class="qty-btn" @click="adjustQuantity(100)">+</button>
          </div>
        </div>
        
        <div class="form-group">
          <label>成本价</label>
          <input 
            type="text"
            :value="formData.cost_price || ''"
            @change="formData.cost_price = parseFloat(($event.target as HTMLInputElement).value) || 0"
            placeholder="均价"
            class="input-sm"
          />
        </div>
        
        <div class="form-actions-inline">
          <button class="btn btn-primary btn-sm" @click="savePosition">
            {{ editingIndex !== null ? '保存' : '添加' }}
          </button>
          <button v-if="editingIndex !== null" class="btn btn-secondary btn-sm" @click="resetForm">
            取消
          </button>
        </div>
      </div>
    </div>

    <!-- 持仓列表 -->
    <div class="positions-list">
      <div v-if="portfolio.positions.length === 0" class="empty-state">
        <p>暂无持仓记录，请添加您的持仓</p>
      </div>
      
      <table v-else class="positions-table">
        <thead>
          <tr>
            <th>股票</th>
            <th>数量</th>
            <th>成本价</th>
            <th>现价</th>
            <th>盈亏</th>
            <th>仓位</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(pos, index) in portfolio.positions" :key="pos.ts_code">
            <td class="stock-cell">
              <span class="stock-name">{{ pos.name || pos.ts_code }}</span>
              <span class="stock-code">{{ pos.ts_code }}</span>
            </td>
            <td>{{ pos.quantity }}</td>
            <td>¥{{ formatNumber(pos.cost_price) }}</td>
            <td>
              <span v-if="pos.current_price">¥{{ formatNumber(pos.current_price) }}</span>
              <span v-else class="no-data">--</span>
            </td>
            <td>
              <div v-if="pos.profit !== undefined" :class="pos.profit >= 0 ? 'profit' : 'loss'">
                <span>{{ pos.profit >= 0 ? '+' : '' }}¥{{ formatNumber(pos.profit) }}</span>
                <span class="profit-pct">{{ formatPercent(pos.profit_pct || 0) }}</span>
              </div>
              <span v-else class="no-data">--</span>
            </td>
            <td>{{ pos.weight ? pos.weight.toFixed(1) + '%' : '--' }}</td>
            <td class="actions-cell">
              <button class="action-btn edit" @click="editPosition(index)">✏️</button>
              <button class="action-btn delete" @click="deletePosition(index)">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 诊断结果 -->
    <div v-if="diagnosisResult" class="diagnosis-section">
      <div class="diagnosis-header">
        <h3>🩺 持仓诊断报告</h3>
        <button class="btn btn-secondary btn-sm" @click="diagnosisResult = null">关闭</button>
      </div>
      <div class="diagnosis-content" v-html="diagnosisResult"></div>
    </div>
  </div>
</template>

<style scoped>
.portfolio-manager {
  padding: 20px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
  font-size: 1.4rem;
  color: var(--text-primary, #fff);
}

.header-actions {
  display: flex;
  gap: 10px;
}

/* 总资金 */
.capital-section {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--bg-secondary, #1e1e2e);
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.capital-section label {
  color: var(--text-secondary, #888);
  font-size: 0.9rem;
}

.capital-input {
  display: flex;
  align-items: center;
  background: var(--bg-tertiary, #2a2a3e);
  border-radius: 8px;
  padding: 0 12px;
}

.currency {
  color: var(--text-secondary, #888);
  font-size: 1.1rem;
}

.capital-input input {
  background: none;
  border: none;
  color: var(--text-primary, #fff);
  font-size: 1.2rem;
  font-weight: 600;
  padding: 10px;
  width: 140px;
}

.capital-input input:focus {
  outline: none;
}

.capital-stats {
  display: flex;
  gap: 24px;
  margin-left: auto;
  font-size: 0.9rem;
}

.capital-stats span {
  color: var(--text-secondary, #888);
}

/* 添加表单 */
.add-form {
  background: var(--bg-secondary, #1e1e2e);
  padding: 16px 20px;
  border-radius: 12px;
  margin-bottom: 20px;
}

.form-row-inline {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: nowrap;
}

@media (max-width: 900px) {
  .form-row-inline {
    flex-wrap: wrap;
  }
}

.form-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: auto;
}

.form-group label {
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
  white-space: nowrap;
}

.form-group input {
  background: var(--bg-tertiary, #2a2a3e);
  border: 1px solid var(--border-color, #333);
  border-radius: 6px;
  padding: 8px 10px;
  color: var(--text-primary, #fff);
  font-size: 0.9rem;
}

.form-group input:focus {
  outline: none;
  border-color: var(--primary-color, #8b5cf6);
}

/* 股票代码自动识别 */
.code-input-wrapper {
  position: relative;
}

.lookup-loading {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-secondary, #888);
}

.readonly-input {
  background: var(--bg-tertiary, #2a2a3e) !important;
  opacity: 0.8;
  cursor: default;
}

/* 股数加减按钮 */
.quantity-control {
  display: flex;
  align-items: center;
  gap: 4px;
}

.quantity-control input {
  width: 80px;
  text-align: center;
}

.qty-btn {
  width: 36px;
  height: 36px;
  border: 1px solid var(--border-color, #333);
  border-radius: 6px;
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-primary, #fff);
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.qty-btn:hover:not(:disabled) {
  background: var(--primary-color, #8b5cf6);
}

.qty-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* 可用资金 */
.capital-stats .available {
  color: #22c55e;
}

/* 紧凑输入框 */
.input-sm {
  width: 90px;
  padding: 8px 10px !important;
  font-size: 0.9rem !important;
}

.qty-input {
  width: 60px;
  text-align: center;
  background: var(--bg-tertiary, #2a2a3e);
  border: 1px solid var(--border-color, #333);
  border-radius: 4px;
  padding: 8px 4px;
  color: var(--text-primary, #fff);
  font-size: 0.9rem;
}

.qty-input:focus {
  outline: none;
  border-color: var(--primary-color, #8b5cf6);
}

.form-actions-inline {
  display: flex;
  gap: 8px;
  align-items: center;
}

.btn-sm {
  padding: 8px 12px;
  font-size: 0.85rem;
}

.form-actions {
  display: flex;
  gap: 10px;
}

/* 持仓列表 */
.positions-list {
  background: var(--bg-secondary, #1e1e2e);
  border-radius: 12px;
  overflow: hidden;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-secondary, #888);
}

.positions-table {
  width: 100%;
  border-collapse: collapse;
}

.positions-table th,
.positions-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-color, #333);
}

.positions-table th {
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-secondary, #888);
  font-weight: 500;
  font-size: 0.85rem;
}

.positions-table tbody tr:hover {
  background: rgba(139, 92, 246, 0.05);
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stock-name {
  font-weight: 500;
  color: var(--text-primary, #fff);
}

.stock-code {
  font-size: 0.8rem;
  color: var(--text-secondary, #888);
}

.profit {
  color: #22c55e;
}

.loss {
  color: #ef4444;
}

.profit-pct {
  display: block;
  font-size: 0.8rem;
  opacity: 0.8;
}

.no-data {
  color: var(--text-muted, #555);
}

.actions-cell {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: background 0.2s;
}

.action-btn:hover {
  background: var(--bg-tertiary, #2a2a3e);
}

/* 按钮 */
.btn {
  padding: 10px 18px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
}

.btn-sm {
  padding: 8px 14px;
  font-size: 0.85rem;
}

.btn-primary {
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  color: white;
}

.btn-primary:hover {
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.4);
}

.btn-secondary {
  background: var(--bg-tertiary, #2a2a3e);
  color: var(--text-primary, #fff);
  border: 1px solid var(--border-color, #333);
}

.btn-secondary:hover {
  background: var(--bg-hover, #333);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 诊断结果 */
.diagnosis-section {
  background: var(--bg-secondary, #1e1e2e);
  border-radius: 12px;
  margin-top: 20px;
  overflow: hidden;
}

.diagnosis-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), transparent);
  border-bottom: 1px solid var(--border-color, #333);
}

.diagnosis-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--text-primary, #fff);
}

.diagnosis-content {
  padding: 20px;
  line-height: 1.8;
  color: var(--text-secondary, #888);
  max-height: 500px;
  overflow-y: auto;
}

.diagnosis-content :deep(h3) {
  color: var(--text-primary, #fff);
  margin-top: 20px;
  margin-bottom: 12px;
}

.diagnosis-content :deep(strong) {
  color: var(--primary-color, #8b5cf6);
}

.diagnosis-content :deep(ul) {
  padding-left: 20px;
}
</style>
