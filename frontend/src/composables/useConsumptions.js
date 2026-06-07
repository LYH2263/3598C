import { reactive, ref } from 'vue'
import http from '../utils/http'
import { categoryMap, formatMoney } from './useFormatters'

export function useConsumptions() {
  const consumptionFilters = reactive({
    category: '',
    start_date: '',
    end_date: ''
  })
  const consumptions = ref([])
  const consumptionStats = reactive({
    category_stats: [],
    daily_trend: []
  })

  async function loadConsumptions() {
    const params = {}
    if (consumptionFilters.category) params.category = consumptionFilters.category
    if (consumptionFilters.start_date) params.start_date = consumptionFilters.start_date
    if (consumptionFilters.end_date) params.end_date = consumptionFilters.end_date

    const { data } = await http.get('/billing/consumptions/', { params })
    consumptions.value = data
  }

  async function loadConsumptionStats() {
    const params = {}
    if (consumptionFilters.start_date) params.start_date = consumptionFilters.start_date
    if (consumptionFilters.end_date) params.end_date = consumptionFilters.end_date
    const { data } = await http.get('/billing/consumptions/stats/', { params })
    Object.assign(consumptionStats, data)
  }

  function consumeStatsForCategory() {
    return consumptionStats.category_stats.map((item) => ({
      label: categoryMap[item.category] || item.category,
      value: formatMoney(item.total_cost)
    }))
  }

  function consumeStatsForTrend() {
    return consumptionStats.daily_trend.map((item) => ({
      label: item.day,
      value: formatMoney(item.total_cost)
    }))
  }

  async function loadAll() {
    await Promise.all([loadConsumptions(), loadConsumptionStats()])
  }

  return {
    consumptionFilters,
    consumptions,
    consumptionStats,
    loadConsumptions,
    loadConsumptionStats,
    consumeStatsForCategory,
    consumeStatsForTrend,
    loadAll
  }
}
