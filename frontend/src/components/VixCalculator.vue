<template>
  <div class="vix-calculator">
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card header="VIX指数计算器">
          <el-form :model="form" label-width="120px">
            <el-form-item label="标的物价格">
              <el-input-number v-model="form.underlying_price" :min="0" :step="10" />
            </el-form-item>
            
            <el-form-item label="计算方式">
              <el-radio-group v-model="form.method">
                <el-radio value="simple">简化计算</el-radio>
                <el-radio value="full">完整计算</el-radio>
              </el-radio-group>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="calculateVix" :loading="loading">
                计算VIX指数
              </el-button>
              <el-button @click="getCrudeOilVix" :loading="loading">
                获取原油VIX
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card header="计算结果">
          <div v-if="vixResult" class="result-container">
            <div class="vix-value">
              <h2>VIX指数</h2>
              <div class="value" :class="getVixClass(vixResult.vix)">
                {{ vixResult.vix.toFixed(2) }}
              </div>
            </div>
            
            <el-divider />
            
            <el-descriptions :column="1" border>
              <el-descriptions-item label="标的物价格">
                {{ vixResult.underlying_price }}
              </el-descriptions-item>
              <el-descriptions-item label="标的物代码" v-if="vixResult.symbol">
                {{ vixResult.symbol }}
              </el-descriptions-item>
              <el-descriptions-item label="波动率水平">
                <el-tag :type="getVixTagType(vixResult.vix)">
                  {{ getVixLevel(vixResult.vix) }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
          
          <el-empty v-else description="请点击计算按钮获取VIX指数" />
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card header="VIX指数说明">
          <el-alert
            title="什么是VIX指数？"
            type="info"
            :closable="false"
            show-icon
          >
            <p>VIX指数（波动率指数）是由CBOE开发的，用于衡量市场对未来30天波动率的预期。</p>
            <p>VIX指数越高，表示市场预期未来波动越大；VIX指数越低，表示市场预期未来波动越小。</p>
          </el-alert>
          
          <el-divider />
          
          <h4>VIX指数水平解读：</h4>
          <el-table :data="vixLevels" border style="width: 100%">
            <el-table-column prop="range" label="VIX范围" width="150" />
            <el-table-column prop="level" label="波动率水平" width="150">
              <template #default="scope">
                <el-tag :type="scope.row.type">{{ scope.row.level }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="市场状态" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { api } from '../api'
import { ElMessage } from 'element-plus'

export default {
  name: 'VixCalculator',
  setup() {
    const loading = ref(false)
    const vixResult = ref(null)
    
    const form = reactive({
      underlying_price: 500,
      method: 'simple'
    })
    
    const vixLevels = [
      { range: '0-15', level: '低', type: 'success', description: '市场平静，预期波动较小' },
      { range: '15-20', level: '正常', type: 'info', description: '市场正常波动' },
      { range: '20-30', level: '偏高', type: 'warning', description: '市场存在一定不确定性' },
      { range: '30+', level: '高', type: 'danger', description: '市场恐慌，预期大幅波动' }
    ]
    
    const calculateVix = async () => {
      loading.value = true
      try {
        const response = await api.calculateVix({
          underlying_price: form.underlying_price,
          options: []
        })
        
        if (response.success) {
          vixResult.value = response
          ElMessage.success('VIX指数计算成功')
        } else {
          ElMessage.error(response.error)
        }
      } catch (error) {
        ElMessage.error('计算失败：' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const getCrudeOilVix = async () => {
      loading.value = true
      try {
        const response = await api.getCrudeOilVix()
        
        if (response.success) {
          vixResult.value = response
          ElMessage.success('原油VIX指数获取成功')
        } else {
          ElMessage.error(response.error)
        }
      } catch (error) {
        ElMessage.error('获取失败：' + error.message)
      } finally {
        loading.value = false
      }
    }
    
    const getVixClass = (vix) => {
      if (vix < 15) return 'low'
      if (vix < 20) return 'normal'
      if (vix < 30) return 'high'
      return 'very-high'
    }
    
    const getVixTagType = (vix) => {
      if (vix < 15) return 'success'
      if (vix < 20) return 'info'
      if (vix < 30) return 'warning'
      return 'danger'
    }
    
    const getVixLevel = (vix) => {
      if (vix < 15) return '低波动率'
      if (vix < 20) return '正常波动率'
      if (vix < 30) return '偏高波动率'
      return '高波动率'
    }
    
    return {
      loading,
      form,
      vixResult,
      vixLevels,
      calculateVix,
      getCrudeOilVix,
      getVixClass,
      getVixTagType,
      getVixLevel
    }
  }
}
</script>

<style scoped>
.vix-calculator {
  padding: 20px;
}

.result-container {
  text-align: center;
}

.vix-value {
  margin-bottom: 20px;
}

.vix-value h2 {
  color: #666;
  margin-bottom: 10px;
}

.vix-value .value {
  font-size: 48px;
  font-weight: bold;
}

.vix-value .value.low {
  color: #67c23a;
}

.vix-value .value.normal {
  color: #409eff;
}

.vix-value .value.high {
  color: #e6a23c;
}

.vix-value .value.very-high {
  color: #f56c6c;
}
</style>
