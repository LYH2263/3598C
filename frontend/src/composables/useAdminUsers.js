import { reactive, ref } from 'vue'
import { ElMessageBox, ElNotification } from 'element-plus'
import http from '../utils/http'

export function useAdminUsers(onWalletAction) {
  const adminUsers = ref([])
  const adminUserFilters = reactive({
    keyword: '',
    role: '',
    is_active: ''
  })

  async function loadAdminUsers() {
    const params = {}
    if (adminUserFilters.keyword) params.keyword = adminUserFilters.keyword
    if (adminUserFilters.role) params.role = adminUserFilters.role
    if (adminUserFilters.is_active) params.is_active = adminUserFilters.is_active
    const { data } = await http.get('/auth/admin/users/', { params })
    adminUsers.value = data
  }

  async function updateUserRole(row, role) {
    await http.patch(`/auth/admin/users/${row.id}/`, { role })
    ElNotification({ title: '角色已更新', message: '用户角色修改成功。', type: 'success' })
    await loadAdminUsers()
  }

  async function updateUserStatus(row, value) {
    await http.patch(`/auth/admin/users/${row.id}/`, { is_active: value })
    ElNotification({ title: '账号状态已更新', message: '启用状态修改成功。', type: 'success' })
    await loadAdminUsers()
  }

  async function walletAction(row, action) {
    const result = await ElMessageBox.prompt(
      action === 'freeze' ? '请输入冻结原因' : '请输入解冻备注（可选）',
      action === 'freeze' ? '冻结账户' : '解冻账户',
      {
        confirmButtonText: '提交',
        cancelButtonText: '取消',
        inputPlaceholder: '请输入说明'
      }
    ).catch(() => null)

    if (!result) return

    await http.post(`/billing/wallets/${row.id}/action/`, {
      action,
      reason: result.value || ''
    })
    ElNotification({
      title: action === 'freeze' ? '账户已冻结' : '账户已解冻',
      message: '钱包状态更新成功。',
      type: 'success'
    })
    await Promise.all([loadAdminUsers(), onWalletAction ? onWalletAction() : Promise.resolve()])
  }

  return {
    adminUsers,
    adminUserFilters,
    loadAdminUsers,
    updateUserRole,
    updateUserStatus,
    walletAction
  }
}
