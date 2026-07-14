<script>
import api from '@/utils/api.js'

export default {
  onLaunch() {
    console.log('视频下载 App 启动')
    // 检查登录状态
    if (!api.isLoggedIn()) {
      uni.reLaunch({ url: '/pages/login/login' })
    }
  },
  onShow() {},
  onHide() {}
}
</script>

<style>
/* ── 全局样式 ── */
page {
  background-color: #0a0e1a;
  color: #e8edf5;
  font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 28rpx;
  line-height: 1.6;
}

/* 主题色 */
:root {
  --bg: #0a0e1a;
  --bg-card: #141b2d;
  --bg-card-hover: #1c2438;
  --border: rgba(99, 119, 255, 0.12);
  --text: #e8edf5;
  --text-dim: #8892b0;
  --text-muted: #5a6378;
  --primary: #6c7cff;
  --primary-glow: rgba(108, 124, 255, 0.4);
  --success: #34d399;
  --warning: #fbbf24;
  --error: #f87171;
  --info: #60a5fa;
}

/* 通用类 */
.container { padding: 24rpx; min-height: 100vh; }
.card { background: var(--bg-card); border-radius: 24rpx; padding: 32rpx; margin-bottom: 24rpx; }
.btn-primary { background: linear-gradient(135deg, #6c7cff, #818cf8); color: #fff; border: none; border-radius: 16rpx; padding: 24rpx 48rpx; font-size: 30rpx; font-weight: 600; text-align: center; }
.btn-primary[disabled] { opacity: 0.4; }
.btn-ghost { background: transparent; color: #8892b0; border: 1rpx solid rgba(99, 119, 255, 0.12); border-radius: 16rpx; padding: 20rpx 40rpx; font-size: 28rpx; }
.text-dim { color: #8892b0; }
.text-muted { color: #5a6378; }
.text-success { color: #34d399; }
.text-error { color: #f87171; }
.text-warning { color: #fbbf24; }
.flex { display: flex; }
.flex-col { display: flex; flex-direction: column; }
.flex-center { display: flex; align-items: center; justify-content: center; }
.flex-between { display: flex; align-items: center; justify-content: space-between; }
.gap-sm { gap: 12rpx; }
.gap-md { gap: 24rpx; }
.status-bar { height: var(--status-bar-height); }
.nav-bar { display: flex; align-items: center; justify-content: space-between; padding: 0 24rpx; height: 88rpx; line-height: 88rpx; }
.nav-bar-title { font-size: 34rpx; font-weight: 600; color: #e8edf5; }

@keyframes spin { to { transform: rotate(360deg); } }
.spinner { width: 36rpx; height: 36rpx; border: 4rpx solid rgba(108, 124, 255, 0.2); border-top-color: #6c7cff; border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10rpx); } to { opacity: 1; transform: translateY(0); } }
.fade-in { animation: fadeIn 0.3s ease; }
.scroll-area { height: 100vh; }
</style>
