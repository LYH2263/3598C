<script setup>
import { formatDateTime, formatMoney } from '../../composables/useFormatters'

const props = defineProps({
  orderForm: {
    type: Object,
    required: true
  },
  walletLogs: {
    type: Array,
    required: true
  },
  actionLoading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:orderForm', 'submit'])
</script>

<template>
  <div class="form-grid">
    <el-card class="section-card" shadow="never">
      <h3 class="section-title">快速提交充值订单</h3>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="充值金额（元）">
          <el-input-number
            v-model="props.orderForm.amount"
            :min="0"
            :precision="2"
            :step="10"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="充值渠道">
          <el-select v-model="props.orderForm.channel" style="width: 100%">
            <el-option label="支付宝" value="alipay" />
            <el-option label="微信支付" value="wechat" />
            <el-option label="银行卡" value="bank" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="props.orderForm.submit_remark" placeholder="请输入订单备注（可选）" />
        </el-form-item>
        <el-button
          type="primary"
          :loading="actionLoading"
          style="width: 100%"
          @click="$emit('submit')"
        >
          提交充值订单
        </el-button>
      </el-form>
    </el-card>

    <el-card class="section-card" shadow="never">
      <h3 class="section-title">余额变动日志</h3>
      <el-table :data="walletLogs.slice(0, 8)" stripe border empty-text="暂无余额日志">
        <el-table-column label="时间" min-width="165">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="change_type" label="类型" min-width="100" />
        <el-table-column label="变动" min-width="110">
          <template #default="{ row }">{{ formatMoney(row.amount_delta) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
