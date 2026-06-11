<template>
  <div class="market-view">
    <el-row :gutter="20">
      <!-- 合约列表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>主力合约列表</span>
              <el-select v-model="selectedExchange" placeholder="选择交易所" clearable style="width: 160px" @change="loadContracts">
                <el-option label="全部" value="" />
                <el-option label="上期所" value="SHFE" />
                <el-option label="大商所" value="DCE" />
                <el-option label="郑商所" value="CZCE" />
                <el-option label="中金所" value="CFFEX" />
                <el-option label="能源中心" value="INE" />
              </el-select>
            </div>
          </template>
          <el-table :data="contractList" stripe v-loading="marketStore.loading" max-height="500">
            <el-table-column prop="symbol" label="合约代码" width="180" />
            <el-table-column prop="exchange" label="交易所" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="viewKline(row.symbol)">K线</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 实时行情 -->
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>实时行情</span>
            </div>
          </template>
          <el-form :inline="true" size="small" @submit.prevent="fetchQuote">
            <el-input v-model="quoteSymbol" placeholder="输入合约代码" style="width: 160px; margin-right: 8px" />
            <el-button type="primary" @click="fetchQuote">查询</el-button>
          </el-form>
          <div v-if="quote" class="quote-info">
            <div class="quote-row">
              <span class="label">合约</span>
              <span class="value">{{ quote.symbol }}</span>
            </div>
            <div class="quote-row">
              <span class="label">最新价</span>
              <span class="value" :class="priceClass">{{ quote.last_price }}</span>
            </div>
            <div class="quote-row">
              <span class="label">买价</span>
              <span class="value">{{ quote.bid_price }}</span>
            </div>
            <div class="quote-row">
              <span class="label">卖价</span>
              <span class="value">{{ quote.ask_price }}</span>
            </div>
            <div class="quote-row">
              <span class="label">成交量</span>
              <span class="value">{{ quote.volume }}</span>
            </div>
            <div class="quote-row">
              <span class="label">持仓量</span>
              <span class="value">{{ quote.open_interest }}</span>
            </div>
            <div class="quote-row">
              <span class="label">最高</span>
              <span class="value">{{ quote.highest }}</span>
            </div>
            <div class="quote-row">
              <span class="label">最低</span>
              <span class="value">{{ quote.lowest }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- K线弹窗 -->
    <el-dialog v-model="klineVisible" :title="`${klineSymbol} K线图`" width="80%">
      <div class="kline-form">
        <el-date-picker v-model="klineDateRange" type="daterange" start-placeholder="开始日期" end-placeholder="结束日期" size="small" />
        <el-button type="primary" size="small" @click="loadKline" style="margin-left: 8px">加载</el-button>
      </div>
      <v-chart :option="klineOption" style="height: 500px" autoresize />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMarketStore } from '@/stores'
import { marketApi } from '@/api'
import type { QuoteData, KlineData } from '@/types'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CandlestickChart, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const marketStore = useMarketStore()

const selectedExchange = ref('')
const quoteSymbol = ref('')
const quote = ref<QuoteData | null>(null)
const klineVisible = ref(false)
const klineSymbol = ref('')
const klineDateRange = ref<[Date, Date] | null>(null)
const klineData = ref<KlineData[]>([])

const contractList = computed(() =>
  marketStore.contracts.map((c) => ({ symbol: c, exchange: c.split('.')[0] }))
)

const priceClass = computed(() => {
  if (!quote.value) return ''
  return quote.value.last_price >= quote.value.pre_close ? 'price-up' : 'price-down'
})

const klineOption = computed(() => {
  if (!klineData.value.length) return {}
  const dates = klineData.value.map((d) => d.date?.toString().slice(0, 10) || '')
  const ohlc = klineData.value.map((d) => [d.open, d.close, d.low, d.high])
  const volumes = klineData.value.map((d) => d.volume)

  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['K线', '成交量'] },
    grid: [
      { left: '10%', right: '5%', top: '5%', height: '55%' },
      { left: '10%', right: '5%', top: '68%', height: '20%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0 },
      { type: 'category', data: dates, gridIndex: 1 },
    ],
    yAxis: [
      { scale: true, gridIndex: 0 },
      { scale: true, gridIndex: 1 },
    ],
    dataZoom: [
      { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
      { show: true, xAxisIndex: [0, 1], type: 'slider', bottom: '2%' },
    ],
    series: [
      {
        name: 'K线',
        type: 'candlestick',
        data: ohlc,
        xAxisIndex: 0,
        yAxisIndex: 0,
        itemStyle: {
          color: '#ef232a',
          color0: '#14b143',
          borderColor: '#ef232a',
          borderColor0: '#14b143',
        },
      },
      {
        name: '成交量',
        type: 'bar',
        data: volumes,
        xAxisIndex: 1,
        yAxisIndex: 1,
      },
    ],
  }
})

async function loadContracts() {
  await marketStore.fetchContracts(selectedExchange.value || undefined)
}

async function fetchQuote() {
  if (!quoteSymbol.value) return
  try {
    const res = await marketApi.getQuote(quoteSymbol.value)
    quote.value = res.data
  } catch (e) {
    console.error(e)
  }
}

function viewKline(symbol: string) {
  klineSymbol.value = symbol
  klineVisible.value = true
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 3)
  klineDateRange.value = [start, end]
}

async function loadKline() {
  if (!klineDateRange.value) return
  const [start, end] = klineDateRange.value
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  try {
    const res = await marketApi.getKline(klineSymbol.value, fmt(start), fmt(end))
    klineData.value = res.data.data
  } catch (e) {
    console.error(e)
  }
}

// 初始化加载
loadContracts()
</script>

<style scoped>
.market-view {
  height: 100%;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.quote-info {
  margin-top: 16px;
}
.quote-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}
.quote-row .label {
  color: #999;
}
.quote-row .value {
  font-weight: bold;
}
.price-up {
  color: #ef232a;
}
.price-down {
  color: #14b143;
}
.kline-form {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}
</style>
