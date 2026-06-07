import { reactive } from 'vue'
import http from '../utils/http'

export function useDashboard() {
  const dashboard = reactive({
    wallet: { balance: '0.00', is_frozen: false, frozen_reason: '' },
    summary: { total_recharge: '0.00', total_consumption: '0.00', pending_recharge_orders: 0 },
    recent_recharges: [],
    recent_consumptions: []
  })

  async function loadDashboard() {
    const { data } = await http.get('/billing/dashboard/')
    Object.assign(dashboard, data)
  }

  return {
    dashboard,
    loadDashboard
  }
}
