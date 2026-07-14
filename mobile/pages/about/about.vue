<template>
  <view class="container">
    <view class="status-bar"></view>

    <!-- 导航 -->
    <view class="nav-bar">
      <text class="nav-bar-title">我的</text>
    </view>

    <!-- 用户信息 -->
    <view class="card user-card" v-if="user">
      <view class="user-header">
        <view class="avatar">{{ user.username.charAt(0).toUpperCase() }}</view>
        <view class="user-info">
          <text class="user-name">{{ user.username }}</text>
          <text class="user-email">{{ user.email }}</text>
        </view>
        <view class="role-badge" :class="'role-' + user.role">{{ roleText }}</view>
      </view>

      <!-- 配额 -->
      <view class="quota-section" v-if="quota">
        <view class="quota-row">
          <text class="quota-label">今日已用</text>
          <text class="quota-value">{{ quota.used }} / {{ quota.limit }}</text>
        </view>
        <view class="quota-bar">
          <view class="quota-fill" :style="{ width: quotaPercent + '%' }"></view>
        </view>
        <text class="quota-hint">剩余 {{ quota.remaining }} 次 · {{ quota.total_size_mb }}MB</text>
      </view>
    </view>

    <!-- 功能列表 -->
    <view class="card">
      <view class="menu-item" @tap="copyAppId">
        <text class="menu-icon">📱</text>
        <text class="menu-label">AppID</text>
        <text class="menu-value">wxce2c4be552d5867f</text>
      </view>
      <view class="menu-item" @tap="openDocs">
        <text class="menu-icon">📖</text>
        <text class="menu-label">API 文档</text>
        <text class="menu-arrow">›</text>
      </view>
    </view>

    <!-- 技术栈 -->
    <view class="card">
      <text class="section-title">技术架构</text>
      <view class="tech-list">
        <view class="tech-item">
          <text class="tech-name">FastAPI</text>
          <text class="tech-desc">高性能异步 API</text>
        </view>
        <view class="tech-item">
          <text class="tech-name">PostgreSQL</text>
          <text class="tech-desc">用户数据持久化</text>
        </view>
        <view class="tech-item">
          <text class="tech-name">Redis</text>
          <text class="tech-desc">任务队列 + 限流</text>
        </view>
        <view class="tech-item">
          <text class="tech-name">阿里云 OSS</text>
          <text class="tech-desc">视频文件存储</text>
        </view>
        <view class="tech-item">
          <text class="tech-name">Docker</text>
          <text class="tech-desc">容器化部署</text>
        </view>
        <view class="tech-item">
          <text class="tech-name">JWT</text>
          <text class="tech-desc">用户鉴权</text>
        </view>
      </view>
    </view>

    <!-- 退出登录 -->
    <button class="logout-btn" @tap="handleLogout">退出登录</button>

    <text class="version-text">v2.0.0 · 视频下载智能体</text>
  </view>
</template>

<script>
import api from '@/utils/api.js'

export default {
  data() {
    return {
      user: null,
      quota: null,
    }
  },
  computed: {
    roleText() {
      const map = { free: '免费', premium: '会员', admin: '管理员' }
      return map[this.user?.role] || '用户'
    },
    quotaPercent() {
      if (!this.quota || !this.quota.limit) return 0
      return Math.min(100, (this.quota.used / this.quota.limit) * 100)
    },
  },
  onShow() {
    this.user = api.getUser()
    this.loadQuota()
  },
  methods: {
    async loadQuota() {
      try {
        this.quota = await api.getQuota()
      } catch (e) {
        console.log('quota error', e)
      }
    },
    copyAppId() {
      uni.setClipboardData({ data: 'wxce2c4be552d5867f' })
      api.toast('已复制', 'success')
    },
    openDocs() {
      // #ifdef H5
      window.open('https://api.aibuddy.top/docs', '_blank')
      // #endif
      // #ifndef H5
      api.toast('请在浏览器访问 api.aibuddy.top/docs')
      // #endif
    },
    handleLogout() {
      uni.showModal({
        title: '退出登录',
        content: '确定退出当前账号？',
        success(res) {
          if (res.confirm) {
            api.logout()
          }
        },
      })
    },
  },
}
</script>

<style scoped>
.user-card { padding: 32rpx; }
.user-header { display: flex; align-items: center; gap: 24rpx; margin-bottom: 32rpx; }
.avatar { width: 88rpx; height: 88rpx; border-radius: 24rpx; background: linear-gradient(135deg, #6c7cff, #818cf8); display: flex; align-items: center; justify-content: center; font-size: 40rpx; font-weight: 700; color: #fff; }
.user-info { flex: 1; display: flex; flex-direction: column; }
.user-name { font-size: 34rpx; font-weight: 600; color: #e8edf5; }
.user-email { font-size: 24rpx; color: #8892b0; margin-top: 4rpx; }
.role-badge { padding: 6rpx 20rpx; border-radius: 8rpx; font-size: 22rpx; }
.role-free { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.role-premium { background: rgba(251, 191, 36, 0.15); color: #fbbf24; }
.role-admin { background: rgba(248, 113, 113, 0.15); color: #f87171; }
.quota-section { margin-top: 24rpx; padding-top: 24rpx; border-top: 1rpx solid rgba(99, 119, 255, 0.08); }
.quota-row { display: flex; justify-content: space-between; margin-bottom: 12rpx; }
.quota-label { font-size: 26rpx; color: #8892b0; }
.quota-value { font-size: 26rpx; color: #e8edf5; font-weight: 600; }
.quota-bar { height: 12rpx; background: rgba(99, 119, 255, 0.1); border-radius: 6rpx; overflow: hidden; }
.quota-fill { height: 100%; background: linear-gradient(90deg, #6c7cff, #818cf8); border-radius: 6rpx; transition: width 0.3s; }
.quota-hint { display: block; margin-top: 12rpx; font-size: 22rpx; color: #5a6378; }
.menu-item { display: flex; align-items: center; padding: 28rpx 0; border-bottom: 1rpx solid rgba(99, 119, 255, 0.06); }
.menu-item:last-child { border-bottom: none; }
.menu-icon { font-size: 36rpx; margin-right: 20rpx; }
.menu-label { flex: 1; font-size: 30rpx; color: #e8edf5; }
.menu-value { font-size: 24rpx; color: #5a6378; }
.menu-arrow { font-size: 36rpx; color: #5a6378; }
.section-title { display: block; font-size: 28rpx; color: #8892b0; margin-bottom: 24rpx; }
.tech-list { display: flex; flex-direction: column; gap: 16rpx; }
.tech-item { display: flex; align-items: center; }
.tech-name { font-size: 28rpx; color: #6c7cff; font-weight: 600; width: 180rpx; }
.tech-desc { font-size: 26rpx; color: #8892b0; }
.logout-btn { width: 100%; height: 88rpx; line-height: 88rpx; margin-top: 24rpx; background: rgba(248, 113, 113, 0.1); color: #f87171; border: none; border-radius: 20rpx; font-size: 30rpx; }
.logout-btn::after { border: none; }
.version-text { display: block; text-align: center; margin-top: 48rpx; font-size: 22rpx; color: #5a6378; }
</style>
