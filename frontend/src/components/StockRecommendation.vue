<script setup lang="ts">
/**
 * 股票推荐卡片组件
 * 显示推荐股票的详细信息
 */

interface PositionStrategy {
  initial_pct: number
  add_condition: string
  max_pct: number
}

interface StockRecommendation {
  rank: number
  ts_code: string
  name: string
  sector: string
  signal: string
  score: number
  current_price: number
  buy_price?: number
  sell_price?: number
  target_price?: number  // 兼容旧格式
  stop_loss_price: number
  position_pct?: number  // 兼容旧格式
  position_strategy?: PositionStrategy
  hold_period: string
  entry_timing: string
  reasons: string[]
  risk_factors: string[]
}

defineProps<{
  stock: StockRecommendation
}>()

function getSignalClass(signal: string) {
  if (signal === '买入') return 'signal-buy'
  if (signal === '回避') return 'signal-sell'
  return 'signal-hold'
}

function getScoreColor(score: number) {
  if (score >= 80) return '#22c55e'
  if (score >= 60) return '#eab308'
  return '#ef4444'
}
</script>

<template>
  <div class="stock-card">
    <!-- 头部：排名和基本信息 -->
    <div class="card-header">
      <div class="rank-badge">{{ stock.rank }}</div>
      <div class="stock-info">
        <div class="stock-name">{{ stock.name }}</div>
        <div class="stock-code">{{ stock.ts_code }} · {{ stock.sector }}</div>
      </div>
      <div class="signal-badge" :class="getSignalClass(stock.signal)">
        {{ stock.signal }}
      </div>
    </div>

    <!-- 评分进度条 -->
    <div class="score-section">
      <div class="score-label">
        <span>推荐强度</span>
        <span class="score-value" :style="{ color: getScoreColor(stock.score) }">
          {{ stock.score }}分
        </span>
      </div>
      <div class="score-bar">
        <div 
          class="score-fill" 
          :style="{ 
            width: `${stock.score}%`,
            background: getScoreColor(stock.score)
          }"
        ></div>
      </div>
    </div>

    <!-- 价格信息表格 -->
    <div class="price-table">
      <div class="price-row">
        <span class="price-label">当前价</span>
        <span class="price-value current">¥{{ stock.current_price?.toFixed(2) || 'N/A' }}</span>
      </div>
      <div class="price-row">
        <span class="price-label">建议买入</span>
        <span class="price-value buy">¥{{ (stock.buy_price || stock.current_price)?.toFixed(2) || 'N/A' }}</span>
      </div>
      <div class="price-row">
        <span class="price-label">目标卖出</span>
        <span class="price-value target">¥{{ (stock.sell_price || stock.target_price)?.toFixed(2) || 'N/A' }}</span>
      </div>
      <div class="price-row">
        <span class="price-label">止损价</span>
        <span class="price-value stoploss">¥{{ stock.stop_loss_price?.toFixed(2) || 'N/A' }}</span>
      </div>
    </div>

    <!-- 仓位策略 -->
    <div class="position-section">
      <div class="position-title">📊 仓位策略</div>
      <template v-if="stock.position_strategy">
        <div class="position-detail">
          <span class="position-label">底仓</span>
          <span class="position-value">{{ stock.position_strategy.initial_pct }}%</span>
        </div>
        <div class="position-condition">
          {{ stock.position_strategy.add_condition }}
        </div>
        <div class="position-detail">
          <span class="position-label">最大仓位</span>
          <span class="position-value">{{ stock.position_strategy.max_pct }}%</span>
        </div>
      </template>
      <template v-else>
        <div class="position-detail">
          <span class="position-label">建议仓位</span>
          <span class="position-value">{{ stock.position_pct || 20 }}%</span>
        </div>
      </template>
      <div class="hold-period">
        <span class="position-label">持仓周期</span>
        <span class="position-value">{{ stock.hold_period }}</span>
      </div>
    </div>

    <!-- 买入时机 -->
    <div class="timing-section">
      <div class="timing-label">⏰ 买入时机</div>
      <div class="timing-text">{{ stock.entry_timing }}</div>
    </div>

    <!-- 推荐理由 -->
    <div class="reasons-section">
      <div class="section-title">📊 推荐理由</div>
      <ul class="reason-list">
        <li v-for="(reason, index) in stock.reasons" :key="index">
          {{ reason }}
        </li>
      </ul>
    </div>

    <!-- 风险因素 -->
    <div class="risks-section">
      <div class="section-title">⚠️ 风险提示</div>
      <ul class="risk-list">
        <li v-for="(risk, index) in stock.risk_factors" :key="index">
          {{ risk }}
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.stock-card {
  background: var(--bg-secondary, #1e1e2e);
  border: 1px solid var(--border-color, #333);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.2s ease;
}

.stock-card:hover {
  border-color: var(--primary-color, #8b5cf6);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.rank-badge {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #8b5cf6, #6366f1);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  color: white;
}

.stock-info {
  flex: 1;
}

.stock-name {
  font-weight: 600;
  font-size: 1.2rem;
  color: var(--text-primary, #fff);
}

.stock-code {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
}

.signal-badge {
  padding: 6px 12px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 0.9rem;
}

.signal-buy {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
  border: 1px solid #22c55e;
}

.signal-hold {
  background: rgba(234, 179, 8, 0.2);
  color: #eab308;
  border: 1px solid #eab308;
}

.signal-sell {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border: 1px solid #ef4444;
}

.score-section {
  margin-bottom: 16px;
}

.score-label {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 6px;
  color: var(--text-secondary, #888);
}

.score-value {
  font-weight: 600;
}

.score-bar {
  height: 6px;
  background: var(--bg-tertiary, #2a2a3e);
  border-radius: 3px;
  overflow: hidden;
}

.score-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
}

.price-table {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  background: var(--bg-tertiary, #2a2a3e);
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.price-value.buy {
  color: #3b82f6;
}

.price-row {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.price-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
}

.price-value {
  font-weight: 600;
  font-size: 1rem;
}

.price-value.current {
  color: var(--text-primary, #fff);
}

.price-value.target {
  color: #22c55e;
}

.price-value.stoploss {
  color: #ef4444;
}

.position-info {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  gap: 8px;
}

.info-label {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
}

.info-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary-color, #8b5cf6);
}

.position-section {
  background: var(--bg-tertiary, #2a2a3e);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.position-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin-bottom: 8px;
}

.position-detail {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
}

.position-label {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
}

.position-value {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--primary-color, #8b5cf6);
}

.position-condition {
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 4px;
  padding: 8px;
  margin: 8px 0;
  font-size: 0.85rem;
  color: var(--text-primary, #fff);
}

.hold-period {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  border-top: 1px solid rgba(255,255,255,0.1);
  margin-top: 8px;
  padding-top: 8px;
}

.timing-section {
  background: rgba(139, 92, 246, 0.1);
  border: 1px solid rgba(139, 92, 246, 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 16px;
}

.timing-label {
  font-size: 0.85rem;
  color: var(--primary-color, #8b5cf6);
  margin-bottom: 4px;
}

.timing-text {
  font-size: 0.9rem;
  color: var(--text-primary, #fff);
}

.reasons-section,
.risks-section {
  margin-bottom: 12px;
}

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary, #fff);
  margin-bottom: 8px;
}

.reason-list,
.risk-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.reason-list li,
.risk-list li {
  font-size: 0.85rem;
  color: var(--text-secondary, #888);
  padding: 4px 0;
  padding-left: 16px;
  position: relative;
}

.reason-list li::before {
  content: "✓";
  position: absolute;
  left: 0;
  color: #22c55e;
}

.risk-list li::before {
  content: "!";
  position: absolute;
  left: 0;
  color: #ef4444;
}
</style>
