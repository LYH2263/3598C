<script setup>
import { computed } from 'vue'
import { formatDateTime } from '../../composables/useFormatters'
import { useAuthStore } from '../../stores/auth'

defineProps({
  announcements: {
    type: Array,
    required: true
  },
  announcementForm: {
    type: Object,
    required: true
  },
  notifications: {
    type: Object,
    required: true
  },
  actionLoading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['update:announcementForm', 'publish', 'markOneRead', 'markAllRead'])

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.profile?.role === 'admin')
</script>

<template>
  <template v-if="isAdmin">
    <el-form label-position="top" class="section-card" shadow="never" @submit.prevent>
      <el-form-item label="公告标题">
        <el-input v-model="announcementForm.title" placeholder="请输入公告标题" clearable />
      </el-form-item>
      <el-form-item label="公告内容">
        <el-input
          v-model="announcementForm.content"
          type="textarea"
          :rows="4"
          placeholder="请输入公告内容"
        />
      </el-form-item>
      <el-form-item>
        <el-switch
          v-model="announcementForm.is_active"
          active-text="立即生效"
          inactive-text="仅保存"
        />
      </el-form-item>
      <el-button type="primary" :loading="actionLoading" @click="$emit('publish')">
        发布公告并推送通知
      </el-button>
    </el-form>
  </template>

  <div class="table-grid" style="margin-top: 14px">
    <el-card class="section-card" shadow="never">
      <h3 class="section-title">公告历史</h3>
      <el-timeline>
        <el-timeline-item
          v-for="item in announcements"
          :key="item.id"
          :timestamp="formatDateTime(item.published_at)"
        >
          <h4 style="margin: 0 0 6px">{{ item.title }}</h4>
          <p style="margin: 0; color: var(--text-sub)">{{ item.content }}</p>
        </el-timeline-item>
      </el-timeline>
    </el-card>

    <el-card class="section-card" shadow="never">
      <h3 class="section-title">我的通知</h3>
      <el-button size="small" style="margin-bottom: 8px" @click="$emit('markAllRead')">
        全部标记已读
      </el-button>
      <el-table :data="notifications.items" stripe border empty-text="暂无通知">
        <el-table-column prop="title" label="标题" min-width="160" show-overflow-tooltip />
        <el-table-column label="类型" min-width="100">
          <template #default="{ row }">{{ row.notice_type_display }}</template>
        </el-table-column>
        <el-table-column label="时间" min-width="165">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_read ? 'info' : 'warning'" effect="plain">
              {{ row.is_read ? '已读' : '未读' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="90">
          <template #default="{ row }">
            <el-button size="small" :disabled="row.is_read" @click="$emit('markOneRead', row)">
              已读
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
