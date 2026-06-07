import { reactive } from 'vue'
import http from '../utils/http'

export function useNotifications() {
  const notifications = reactive({
    unread_count: 0,
    items: [],
  })

  async function loadNotifications() {
    const { data } = await http.get('/notices/notifications/')
    notifications.unread_count = data.unread_count
    notifications.items = data.items
  }

  async function markNotificationRead(notification) {
    await http.post('/notices/notifications/read/', { notification_id: notification.id })
    await loadNotifications()
  }

  async function markAllNotificationsRead() {
    await http.post('/notices/notifications/read/', { mark_all: true })
    await loadNotifications()
  }

  return {
    notifications,
    loadNotifications,
    markNotificationRead,
    markAllNotificationsRead,
  }
}
