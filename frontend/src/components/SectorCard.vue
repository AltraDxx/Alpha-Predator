<script setup lang="ts">
/**
 * 板块卡片组件
 * 显示板块名称、涨跌幅、资金流向和信号
 */

interface Sector {
  name: string
  change_pct: number
  money_flow: number
  hot_level: string
  signal: string
  reason: string
}

const props = defineProps<{
  sector: Sector
  selected: boolean
}>()

const emit = defineEmits<{
  (e: 'toggle'): void
}>()

function getSignalClass(signal: string) {
  if (signal === '利多') return 'signal-bullish'
  if (signal === '利空') return 'signal-bearish'
  return 'signal-neutral'
}

function getChangeClass(change: number) {
  if (change > 0) return 'change-up'
  if (change < 0) return 'change-down'
  return ''
}

function formatMoneyFlow(flow: number) {
  if (flow >= 0) return `+${flow.toFixed(2)}亿`
  return `${flow.toFixed(2)}亿`
}
</script>

<template>
  <div 
    class="sector-card" 
    :class="{ selected }"
    @click="emit('toggle')"
  >
    <div class="card-header">
      <span class="sector-name">{{ sector.name }}</span>
      <span class="hot-level" :class="`hot-${sector.hot_level}`">
        {{ sector.hot_level === '高' ? '🔥' : sector.hot_level === '中' ? '📈' : '📊' }}
      </span>
    </div>
    
    <div class="card-body">
      <div class="metric">
        <span class="label">涨跌幅</span>
        <span class="value" :class="getChangeClass(sector.change_pct)">
          {{ sector.change_pct > 0 ? '+' : '' }}{{ sector.change_pct.toFixed(2) }}%
        </span>
      </div>
      <div class="metric">
        <span class="label">资金流</span>
        <span class="value" :class="getChangeClass(sector.money_flow)">
          {{ formatMoneyFlow(sector.money_flow) }}
        </span>
      </div>
    </div>
    
    <div class="card-footer">
      <span class="signal" :class="getSignalClass(sector.signal)">
        {{ sector.signal }}
      </span>
      <span class="reason">{{ sector.reason }}</span>
    </div>
    
    <div v-if="selected" class="selected-indicator">✓</div>
  </div>
</template>

<style scoped>
.sector-card {
  background: var(--bg-secondary, #1e1e2e);
  border: 1px solid var(--border-color, #333);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.sector-card:hover {
  border-color: var(--primary-color, #8b5cf6);
  transform: translateY(-2px);
}

.sector-card.selected {
  border-color: var(--primary-color, #8b5cf6);
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), transparent);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.sector-name {
  font-weight: 600;
  font-size: 1.1rem;
  color: var(--text-primary, #fff);
}

.hot-level {
  font-size: 1.2rem;
}

.card-body {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label {
  font-size: 0.75rem;
  color: var(--text-secondary, #888);
}

.value {
  font-weight: 600;
  font-size: 1rem;
}

.change-up {
  color: #22c55e;
}

.change-down {
  color: #ef4444;
}

.card-footer {
  display: flex;
  gap: 8px;
  align-items: center;
}

.signal {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 500;
}

.signal-bullish {
  background: rgba(34, 197, 94, 0.2);
  color: #22c55e;
}

.signal-bearish {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
}

.signal-neutral {
  background: rgba(156, 163, 175, 0.2);
  color: #9ca3af;
}

.reason {
  font-size: 0.8rem;
  color: var(--text-secondary, #888);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: var(--primary-color, #8b5cf6);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.8rem;
}
</style>
