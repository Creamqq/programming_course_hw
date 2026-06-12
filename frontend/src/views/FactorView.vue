<template>
  <div class="factor-view">
    <el-row :gutter="20">
      <!-- 因子列表与参数 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>因子选择</span></template>
          <el-form label-width="80px" size="small">
            <el-form-item label="因子">
              <el-select v-model="selectedFactor" placeholder="选择因子">
                <el-option
                  v-for="f in factorStore.factorList"
                  :key="f.name"
                  :label="f.label"
                  :value="f.name"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="合约">
              <el-input v-model="symbols" type="textarea" :rows="3" placeholder="合约代码，逗号分隔" />
            </el-form-item>
            <el-form-item label="开始日期">
              <el-date-picker v-model="startDate" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="endDate" type="date" placeholder="选择日期" style="width: 100%" />
            </el-form-item>
            <el-form-item label="窗口期">
              <el-input-number v-model="window" :min="5" :max="120" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="computeFactor" :loading="factorStore.loading">计算因子</el-button>
              <el-button type="success" @click="computeIC" :loading="factorStore.loading">计算IC</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- IC统计 -->
        <el-card v-if="factorStore.icSummary.ic_mean" style="margin-top: 16px">
          <template #header><span>IC统计</span></template>
          <el-descriptions :column="1" size="small" border>
            <el-descriptions-item label="IC均值">{{ factorStore.icSummary.ic_mean }}</el-descriptions-item>
            <el-descriptions-item label="IC标准差">{{ factorStore.icSummary.ic_std }}</el-descriptions-item>
            <el-descriptions-item label="IR">{{ factorStore.icSummary.ir }}</el-descriptions-item>
            <el-descriptions-item label="IC正值占比">{{ (factorStore.icSummary.ic_positive_rate * 100).toFixed(1) }}%</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 因子值排名 -->
      <el-col :span="16">
        <el-card>
          <template #header><span>截面因子排名</span></template>
          <el-table :data="factorStore.factorValues" stripe max-height="400" size="small">
            <el-table-column prop="rank" label="排名" width="80" />
            <el-table-column prop="symbol" label="合约" width="180" />
            <el-table-column prop="factor_value" label="因子值" width="120">
              <template #default="{ row }">
                <span :style="{ color: row.factor_value > 0 ? '#ef232a' : '#14b143' }">
                  {{ row.factor_value?.toFixed(4) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- IC序列图 -->
        <el-card v-if="factorStore.icData.length" style="margin-top: 16px">
          <template #header><span>IC时序图</span></template>
          <v-chart :option="icOption" style="height: 300px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useFactorStore } from '@/stores'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const factorStore = useFactorStore()

const selectedFactor = ref('momentum')
const symbols = ref('SHFE.cu2608,SHFE.al2608,SHFE.zn2608,DCE.m2608,DCE.y2608,CZCE.SA608,CZCE.MA608')
const startDate = ref(new Date(Date.now() - 90 * 86400000))
const endDate = ref(new Date())
const window = ref(20)

const fmt = (d: Date) => d.toISOString().slice(0, 10)

const icOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: factorStore.icData.map((d) => d.date),
  },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'bar',
      data: factorStore.icData.map((d) => d.ic),
      itemStyle: {
        color: (params: any) => (params.value >= 0 ? '#ef232a' : '#14b143'),
      },
    },
  ],
  grid: { left: '10%', right: '5%', top: '10%', bottom: '15%' },
}))

async function computeFactor() {
  await factorStore.computeFactor({
    symbols: symbols.value,
    factorName: selectedFactor.value,
    startDate: fmt(startDate.value),
    endDate: fmt(endDate.value),
    window: window.value,
  })
}

async function computeIC() {
  await factorStore.computeIC({
    symbols: symbols.value,
    factorName: selectedFactor.value,
    startDate: fmt(startDate.value),
    endDate: fmt(endDate.value),
    window: window.value,
  })
}

onMounted(() => {
  factorStore.fetchFactorList()
})
</script>

<style scoped>
.factor-view {
  height: 100%;
}
</style>
