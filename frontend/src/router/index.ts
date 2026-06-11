import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/market',
    },
    {
      path: '/market',
      name: 'Market',
      component: () => import('@/views/MarketView.vue'),
      meta: { title: '市场总览' },
    },
    {
      path: '/factor',
      name: 'Factor',
      component: () => import('@/views/FactorView.vue'),
      meta: { title: '因子分析' },
    },
    {
      path: '/portfolio',
      name: 'Portfolio',
      component: () => import('@/views/PortfolioView.vue'),
      meta: { title: '组合监控' },
    },
    {
      path: '/backtest',
      name: 'Backtest',
      component: () => import('@/views/BacktestView.vue'),
      meta: { title: '回测面板' },
    },
    {
      path: '/trade',
      name: 'Trade',
      component: () => import('@/views/TradeView.vue'),
      meta: { title: '交易控制' },
    },
  ],
})

router.beforeEach((to) => {
  document.title = `${to.meta.title || '截面多空交易系统'} - 截面多空交易系统`
})

export default router
