<template>
  <div class="portfolio-view">
    <el-row :gutter="20">
      <!-- 组合构建参数 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>组合构建</span></template>
          <el-form label-width="80px" size="small">
            <el-form-item label="因子">
              <el-select v-model="factorName" placeholder="选择因子">
                <el-option label="动量" value="momentum" />
                <el-option label="波动率" value="volatility" />
                <el-option label="成交量比" value="volume_ratio" />
                <el-option label="持仓变化" value="open_interest_change" />
              </el-select>
            </el-form-item>
            <el-form-item label="合约">
              <el-input v-model="symbols" type="textarea" :rows="3" placeholder="合约代码，逗号分隔" />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker v-model="startDate" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="endDate" type="date" style="width: 100%" />
            </el-form-item>
            <el-form-item label="做多比例">
              <el-slider v-model="longRatio" :min="10" :max="50" :step="5" :format-tooltip="(v: number) => v + '%'" />
            </el-form-item>
            <el-form-item label="做空比例">
              <el-slider v-model="shortRatio" :min="10" :max="50" :step="5" :format-tooltip="(v: number) => v + '%'" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="buildPortfolio" :loading="portfolioStore.loading">构建组合</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 组合持仓 -->
      <el-col :span="16">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>多空持仓</span>
              <el-tag type="success">做多 {{ longCount }}</el-tag>
              <el-tag type="danger">做空 {{ shortCount }}</el-tag>
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
          </el-table>
        </el-card>

        <!-- 权重分布图 -->
        <el-card v-if="portfolioStore.positions.length" style="margin-top: 16px">
          <template #header><span>权重分布</span></template>
          <v-chart :option="weightOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { usePortfolioStore } from '@/stores'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([PieChart, TooltipComponent, LegendComponent, CanvasRenderer])

const portfolioStore = usePortfolioStore()

const factorName = ref('momentum')
const symbols = ref('SHFE.cu2608,SHFE.al2608,SHFE.zn2608,DCE.m2608,DCE.y2608,CZCE.SA608,CZCE.MA608')
const startDate = ref(new Date(Date.now() - 90 * 86400000))
const endDate = ref(new Date())
const longRatio = ref(30)
const shortRatio = ref(30)

const fmt = (d: Date) => d.toISOString().slice(0, 10)

const longCount = computed(() => portfolioStore.positions.filter((p) => p.direction === 'long').length)
const shortCount = computed(() => portfolioStore.positions.filter((p) => p.direction === 'short').length)

const weightOption = computed(() => ({
  tooltip: { trigger: 'item', formatter: '{b}: {d}%' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['40%', '70%'],
      data: portfolioStore.positions.map((p) => ({
        name: `${p.symbol}(${p.direction === 'long' ? '多' : '空'})`,
        value: (p.weight * 100).toFixed(2),
        itemStyle: {
          color: p.direction === 'long' ? '#67c23a' : '#f56c6c',
        },
      })),
    },
  ],
}))

async function buildPortfolio() {
  await portfolioStore.buildPortfolio({
    symbols: symbols.value,
    factorName: factorName.value,
    startDate: fmt(startDate.value),
    endDate: fmt(endDate.value),
    longRatio: longRatio.value / 100,
    shortRatio: shortRatio.value / 100,
  })
}
</script>

<style scoped>
.portfolio-view {
  height: 100%;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
