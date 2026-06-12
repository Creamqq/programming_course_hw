<template>
  <div class="market-view">
    <el-row :gutter="20">
      <!-- 合约列表 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>期货合约列表</span>
              <div class="header-actions">
                <el-input v-model="contractFilter" placeholder="搜索合约" clearable style="width: 160px; margin-right: 8px" />
                <el-select v-model="selectedExchange" placeholder="选择交易所" clearable style="width: 140px; margin-right: 8px" @change="loadContracts">
                  <el-option label="全部" value="" />
                  <el-option label="上期所" value="SHFE" />
                  <el-option label="大商所" value="DCE" />
                  <el-option label="郑商所" value="CZCE" />
                  <el-option label="中金所" value="CFFEX" />
                  <el-option label="能源中心" value="INE" />
                  <el-option label="广期所" value="GFEX" />
                </el-select>
                <el-button type="warning" size="small" @click="refreshContracts" :loading="marketStore.loading">刷新数据</el-button>
              </div>
            </div>
          </template>
          <el-table :data="filteredContracts" stripe v-loading="marketStore.loading" max-height="500">
            <el-table-column prop="symbol" label="合约代码" width="200" />
            <el-table-column prop="exchange" label="交易所" width="100" />
            <el-table-column prop="product" label="品种" width="100" />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="viewKline(row.symbol)">K线</el-button>
              </template>
            </el-table-column>
            <template #empty>
              <div v-if="loadError" style="color: #f56c6c">{{ loadError }}</div>
              <div v-else>暂无数据</div>
            </template>
          </el-table>
        </el-card>
      </el-col>

      <!-- 实时行情 -->
      <el-col :span="8">
        <!-- 数据缓存 -->
        <el-card style="margin-bottom: 20px">
          <template #header>
            <div class="card-header">
              <span>数据缓存</span>
              <el-button size="small" @click="loadCacheStats">刷新</el-button>
            </div>
          </template>
          <div v-if="cacheStats" class="cache-info">
            <div class="quote-row">
              <span class="label">合约缓存</span>
              <span class="value">{{ cacheStats.contracts?.count || 0 }} 个 ({{ cacheStats.contracts?.saved_at || '无' }})</span>
            </div>
            <div class="quote-row">
              <span class="label">K线文件</span>
              <span class="value">{{ cacheStats.kline_files || 0 }} 个</span>
            </div>
            <div class="quote-row">
              <span class="label">K线总大小</span>
              <span class="value">{{ cacheStats.kline_total_size_mb || 0 }} MB</span>
            </div>
          </div>
          <el-divider />
          <div>
            <div style="margin-bottom: 8px; font-size: 13px; color: #666">预下载K线数据</div>
            <el-form :inline="true" size="small" @submit.prevent="prefetchKline">
              <el-date-picker v-model="prefetchDateRange" type="daterange" start-placeholder="开始" end-placeholder="结束" style="width: 240px; margin-right: 8px" />
              <el-select v-model="prefetchExchange" placeholder="交易所" clearable style="width: 100px; margin-right: 8px">
                <el-option label="全部" value="" />
                <el-option label="上期所" value="SHFE" />
                <el-option label="大商所" value="DCE" />
                <el-option label="郑商所" value="CZCE" />
              </el-select>
              <el-input-number v-model="prefetchLimit" :min="1" :max="100" style="width: 100px; margin-right: 8px" />
              <el-button type="primary" @click="prefetchKline" :loading="prefetching">下载</el-button>
            </el-form>
            <div v-if="prefetchResult" style="margin-top: 8px; font-size: 12px; color: #67c23a">
              下载完成: 成功 {{ prefetchResult.success }} / 请求 {{ prefetchResult.requested }}
            </div>
          </div>
        </el-card>

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
        <el-button type="primary" size="small" @click="loadKline" :loading="klineLoading" style="margin-left: 8px">加载</el-button>
        <span v-if="klineError" style="color: #f56c6c; margin-left: 12px; font-size: 12px">{{ klineError }}</span>
      </div>
      <div v-if="klineLoading" style="text-align: center; padding: 60px">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <div style="margin-top: 12px; color: #999">加载K线数据中...</div>
      </div>
      <v-chart v-else-if="klineData.length" :option="klineOption" style="height: 500px" autoresize />
      <div v-else style="text-align: center; padding: 60px; color: #999">选择日期范围后点击加载</div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useMarketStore } from '@/stores'
import { marketApi } from '@/api'
import type { QuoteData, KlineData } from '@/types'
import { Loading } from '@element-plus/icons-vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CandlestickChart, LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent, DataZoomComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([CandlestickChart, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, DataZoomComponent, CanvasRenderer])

const marketStore = useMarketStore()

const selectedExchange = ref('')
const contractFilter = ref('')
const quoteSymbol = ref('')
const loadError = ref('')
const quote = ref<QuoteData | null>(null)
const klineVisible = ref(false)
const klineSymbol = ref('')
const klineDateRange = ref<[Date, Date] | null>(null)
const klineData = ref<KlineData[]>([])
const klineLoading = ref(false)
const klineError = ref('')
const cacheStats = ref<any>(null)
const prefetchDateRange = ref<[Date, Date] | null>(null)
const prefetchExchange = ref('')
const prefetchLimit = ref(20)
const prefetching = ref(false)
const prefetchResult = ref<any>(null)
const contractList = computed(() =>
  marketStore.contracts.map((c) => {
    const parts = c.split('.')
    return {
      symbol: c,
      exchange: parts[0] || '',
      product: parts[1] ? parts[1].replace(/\d+$/, '') : '',
    }
  })
)

const filteredContracts = computed(() => {
  if (!contractFilter.value) return contractList.value
  const keyword = contractFilter.value.toLowerCase()
  return contractList.value.filter((c) =>
    c.symbol.toLowerCase().includes(keyword) ||
    c.product.toLowerCase().includes(keyword)
  )
})

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
  loadError.value = ''
  try {
    await marketStore.fetchContracts(selectedExchange.value || undefined)
    if (marketStore.contracts.length === 0) {
      loadError.value = '未获取到合约数据，请检查后端日志和 tqsdk 连接'
    }
  } catch (e: any) {
    loadError.value = '加载失败: ' + (e.message || e)
  }
}

async function refreshContracts() {
  loadError.value = ''
  try {
    await marketStore.fetchContracts(selectedExchange.value || undefined, true)
  } catch (e: any) {
    loadError.value = '刷新失败: ' + (e.message || e)
  }
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
  klineData.value = []
  klineError.value = ''
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 3)
  klineDateRange.value = [start, end]
  // 自动加载
  loadKline()
}

async function loadKline() {
  if (!klineDateRange.value) return
  klineLoading.value = true
  klineError.value = ''
  const [start, end] = klineDateRange.value
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  try {
    const res = await marketApi.getKline(klineSymbol.value, fmt(start), fmt(end))
    klineData.value = res.data.data
    if (!klineData.value.length) {
      klineError.value = '未获取到数据，可能该合约在此期间无交易'
    }
  } catch (e: any) {
    klineError.value = '加载失败: ' + (e.response?.data?.detail || e.message || e)
  } finally {
    klineLoading.value = false
  }
}

async function loadCacheStats() {
  try {
    const res = await marketApi.getCacheStats()
    cacheStats.value = res.data
  } catch (e) {
    console.error(e)
  }
}

async function prefetchKline() {
  if (!prefetchDateRange.value) return
  prefetching.value = true
  prefetchResult.value = null
  const [start, end] = prefetchDateRange.value
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  try {
    const res = await marketApi.prefetchKline(
      prefetchExchange.value || undefined,
      fmt(start), fmt(end), 'daily', prefetchLimit.value
    )
    prefetchResult.value = res.data
    loadCacheStats()
  } catch (e: any) {
    prefetchResult.value = { success: 0, requested: 0, error: e.message }
  } finally {
    prefetching.value = false
  }
}

// 初始化加载
loadContracts()
loadCacheStats()
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
.header-actions {
  display: flex;
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
