import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { BacktestResult, FactorValue, PortfolioPosition } from '@/types'
import { marketApi, factorApi, portfolioApi, backtestApi, tradeApi } from '@/api'

export const useMarketStore = defineStore('market', () => {
  const contracts = ref<string[]>([])
  const loading = ref(false)

  async function fetchContracts(exchange?: string, forceRefresh = false) {
    loading.value = true
    try {
      const res = await marketApi.getContracts(exchange, forceRefresh)
      contracts.value = res.data.contracts
    } finally {
      loading.value = false
    }
  }

  return { contracts, loading, fetchContracts }
})

export const useFactorStore = defineStore('factor', () => {
  const factorList = ref<Array<{ name: string; label: string; description: string }>>([])
  const factorValues = ref<FactorValue[]>([])
  const icData = ref<Array<{ date: string; ic: number }>>([])
  const icSummary = ref({ ic_mean: 0, ic_std: 0, ir: 0, ic_positive_rate: 0 })
  const loading = ref(false)

  async function fetchFactorList() {
    const res = await factorApi.getFactorList()
    factorList.value = res.data.factors
  }

  async function computeFactor(params: { symbols: string; factorName: string; startDate: string; endDate: string; window?: number }) {
    loading.value = true
    try {
      const res = await factorApi.computeFactor(
        params.symbols, params.factorName, params.startDate, params.endDate, params.window
      )
      factorValues.value = res.data.data
    } finally {
      loading.value = false
    }
  }

  async function computeIC(params: { symbols: string; factorName: string; startDate: string; endDate: string; window?: number; forwardPeriod?: number }) {
    loading.value = true
    try {
      const res = await factorApi.computeIC(
        params.symbols, params.factorName, params.startDate, params.endDate, params.window, params.forwardPeriod
      )
      icData.value = res.data.ic_series
      icSummary.value = res.data.summary
    } finally {
      loading.value = false
    }
  }

  return { factorList, factorValues, icData, icSummary, loading, fetchFactorList, computeFactor, computeIC }
})

export const usePortfolioStore = defineStore('portfolio', () => {
  const positions = ref<PortfolioPosition[]>([])
  const loading = ref(false)

  async function buildPortfolio(params: { symbols: string; factorName: string; startDate: string; endDate: string; longRatio?: number; shortRatio?: number }) {
    loading.value = true
    try {
      const res = await portfolioApi.buildPortfolio(
        params.symbols, params.factorName, params.startDate, params.endDate, params.longRatio, params.shortRatio
      )
      positions.value = res.data.portfolio
    } finally {
      loading.value = false
    }
  }

  async function fetchPositions() {
    const res = await portfolioApi.getPositions()
    positions.value = res.data.positions
  }

  return { positions, loading, buildPortfolio, fetchPositions }
})

export const useBacktestStore = defineStore('backtest', () => {
  const result = ref<BacktestResult | null>(null)
  const loading = ref(false)

  async function runBacktest(config: any) {
    loading.value = true
    try {
      const res = await backtestApi.runBacktest(config)
      result.value = res.data
    } finally {
      loading.value = false
    }
  }

  return { result, loading, runBacktest }
})

export const useTradeStore = defineStore('trade', () => {
  const isTrading = ref(false)

  async function startTrading() {
    await tradeApi.startTrading()
    isTrading.value = true
  }

  async function stopTrading() {
    await tradeApi.stopTrading()
    isTrading.value = false
  }

  async function fetchStatus() {
    const res = await tradeApi.getStatus()
    isTrading.value = res.data.is_trading
  }

  return { isTrading, startTrading, stopTrading, fetchStatus }
})
