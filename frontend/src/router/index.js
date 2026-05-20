import { createRouter, createWebHistory } from 'vue-router'
import GreeksAnalysis from '../views/GreeksAnalysis.vue'
import VolatilitySurface from '../views/VolatilitySurface.vue'

const routes = [
  {
    path: '/',
    redirect: '/greeks'
  },
  {
    path: '/greeks',
    name: 'GreeksAnalysis',
    component: GreeksAnalysis
  },
  {
    path: '/volatility',
    name: 'VolatilitySurface',
    component: VolatilitySurface
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
