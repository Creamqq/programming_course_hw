<template>
  <div class="strategy-analysis">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card header="策略选择">
          <el-form :model="form" label-width="120px">
            <el-form-item label="选择策略">
              <el-select v-model="form.strategy_id" placeholder="请选择策略" @change="onStrategyChange">
                <el-option
                  v-for="strategy in strategies"
                  :key="strategy.id"
                  :label="strategy.name"
                  :value="strategy.id"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="标的物价格">
              <el-input-number v-model="form.params.underlying_price" :min="0" :step="10" />
            </el-form-item>
            
            <el-form-item label="到期天数">
              <el-input-number v-model="form.params.time_to_expiry" :min="1" :max="365" />
            </el-form-item>
            
            <el-form-item label="波动率">
              <el-slider v-model="form.params.volatility" :min="0.1" :max="0.8" :step="0.01" show-input />
            </el-form-item>
            
            <el-divider>策略参数</el-divider>
            
            <template v-if="form.strategy_id === 'short_straddle'">
              <el-form-item label="看涨期权权利金">
                <el-input-number v-model="form.params.call_premium" :min="0" :step="1" />
              </el-form-item>
              <el-form-item label="看跌期权权利金">
                <el-input-number v-model="form.params.put_premium" :min="0" :step="1" />
              </el-form-item>
            </template>
            
            <template v-if="form.strategy_id === 'short_strangle'">
              <el-form-item label="看涨执行价">
                <el-input-number v-model="form.params.call_strike" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="看跌执行价">
                <el-input-number v-model="form.params.put_strike" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="看涨权利金">
                <el-input-number v-model="form.params.call_premium" :min="0" :step="1" />
              </el-form-item>
              <el-form-item label="看跌权利金">
                <el-input-number v-model="form.params.put_premium" :min="0" :step="1" />
              </el-form-item>
            </template>
            
            <template v-if="form.strategy_id === 'iron_condor'">
              <el-form-item label="看跌低执行价">
                <el-input-number v-model="form.params.put_strike_low" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="看跌高执行价">
                <el-input-number v-model="form.params.put_strike_high" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="看涨低执行价">
                <el-input-number v-model="form.params.call_strike_low" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="看涨高执行价">
                <el-input-number v-model="form.params.call_strike_high" :min="0" :step="10" />
              </el-form-item>
            </template>
            
            <template v-if="form.strategy_id === 'calendar_spread'">
              <el-form-item label="执行价">
                <el-input-number v-model="form.params.strike" :min="0" :step="10" />
              </el-form-item>
              <el-form-item label="近月权利金">
                <el-input-number v-model="form.params.near_premium" :min="0" :step="1" />
              </el-form-item>
              <el-form-item label="远月权利金">
                <el-input-number v-model="form.params.far_premium" :min="0" :step="1" />
              </el-form-item>
            </template>
            
            <el-form-item>
              <el-button type="primary" @click="analyzeStrategy" :loading="loading">
                分析策略
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card header="分析结果">
          <div v-if="analysisResult" class="analysis-result">
            <el-row :gutter="20">
              <el-col :span="24">
                <h3>{{ analysisResult.strategy_name }}</h3>
                <el-divider />
              </el-col>
            </el-row>
            
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="stat-card">
                  <h3>最大盈利</h3>
                  <div class="value positive">{{ analysisResult.analysis.max_profit }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <h3>最大亏损</h3>
                  <div class="value negative">{{ analysisResult.analysis.max_loss }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <h3>盈亏比</h3>
                  <div class="value">{{ analysisResult.analysis.risk_reward_ratio }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="stat-card">
                  <h3>盈利概率</h3>
                  <div class="value">{{ analysisResult.monte_carlo.probability_of_profit }}%</div>
                </div>
              </el-col>
            </el-row>
            
            <el-divider />
            
            <el-row :gutter="20">
              <el-col :span="12">
                <h4>Greeks风险指标</h4>
                <el-table :data="getGreeksData()" border style="width: 100%">
                  <el-table-column prop="name" label="指标" width="100" />
                  <el-table-column prop="value" label="值" />
                  <el-table-column prop="description" label="说明" />
                </el-table>
              </el-col>
              
              <el-col :span="12">
                <h4>风险度量</h4>
                <el-table :data="getRiskData()" border style="width: 100%">
                  <el-table-column prop="name" label="指标" width="120" />
                  <el-table-column prop="value" label="值" />
                </el-table>
              </el-col>
            </el-row>
            
            <el-divider />
            
            <el-row>
              <el-col :span="24">
                <h4>损益曲线</h4>
                <div ref="pnlChart" style="width: 100%; height: 400px;"></div>
              </el-col>
            </el-row>
          </div>
          
          <el-empty v-else description="请选择策略并点击分析按钮" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive, onMounted, nextTick } from 'vue'
import { api } from '../api'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

export default {
  name: 'StrategyAnalysis',
  setup() {
    const loading = ref(false)
    const strategies = ref([])
    const analysisResult = ref(null)
    const pnlChart = ref(null)
    let chartInstance = null
    
    const form = reactive({
      strategy_id: 'short_straddle',
      params: {
        underlying_price: 500,
        time_to_expiry: 30,
        volatility: 0.25,
        call_premium: 15,
        put_premium: 12,
        call_strike: 520,
        put_strike: 480,
        put_strike_low: 460,
        put_strike_high: 480,
        call_strike_low: 520,
        call_strike_high: 540,
        put_premium_low: 3,
        put_premium_high: 6,
        call_premium_low: 8,
        call_premium_high: 4,
        strike: 500,
        near_premium: 10,
        far_premium: 18
      }
    })
    
    const loadStrategies = async () => {
      try {
        const response = await api.getStrategies()
        if (response.success) {
          strategies.value = response.strategies
        }
      } catch (error) {
        ElMessage.error('加载策略列表失败')
      }
    }
    
    const onStrategyChange = () => {
      analysisResult.value = null
    }
    
    const analyzeStrategy = async () => {
      loading.value = true
      try {
        const response = await api.analyzeStrategy({
          strategy_id: form.strategy_id,
          params: form.params
        })
        
        if (response.success) {
          analysisResult.value = response
          await nextTick()
          renderPnlChart()
          ElMessage.success('策略分析完成')
        } else {
          ElMessage.error(response.error)
        }
      } catch (error) {
        ElMessage.error('分析失败：' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const getGreeksData = () => {
      if (!analysisResult.value) return []
      const analysis = analysisResult.value.analysis
      return [
        { name: 'Delta', value: analysis.delta, description: '价格敏感度' },
        { name: 'Gamma', value: analysis.gamma, description: 'Delta变化率' },
        { name: 'Theta', value: analysis.theta, description: '时间衰减' },
        { name: 'Vega', value: analysis.vega, description: '波动率敏感度' }
      ]
    }
    
    const getRiskData = () => {
      if (!analysisResult.value) return []
      const mc = analysisResult.value.monte_carlo
      return [
        { name: 'VaR (95%)', value: mc.var_95 },
        { name: 'VaR (99%)', value: mc.var_99 },
        { name: '预期损失 (95%)', value: mc.expected_shortfall_95 },
        { name: '平均损益', value: mc.mean_pnl },
        { name: '损益标准差', value: mc.std_pnl }
      ]
    }
    
    const renderPnlChart = () => {
      if (!pnlChart.value || !analysisResult.value) return
      
      if (chartInstance) {
        chartInstance.dispose()
      }
      
      chartInstance = echarts.init(pnlChart.value)
      
      const { price_range, pnl } = analysisResult.value.pnl_profile
      
      const option = {
        title: {
          text: '到期日损益曲线',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            return `价格: ${params[0].value[0].toFixed(2)}<br/>损益: ${params[0].value[1].toFixed(2)}`
          }
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
        series: [{
          type: 'line',
          data: price_range.map((price, index) => [price, pnl[index]]),
          smooth: true,
          lineStyle: {
            width: 3
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
              { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
            ])
          },
          markLine: {
            data: [
              { yAxis: 0, name: '盈亏平衡', lineStyle: { color: '#999' } }
            ]
          }
        }]
      }
      
      chartInstance.setOption(option)
    }
    
    onMounted(() => {
      loadStrategies()
    })
    
    return {
      loading,
      strategies,
      form,
      analysisResult,
      pnlChart,
      onStrategyChange,
      analyzeStrategy,
      getGreeksData,
      getRiskData
    }
  }
}
</script>

<style scoped>
.strategy-analysis {
  padding: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
  margin-bottom: 20px;
}

.stat-card h3 {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 10px;
}

.stat-card .value {
  font-size: 28px;
  font-weight: bold;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}
</style>
