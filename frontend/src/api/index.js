import axios from 'axios'

const API_BASE_URL = '/api'

export const api = {
  async getHealth() {
    const response = await axios.get(`${API_BASE_URL}/health`)
    return response.data
  },

  async getCrudeOilOptions() {
    const response = await axios.get(`${API_BASE_URL}/crude-oil/options`)
    return response.data
  },

  async calculateVix(data) {
    const response = await axios.post(`${API_BASE_URL}/vix/calculate`, data)
    return response.data
  },

  async getCrudeOilVix() {
    const response = await axios.get(`${API_BASE_URL}/vix/crude-oil`)
    return response.data
  },

  async getStrategies() {
    const response = await axios.get(`${API_BASE_URL}/strategies/list`)
    return response.data
  },

  async buildStrategy(data) {
    const response = await axios.post(`${API_BASE_URL}/strategies/build`, data)
    return response.data
  },

  async analyzeStrategy(data) {
    const response = await axios.post(`${API_BASE_URL}/strategies/analyze`, data)
    return response.data
  },

  async compareStrategies(data) {
    const response = await axios.post(`${API_BASE_URL}/strategies/compare`, data)
    return response.data
  },

  async calculateGreeks(data) {
    const response = await axios.post(`${API_BASE_URL}/risk/greeks`, data)
    return response.data
  }
}
