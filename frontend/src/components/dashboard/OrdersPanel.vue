<script setup>
import { computed } from 'vue'
import {
  channelMap,
  orderStatusMap,
  formatMoney,
  formatDateTime
} from '../../composables/useFormatters'
import { useAuthStore } from '../../stores/auth'

defineProps({
  orders: {
    type: Array,
    required: true
  },
  orderFilters: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['update:orderFilters', 'search', 'review'])

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')
</script>

<template>
  <el-row :gutter="12" style="margin-bottom: 12px">
    <el-col :span="8">
      <el-select v-model="orderFilters.status" style="width: 100%" placeholder="按状态筛选">
        <el-option label="全部状态" value="" />
        <el-option label="待审核" value="pending" />
        <el-option label="已通过" value="approved" />
        <el-option label="已驳回" value="rejected" />
      </el-select>
    </el-col>
    <el-col v-if="isAdmin" :span="8">
      <el-input v-model="orderFilters.user_id" placeholder="按用户ID筛选" clearable />
    </el-col>
    <el-col :span="8">
      <el-button @click="$emit('search')">查询订单</el-button>
    </el-col>
  </el-row>

  <el-table :data="orders" stripe border empty-text="暂无订单记录">
    <el-table-column prop="order_no" label="订单号" min-width="180" />
    <el-table-column prop="user_name" label="用户" min-width="120" />
    <el-table-column label="金额" min-width="100">
      <template #default="{ row }">¥ {{ formatMoney(row.amount) }}</template>
    </el-table-column>
    <el-table-column label="渠道" min-width="100">
      <template #default="{ row }">{{ channelMap[row.channel] || row.channel }}</template>
    </el-table-column>
    <el-table-column label="状态" min-width="110">
      <template #default="{ row }">
        <el-tag :type="orderStatusMap[row.status]?.type || 'info'" effect="plain">
          {{ orderStatusMap[row.status]?.label || row.status }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="提交时间" min-width="165">
      <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
    </el-table-column>
    <el-table-column v-if="isAdmin" label="操作" min-width="180" fixed="right">
      <template #default="{ row }">
        <el-space>
          <el-button
            size="small"
            type="success"
            :disabled="row.status !== 'pending'"
            @click="$emit('review', row, 'approved')"
          >
            通过
          </el-button>
          <el-button
            size="small"
            type="danger"
            :disabled="row.status !== 'pending'"
            @click="$emit('review', row, 'rejected')"
          >
            驳回
          </el-button>
        </el-space>
      </template>
    </el-table-column>
  </el-table>
</template>
