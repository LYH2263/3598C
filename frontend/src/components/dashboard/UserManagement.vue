<script setup>
import { formatMoney } from '../../composables/useFormatters'

defineProps({
  adminUsers: {
    type: Array,
    required: true
  },
  adminUserFilters: {
    type: Object,
    required: true
  }
})

defineEmits(['update:adminUserFilters', 'search', 'updateRole', 'updateStatus', 'walletAction'])
</script>

<template>
  <el-row :gutter="12" style="margin-bottom: 12px">
    <el-col :span="8">
      <el-input v-model="adminUserFilters.keyword" placeholder="搜索用户名/学号/手机号" clearable />
    </el-col>
    <el-col :span="6">
      <el-select v-model="adminUserFilters.role" style="width: 100%" placeholder="角色筛选">
        <el-option label="全部角色" value="" />
        <el-option label="学生" value="student" />
        <el-option label="管理员" value="admin" />
      </el-select>
    </el-col>
    <el-col :span="6">
      <el-select v-model="adminUserFilters.is_active" style="width: 100%" placeholder="状态筛选">
        <el-option label="全部状态" value="" />
        <el-option label="启用" value="true" />
        <el-option label="禁用" value="false" />
      </el-select>
    </el-col>
    <el-col :span="4">
      <el-button @click="$emit('search')">查询用户</el-button>
    </el-col>
  </el-row>

  <el-table :data="adminUsers" stripe border empty-text="暂无用户数据">
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="username" label="用户名" min-width="120" />
    <el-table-column prop="email" label="邮箱" min-width="180" />
    <el-table-column label="角色" min-width="140">
      <template #default="{ row }">
        <el-select
          :model-value="row.profile.role"
          size="small"
          @change="(val) => $emit('updateRole', row, val)"
        >
          <el-option label="学生" value="student" />
          <el-option label="管理员" value="admin" />
        </el-select>
      </template>
    </el-table-column>
    <el-table-column label="启用" min-width="90">
      <template #default="{ row }">
        <el-switch
          :model-value="row.is_active"
          @change="(val) => $emit('updateStatus', row, val)"
        />
      </template>
    </el-table-column>
    <el-table-column label="钱包余额" min-width="110">
      <template #default="{ row }">¥ {{ formatMoney(row.balance) }}</template>
    </el-table-column>
    <el-table-column label="冻结状态" min-width="130">
      <template #default="{ row }">
        <el-tag :type="row.wallet_frozen ? 'danger' : 'success'" effect="plain">
          {{ row.wallet_frozen ? '已冻结' : '正常' }}
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column label="钱包操作" min-width="170" fixed="right">
      <template #default="{ row }">
        <el-space>
          <el-button
            size="small"
            type="danger"
            plain
            :disabled="row.wallet_frozen"
            @click="$emit('walletAction', row, 'freeze')"
          >
            冻结
          </el-button>
          <el-button
            size="small"
            type="success"
            plain
            :disabled="!row.wallet_frozen"
            @click="$emit('walletAction', row, 'unfreeze')"
          >
            解冻
          </el-button>
        </el-space>
      </template>
    </el-table-column>
  </el-table>
</template>
