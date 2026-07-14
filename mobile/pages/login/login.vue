<template>
  <view class="login-page">
    <view class="login-bg"></view>

    <view class="login-container">
      <!-- Logo -->
      <view class="logo-section">
        <view class="logo-icon">
          <text class="logo-text">VD</text>
        </view>
        <text class="app-title">视频下载</text>
        <text class="app-subtitle">多平台无水印 · 高清下载</text>
      </view>

      <!-- 表单 -->
      <view class="form-section">
        <view v-if="mode === 'login'" class="form-group">
          <input
            v-model="form.account"
            class="form-input"
            placeholder="用户名或邮箱"
            placeholder-class="placeholder"
          />
          <input
            v-model="form.password"
            class="form-input"
            placeholder="密码"
            placeholder-class="placeholder"
            password
          />
        </view>

        <view v-else class="form-group">
          <input
            v-model="form.username"
            class="form-input"
            placeholder="用户名"
            placeholder-class="placeholder"
          />
          <input
            v-model="form.email"
            class="form-input"
            placeholder="邮箱"
            placeholder-class="placeholder"
          />
          <input
            v-model="form.password"
            class="form-input"
            placeholder="密码 (至少6位)"
            placeholder-class="placeholder"
            password
          />
        </view>

        <button class="submit-btn" :loading="loading" @tap="handleSubmit">
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </button>

        <view class="switch-mode" @tap="switchMode">
          <text>{{ mode === 'login' ? '没有账号？去注册' : '已有账号？去登录' }}</text>
        </view>
      </view>

      <!-- 功能亮点 -->
      <view class="features-section">
        <view class="feature-item">
          <text class="feature-icon">🎬</text>
          <text class="feature-label">13+ 平台</text>
        </view>
        <view class="feature-item">
          <text class="feature-icon">🚫</text>
          <text class="feature-label">无水印</text>
        </view>
        <view class="feature-item">
          <text class="feature-icon">⚡</text>
          <text class="feature-label">高清下载</text>
        </view>
        <view class="feature-item">
          <text class="feature-icon">📱</text>
          <text class="feature-label">保存相册</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import api from '@/utils/api.js'

export default {
  data() {
    return {
      mode: 'login',
      loading: false,
      form: {
        account: '',
        username: '',
        email: '',
        password: '',
      },
    }
  },
  methods: {
    switchMode() {
      this.mode = this.mode === 'login' ? 'register' : 'login'
      this.form.password = ''
    },

    async handleSubmit() {
      if (this.loading) return

      if (this.mode === 'login') {
        if (!this.form.account || !this.form.password) {
          uni.showToast({ title: '请填写完整', icon: 'none' })
          return
        }
        await this.handleLogin()
      } else {
        if (!this.form.username || !this.form.email || !this.form.password) {
          uni.showToast({ title: '请填写完整', icon: 'none' })
          return
        }
        if (this.form.password.length < 6) {
          uni.showToast({ title: '密码至少6位', icon: 'none' })
          return
        }
        await this.handleRegister()
      }
    },

    async handleLogin() {
      this.loading = true
      try {
        const res = await api.login(this.form.account, this.form.password)
        if (res.success) {
          api.setTokens(res.access_token, res.refresh_token)
          api.saveUser(res.user)
          uni.showToast({ title: '登录成功', icon: 'success' })
          setTimeout(() => {
            uni.switchTab({ url: '/pages/index/index' })
          }, 800)
        }
      } catch (e) {
        uni.showToast({ title: e.error || '登录失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },

    async handleRegister() {
      this.loading = true
      try {
        const res = await api.register(this.form.username, this.form.email, this.form.password)
        if (res.success) {
          api.setTokens(res.access_token, res.refresh_token)
          api.saveUser(res.user)
          uni.showToast({ title: '注册成功', icon: 'success' })
          setTimeout(() => {
            uni.switchTab({ url: '/pages/index/index' })
          }, 800)
        }
      } catch (e) {
        uni.showToast({ title: e.error || '注册失败', icon: 'none' })
      } finally {
        this.loading = false
      }
    },
  },
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  background: #0a0e1a;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  top: -200rpx;
  left: -100rpx;
  right: -100rpx;
  height: 600rpx;
  background: radial-gradient(circle at 30% 50%, rgba(108, 124, 255, 0.15), transparent 70%);
}

.login-container {
  position: relative;
  z-index: 1;
  padding: 120rpx 48rpx 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.logo-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 60rpx;
}

.logo-icon {
  width: 120rpx;
  height: 120rpx;
  border-radius: 30rpx;
  background: linear-gradient(135deg, #6c7cff, #5568ff);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 12rpx 40rpx rgba(108, 124, 255, 0.4);
  margin-bottom: 24rpx;
}

.logo-text {
  font-size: 48rpx;
  font-weight: 800;
  color: #fff;
}

.app-title {
  font-size: 40rpx;
  font-weight: 700;
  color: #e8edf5;
  margin-bottom: 8rpx;
}

.app-subtitle {
  font-size: 26rpx;
  color: #8892b0;
}

.form-section {
  width: 100%;
  margin-bottom: 48rpx;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 24rpx;
  margin-bottom: 32rpx;
}

.form-input {
  width: 100%;
  height: 96rpx;
  padding: 0 32rpx;
  font-size: 30rpx;
  color: #e8edf5;
  background: rgba(20, 27, 45, 0.8);
  border: 2rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 20rpx;
  transition: border-color 0.2s;
}

.placeholder {
  color: #5a6378;
}

.submit-btn {
  width: 100%;
  height: 96rpx;
  line-height: 96rpx;
  font-size: 32rpx;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #6c7cff, #5568ff);
  border-radius: 20rpx;
  border: none;
  box-shadow: 0 8rpx 32rpx rgba(108, 124, 255, 0.3);
}

.submit-btn::after {
  border: none;
}

.switch-mode {
  text-align: center;
  margin-top: 24rpx;
}

.switch-mode text {
  font-size: 28rpx;
  color: #6c7cff;
}

.features-section {
  display: flex;
  justify-content: space-around;
  width: 100%;
  padding: 32rpx 0;
}

.feature-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8rpx;
}

.feature-icon {
  font-size: 40rpx;
}

.feature-label {
  font-size: 22rpx;
  color: #8892b0;
}
</style>
