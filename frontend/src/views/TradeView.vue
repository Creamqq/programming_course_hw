<template>
  <div class="trade-view">
    <el-row :gutter="20">
      <!-- 交易控制 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>交易控制</span></template>
          <div class="trade-status">
            <div class="status-indicator">
              <span class="dot" :class="{ active: tradeStore.isTrading }"></span>
              <span>{{ tradeStore.isTrading ? '交易中' : '已停止' }}</span>
            </div>
            <el-button
              v-if="!tradeStore.isTrading"
              type="success"
              size="large"
              @click="tradeStore.startTrading()"
            >
              启动交易
            </el-button>
            <el-button
              v-else
              type="danger"
              size="large"
              @click="tradeStore.stopTrading()"
            >
              停止交易
            </el-button>
          </div>
        </el-card>

        <!-- 手动下单 -->
        <el-card style="margin-top: 16px">
          <template #header><span>手动下单</span></template>
          <el-form label-width="80px" size="small">
            <el-form-item label="合约">
              <el-input v-model="signal.symbol" placeholder="如 SHFE.cu2401" />
            </el-form-item>
            <el-form-item label="方向">
              <el-select v-model="signal.direction">
                <el-option label="开多" value="buy" />
                <el-option label="开空" value="sell" />
                <el-option label="平多" value="close_long" />
                <el-option label="平空" value="close_short" />
              </el-select>
            </el-form-item>
            <el-form-item label="手数">
              <el-input-number v-model="signal.lots" :min="1" />
            </el-form-item>
            <el-form-item label="价格">
              <el-input-number v-model="signal.price" :precision="2" :min="0" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="executeSignal">下单</el-button>
              <el-button type="danger" @click="closeAll">一键平仓</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 当前持仓 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>当前持仓</span>
              <el-button size="small" @click="fetchPositions">刷新</el-button>
            </div>
          </template>
          <el-table :data="portfolioStore.positions" stripe size="small">
            <el-table-column prop="symbol" label="合约" width="180" />
            <el-table-column prop="direction" label="方向" width="100">
              <template #default="{ row }">
                <el-tag :type="row.direction === 'long' ? 'success' : 'danger'" size="small">
                  {{ row.direction === 'long' ? '做多' : '做空' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="weight" label="权重" width="120">
              <template #default="{ row }">
                {{ (row.weight * 100).toFixed(2) }}%
              </template>
            </el-table-column>
            <el-table-column prop="lots" label="手数" width="80" />
          </el-table>
          <el-empty v-if="!portfolioStore.positions.length" description="暂无持仓" />
        </el-card>

        <!-- 交易日志 -->
        <el-card style="margin-top: 16px">
          <template #header><span>交易日志</span></template>
          <el-table :data="tradeLogs" stripe max-height="300" size="small">
            <el-table-column prop="time" label="时间" width="180" />
            <el-table-column prop="action" label="操作" width="100" />
            <el-table-column prop="detail" label="详情" />
          </el-table>
          <el-empty v-if="!tradeLogs.length" description="暂无交易记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useTradeStore, usePortfolioStore } from '@/stores'
import { tradeApi } from '@/api'
import { ElMessage } from 'element-plus'

const tradeStore = useTradeStore()
const portfolioStore = usePortfolioStore()

const signal = ref({
  symbol: '',
  direction: 'buy' as 'buy' | 'sell' | 'close_long' | 'close_short',
  lots: 1,
  price: 0,
})

const tradeLogs = ref<Array<{ time: string; action: string; detail: string }>>([])

async function executeSignal() {
  try {
    const res = await tradeApi.executeSignal(signal.value)
    if (res.data.status === 'success') {
      ElMessage.success('下单成功')
      tradeLogs.value.unshift({
        time: new Date().toLocaleString(),
        action: signal.value.direction,
        detail: `${signal.value.symbol} ${signal.value.lots}手`,
      })
    } else {
      ElMessage.error(res.data.message || '下单失败')
    }
  } catch (e: any) {
    ElMessage.error('下单失败: ' + e.message)
  }
}

async function closeAll() {
  try {
    await tradeApi.closeAll()
    ElMessage.success('已平仓')
    tradeLogs.value.unshift({
      time: new Date().toLocaleString(),
      action: '一键平仓',
      detail: '全部持仓',
    })
    fetchPositions()
  } catch (e: any) {
    ElMessage.error('平仓失败: ' + e.message)
  }
}

async function fetchPositions() {
  await portfolioStore.fetchPositions()
}

onMounted(() => {
  tradeStore.fetchStatus()
  fetchPositions()
})
</script>

<style scoped>
.trade-view {
  height: 100%;
}
.trade-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 20px 0;
}
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
}
.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: #999;
}
.dot.active {
  background-color: #67c23a;
  box-shadow: 0 0 8px #67c23a;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
