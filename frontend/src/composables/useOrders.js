import { reactive, ref, computed } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import http from '../utils/http'
import { useAuthStore } from '../stores/auth'

export function useOrders(onDataChange) {
  const authStore = useAuthStore()
  const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

  const orderForm = reactive({
    amount: null,
    channel: 'alipay',
    submit_remark: ''
  })

  const orderFilters = reactive({
    status: '',
    user_id: ''
  })

  const orders = ref([])

  async function loadOrders() {
    const params = {}
    if (orderFilters.status) params.status = orderFilters.status
    if (isAdmin.value && orderFilters.user_id) params.user_id = orderFilters.user_id
    const { data } = await http.get('/billing/recharge-orders/', { params })
    orders.value = data
  }

  async function submitRechargeOrder() {
    if (!orderForm.amount || Number(orderForm.amount) <= 0) {
      ElNotification({ title: '提交失败', message: '请输入有效金额。', type: 'warning' })
      return
    }

    try {
      await http.post('/billing/recharge-orders/', orderForm)
      ElNotification({ title: '订单已提交', message: '请等待管理员审核。', type: 'success' })
      orderForm.amount = null
      orderForm.submit_remark = ''
      if (onDataChange) await onDataChange()
    } catch (error) {
      // Error handled by http interceptor
    }
  }

  async function reviewOrder(order, action) {
    const result = await ElMessageBox.prompt(
      action === 'approved' ? '请输入通过备注（可选）' : '请输入驳回原因',
      action === 'approved' ? '通过订单' : '驳回订单',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入审核备注'
      }
    ).catch(() => null)

    if (!result) return

    try {
      await http.post(`/billing/recharge-orders/${order.id}/review/`, {
        action,
        review_remark: result.value || ''
      })
      ElNotification({ title: '审核完成', message: '订单状态已更新。', type: 'success' })
      if (onDataChange) await onDataChange()
    } catch (error) {
      // Error handled by http interceptor
    }
  }

  return {
    orderForm,
    orderFilters,
    orders,
    loadOrders,
    submitRechargeOrder,
    reviewOrder
  }
}
