<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import DashboardSummary from '../components/dashboard/DashboardSummary.vue'
import StudentOverview from '../components/dashboard/StudentOverview.vue'
import OrdersPanel from '../components/dashboard/OrdersPanel.vue'
import UserManagement from '../components/dashboard/UserManagement.vue'
import ConsumptionStats from '../components/dashboard/ConsumptionStats.vue'
import AnnouncementsPanel from '../components/dashboard/AnnouncementsPanel.vue'

import { useAuthStore } from '../stores/auth'
import { useDashboard } from '../composables/useDashboard'
import { useOrders } from '../composables/useOrders'
import { useConsumptions } from '../composables/useConsumptions'
import { useWalletLogs } from '../composables/useWalletLogs'
import { useAnnouncements } from '../composables/useAnnouncements'
import { useNotifications } from '../composables/useNotifications'
import { useAdminUsers } from '../composables/useAdminUsers'

const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const actionLoading = ref(false)
const activeTab = ref('overview')

const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

const { dashboard, loadDashboard } = useDashboard()
const { walletLogs, loadWalletLogs } = useWalletLogs()
const { notifications, loadNotifications, markNotificationRead, markAllNotificationsRead } = useNotifications()

async function onOrdersChanged() {
  await Promise.all([loadOrders(), loadDashboard(), loadNotifications()])
}

async function onAnnouncementPublished() {
  await loadNotifications()
}

async function onWalletActionChanged() {
  await loadWalletLogs()
}

const {
  orderForm,
  orderFilters,
  orders,
  loadOrders,
  submitRechargeOrder,
  reviewOrder,
} = useOrders(onOrdersChanged)

const {
  consumptionFilters,
  consumptions,
  consumptionStats,
  loadConsumptions,
  loadConsumptionStats,
  consumeStatsForCategory,
  consumeStatsForTrend,
  loadAll: loadConsumptionAll,
} = useConsumptions()

const {
  announcements,
  announcementForm,
  loadAnnouncements,
  publishAnnouncement,
} = useAnnouncements(onAnnouncementPublished)

const {
  adminUsers,
  adminUserFilters,
  loadAdminUsers,
  updateUserRole,
  updateUserStatus,
  walletAction,
} = useAdminUsers(onWalletActionChanged)

async function handleSubmitRecharge() {
  actionLoading.value = true
  try {
    await submitRechargeOrder()
  } finally {
    actionLoading.value = false
  }
}

async function handlePublishAnnouncement() {
  actionLoading.value = true
  try {
    await publishAnnouncement()
  } finally {
    actionLoading.value = false
  }
}

async function refreshAll() {
  loading.value = true
  try {
    const tasks = [
      loadDashboard(),
      loadOrders(),
      loadConsumptions(),
      loadConsumptionStats(),
      loadWalletLogs(),
      loadAnnouncements(),
      loadNotifications(),
    ]
    if (isAdmin.value) tasks.push(loadAdminUsers())
    await Promise.all(tasks)
  } finally {
    loading.value = false
  }
}

async function logout() {
  authStore.clearSession()
  await router.push('/login')
}

onMounted(async () => {
  if (!authStore.user) {
    try {
      await authStore.fetchMe()
    } catch (_error) {
      authStore.clearSession()
      await router.push('/login')
      return
    }
  }

  activeTab.value = isAdmin.value ? 'orders' : 'overview'
  await refreshAll()
})
</script>

<template>
  <main class="page-shell animated-in">
    <section class="dashboard-wrap">
      <el-card class="section-card" shadow="never">
        <el-row justify="space-between" align="middle" :gutter="12">
          <el-col :xs="24" :sm="18">
            <h2 class="section-title">学生水电充值管理系统</h2>
            <p style="margin: 0; color: var(--text-sub)">
              当前身份：{{ isAdmin ? '管理员' : '学生' }} ｜ 未读通知：{{ notifications.unread_count }}
            </p>
          </el-col>
          <el-col :xs="24" :sm="6" style="text-align: right">
            <el-button style="margin-right: 8px" @click="refreshAll">刷新数据</el-button>
            <el-button type="danger" plain @click="logout">退出登录</el-button>
          </el-col>
        </el-row>
      </el-card>

      <el-skeleton :loading="loading" animated :rows="8">
        <template #template>
          <el-card class="section-card" shadow="never">
            <el-skeleton-item variant="h3" style="width: 40%" />
            <el-skeleton-item variant="text" style="width: 100%" />
            <el-skeleton-item variant="text" style="width: 100%" />
          </el-card>
        </template>

        <template #default>
          <DashboardSummary :dashboard="dashboard" />

          <el-card class="section-card" shadow="never">
            <el-tabs v-model="activeTab">
              <el-tab-pane v-if="!isAdmin" label="总览" name="overview">
                <StudentOverview
                  :order-form="orderForm"
                  :wallet-logs="walletLogs"
                  :action-loading="actionLoading"
                  @submit="handleSubmitRecharge"
                />
              </el-tab-pane>

              <el-tab-pane :label="isAdmin ? '订单审核' : '充值订单'" name="orders">
                <OrdersPanel
                  :orders="orders"
                  :order-filters="orderFilters"
                  @search="loadOrders"
                  @review="reviewOrder"
                />
              </el-tab-pane>

              <el-tab-pane v-if="isAdmin" label="用户管理" name="users">
                <UserManagement
                  :admin-users="adminUsers"
                  :admin-user-filters="adminUserFilters"
                  @search="loadAdminUsers"
                  @update-role="updateUserRole"
                  @update-status="updateUserStatus"
                  @wallet-action="walletAction"
                />
              </el-tab-pane>

              <el-tab-pane label="消费统计" name="consumptions">
                <ConsumptionStats
                  :consumption-filters="consumptionFilters"
                  :consumptions="consumptions"
                  :consumption-stats="consumptionStats"
                  :consume-stats-for-category="consumeStatsForCategory"
                  :consume-stats-for-trend="consumeStatsForTrend"
                  @search="loadConsumptionAll"
                />
              </el-tab-pane>

              <el-tab-pane :label="isAdmin ? '公告发布' : '公告通知'" name="announcements">
                <AnnouncementsPanel
                  :announcements="announcements"
                  :announcement-form="announcementForm"
                  :notifications="notifications"
                  :action-loading="actionLoading"
                  @publish="handlePublishAnnouncement"
                  @mark-one-read="markNotificationRead"
                  @mark-all-read="markAllNotificationsRead"
                />
              </el-tab-pane>
            </el-tabs>
          </el-card>
        </template>
      </el-skeleton>
    </section>
  </main>
</template>
