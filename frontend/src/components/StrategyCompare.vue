<template>
  <div class="strategy-compare">
    <el-card header="策略对比分析">
      <el-form :inline="true" :model="form">
        <el-form-item label="标的物价格">
          <el-input-number v-model="form.underlying_price" :min="0" :step="10" />
        </el-form-item>
        <el-form-item label="到期天数">
          <el-input-number v-model="form.time_to_expiry" :min="1" :max="365" />
        </el-form-item>
        <el-form-item label="波动率">
          <el-slider v-model="form.volatility" :min="0.1" :max="0.8" :step="0.01" show-input style="width: 200px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="compareStrategies" :loading="loading">
            对比策略
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="compareResult">
      <el-col :span="24">
        <el-card header="策略对比概览">
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in comparisonCards" :key="item.title">
              <div class="comparison-card">
                <h4>{{ item.title }}</h4>
                <el-tag :type="item.type" size="large">{{ item.strategy }}</el-tag>
                <p class="value">{{ item.value }}</p>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="compareResult">
      <el-col :span="24">
        <el-card header="策略详细对比">
          <el-table :data="strategiesTableData" border style="width: 100%">
            <el-table-column prop="name" label="策略名称" width="200" fixed />
            <el-table-column prop="max_profit" label="最大盈利" width="120">
              <template #default="scope">
                <span class="positive">{{ scope.row.max_profit }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="max_loss" label="最大亏损" width="120">
              <template #default="scope">
                <span class="negative">{{ scope.row.max_loss }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="risk_reward_ratio" label="盈亏比" width="100" />
            <el-table-column prop="probability_of_profit" label="盈利概率" width="120">
              <template #default="scope">
                <el-progress :percentage="scope.row.probability_of_profit" :color="getProgressColor(scope.row.probability_of_profit)" />
              </template>
            </el-table-column>
            <el-table-column prop="var_95" label="VaR(95%)" width="120">
              <template #default="scope">
                <span class="negative">{{ scope.row.var_95 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="delta" label="Delta" width="80" />
            <el-table-column prop="gamma" label="Gamma" width="80" />
            <el-table-column prop="theta" label="Theta" width="80" />
            <el-table-column prop="vega" label="Vega" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="compareResult">
      <el-col :span="24">
        <el-card header="损益曲线对比">
          <div ref="compareChart" style="width: 100%; height: 500px;"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="compareResult">
      <el-col :span="24">
        <el-card header="策略风险分析">
          <div v-for="strategy in compareResult.strategies" :key="strategy.name" class="strategy-risk-card">
            <h4>{{ strategy.name }}</h4>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="盈亏平衡点">
                    {{ strategy.analysis.breakeven_points.join(', ') || '无' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="净权利金">
                    {{ strategy.analysis.net_premium }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
              <el-col :span="12">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="预期损益">
                    {{ strategy.monte_carlo.mean_pnl }}
                  </el-descriptions-item>
                  <el-descriptions-item label="损益标准差">
                    {{ strategy.monte_carlo.std_pnl }}
                  </el-descriptions-item>
                </el-descriptions>
              </el-col>
            </el-row>
            <el-divider />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, nextTick } from 'vue'
import { api } from '../api'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

export default {
  name: 'StrategyCompare',
  setup() {
    const loading = ref(false)
    const compareResult = ref(null)
    const compareChart = ref(null)
    let chartInstance = null
    
    const form = reactive({
      underlying_price: 500,
      time_to_expiry: 30,
      volatility: 0.25
    })
    
    const compareStrategies = async () => {
      loading.value = true
      try {
        const response = await api.compareStrategies(form)
        
        if (response.success) {
          compareResult.value = response.data
          await nextTick()
          renderCompareChart()
          ElMessage.success('策略对比完成')
        } else {
          ElMessage.error(response.error)
        }
      } catch (error) {
        ElMessage.error('对比失败：' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const comparisonCards = ref([])
    
    const updateComparisonCards = () => {
      if (!compareResult.value) return
      
      const comparison = compareResult.value.comparison
      const strategies = compareResult.value.strategies
      
      cards = []
      
      const bestProfit = strategies.find(s => s.name === comparison.best_max_profit)
      if (bestProfit) {
        cards.push({
          title: '最大盈利最高',
          strategy: comparison.best_max_profit,
          value: bestProfit.analysis.max_profit,
          type: 'success'
        })
      }
      
      const lowestLoss = strategies.find(s => s.name === comparison.lowest_max_loss)
      if (lowestLoss) {
        cards.push({
          title: '最大亏损最小',
          strategy: comparison.lowest_max_loss,
          value: lowestLoss.analysis.max_loss,
          type: 'warning'
        })
      }
      
      const bestRatio = strategies.find(s => s.name === comparison.best_risk_reward)
      if (bestRatio) {
        cards.push({
          title: '盈亏比最佳',
          strategy: comparison.best_risk_reward,
          value: bestRatio.analysis.risk_reward_ratio,
          type: 'primary'
        })
      }
      
      const highestProb = strategies.find(s => s.name === comparison.highest_profit_probability)
      if (highestProb) {
        cards.push({
          title: '盈利概率最高',
          strategy: comparison.highest_profit_probability,
          value: highestProb.monte_carlo.probability_of_profit + '%',
          type: 'info'
        })
      }
      
      comparisonCards.value = cards
    }
    
    const strategiesTableData = ref([])
    
    const updateTableData = () => {
      if (!compareResult.value) return
      
      strategiesTableData.value = compareResult.value.strategies.map(s => ({
        name: s.name,
        max_profit: s.analysis.max_profit,
        max_loss: s.analysis.max_loss,
        risk_reward_ratio: s.analysis.risk_reward_ratio,
        probability_of_profit: s.monte_carlo.probability_of_profit,
        var_95: s.monte_carlo.var_95,
        delta: s.analysis.delta,
        gamma: s.analysis.gamma,
        theta: s.analysis.theta,
        vega: s.analysis.vega
      }))
    }
    
    const renderCompareChart = () => {
      if (!compareChart.value || !compareResult.value) return
      
      if (chartInstance) {
        chartInstance.dispose()
      }
      
      chartInstance = echarts.init(compareChart.value)
      
      const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666']
      const series = compareResult.value.strategies.map((strategy, index) => ({
        name: strategy.name,
        type: 'line',
        data: strategy.pnl_profile.price_range.map((price, i) => [
          price,
          strategy.pnl_profile.pnl[i]
        ]),
        smooth: true,
        lineStyle: {
          width: 2,
          color: colors[index % colors.length]
        }
      }))
      
      const option = {
        title: {
          text: '策略损益曲线对比',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            let result = `价格: ${params[0].value[0].toFixed(2)}<br/>`
            params.forEach(param => {
              result += `${param.seriesName}: ${param.value[1].toFixed(2)}<br/>`
            })
            return result
          }
        },
        legend: {
          data: compareResult.value.strategies.map(s => s.name),
          top: 30
        },
        xAxis: {
          type: 'value',
          name: '标的物价格',
          nameLocation: 'middle',
          nameGap: 30
        },
        yAxis: {
          type: 'value',
          name: '损益',
          nameLocation: 'middle',
          nameGap: 40
        },
        series: series
      }
      
      chartInstance.setOption(option)
      
      updateComparisonCards()
      updateTableData()
    }
    
    const getProgressColor = (percentage) => {
      if (percentage >= 70) return '#67c23a'
      if (percentage >= 50) return '#e6a23c'
      return '#f56c6c'
    }
    
    return {
      loading,
      form,
      compareResult,
      compareChart,
      comparisonCards,
      strategiesTableData,
      compareStrategies,
      getProgressColor
    }
  }
}
</script>

<style scoped>
.strategy-compare {
  padding: 20px;
}

.comparison-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
}

.comparison-card h4 {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 10px;
}

.comparison-card .value {
  font-size: 24px;
  font-weight: bold;
  margin-top: 10px;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}

.strategy-risk-card {
  margin-bottom: 20px;
}

.strategy-risk-card h4 {
  margin-bottom: 15px;
  color: #409eff;
}
</style>
