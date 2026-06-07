import { reactive, ref, computed } from 'vue'
import { ElNotification } from 'element-plus'
import http from '../utils/http'
import { useAuthStore } from '../stores/auth'

export function useAnnouncements(onDataChange) {
  const authStore = useAuthStore()
  const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')

  const announcements = ref([])

  const announcementForm = reactive({
    title: '',
    content: '',
    is_active: true
  })

  async function loadAnnouncements() {
    const params = isAdmin.value ? { include_inactive: true } : {}
    const { data } = await http.get('/notices/announcements/', { params })
    announcements.value = data
  }

  async function publishAnnouncement() {
    if (!announcementForm.title.trim() || !announcementForm.content.trim()) {
      ElNotification({ title: '发布失败', message: '请填写公告标题和内容。', type: 'warning' })
      return
    }

    try {
      const { data } = await http.post('/notices/announcements/', announcementForm)
      ElNotification({
        title: '公告已发布',
        message: `已推送 ${data.push_count} 位用户。`,
        type: 'success'
      })
      announcementForm.title = ''
      announcementForm.content = ''
      announcementForm.is_active = true
      await loadAnnouncements()
      if (onDataChange) await onDataChange()
    } catch (error) {
      // Error handled by http interceptor
    }
  }

  return {
    announcements,
    announcementForm,
    loadAnnouncements,
    publishAnnouncement
  }
}
