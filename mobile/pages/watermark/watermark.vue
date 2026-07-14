<template>
  <view class="page">
    <view class="status-bar"></view>
    <view class="nav-bar">
      <view class="nav-back" @tap="goBack">‹ 返回</view>
      <view class="nav-bar-title">去除水印</view>
      <view style="width: 80rpx;"></view>
    </view>

    <scroll-view scroll-y class="content" :style="{ top: '88px' }">
      <!-- 说明 -->
      <view class="desc-card">
        <text class="desc-text">在视频画面上拖拽框选水印区域，或点击下方预设位置快速选择。</text>
      </view>

      <!-- 预设位置 -->
      <view class="presets">
        <view class="preset-btn" @tap="setPreset('tl')">↖ 左上</view>
        <view class="preset-btn" @tap="setPreset('tr')">↗ 右上</view>
        <view class="preset-btn" @tap="setPreset('bl')">↙ 左下</view>
        <view class="preset-btn" @tap="setPreset('br')">↘ 右下</view>
        <view class="preset-btn" @tap="setPreset('center')">⊙ 居中</view>
      </view>

      <!-- 视频预览 + 选区 -->
      <view class="video-card">
        <video
          v-if="videoUrl"
          class="video-preview"
          :src="videoUrl"
          controls
          object-fit="contain"
          @loadedmetadata="onVideoLoaded"
          id="wmVideo"
        ></video>

        <!-- 选区覆盖层 -->
        <view
          v-if="selW > 0"
          class="sel-box"
          :style="selBoxStyle"
        >
          <text class="sel-label">{{ realW }}x{{ realH }}</text>
        </view>
      </view>

      <!-- 触摸选区提示 -->
      <view v-if="selW === 0" class="touch-hint">
        <text>👆 在视频画面上拖拽选择水印区域</text>
      </view>

      <!-- 坐标显示 -->
      <view class="coords-card">
        <view class="coord-item">
          <text class="coord-label">X</text>
          <text class="coord-val">{{ realX }}</text>
        </view>
        <view class="coord-item">
          <text class="coord-label">Y</text>
          <text class="coord-val">{{ realY }}</text>
        </view>
        <view class="coord-item">
          <text class="coord-label">宽</text>
          <text class="coord-val">{{ realW }}</text>
        </view>
        <view class="coord-item">
          <text class="coord-label">高</text>
          <text class="coord-val">{{ realH }}</text>
        </view>
        <view class="coord-item coord-video">
          <text class="coord-label">视频</text>
          <text class="coord-val">{{ videoW }}x{{ videoH }}</text>
        </view>
      </view>

      <!-- 处理中提示 -->
      <view v-if="processing" class="processing-card">
        <view class="spinner"></view>
        <text>正在使用 ffmpeg 去除水印...</text>
      </view>

      <!-- 操作按钮 -->
      <view class="actions">
        <view class="btn-cancel" @tap="goBack">取消</view>
        <view
          class="btn-apply"
          :class="{ disabled: realW < 5 || processing }"
          @tap="applyWatermark"
        >
          <view v-if="processing" class="spinner" style="width: 28rpx; height: 28rpx;"></view>
          <text>{{ processing ? '处理中' : '去除水印' }}</text>
        </view>
      </view>

      <view style="height: 60rpx;"></view>
    </scroll-view>

    <!-- 触摸选区层 -->
    <view
      class="touch-layer"
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      :style="touchLayerStyle"
    ></view>
  </view>
</template>

<script>
import api from '@/utils/api.js'

export default {
  data() {
    return {
      taskId: '',
      title: '',
      videoUrl: '',
      videoW: 0,
      videoH: 0,
      displayScale: 1,
      videoDisplayW: 0,
      videoDisplayH: 0,
      videoOffsetX: 0,
      videoOffsetY: 0,
      selX: 0,
      selY: 0,
      selW: 0,
      selH: 0,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      processing: false,
    }
  },

  computed: {
    realX() {
      return Math.round(this.selX / this.displayScale)
    },
    realY() {
      return Math.round(this.selY / this.displayScale)
    },
    realW() {
      return Math.round(this.selW / this.displayScale)
    },
    realH() {
      return Math.round(this.selH / this.displayScale)
    },
    selBoxStyle() {
      return `left: ${this.videoOffsetX + this.selX}px; top: ${this.videoOffsetY + this.selY}px; width: ${this.selW}px; height: ${this.selH}px;`
    },
    touchLayerStyle() {
      return `left: ${this.videoOffsetX}px; top: ${this.videoOffsetY}px; width: ${this.videoDisplayW}px; height: ${this.videoDisplayH}px;`
    },
  },

  onLoad(options) {
    this.taskId = options.taskId
    this.title = decodeURIComponent(options.title || '')
    this.videoUrl = api.getFileUrl(this.taskId)
  },

  methods: {
    onVideoLoaded(e) {
      // 获取视频原始尺寸
      // #ifdef APP-PLUS || MP-WEIXIN
      uni.createSelectorQuery()
        .in(this)
        .select('.video-preview')
        .boundingClientRect((rect) => {
          if (rect) {
            this.videoDisplayW = rect.width
            this.videoDisplayH = rect.height
            this.videoOffsetX = rect.left
            this.videoOffsetY = rect.top
          }
        })
        .exec()
      // #endif

      // #ifdef H5
      const video = document.querySelector('.video-preview')
      if (video) {
        this.videoW = video.videoWidth
        this.videoH = video.videoHeight
        const rect = video.getBoundingClientRect()
        this.videoDisplayW = rect.width
        this.videoDisplayH = rect.height
        this.videoOffsetX = rect.left
        this.videoOffsetY = rect.top
        this.displayScale = rect.width / (this.videoW || rect.width)
      }
      // #endif
    },

    onTouchStart(e) {
      const touch = e.touches[0]
      this.isDragging = true
      this.dragStartX = touch.clientX - this.videoOffsetX
      this.dragStartY = touch.clientY - this.videoOffsetY
      this.selX = this.dragStartX
      this.selY = this.dragStartY
      this.selW = 0
      this.selH = 0
    },

    onTouchMove(e) {
      if (!this.isDragging) return
      const touch = e.touches[0]
      let curX = touch.clientX - this.videoOffsetX
      let curY = touch.clientY - this.videoOffsetY

      curX = Math.max(0, Math.min(curX, this.videoDisplayW))
      curY = Math.max(0, Math.min(curY, this.videoDisplayH))

      this.selX = Math.min(this.dragStartX, curX)
      this.selY = Math.min(this.dragStartY, curY)
      this.selW = Math.abs(curX - this.dragStartX)
      this.selH = Math.abs(curY - this.dragStartY)
    },

    onTouchEnd() {
      this.isDragging = false
      if (this.selW < 5 || this.selH < 5) {
        this.selW = 0
        this.selH = 0
      }
    },

    setPreset(position) {
      if (!this.videoW) {
        api.toast('视频尚未加载', 'none')
        return
      }

      const margin = 0.02
      const wmW = Math.round(this.videoW * 0.25)
      const wmH = Math.round(this.videoH * 0.10)
      const offsetX = Math.round(this.videoW * margin)
      const offsetY = Math.round(this.videoH * margin)

      let realX, realY
      switch (position) {
        case 'tl': realX = offsetX; realY = offsetY; break
        case 'tr': realX = this.videoW - wmW - offsetX; realY = offsetY; break
        case 'bl': realX = offsetX; realY = this.videoH - wmH - offsetY; break
        case 'br': realX = this.videoW - wmW - offsetX; realY = this.videoH - wmH - offsetY; break
        case 'center': realX = Math.round((this.videoW - wmW) / 2); realY = Math.round((this.videoH - wmH) / 2); break
      }

      this.selX = realX * this.displayScale
      this.selY = realY * this.displayScale
      this.selW = wmW * this.displayScale
      this.selH = wmH * this.displayScale
    },

    async applyWatermark() {
      if (this.realW < 5 || this.processing) return

      this.processing = true
      try {
        const res = await api.removeWatermark(
          this.taskId, this.realX, this.realY, this.realW, this.realH
        )
        if (res.success) {
          api.toast('水印去除成功', 'success')
          this.videoUrl = api.getFileUrl(this.taskId) + '?t=' + Date.now()
          this.selW = 0
          this.selH = 0
        }
      } catch (e) {
        api.toast(e.error || '去水印失败', 'error')
      } finally {
        this.processing = false
      }
    },

    goBack() {
      uni.navigateBack()
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

.nav-back {
  font-size: 30rpx;
  color: #6c7cff;
}

.content {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  padding: 0 32rpx;
}

.desc-card {
  background: rgba(96, 165, 250, 0.08);
  border-radius: 16rpx;
  padding: 24rpx;
  margin-bottom: 24rpx;
}

.desc-text {
  font-size: 24rpx;
  color: #60a5fa;
  line-height: 1.5;
}

.presets {
  display: flex;
  gap: 12rpx;
  flex-wrap: wrap;
  margin-bottom: 24rpx;
}

.preset-btn {
  padding: 14rpx 24rpx;
  background: rgba(255, 255, 255, 0.04);
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 12rpx;
  font-size: 24rpx;
  color: #8892b0;
}

.video-card {
  position: relative;
  background: #000;
  border-radius: 20rpx;
  overflow: hidden;
  margin-bottom: 24rpx;
}

.video-preview {
  width: 100%;
  height: 400rpx;
}

.sel-box {
  position: fixed;
  border: 2rpx dashed #6c7cff;
  background: rgba(108, 124, 255, 0.15);
  pointer-events: none;
  z-index: 100;
}

.sel-label {
  position: absolute;
  top: -36rpx;
  left: 0;
  font-size: 20rpx;
  color: #6c7cff;
  background: rgba(10, 14, 26, 0.9);
  padding: 2rpx 8rpx;
  border-radius: 4rpx;
  white-space: nowrap;
}

.touch-hint {
  text-align: center;
  padding: 20rpx;
  margin-bottom: 24rpx;
}

.touch-hint text {
  font-size: 24rpx;
  color: #5a6378;
}

.touch-layer {
  position: fixed;
  z-index: 50;
}

.coords-card {
  display: flex;
  gap: 24rpx;
  padding: 24rpx;
  background: #141b2d;
  border-radius: 16rpx;
  margin-bottom: 24rpx;
}

.coord-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.coord-video {
  margin-left: auto;
}

.coord-label {
  font-size: 20rpx;
  color: #5a6378;
}

.coord-val {
  font-size: 28rpx;
  font-weight: 600;
  color: #e8edf5;
  margin-top: 4rpx;
}

.processing-card {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 24rpx;
  background: rgba(251, 191, 36, 0.08);
  border-radius: 16rpx;
  margin-bottom: 24rpx;
}

.processing-card text {
  font-size: 24rpx;
  color: #fbbf24;
}

.actions {
  display: flex;
  gap: 16rpx;
}

.btn-cancel {
  flex: 1;
  text-align: center;
  padding: 24rpx;
  background: transparent;
  border: 1rpx solid rgba(99, 119, 255, 0.12);
  border-radius: 16rpx;
  font-size: 28rpx;
  color: #8892b0;
}

.btn-apply {
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

.btn-apply.disabled {
  opacity: 0.4;
}
</style>
