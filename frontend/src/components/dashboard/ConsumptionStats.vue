<script setup>
import SimpleBarChart from '../SimpleBarChart.vue'
import { categoryMap, formatDateTime, formatMoney } from '../../composables/useFormatters'

defineProps({
  consumptionFilters: {
    type: Object,
    required: true,
  },
  consumptions: {
    type: Array,
    required: true,
  },
  consumptionStats: {
    type: Object,
    required: true,
  },
  consumeStatsForCategory: {
    type: Function,
    required: true,
  },
  consumeStatsForTrend: {
    type: Function,
    required: true,
  },
})

defineEmits(['update:consumptionFilters', 'search'])
</script>

<template>
  <el-row :gutter="12" style="margin-bottom: 12px">
    <el-col :span="6">
      <el-select
        v-model="consumptionFilters.category"
        style="width: 100%"
        placeholder="按类别筛选"
      >
        <el-option label="全部类别" value="" />
        <el-option label="水费" value="water" />
        <el-option label="电费" value="electricity" />
      </el-select>
    </el-col>
    <el-col :span="6">
      <el-date-picker
        v-model="consumptionFilters.start_date"
        value-format="YYYY-MM-DD"
        type="date"
        placeholder="开始日期"
        style="width: 100%"
      />
    </el-col>
    <el-col :span="6">
      <el-date-picker
        v-model="consumptionFilters.end_date"
        value-format="YYYY-MM-DD"
        type="date"
        placeholder="结束日期"
        style="width: 100%"
      />
    </el-col>
    <el-col :span="6">
      <el-button @click="$emit('search')">查询统计</el-button>
    </el-col>
  </el-row>

  <div class="form-grid" style="margin-bottom: 14px">
    <SimpleBarChart
      title="分类消费金额（元）"
      :items="consumeStatsForCategory()"
    />
    <SimpleBarChart
      title="每日消费趋势（元）"
      :items="consumeStatsForTrend()"
      color="#2b9f6c"
    />
  </div>

  <el-table :data="consumptions" stripe border empty-text="暂无消费记录">
    <el-table-column label="时间" min-width="165">
      <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
    </el-table-column>
    <el-table-column label="类别" min-width="100">
      <template #default="{ row }">{{ categoryMap[row.category] || row.category }}</template>
    </el-table-column>
    <el-table-column label="用量" min-width="90">
      <template #default="{ row }">{{ formatMoney(row.usage) }}</template>
    </el-table-column>
    <el-table-column label="金额" min-width="100">
      <template #default="{ row }">¥ {{ formatMoney(row.cost_amount) }}</template>
    </el-table-column>
    <el-table-column prop="user_name" label="用户" min-width="120" />
    <el-table-column prop="remark" label="备注" min-width="180" show-overflow-tooltip />
  </el-table>
</template>
