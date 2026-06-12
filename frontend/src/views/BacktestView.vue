<template>
  <div class="backtest-view">
    <el-row :gutter="20">
      <!-- 回测参数 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>回测配置</span></template>
          <el-form label-width="80px" size="small">
            <el-form-item label="预设">
              <el-select v-model="presetName" placeholder="选择预设策略" @change="applyPreset">
                <el-option v-for="p in presets" :key="p.name" :label="p.name" :value="p.name" />
              </el-select>
            </el-form-item>
            <el-form-item label="合约池">
              <el-select
                v-model="config.universe"
                multiple
                filterable
                remote
                :remote-method="searchContracts"
                :loading="contractsLoading"
                placeholder="搜索并选择合约"
                style="width: 100%"
              >
                <el-option
                  v-for="c in contractOptions"
                  :key="c.value"
                  :label="c.label"
                  :value="c.value"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="因子">
              <el-select v-model="config.factor_name">
                <el-option label="动量" value="momentum" />
                <el-option label="波动率" value="volatility" />
                <el-option label="成交量比" value="volume_ratio" />
                <el-option label="持仓变化" value="open_interest_change" />
                <el-option label="量价背离" value="price_oi_divergence" />
                <el-option label="振幅" value="high_low_range" />
              </el-select>
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker v-model="config.start_date" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="config.end_date" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="初始资金">
              <el-input-number v-model="config.initial_capital" :min="100000" :step="100000" />
            </el-form-item>
            <el-form-item label="手续费率">
              <el-input-number v-model="config.commission_rate" :min="0" :max="0.01" :step="0.00001" :precision="5" />
            </el-form-item>
            <el-form-item label="滑点">
              <el-input-number v-model="config.slippage" :min="0" :max="10" />
            </el-form-item>
            <el-form-item label="调仓频率">
              <el-radio-group v-model="config.rebalance_freq">
                <el-radio-button value="daily">日频</el-radio-button>
                <el-radio-button value="weekly">周频</el-radio-button>
                <el-radio-button value="monthly">月频</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="做多比例">
              <el-slider v-model="longRatioPct" :min="10" :max="50" :step="5" />
            </el-form-item>
            <el-form-item label="做空比例">
              <el-slider v-model="shortRatioPct" :min="10" :max="50" :step="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runBacktest" :loading="backtestStore.loading" size="large">
                运行回测
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 回测结果 -->
      <el-col :span="16">
        <!-- 绩效指标 -->
        <el-card v-if="backtestStore.result">
          <template #header><span>绩效指标</span></template>
          <el-row :gutter="16">
            <el-col :span="6">
              <el-statistic title="总收益" :value="(backtestStore.result.total_return * 100).toFixed(2)" suffix="%" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="年化收益" :value="(backtestStore.result.annual_return * 100).toFixed(2)" suffix="%" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="夏普比率" :value="backtestStore.result.sharpe_ratio.toFixed(4)" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="最大回撤" :value="(backtestStore.result.max_drawdown * 100).toFixed(2)" suffix="%" />
            </el-col>
          </el-row>
          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="6">
              <el-statistic title="Calmar" :value="backtestStore.result.calmar_ratio.toFixed(4)" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="胜率" :value="(backtestStore.result.win_rate * 100).toFixed(2)" suffix="%" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="盈亏比" :value="backtestStore.result.profit_loss_ratio.toFixed(4)" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="交易次数" :value="backtestStore.result.trades.length" />
            </el-col>
          </el-row>
        </el-card>

        <!-- 净值曲线 -->
        <el-card v-if="backtestStore.result" style="margin-top: 16px">
          <template #header><span>净值曲线 & 回撤</span></template>
          <v-chart :option="equityOption" style="height: 400px" autoresize />
        </el-card>

        <!-- 交易明细 -->
        <el-card v-if="backtestStore.result?.trades.length" style="margin-top: 16px">
          <template #header><span>交易明细</span></template>
          <el-table :data="backtestStore.result.trades" stripe max-height="300" size="small">
            <el-table-column prop="date" label="日期" width="120" />
            <el-table-column prop="symbol" label="合约" width="160" />
            <el-table-column prop="direction" label="方向" width="80" />
            <el-table-column prop="action" label="操作" width="80">
              <template #default="{ row }">
                <el-tag :type="row.action === 'open' ? 'success' : 'warning'" size="small">
                  {{ row.action === 'open' ? '开仓' : '平仓' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useBacktestStore } from '@/stores'
import { backtestApi, marketApi } from '@/api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const backtestStore = useBacktestStore()

const presetName = ref('')
const presets = ref<Array<{ name: string; config: any }>>([])

const longRatioPct = ref(30)
const shortRatioPct = ref(30)

const contractsLoading = ref(false)
const contractOptions = ref<Array<{ value: string; label: string }>>([])
const allContracts = ref<string[]>([])

async function searchContracts(query: string) {
  if (allContracts.value.length === 0) {
    contractsLoading.value = true
    try {
      const res = await marketApi.getContracts()
      allContracts.value = res.data.contracts || []
    } finally {
      contractsLoading.value = false
    }
  }
  if (query) {
    contractOptions.value = allContracts.value
      .filter(c => c.toLowerCase().includes(query.toLowerCase()))
      .slice(0, 50)
      .map(c => ({ value: c, label: c }))
  } else {
    contractOptions.value = allContracts.value.slice(0, 50).map(c => ({ value: c, label: c }))
  }
}

const config = ref({
  start_date: new Date(Date.now() - 365 * 86400000).toISOString().slice(0, 10),
  end_date: new Date().toISOString().slice(0, 10),
  initial_capital: 1000000,
  commission_rate: 0.0001,
  slippage: 1,
  rebalance_freq: 'daily' as 'daily' | 'weekly' | 'monthly',
  long_ratio: 0.3,
  short_ratio: 0.3,
  factor_name: 'momentum',
  universe: [] as string[],
})

const equityOption = computed(() => {
  const result = backtestStore.result
  if (!result) return {}

  const dates = result.equity_curve.map((e) => e.date?.toString().slice(0, 10) || '')
  const equity = result.equity_curve.map((e) => e.equity)
  const drawdown = result.drawdown_curve.map((d) => (d.drawdown * 100).toFixed(4))

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['净值', '回撤'] },
    grid: [
      { left: '10%', right: '5%', top: '5%', height: '50%' },
      { left: '10%', right: '5%', top: '65%', height: '25%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0 },
      { type: 'category', data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { type: 'value', gridIndex: 0, name: '净值' },
      { type: 'value', gridIndex: 1, name: '回撤%' },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
    ],
    series: [
      {
        name: '净值',
        type: 'line',
        data: equity,
        xAxisIndex: 0,
        yAxisIndex: 0,
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.1 },
      },
      {
        name: '回撤',
        type: 'line',
        data: drawdown,
        xAxisIndex: 1,
        yAxisIndex: 1,
        itemStyle: { color: '#f56c6c' },
        areaStyle: { opacity: 0.3, color: '#f56c6c' },
      },
    ],
  }
})

function applyPreset() {
  const preset = presets.value.find((p) => p.name === presetName.value)
  if (preset) {
    Object.assign(config.value, preset.config)
  }
}

async function runBacktest() {
  config.value.long_ratio = longRatioPct.value / 100
  config.value.short_ratio = shortRatioPct.value / 100
  // 确保日期为字符串
  const payload = {
    ...config.value,
    start_date: typeof config.value.start_date === 'string'
      ? config.value.start_date
      : new Date(config.value.start_date).toISOString().slice(0, 10),
    end_date: typeof config.value.end_date === 'string'
      ? config.value.end_date
      : new Date(config.value.end_date).toISOString().slice(0, 10),
  }
  await backtestStore.runBacktest(payload)
}

onMounted(async () => {
  const res = await backtestApi.getPresets()
  presets.value = res.data.presets
})
</script>

<style scoped>
.backtest-view {
  height: 100%;
}
</style>
