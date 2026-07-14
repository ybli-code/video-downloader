<template>
  <view class="page">
    <view class="status-bar"></view>
    <view class="nav-bar">
      <view class="nav-bar-title">关于</view>
    </view>

    <view class="content">
      <!-- Logo -->
      <view class="logo-section">
        <view class="logo-icon">
          <text class="logo-emoji">⬇️</text>
        </view>
        <text class="app-name">视频下载</text>
        <text class="app-version">v1.0.0</text>
      </view>

      <!-- 功能列表 -->
      <view class="info-card">
        <view class="info-item">
          <text class="info-icon">🎯</text>
          <view class="info-text">
            <text class="info-title">多平台支持</text>
            <text class="info-desc">YouTube / 抖音 / B站 / 小红书 / TikTok 等 12+ 平台</text>
          </view>
        </view>
        <view class="info-item">
          <text class="info-icon">🚫</text>
          <view class="info-text">
            <text class="info-title">无水印下载</text>
            <text class="info-desc">自动获取原始视频流，下载不含平台水印</text>
          </view>
        </view>
        <view class="info-item">
          <text class="info-icon">✨</text>
          <view class="info-text">
            <text class="info-title">最高清画质</text>
            <text class="info-desc">自动选择最高分辨率和码率</text>
          </view>
        </view>
        <view class="info-item">
          <text class="info-icon">✂️</text>
          <view class="info-text">
            <text class="info-title">手动去水印</text>
            <text class="info-desc">框选水印区域，ffmpeg 自动修复</text>
          </view>
        </view>
        <view class="info-item">
          <text class="info-icon">💾</text>
          <view class="info-text">
            <text class="info-title">保存到相册</text>
            <text class="info-desc">下载完成后一键保存到手机相册</text>
          </view>
        </view>
      </view>

      <!-- 技术栈 -->
      <view class="tech-card">
        <text class="card-title">技术架构</text>
        <view class="tech-list">
          <view class="tech-item">
            <text class="tech-label">前端</text>
            <text class="tech-val">UniApp (Vue 3) → App / 小程序 / H5</text>
          </view>
          <view class="tech-item">
            <text class="tech-label">后端</text>
            <text class="tech-val">Flask + yt-dlp + httpx</text>
          </view>
          <view class="tech-item">
            <text class="tech-label">引擎</text>
            <text class="tech-val">yt-dlp + 自研解析器 + ffmpeg</text>
          </view>
        </view>
      </view>

      <!-- 免责声明 -->
      <view class="warn-card">
        <text class="card-title">免责声明</text>
        <text class="warn-text">
          本应用仅供个人学习存档使用。请遵守各平台服务条款及著作权法，下载内容不得用于商业用途或二次分发。去除水印后冒充原创发布可能侵犯著作权人的保护作品完整权。
        </text>
      </view>

      <view style="height: 120rpx;"></view>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {}
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
  padding: 0 32rpx;
  height: 88rpx;
}

.content {
  padding: 0 32rpx;
}

.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40rpx 0 60rpx;
}

.logo-icon {
  width: 120rpx;
  height: 120rpx;
  background: linear-gradient(135deg, #6c7cff, #a855f7);
  border-radius: 30rpx;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-emoji {
  font-size: 60rpx;
}

.app-name {
  font-size: 36rpx;
  font-weight: 700;
  color: #e8edf5;
  margin-top: 20rpx;
}

.app-version {
  font-size: 24rpx;
  color: #5a6378;
  margin-top: 4rpx;
}

.info-card {
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 24rpx;
  padding: 8rpx 28rpx;
  margin-bottom: 24rpx;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 20rpx;
  padding: 28rpx 0;
  border-bottom: 1rpx solid rgba(99, 119, 255, 0.06);
}

.info-item:last-child {
  border-bottom: none;
}

.info-icon {
  font-size: 40rpx;
  flex-shrink: 0;
}

.info-text {
  flex: 1;
}

.info-title {
  font-size: 28rpx;
  font-weight: 600;
  color: #e8edf5;
  display: block;
}

.info-desc {
  font-size: 24rpx;
  color: #5a6378;
  margin-top: 4rpx;
  display: block;
  line-height: 1.4;
}

.tech-card {
  background: #141b2d;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 24rpx;
  padding: 28rpx;
  margin-bottom: 24rpx;
}

.card-title {
  font-size: 26rpx;
  font-weight: 600;
  color: #8892b0;
  margin-bottom: 20rpx;
  display: block;
}

.tech-list {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
}

.tech-item {
  display: flex;
  align-items: center;
  gap: 16rpx;
}

.tech-label {
  font-size: 24rpx;
  color: #5a6378;
  min-width: 80rpx;
}

.tech-val {
  font-size: 24rpx;
  color: #e8edf5;
  flex: 1;
}

.warn-card {
  background: rgba(248, 113, 113, 0.06);
  border: 1rpx solid rgba(248, 113, 113, 0.12);
  border-radius: 24rpx;
  padding: 28rpx;
}

.warn-text {
  font-size: 22rpx;
  color: #8892b0;
  line-height: 1.6;
  margin-top: 12rpx;
  display: block;
}
</style>
