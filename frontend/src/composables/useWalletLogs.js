import { ref } from 'vue'
import http from '../utils/http'

export function useWalletLogs() {
  const walletLogs = ref([])

  async function loadWalletLogs() {
    const { data } = await http.get('/billing/wallet-logs/')
    walletLogs.value = data
  }

  return {
    walletLogs,
    loadWalletLogs,
  }
}
