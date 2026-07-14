<template>
  <view class="page">
    <!-- 自定义导航栏 -->
    <view class="status-bar"></view>
    <view class="nav-bar">
      <view class="nav-bar-title">视频下载</view>
      <view class="nav-badge">
        <view class="badge-dot"></view>
        <text>在线</text>
      </view>
    </view>

    <scroll-view scroll-y class="content" :style="{ top: navBarHeight + 'px' }">
      <!-- Logo 区 -->
      <view class="logo-section">
        <view class="logo-icon">
          <text class="logo-emoji">⬇️</text>
        </view>
        <view class="logo-text">
          <text class="logo-title">多平台无水印下载</text>
          <text class="logo-sub">YouTube · 抖音 · B站 · 小红书 · TikTok</text>
        </view>
      </view>

      <!-- 输入卡片 -->
      <view class="input-card">
        <view class="input-row">
          <view class="input-icon">🔗</view>
          <input
            class="url-input"
            v-model="url"
            placeholder="粘贴视频链接..."
            placeholder-class="placeholder"
            @input="onInput"
            @confirm="handleSubmit"
          />
          <view v-if="url" class="clear-btn" @tap="url = ''">✕</view>
        </view>

        <!-- 平台检测结果 -->
        <view v-if="platformHint" class="platform-hint">
          <view class="hint-dot" :style="{ background: platformColor }"></view>
          <text>{{ platformHint }}</text>
        </view>

        <!-- 操作按钮 -->
        <view class="action-row">
          <view class="btn-paste" @tap="handlePaste">
            <text class="btn-icon">📋</text>
            <text>粘贴链接</text>
          </view>
          <view
            class="btn-download"
            :class="{ disabled: !url || submitting }"
            @tap="handleSubmit"
          >
            <view v-if="submitting" class="spinner"></view>
            <text v-else class="btn-icon">⬇️</text>
            <text>{{ submitting ? '提交中' : '开始下载' }}</text>
          </view>
        </view>
      </view>

      <!-- 支持平台 -->
      <view class="platforms-section">
        <text class="section-label">支持平台</text>
        <view class="platform-chips">
          <view
            v-for="p in platforms"
            :key="p.name"
            class="platform-chip"
          >
            <view class="chip-icon" :style="{ background: p.color }">
              <text>{{ p.icon }}</text>
            </view>
            <text class="chip-name">{{ p.name }}</text>
          </view>
        </view>
      </view>

      <!-- 功能特性 -->
      <view class="features-section">
        <view class="feature-item">
          <view class="feature-icon" style="background: rgba(52,211,153,0.12);">
            <text style="font-size: 36rpx;">🚫</text>
          </view>
          <view class="feature-text">
            <text class="feature-title">无水印下载</text>
            <text class="feature-desc">自动获取原始视频流</text>
          </view>
        </view>
        <view class="feature-item">
          <view class="feature-icon" style="background: rgba(108,124,255,0.12);">
            <text style="font-size: 36rpx;">📱</text>
          </view>
          <view class="feature-text">
            <text class="feature-title">多平台支持</text>
            <text class="feature-desc">12+ 主流视频平台</text>
          </view>
        </view>
        <view class="feature-item">
          <view class="feature-icon" style="background: rgba(251,191,36,0.12);">
            <text style="font-size: 36rpx;">✨</text>
          </view>
          <view class="feature-text">
            <text class="feature-title">最高清画质</text>
            <text class="feature-desc">自动选择最高分辨率</text>
          </view>
        </view>
        <view class="feature-item">
          <view class="feature-icon" style="background: rgba(168,85,247,0.12);">
            <text style="font-size: 36rpx;">✂️</text>
          </view>
          <view class="feature-text">
            <text class="feature-title">手动去水印</text>
            <text class="feature-desc">框选区域自动修复</text>
          </view>
        </view>
      </view>

      <!-- 最近任务 -->
      <view v-if="recentTasks.length > 0" class="recent-section">
        <view class="section-header">
          <text class="section-label">最近下载</text>
          <text class="see-all" @tap="goToTasks">查看全部 ›</text>
        </view>
        <view
          v-for="task in recentTasks.slice(0, 3)"
          :key="task.task_id"
          class="recent-card"
          @tap="goToTask(task)"
        >
          <image
            v-if="task.thumbnail"
            class="recent-thumb"
            :src="task.thumbnail"
            mode="aspectFill"
          />
          <view v-else class="recent-thumb-placeholder">
            <text>🎬</text>
          </view>
          <view class="recent-info">
            <text class="recent-title">{{ task.title || task.url }}</text>
            <view class="recent-meta">
              <view class="platform-tag" :style="{ background: getPlatformColor(task.platform) + '22', color: getPlatformColor(task.platform) }">
                <text>{{ task.platform }}</text>
              </view>
              <text class="recent-status" :class="'status-' + task.status">
                {{ getStatusText(task.status) }}
              </text>
            </view>
          </view>
        </view>
      </view>

      <view style="height: 120rpx;"></view>
    </scroll-view>
  </view>
</template>

<script>
import api from '@/utils/api.js'
import config from '@/utils/config.js'

export default {
  data() {
    return {
      url: '',
      platformHint: '',
      platformColor: '#6c7cff',
      submitting: false,
      platforms: [],
      recentTasks: [],
      navBarHeight: 88,
      detectTimer: null,
    }
  },

  onLoad() {
    this.loadPlatforms()
    this.loadRecentTasks()
  },

  onShow() {
    this.loadRecentTasks()
  },

  methods: {
    onInput() {
      clearTimeout(this.detectTimer)
      if (!this.url.trim()) {
        this.platformHint = ''
        return
      }
      this.detectTimer = setTimeout(() => this.detectPlatform(), 400)
    },

    async detectPlatform() {
      if (!this.url.trim()) return
      try {
        const res = await api.detectPlatform(this.url.trim())
        this.platformColor = this.getPlatformColor(res.platform)
        if (res.supported) {
          this.platformHint = `检测到: ${res.platform} - 点击下载获取无水印视频`
        } else {
          this.platformHint = '未识别平台，将尝试通用下载器'
        }
      } catch (e) {
        // 静默失败
      }
    },

    async handlePaste() {
      const text = await api.pasteFromClipboard()
      if (text) {
        this.url = text.trim()
        this.onInput()
        api.toast('已粘贴', 'success')
      } else {
        api.toast('剪贴板为空', 'none')
      }
    },

    async handleSubmit() {
      if (!this.url.trim() || this.submitting) return
      this.submitting = true

      try {
        const res = await api.submitDownload(this.url.trim())
        if (res.success) {
          api.toast('已开始下载', 'success')
          this.url = ''
          this.platformHint = ''
          // 跳转到任务页
          setTimeout(() => {
            uni.switchTab({ url: '/pages/tasks/tasks' })
          }, 800)
        }
      } catch (e) {
        api.toast(e.error || '提交失败', 'error')
      } finally {
        this.submitting = false
      }
    },

    async loadPlatforms() {
      try {
        const res = await api.getPlatforms()
        this.platforms = res.platforms || []
      } catch (e) {
        this.platforms = [
          { name: 'YouTube', icon: 'YT', color: '#FF0000' },
          { name: '抖音', icon: 'DY', color: '#161823' },
          { name: 'B站', icon: 'B', color: '#00A1D6' },
          { name: '小红书', icon: 'XHS', color: '#FF2442' },
          { name: 'TikTok', icon: 'TT', color: '#000000' },
        ]
      }
    },

    async loadRecentTasks() {
      try {
        const res = await api.getTasks()
        this.recentTasks = (res.tasks || []).slice(0, 5)
      } catch (e) {
        // 静默
      }
    },

    goToTasks() {
      uni.switchTab({ url: '/pages/tasks/tasks' })
    },

    goToTask(task) {
      if (task.status === 'completed') {
        uni.navigateTo({
          url: `/pages/watermark/watermark?taskId=${task.task_id}&title=${encodeURIComponent(task.title || '')}`,
        })
      } else {
        uni.switchTab({ url: '/pages/tasks/tasks' })
      }
    },

    getPlatformColor(name) {
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

.nav-badge {
  display: flex;
  align-items: center;
  gap: 8rpx;
  padding: 8rpx 20rpx;
  background: rgba(52, 211, 153, 0.1);
  border-radius: 100rpx;
}

.nav-badge text {
  font-size: 22rpx;
  color: #34d399;
}

.badge-dot {
  width: 12rpx;
  height: 12rpx;
  background: #34d399;
  border-radius: 50%;
}

.content {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0 32rpx;
}

/* Logo */
.logo-section {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 20rpx 0 40rpx;
}

.logo-icon {
  width: 80rpx;
  height: 80rpx;
  background: linear-gradient(135deg, #6c7cff, #a855f7);
  border-radius: 20rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-emoji {
  font-size: 40rpx;
}

.logo-title {
  font-size: 36rpx;
  font-weight: 700;
  color: #e8edf5;
  display: block;
}

.logo-sub {
  font-size: 22rpx;
  color: #5a6378;
  margin-top: 4rpx;
  display: block;
}

/* 输入卡片 */
.input-card {
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 28rpx;
  padding: 12rpx;
  margin-bottom: 32rpx;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 20rpx;
}

.input-icon {
  font-size: 36rpx;
  flex-shrink: 0;
}

.url-input {
  flex: 1;
  font-size: 30rpx;
  color: #e8edf5;
  padding: 8rpx 0;
}

.placeholder {
  color: #5a6378;
  font-size: 28rpx;
}

.clear-btn {
  width: 44rpx;
  height: 44rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #5a6378;
  font-size: 28rpx;
}

.platform-hint {
  display: flex;
  align-items: center;
  gap: 12rpx;
  padding: 8rpx 24rpx 16rpx;
}

.hint-dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
}

.platform-hint text {
  font-size: 24rpx;
  color: #60a5fa;
}

.action-row {
  display: flex;
  gap: 16rpx;
  padding: 8rpx;
}

.btn-paste {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  padding: 24rpx;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 16rpx;
  font-size: 28rpx;
  color: #8892b0;
}

.btn-download {
  flex: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10rpx;
  padding: 24rpx;
  background: linear-gradient(135deg, #6c7cff, #818cf8);
  border-radius: 16rpx;
  font-size: 30rpx;
  font-weight: 600;
  color: #fff;
}

.btn-download.disabled {
  opacity: 0.4;
}

.btn-icon {
  font-size: 32rpx;
}

/* 平台 */
.platforms-section {
  margin-bottom: 32rpx;
}

.section-label {
  font-size: 26rpx;
  color: #5a6378;
  margin-bottom: 16rpx;
  display: block;
}

.platform-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.platform-chip {
  display: flex;
  align-items: center;
  gap: 10rpx;
  padding: 12rpx 20rpx;
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 100rpx;
}

.chip-icon {
  width: 36rpx;
  height: 36rpx;
  border-radius: 8rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chip-icon text {
  font-size: 18rpx;
  font-weight: 700;
  color: #fff;
}

.chip-name {
  font-size: 24rpx;
  color: #8892b0;
}

/* 功能特性 */
.features-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16rpx;
  margin-bottom: 32rpx;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16rpx;
  padding: 28rpx;
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 24rpx;
}

.feature-icon {
  width: 64rpx;
  height: 64rpx;
  border-radius: 16rpx;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.feature-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #e8edf5;
  display: block;
}

.feature-desc {
  font-size: 22rpx;
  color: #5a6378;
  margin-top: 4rpx;
  display: block;
}

/* 最近任务 */
.recent-section {
  margin-bottom: 32rpx;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16rpx;
}

.see-all {
  font-size: 24rpx;
  color: #6c7cff;
}

.recent-card {
  display: flex;
  align-items: center;
  gap: 20rpx;
  padding: 20rpx;
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 20rpx;
  margin-bottom: 16rpx;
}

.recent-thumb {
  width: 100rpx;
  height: 100rpx;
  border-radius: 16rpx;
  flex-shrink: 0;
  background: #0a0e1a;
}

.recent-thumb-placeholder {
  width: 100rpx;
  height: 100rpx;
  border-radius: 16rpx;
  flex-shrink: 0;
  background: rgba(108, 124, 255, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40rpx;
}

.recent-info {
  flex: 1;
  min-width: 0;
}

.recent-title {
  font-size: 26rpx;
  color: #e8edf5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.recent-meta {
  display: flex;
  align-items: center;
  gap: 12rpx;
  margin-top: 8rpx;
}

.platform-tag {
  padding: 4rpx 12rpx;
  border-radius: 100rpx;
  font-size: 20rpx;
}

.recent-status {
  font-size: 22rpx;
}

.status-completed { color: #34d399; }
.status-downloading { color: #6c7cff; }
.status-analyzing { color: #60a5fa; }
.status-processing { color: #fbbf24; }
.status-failed { color: #f87171; }
.status-pending { color: #5a6378; }
</style>
