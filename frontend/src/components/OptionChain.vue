<template>
  <div class="option-chain">
    <el-card header="原油期权链数据">
      <el-form :inline="true">
        <el-form-item>
          <el-button type="primary" @click="loadOptionChain" :loading="loading">
            加载期权链
          </el-button>
          <el-button @click="refreshData" :loading="loading">
            刷新数据
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="optionData">
      <el-col :span="6">
        <div class="stat-card">
          <h3>标的物价格</h3>
          <div class="value">{{ optionData.underlying_price }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <h3>标的物代码</h3>
          <div class="value" style="font-size: 20px;">{{ optionData.underlying_symbol }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <h3>到期日</h3>
          <div class="value" style="font-size: 20px;">{{ optionData.expiry_date }}</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <h3>期权数量</h3>
          <div class="value">{{ optionData.options_chain.length }}</div>
        </div>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="optionData">
      <el-col :span="12">
        <el-card header="看涨期权">
          <el-table :data="callOptions" border style="width: 100%" max-height="500">
            <el-table-column prop="strike" label="执行价" width="80" fixed />
            <el-table-column prop="price" label="价格" width="80" />
            <el-table-column prop="implied_vol" label="隐含波动率" width="100">
              <template #default="scope">
                {{ (scope.row.implied_vol * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="delta" label="Delta" width="80" />
            <el-table-column prop="gamma" label="Gamma" width="80" />
            <el-table-column prop="theta" label="Theta" width="80" />
            <el-table-column prop="vega" label="Vega" width="80" />
            <el-table-column prop="volume" label="成交量" width="80" />
            <el-table-column prop="open_interest" label="持仓量" width="80" />
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card header="看跌期权">
          <el-table :data="putOptions" border style="width: 100%" max-height="500">
            <el-table-column prop="strike" label="执行价" width="80" fixed />
            <el-table-column prop="price" label="价格" width="80" />
            <el-table-column prop="implied_vol" label="隐含波动率" width="100">
              <template #default="scope">
                {{ (scope.row.implied_vol * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="delta" label="Delta" width="80" />
            <el-table-column prop="gamma" label="Gamma" width="80" />
            <el-table-column prop="theta" label="Theta" width="80" />
            <el-table-column prop="vega" label="Vega" width="80" />
            <el-table-column prop="volume" label="成交量" width="80" />
            <el-table-column prop="open_interest" label="持仓量" width="80" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;" v-if="optionData">
      <el-col :span="24">
        <el-card header="隐含波动率微笑">
          <div ref="volatilitySmileChart" style="width: 100%; height: 400px;"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-empty v-if="!optionData && !loading" description="请点击加载期权链按钮获取数据" style="margin-top: 50px;" />
  </div>
</template>

<script>
import { ref, computed, nextTick } from 'vue'
import { api } from '../api'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

export default {
  name: 'OptionChain',
  setup() {
    const loading = ref(false)
    const optionData = ref(null)
    const volatilitySmileChart = ref(null)
    let chartInstance = null
    
    const callOptions = computed(() => {
      if (!optionData.value) return []
      return optionData.value.options_chain.filter(opt => opt.type === 'call')
    })
    
    const putOptions = computed(() => {
      if (!optionData.value) return []
      return optionData.value.options_chain.filter(opt => opt.type === 'put')
    })
    
    const loadOptionChain = async () => {
      loading.value = true
      try {
        const response = await api.getCrudeOilOptions()
        
        if (response.success) {
          optionData.value = response.data
          await nextTick()
          renderVolatilitySmile()
          ElMessage.success('期权链数据加载成功')
        } else {
          ElMessage.error(response.error)
        }
      } catch (error) {
        ElMessage.error('加载失败：' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const refreshData = async () => {
      await loadOptionChain()
    }
    
    const renderVolatilitySmile = () => {
      if (!volatilitySmileChart.value || !optionData.value) return
      
      if (chartInstance) {
        chartInstance.dispose()
      }
      
      chartInstance = echarts.init(volatilitySmileChart.value)
      
      const calls = callOptions.value.sort((a, b) => a.strike - b.strike)
      const puts = putOptions.value.sort((a, b) => a.strike - b.strike)
      
      const option = {
        title: {
          text: '隐含波动率微笑曲线',
          left: 'center'
        },
        tooltip: {
          trigger: 'axis',
          formatter: function(params) {
            let result = `执行价: ${params[0].value[0]}<br/>`
            params.forEach(param => {
              result += `${param.seriesName}: ${(param.value[1] * 100).toFixed(1)}%<br/>`
            })
            return result
          }
        },
        legend: {
          data: ['看涨期权', '看跌期权'],
          top: 30
        },
        xAxis: {
          type: 'value',
          name: '执行价',
          nameLocation: 'middle',
          nameGap: 30
        },
        yAxis: {
          type: 'value',
          name: '隐含波动率',
          nameLocation: 'middle',
          nameGap: 40,
          axisLabel: {
            formatter: function(value) {
              return (value * 100).toFixed(0) + '%'
            }
          }
        },
        series: [
          {
            name: '看涨期权',
            type: 'line',
            data: calls.map(opt => [opt.strike, opt.implied_vol]),
            smooth: true,
            lineStyle: {
              width: 2,
              color: '#5470c6'
            }
          },
          {
            name: '看跌期权',
            type: 'line',
            data: puts.map(opt => [opt.strike, opt.implied_vol]),
            smooth: true,
            lineStyle: {
              width: 2,
              color: '#91cc75'
            }
          }
        ]
      }
      
      chartInstance.setOption(option)
    }
    
    return {
      loading,
      optionData,
      callOptions,
      putOptions,
      volatilitySmileChart,
      loadOptionChain,
      refreshData
    }
  }
}
</script>

<style scoped>
.option-chain {
  padding: 20px;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  border-radius: 10px;
  text-align: center;
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
</style>
