<template>
  <div class="greeks-analysis">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card class="input-card">
          <template #header>
            <div class="card-header">
              <span>期权合约查询</span>
            </div>
          </template>
          
          <el-form :model="optionForm" label-width="120px">
            <el-form-item label="合约代码">
              <el-input 
                v-model="optionForm.symbol" 
                placeholder="例如: SHFE.cu2610C126000"
                clearable
              >
                <template #append>
                  <el-button @click="queryOption">查询</el-button>
                </template>
              </el-input>
            </el-form-item>
            
            <el-form-item label="快速选择">
              <el-button-group>
                <el-button size="small" @click="selectCopper">铜期权</el-button>
                <el-button size="small" @click="selectGold">黄金期权</el-button>
              </el-button-group>
            </el-form-item>
            
            <el-form-item label="无风险利率(%)">
              <el-input-number v-model="optionForm.risk_free_rate" :min="0" :max="100" :precision="2" :step="0.1" style="width: 100%"></el-input-number>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="calculateGreeks" :loading="loading">计算希腊字母</el-button>
            </el-form-item>
          </el-form>
          
          <el-divider></el-divider>
          
          <div v-if="optionInfo" class="option-info">
            <h4>期权信息</h4>
            <p><strong>合约代码:</strong> {{ optionInfo.symbol }}</p>
            <p><strong>最新价:</strong> {{ optionInfo.last_price }}</p>
            <p><strong>行权价:</strong> {{ optionInfo.strike }}</p>
            <p><strong>标的价格:</strong> {{ optionInfo.underlying_price }}</p>
            <p><strong>买一价:</strong> {{ optionInfo.bid_price }}</p>
            <p><strong>卖一价:</strong> {{ optionInfo.ask_price }}</p>
            <p><strong>成交量:</strong> {{ optionInfo.volume }}</p>
            <p><strong>持仓量:</strong> {{ optionInfo.open_interest }}</p>
            <p><strong>到期天数:</strong> {{ optionInfo.days_to_expiry || '未知' }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="16">
        <el-card class="result-card" v-if="greeksResult">
          <template #header>
            <div class="card-header">
              <span>希腊字母结果</span>
            </div>
          </template>
          
          <el-row :gutter="20">
            <el-col :span="8" v-for="(value, key) in greeksDisplay" :key="key">
              <div class="greek-item">
                <div class="greek-name">{{ value.name }}</div>
                <div class="greek-value">{{ value.value }}</div>
                <div class="greek-desc">{{ value.desc }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
        
        <el-card class="chart-card" v-if="sensitivityData">
          <template #header>
            <div class="card-header">
              <span>希腊字母敏感性分析</span>
              <el-select v-model="sensitivityParam" @change="updateSensitivityChart" style="width: 200px; margin-left: 20px;">
                <el-option label="标的价格" value="underlying_price"></el-option>
                <el-option label="波动率" value="volatility"></el-option>
                <el-option label="行权价" value="strike"></el-option>
              </el-select>
            </div>
          </template>
          
          <div ref="sensitivityChart" style="width: 100%; height: 400px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

export default {
  name: 'GreeksAnalysis',
  setup() {
    const optionForm = ref({
      symbol: 'SHFE.cu2610C126000',
      risk_free_rate: 3
    })
    
    const optionInfo = ref(null)
    const greeksResult = ref(null)
    const loading = ref(false)
    const sensitivityData = ref(null)
    const sensitivityParam = ref('underlying_price')
    const sensitivityChart = ref(null)
    let chartInstance = null
    
    const greeksDisplay = ref({})
    
    const selectCopper = () => {
      optionForm.value.symbol = 'SHFE.cu2610C126000'
    }
    
    const selectGold = () => {
      optionForm.value.symbol = 'SHFE.au2607P1144'
    }
    
    const queryOption = async () => {
      if (!optionForm.value.symbol) {
        ElMessage.warning('请输入合约代码')
        return
      }
      
      try {
        const response = await axios.get(`/api/option-info/${encodeURIComponent(optionForm.value.symbol)}`)
        
        if (response.data.success) {
          optionInfo.value = response.data.data
          ElMessage.success('查询成功')
        } else {
          ElMessage.error(response.data.error || '查询失败')
        }
      } catch (error) {
        ElMessage.error('查询失败: ' + (error.response?.data?.error || error.message))
      }
    }
    
    const calculateGreeks = async () => {
      if (!optionForm.value.symbol) {
        ElMessage.warning('请输入合约代码')
        return
      }
      
      loading.value = true
      try {
        const response = await axios.post('/api/calculate-greeks-by-symbol', {
          symbol: optionForm.value.symbol,
          risk_free_rate: optionForm.value.risk_free_rate / 100
        })
        
        if (response.data.success) {
          greeksResult.value = response.data.data
          updateGreeksDisplay()
          await calculateSensitivity()
          ElMessage.success('计算成功')
        } else {
          ElMessage.error(response.data.error || '计算失败')
        }
      } catch (error) {
        ElMessage.error('计算失败: ' + (error.response?.data?.error || error.message))
      } finally {
        loading.value = false
      }
    }
    
    const updateGreeksDisplay = () => {
      const greeks = greeksResult.value
      greeksDisplay.value = {
        symbol: {
          name: '合约代码',
          value: greeks.symbol,
          desc: '期权合约完整代码'
        },
        days_to_expiry: {
          name: '到期天数',
          value: greeks.days_to_expiry || '未知',
          desc: '距离到期日的天数'
        },
        delta: {
          name: 'Delta (δ)',
          value: greeks.delta.toFixed(4),
          desc: '标的价格变动1单位，期权价格变动量'
        },
        gamma: {
          name: 'Gamma (γ)',
          value: greeks.gamma.toFixed(6),
          desc: '标的价格变动1单位，Delta变动量'
        },
        theta: {
          name: 'Theta (θ)',
          value: greeks.theta.toFixed(4),
          desc: '每过一天，期权价格变动量'
        },
        vega: {
          name: 'Vega (ν)',
          value: greeks.vega.toFixed(4),
          desc: '波动率变动1%，期权价格变动量'
        },
        rho: {
          name: 'Rho (ρ)',
          value: greeks.rho.toFixed(4),
          desc: '利率变动1%，期权价格变动量'
        },
        price: {
          name: '理论价格',
          value: greeks.price.toFixed(2),
          desc: 'Black-Scholes模型定价'
        }
      }
      
      if (greeks.implied_volatility) {
        greeksDisplay.value.iv = {
          name: '隐含波动率',
          value: (greeks.implied_volatility * 100).toFixed(2) + '%',
          desc: '根据市场价格反推的波动率'
        }
      }
    }
    
    const calculateSensitivity = async () => {
      try {
        const response = await axios.post('/api/greeks-sensitivity', {
          symbol: optionForm.value.symbol,
          parameter: sensitivityParam.value
        })
        
        if (response.data.success) {
          sensitivityData.value = response.data.data
          renderSensitivityChart()
        }
      } catch (error) {
        console.error('敏感性分析失败:', error)
      }
    }
    
    const renderSensitivityChart = () => {
      if (!sensitivityChart.value || !sensitivityData.value) return
      
      if (!chartInstance) {
        chartInstance = echarts.init(sensitivityChart.value)
      }
      
      const data = sensitivityData.value
      const series = []
      const colors = ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de']
      const greekNames = ['delta', 'gamma', 'theta', 'vega', 'rho']
      
      greekNames.forEach((name, index) => {
        series.push({
          name: name.charAt(0).toUpperCase() + name.slice(1),
          type: 'line',
          data: data.greeks[name],
          smooth: true,
          lineStyle: { width: 2 },
          itemStyle: { color: colors[index] }
        })
      })
      
      const option = {
        title: {
          text: '希腊字母敏感性分析',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data: greekNames.map(n => n.charAt(0).toUpperCase() + n.slice(1)),
          top: 30
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: data.parameter_values.map(v => v.toFixed(2)),
          name: getParameterName(data.parameter_name)
        },
        yAxis: {
          type: 'value',
          name: '希腊字母值'
        },
        series: series
      }
      
      chartInstance.setOption(option)
    }
    
    const getParameterName = (param) => {
      const names = {
        'underlying_price': '标的价格',
        'volatility': '波动率',
        'strike': '行权价'
      }
      return names[param] || param
    }
    
    const updateSensitivityChart = () => {
      calculateSensitivity()
    }
    
    onMounted(() => {
      window.addEventListener('resize', () => {
        if (chartInstance) {
          chartInstance.resize()
        }
      })
    })
    
    return {
      optionForm,
      optionInfo,
      greeksResult,
      greeksDisplay,
      loading,
      sensitivityData,
      sensitivityParam,
      sensitivityChart,
      queryOption,
      calculateGreeks,
      updateSensitivityChart,
      selectCopper,
      selectGold
    }
  }
}
</script>

<style scoped>
.greeks-analysis {
  padding: 20px;
}

.input-card, .result-card, .chart-card {
  margin-bottom: 20px;
}

.card-header {
  font-size: 18px;
  font-weight: bold;
}

.greek-item {
  text-align: center;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  margin-bottom: 15px;
}

.greek-name {
  font-size: 16px;
  font-weight: bold;
  color: #409EFF;
  margin-bottom: 10px;
}

.greek-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 10px;
}

.greek-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}

.option-info {
  margin-top: 20px;
}

.option-info h4 {
  margin-bottom: 15px;
  color: #409EFF;
}

.option-info p {
  margin: 8px 0;
  font-size: 14px;
  color: #606266;
}
</style>
