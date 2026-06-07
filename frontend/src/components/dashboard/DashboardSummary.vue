<script setup>
import { formatMoney } from '../composables/useFormatters'

defineProps({
  dashboard: {
    type: Object,
    required: true
  }
})
</script>

<template>
  <section class="summary-grid">
    <article class="summary-card">
      <div class="label">账户余额</div>
      <div class="value">¥ {{ formatMoney(dashboard.wallet.balance) }}</div>
      <div class="summary-note">
        {{ dashboard.wallet.is_frozen ? '账户已冻结' : '账户可正常使用' }}
      </div>
    </article>
    <article class="summary-card">
      <div class="label">累计充值</div>
      <div class="value">¥ {{ formatMoney(dashboard.summary.total_recharge) }}</div>
      <div class="summary-note">
        待审核充值单：{{ dashboard.summary.pending_recharge_orders || 0 }}
      </div>
    </article>
    <article class="summary-card">
      <div class="label">累计消费</div>
      <div class="value">¥ {{ formatMoney(dashboard.summary.total_consumption) }}</div>
      <div class="summary-note">消息中心支持公告与订单提醒</div>
    </article>
  </section>
</template>
