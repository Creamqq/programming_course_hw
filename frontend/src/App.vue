<template>
  <div class="app-container">
    <el-container>
      <el-header>
        <h1>期权VIX指数与策略分析系统</h1>
        <p class="subtitle">基于TqSdk的原油期权交易策略分析</p>
      </el-header>
      
      <el-main>
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="VIX指数计算" name="vix">
            <VixCalculator />
          </el-tab-pane>
          
          <el-tab-pane label="策略分析" name="strategies">
            <StrategyAnalysis />
          </el-tab-pane>
          
          <el-tab-pane label="策略对比" name="compare">
            <StrategyCompare />
          </el-tab-pane>
          
          <el-tab-pane label="期权链数据" name="options">
            <OptionChain />
          </el-tab-pane>
        </el-tabs>
      </el-main>
      
      <el-footer>
        <p>期权分析系统 © 2024 - 使用Python + TqSdk + Vue.js构建</p>
      </el-footer>
    </el-container>
  </div>
</template>

<script>
import { ref } from 'vue'
import VixCalculator from './components/VixCalculator.vue'
import StrategyAnalysis from './components/StrategyAnalysis.vue'
import StrategyCompare from './components/StrategyCompare.vue'
import OptionChain from './components/OptionChain.vue'

export default {
  name: 'App',
  components: {
    VixCalculator,
    StrategyAnalysis,
    StrategyCompare,
    OptionChain
  },
  setup() {
    const activeTab = ref('vix')
    
    return {
      activeTab
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.app-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.el-header {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 20px;
  margin-bottom: 20px;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.el-header h1 {
  color: #333;
  font-size: 28px;
  margin-bottom: 10px;
}

.subtitle {
  color: #666;
  font-size: 14px;
}

.el-main {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
  padding: 20px;
  min-height: 600px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.el-footer {
  text-align: center;
  padding: 20px;
  color: white;
  margin-top: 20px;
}

.el-tabs__content {
  padding: 20px;
}

.card-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
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
  font-size: 32px;
  font-weight: bold;
}

.positive {
  color: #67c23a;
}

.negative {
  color: #f56c6c;
}
</style>
