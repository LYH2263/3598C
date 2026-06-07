export const channelMap = {
  alipay: '支付宝',
  wechat: '微信支付',
  bank: '银行卡',
}

export const orderStatusMap = {
  pending: { label: '待审核', type: 'warning' },
  approved: { label: '已通过', type: 'success' },
  rejected: { label: '已驳回', type: 'danger' },
}

export const categoryMap = {
  water: '水费',
  electricity: '电费',
}

export function formatMoney(value) {
  const amount = Number(value ?? 0)
  if (Number.isNaN(amount)) return '0.00'
  return amount.toFixed(2)
}

export function formatDateTime(value) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
}

export function useFormatters() {
  return {
    channelMap,
    orderStatusMap,
    categoryMap,
    formatMoney,
    formatDateTime,
  }
}
