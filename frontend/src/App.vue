<template>
  <el-container class="app-container">
    <el-aside width="200px" class="app-aside">
      <div class="logo">
        <h3>截面多空</h3>
        <p>交易系统</p>
      </div>
      <el-menu
        :default-active="currentRoute"
        router
        class="app-menu"
        background-color="#1d1e1f"
        text-color="#bfcbd9"
        active-text-color="#409eff"
      >
        <el-menu-item index="/market">
          <el-icon><DataBoard /></el-icon>
          <span>市场总览</span>
        </el-menu-item>
        <el-menu-item index="/factor">
          <el-icon><TrendCharts /></el-icon>
          <span>因子分析</span>
        </el-menu-item>
        <el-menu-item index="/portfolio">
          <el-icon><PieChart /></el-icon>
          <span>组合监控</span>
        </el-menu-item>
        <el-menu-item index="/backtest">
          <el-icon><DataLine /></el-icon>
          <span>回测面板</span>
        </el-menu-item>
        <el-menu-item index="/trade">
          <el-icon><SwitchButton /></el-icon>
          <span>交易控制</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-main class="app-main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentRoute = computed(() => route.path)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  height: 100%;
  font-family: 'Microsoft YaHei', sans-serif;
}

.app-container {
  height: 100vh;
}

.app-aside {
  background-color: #1d1e1f;
  overflow-y: auto;
}

.logo {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #333;
}

.logo h3 {
  color: #409eff;
  font-size: 18px;
  margin-bottom: 4px;
}

.logo p {
  color: #999;
  font-size: 12px;
}

.app-menu {
  border-right: none;
}

.app-main {
  background-color: #f0f2f5;
  padding: 20px;
  overflow-y: auto;
}
</style>
