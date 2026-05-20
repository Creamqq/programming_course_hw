<template>
  <div id="app">
    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <h1>期权分析系统</h1>
        </div>
        <div class="header-right">
          <el-menu mode="horizontal" :default-active="$route.path" router>
            <el-menu-item index="/greeks">希腊字母分析</el-menu-item>
            <el-menu-item index="/volatility">波动率曲面</el-menu-item>
          </el-menu>
        </div>
      </el-header>
      <el-main>
        <router-view></router-view>
      </el-main>
    </el-container>
  </div>
</template>

<script>
export default {
  name: 'App'
}
</script>

<style>
#app {
  font-family: 'Microsoft YaHei', Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  color: #2c3e50;
}

.app-header {
  background-color: #409EFF;
  color: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  color: white;
}

.header-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.header-right .el-menu {
  background-color: transparent;
  border: none;
  height: 60px;
}

.header-right .el-menu-item {
  color: white !important;
  font-size: 16px;
  height: 60px;
  line-height: 60px;
}

.header-right .el-menu-item:hover,
.header-right .el-menu-item.is-active {
  background-color: rgba(255, 255, 255, 0.2) !important;
  border-bottom: 2px solid white !important;
}

.el-main {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: calc(100vh - 60px);
}
</style>
