<template>
  <div class="volatility-surface">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card class="control-card">
          <template #header>
            <div class="card-header">
              <span>波动率曲面控制</span>
            </div>
          </template>
          
          <el-form :model="surfaceForm" label-width="100px">
            <el-form-item label="合约代码">
              <el-input 
                v-model="surfaceForm.symbol" 
                placeholder="例如: SHFE.cu2610C126000"
                clearable
              >
              </el-input>
            </el-form-item>
            
            <el-form-item label="快速选择">
              <el-button-group>
                <el-button size="small" @click="selectCopper">铜期权</el-button>
                <el-button size="small" @click="selectGold">黄金期权</el-button>
              </el-button-group>
            </el-form-item>
            
            <el-form-item label="无风险利率(%)">
              <el-input-number v-model="surfaceForm.risk_free_rate" :min="0" :max="100" :precision="2" :step="0.1" style="width: 100%"></el-input-number>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="generateSurface" :loading="loading">生成波动率曲面</el-button>
            </el-form-item>
          </el-form>
          
          <el-divider></el-divider>
          
          <div v-if="surfaceData">
            <h4>曲面统计信息</h4>
            <p>数据点数: {{ surfaceData.original_strikes ? surfaceData.original_strikes.length : 0 }}</p>
            <p>行权价范围: {{ surfaceData.original_strikes ? Math.min(...surfaceData.original_strikes).toFixed(0) : 0 }} - {{ surfaceData.original_strikes ? Math.max(...surfaceData.original_strikes).toFixed(0) : 0 }}</p>
            <p>到期天数: {{ surfaceData.original_maturities ? Math.min(...surfaceData.original_maturities).toFixed(0) : 0 }} - {{ surfaceData.original_maturities ? Math.max(...surfaceData.original_maturities).toFixed(0) : 0 }}</p>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="18">
        <el-card class="surface-card">
          <template #header>
            <div class="card-header">
              <span>波动率曲面 3D 可视化</span>
              <div style="margin-left: auto;">
                <el-button-group>
                  <el-button :type="viewType === '3d' ? 'primary' : ''" @click="viewType = '3d'">3D视图</el-button>
                  <el-button :type="viewType === 'heatmap' ? 'primary' : ''" @click="viewType = 'heatmap'">热力图</el-button>
                </el-button-group>
              </div>
            </div>
          </template>
          
          <div ref="surfaceChart" style="width: 100%; height: 600px;"></div>
        </el-card>
        
        <el-card class="data-card" v-if="optionsTable.length > 0">
          <template #header>
            <div class="card-header">
              <span>期权数据表</span>
            </div>
          </template>
          
          <el-table :data="optionsTable" style="width: 100%" max-height="400">
            <el-table-column prop="symbol" label="合约代码" width="180"></el-table-column>
            <el-table-column prop="strike" label="行权价" width="100"></el-table-column>
            <el-table-column prop="type" label="类型" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.type === 'call' ? 'success' : 'danger'">
                  {{ scope.row.type === 'call' ? '看涨' : '看跌' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="market_price" label="市场价格" width="100"></el-table-column>
            <el-table-column prop="implied_volatility" label="隐含波动率(%)" width="140">
              <template #default="scope">
                {{ (scope.row.implied_volatility * 100).toFixed(2) }}%
              </template>
            </el-table-column>
            <el-table-column prop="delta" label="Delta" width="100">
              <template #default="scope">
                {{ scope.row.delta.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="gamma" label="Gamma" width="100">
              <template #default="scope">
                {{ scope.row.gamma.toFixed(6) }}
              </template>
            </el-table-column>
            <el-table-column prop="theta" label="Theta" width="100">
              <template #default="scope">
                {{ scope.row.theta.toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column prop="vega" label="Vega" width="100">
              <template #default="scope">
                {{ scope.row.vega.toFixed(4) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import 'echarts-gl'
import { ElMessage } from 'element-plus'

export default {
  name: 'VolatilitySurface',
  setup() {
    const surfaceForm = ref({
      symbol: 'SHFE.cu2610C126000',
      risk_free_rate: 3
    })
    
    const surfaceData = ref(null)
    const optionsTable = ref([])
    const loading = ref(false)
    const viewType = ref('3d')
    const surfaceChart = ref(null)
    let chartInstance = null
    
    const selectCopper = () => {
      surfaceForm.value.symbol = 'SHFE.cu2610C126000'
    }
    
    const selectGold = () => {
      surfaceForm.value.symbol = 'SHFE.au2607P1144'
    }
    
    const generateSurface = async () => {
      if (!surfaceForm.value.symbol) {
        ElMessage.warning('请输入合约代码')
        return
      }
      
      loading.value = true
      try {
        const chainResponse = await axios.post('/api/option-chain-greeks-by-symbol', {
          symbol: surfaceForm.value.symbol,
          risk_free_rate: surfaceForm.value.risk_free_rate / 100
        })
        
        if (chainResponse.data.success) {
          optionsTable.value = chainResponse.data.data.options
          
          const surfaceResponse = await axios.post('/api/volatility-surface-by-symbol', {
            symbol: surfaceForm.value.symbol
          })
          
          if (surfaceResponse.data.success) {
            surfaceData.value = surfaceResponse.data.data
            renderSurface()
            ElMessage.success('波动率曲面生成成功')
          } else {
            ElMessage.error(surfaceResponse.data.error || '波动率曲面生成失败')
          }
        } else {
          ElMessage.error(chainResponse.data.error || '获取期权链失败')
        }
      } catch (error) {
        ElMessage.error('生成失败: ' + (error.response?.data?.error || error.message))
      } finally {
        loading.value = false
      }
    }
    
    const renderSurface = () => {
      if (!surfaceChart.value || !surfaceData.value) return
      
      if (!chartInstance) {
        chartInstance = echarts.init(surfaceChart.value)
      }
      
      const data = surfaceData.value
      const strikes = data.strikes
      const maturities = data.maturities
      const ivs = data.implied_vols
      
      if (viewType.value === '3d') {
        render3DSurface(strikes, maturities, ivs)
      } else {
        renderHeatmap(strikes, maturities, ivs)
      }
    }
    
    const render3DSurface = (strikes, maturities, ivs) => {
      const surfaceData = []
      
      for (let i = 0; i < strikes.length; i++) {
        for (let j = 0; j < strikes[i].length; j++) {
          surfaceData.push([
            strikes[i][j],
            maturities[i][j],
            ivs[i][j] * 100
          ])
        }
      }
      
      const option = {
        title: {
          text: '波动率曲面',
          left: 'center',
          top: 10
        },
        tooltip: {
          trigger: 'item',
          formatter: function(params) {
            return `行权价: ${params.value[0].toFixed(0)}<br/>到期天数: ${params.value[1].toFixed(0)}<br/>隐含波动率: ${params.value[2].toFixed(2)}%`
          }
        },
        visualMap: {
          show: true,
          min: Math.min(...ivs.flat()) * 100,
          max: Math.max(...ivs.flat()) * 100,
          inRange: {
            color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8',
                    '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
          },
          dimension: 2,
          left: 10,
          bottom: 10
        },
        xAxis3D: {
          type: 'value',
          name: '行权价',
          nameTextStyle: { fontSize: 14 }
        },
        yAxis3D: {
          type: 'value',
          name: '到期天数',
          nameTextStyle: { fontSize: 14 }
        },
        zAxis3D: {
          type: 'value',
          name: '隐含波动率(%)',
          nameTextStyle: { fontSize: 14 }
        },
        grid3D: {
          boxWidth: 200,
          boxDepth: 80,
          viewControl: {
            autoRotate: true,
            autoRotateSpeed: 5,
            distance: 200
          },
          light: {
            main: {
              intensity: 1.2,
              shadow: true
            },
            ambient: {
              intensity: 0.3
            }
          }
        },
        series: [{
          type: 'surface',
          wireframe: {
            show: true
          },
          shading: 'color',
          data: surfaceData,
          itemStyle: {
            opacity: 0.8
          }
        }]
      }
      
      chartInstance.setOption(option)
    }
    
    const renderHeatmap = (strikes, maturities, ivs) => {
      const xData = strikes[0].map(v => v.toFixed(0))
      const yData = maturities.map(row => row[0].toFixed(0))
      
      const heatmapData = []
      for (let i = 0; i < ivs.length; i++) {
        for (let j = 0; j < ivs[i].length; j++) {
          heatmapData.push([j, i, (ivs[i][j] * 100).toFixed(2)])
        }
      }
      
      const option = {
        title: {
          text: '波动率热力图',
          left: 'center'
        },
        tooltip: {
          position: 'top',
          formatter: function(params) {
            return `行权价: ${xData[params.value[0]]}<br/>到期天数: ${yData[params.value[1]]}<br/>隐含波动率: ${params.value[2]}%`
          }
        },
        grid: {
          left: '10%',
          right: '10%',
          bottom: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: xData,
          name: '行权价',
          splitArea: { show: true },
          axisLabel: { rotate: 45 }
        },
        yAxis: {
          type: 'category',
          data: yData,
          name: '到期天数',
          splitArea: { show: true }
        },
        visualMap: {
          min: Math.min(...ivs.flat()) * 100,
          max: Math.max(...ivs.flat()) * 100,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '0%',
          inRange: {
            color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8',
                    '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026']
          }
        },
        series: [{
          name: '隐含波动率',
          type: 'heatmap',
          data: heatmapData,
          label: {
            show: true,
            formatter: function(params) {
              return params.value[2]
            }
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      }
      
      chartInstance.setOption(option)
    }
    
    watch(viewType, () => {
      if (surfaceData.value) {
        renderSurface()
      }
    })
    
    onMounted(() => {
      window.addEventListener('resize', () => {
        if (chartInstance) {
          chartInstance.resize()
        }
      })
    })
    
    return {
      surfaceForm,
      surfaceData,
      optionsTable,
      loading,
      viewType,
      surfaceChart,
      generateSurface,
      selectCopper,
      selectGold
    }
  }
}
</script>

<style scoped>
.volatility-surface {
  padding: 20px;
}

.control-card, .surface-card, .data-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  font-size: 18px;
  font-weight: bold;
}

h4 {
  margin: 10px 0;
  color: #409EFF;
}

p {
  margin: 5px 0;
  font-size: 14px;
  color: #606266;
}
</style>
