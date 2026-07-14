<template>
  <view class="page">
    <view class="status-bar"></view>
    <view class="nav-bar">
      <view class="nav-bar-title">下载任务</view>
      <view v-if="tasks.length > 0" class="nav-count">
        <text>{{ tasks.length }} 个任务</text>
      </view>
    </view>

    <scroll-view scroll-y class="content" :style="{ top: '88px' }" @refresherrefresh="onRefresh" :refresher-enabled="true" :refresher-triggered="refreshing">
      <!-- 空状态 -->
      <view v-if="tasks.length === 0" class="empty-state">
        <text class="empty-icon">📦</text>
        <text class="empty-title">还没有下载任务</text>
        <text class="empty-sub">在「下载」页面粘贴链接开始</text>
        <view class="empty-btn" @tap="goToDownload">去下载</view>
      </view>

      <!-- 任务列表 -->
      <view v-else class="task-list">
        <view
          v-for="task in tasks"
          :key="task.task_id"
          class="task-card"
          :class="'card-' + task.status"
        >
          <!-- 卡片头部 -->
          <view class="card-header">
            <image
              v-if="task.thumbnail"
              class="task-thumb"
              :src="task.thumbnail"
              mode="aspectFill"
            />
            <view v-else class="task-thumb-placeholder">
              <text>🎬</text>
            </view>

            <view class="task-info">
              <text class="task-title">{{ task.title || task.url }}</text>
              <view class="task-meta">
                <view class="platform-tag" :style="{ background: getColor(task.platform) + '22', color: getColor(task.platform) }">
                  <text>{{ task.platform }}</text>
                </view>
                <text v-if="task.author" class="meta-item">👤 {{ task.author }}</text>
                <text v-if="task.duration" class="meta-item">⏱ {{ task.duration }}</text>
              </view>
              <view class="task-meta-row2">
                <view v-if="task.watermark_free" class="nowm-tag">
                  <text>✓ 无水印</text>
                </view>
                <view class="status-badge" :class="'badge-' + task.status">
                  <view v-if="isActive(task.status)" class="mini-spinner"></view>
                  <text>{{ getStatusText(task.status) }}</text>
                </view>
              </view>
            </view>
          </view>

          <!-- 进度条 -->
          <view v-if="isActive(task.status) || task.status === 'completed'" class="progress-section">
            <view class="progress-bar">
              <view
                class="progress-fill"
                :class="task.status"
                :style="{ width: task.progress + '%' }"
              ></view>
            </view>
            <text class="progress-text">{{ Math.round(task.progress) }}%</text>
          </view>

          <!-- 进度详情 -->
          <view v-if="isActive(task.status)" class="progress-detail">
            <text v-if="task.speed">⚡ {{ task.speed }}</text>
            <text v-if="task.eta">⏳ {{ task.eta }}</text>
            <text v-if="task.file_size_str">📦 {{ task.file_size_str }}</text>
          </view>

          <!-- 错误信息 -->
          <view v-if="task.status === 'failed' && task.error" class="error-box">
            <text>❌ {{ task.error }}</text>
          </view>

          <!-- 操作按钮 -->
          <view v-if="task.status === 'completed'" class="card-actions">
            <view class="action-btn" @tap="handleSave(task)">
              <text>💾</text>
              <text>保存</text>
            </view>
            <view class="action-btn" @tap="handleWatermark(task)">
              <text>✂️</text>
              <text>去水印</text>
            </view>
            <view class="action-btn action-delete" @tap="handleDelete(task)">
              <text>🗑</text>
              <text>删除</text>
            </view>
          </view>

          <view v-else-if="task.status === 'failed'" class="card-actions">
            <view class="action-btn action-delete" @tap="handleDelete(task)">
              <text>🗑</text>
              <text>删除</text>
            </view>
          </view>
        </view>

        <view style="height: 120rpx;"></view>
      </view>
    </scroll-view>
  </view>
</template>

<script>
import api from '@/utils/api.js'
import config from '@/utils/config.js'

export default {
  data() {
    return {
      tasks: [],
      refreshing: false,
      pollTimer: null,
    }
  },

  onLoad() {
    this.loadTasks()
  },

  onShow() {
    this.loadTasks()
    this.startPolling()
  },

  onHide() {
    this.stopPolling()
  },

  onUnload() {
    this.stopPolling()
  },

  methods: {
    isActive(status) {
      return ['pending', 'analyzing', 'downloading', 'processing'].includes(status)
    },

    async loadTasks() {
      try {
        const res = await api.getTasks()
        this.tasks = res.tasks || []
      } catch (e) {
        api.toast('加载失败', 'error')
      }
    },

    startPolling() {
      this.stopPolling()
      this.pollTimer = setInterval(() => {
        const hasActive = this.tasks.some(t => this.isActive(t.status))
        if (hasActive) {
          this.loadTasks()
        } else {
          this.stopPolling()
        }
      }, config.POLL_INTERVAL)
    },

    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },

    async onRefresh() {
      this.refreshing = true
      await this.loadTasks()
      this.refreshing = false
    },

    async handleSave(task) {
      uni.showLoading({ title: '下载中...' })
      try {
        const result = await api.downloadFile(task.task_id)
        uni.hideLoading()
        if (result.saved) {
          api.toast('已保存到相册', 'success')
        } else {
          api.toast('已下载到临时目录', 'none')
        }
      } catch (e) {
        uni.hideLoading()
        api.toast(e.error || '保存失败', 'error')
      }
    },

    handleWatermark(task) {
      uni.navigateTo({
        url: `/pages/watermark/watermark?taskId=${task.task_id}&title=${encodeURIComponent(task.title || '')}`,
      })
    },

    async handleDelete(task) {
      uni.showModal({
        title: '确认删除',
        content: '删除任务及其视频文件？',
        success: async (res) => {
          if (res.confirm) {
            try {
              await api.deleteTask(task.task_id)
              this.tasks = this.tasks.filter(t => t.task_id !== task.task_id)
              api.toast('已删除', 'none')
            } catch (e) {
              api.toast('删除失败', 'error')
            }
          }
        },
      })
    },

    goToDownload() {
      uni.switchTab({ url: '/pages/index/index' })
    },

    getColor(name) {
      return config.PLATFORM_COLORS[name] || '#5A6378'
    },

    getStatusText(status) {
      return config.STATUS_TEXT[status] || status
    },
  },
}
</script>

<style scoped>
.page {
  min-height: 100vh;
  background: #0a0e1a;
}

.nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32rpx;
  height: 88rpx;
}

.nav-count text {
  font-size: 24rpx;
  color: #5a6378;
}

.content {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0 32rpx;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 120rpx 40rpx;
}

.empty-icon {
  font-size: 80rpx;
  opacity: 0.2;
}

.empty-title {
  font-size: 30rpx;
  color: #8892b0;
  margin-top: 24rpx;
}

.empty-sub {
  font-size: 24rpx;
  color: #5a6378;
  margin-top: 8rpx;
}

.empty-btn {
  margin-top: 32rpx;
  padding: 20rpx 48rpx;
  background: linear-gradient(135deg, #6c7cff, #818cf8);
  border-radius: 16rpx;
  font-size: 28rpx;
  color: #fff;
  font-weight: 600;
}

/* 任务卡片 */
.task-list {
  padding-top: 16rpx;
}

.task-card {
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 20rpx;
}

.card-completed {
  border-color: rgba(52, 211, 153, 0.2);
}

.card-failed {
  border-color: rgba(248, 113, 113, 0.2);
}

.card-header {
  display: flex;
  gap: 20rpx;
  margin-bottom: 20rpx;
}

.task-thumb {
  width: 120rpx;
  height: 120rpx;
  border-radius: 16rpx;
  flex-shrink: 0;
  background: #0a0e1a;
}

.task-thumb-placeholder {
  width: 120rpx;
  height: 120rpx;
  border-radius: 16rpx;
  flex-shrink: 0;
  background: rgba(108, 124, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 48rpx;
}

.task-info {
  flex: 1;
  min-width: 0;
}

.task-title {
  font-size: 26rpx;
  color: #e8edf5;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.4;
}

.task-meta {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 10rpx;
  flex-wrap: wrap;
}

.platform-tag {
  padding: 4rpx 14rpx;
  border-radius: 100rpx;
}

.platform-tag text {
  font-size: 20rpx;
  font-weight: 500;
}

.meta-item {
  font-size: 22rpx;
  color: #5a6378;
}

.task-meta-row2 {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 8rpx;
}

.nowm-tag {
  padding: 2rpx 10rpx;
  background: rgba(52, 211, 153, 0.1);
  border-radius: 100rpx;
}

.nowm-tag text {
  font-size: 18rpx;
  color: #34d399;
  font-weight: 500;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6rpx;
  padding: 2rpx 12rpx;
  border-radius: 100rpx;
}

.status-badge text {
  font-size: 18rpx;
  font-weight: 600;
}

.badge-pending { background: rgba(90, 99, 120, 0.15); }
.badge-pending text { color: #5a6378; }
.badge-analyzing { background: rgba(96, 165, 250, 0.1); }
.badge-analyzing text { color: #60a5fa; }
.badge-downloading { background: rgba(108, 124, 255, 0.15); }
.badge-downloading text { color: #6c7cff; }
.badge-processing { background: rgba(251, 191, 36, 0.1); }
.badge-processing text { color: #fbbf24; }
.badge-completed { background: rgba(52, 211, 153, 0.1); }
.badge-completed text { color: #34d399; }
.badge-failed { background: rgba(248, 113, 113, 0.1); }
.badge-failed text { color: #f87171; }

.mini-spinner {
  width: 16rpx;
  height: 16rpx;
  border: 2rpx solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 进度条 */
.progress-section {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.progress-bar {
  flex: 1;
  height: 10rpx;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 100rpx;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: 100rpx;
  transition: width 0.3s ease;
}

.progress-fill.downloading { background: linear-gradient(90deg, #6c7cff, #818cf8); }
.progress-fill.processing { background: linear-gradient(90deg, #fbbf24, #fcd34d); }
.progress-fill.completed { background: linear-gradient(90deg, #34d399, #6ee7b7); }

.progress-text {
  font-size: 24rpx;
  font-weight: 600;
  min-width: 60rpx;
  text-align: right;
}

.progress-detail {
  display: flex;
  gap: 24rpx;
  margin-top: 12rpx;
  flex-wrap: wrap;
}

.progress-detail text {
  font-size: 22rpx;
  color: #5a6378;
}

/* 错误 */
.error-box {
  margin-top: 12rpx;
  padding: 16rpx 20rpx;
  background: rgba(248, 113, 113, 0.08);
  border-radius: 12rpx;
}

.error-box text {
  font-size: 24rpx;
  color: #f87171;
}

/* 操作按钮 */
.card-actions {
  display: flex;
  gap: 16rpx;
  margin-top: 20rpx;
  padding-top: 20rpx;
  border-top: 1rpx solid rgba(99, 119, 255, 0.08);
}

.action-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  padding: 18rpx;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #8892b0;
}

.action-btn text {
  font-size: 24rpx;
}

.action-delete {
  color: #f87171;
  border-color: rgba(248, 113, 113, 0.15);
}
</style>
