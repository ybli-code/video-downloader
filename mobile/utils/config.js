/**
 * 全局配置
 *
 * 部署时只需修改 API_SERVER 即可，所有平台自动使用
 * 微信小程序要求 HTTPS，请填 Cloudflare Worker URL
 */

// ════════════════ 部署时修改此处 ════════════════
// 你的 Cloudflare Worker URL (提供 HTTPS)
// 示例: 'https://video-downloader-api.yourname.workers.dev'
const API_SERVER = 'https://api.aibuddy.top'
// ════════════════════════════════════════════════

// #ifdef H5
// H5 开发模式用 Vite 代理，生产用绝对路径
const BASE_URL = process.env.NODE_ENV === 'development' ? '/api' : API_SERVER + '/api'
// #endif

// #ifdef APP-PLUS
const BASE_URL = API_SERVER + '/api'
// #endif

// #ifdef MP-WEIXIN
// 微信小程序必须用 HTTPS
const BASE_URL = API_SERVER + '/api'
// #endif

// #ifndef H5 || APP-PLUS || MP-WEIXIN
const BASE_URL = API_SERVER + '/api'
// #endif

// 文件下载基础 URL（用于视频预览和文件下载）
const FILE_BASE_URL = BASE_URL + '/download'

export default {
  BASE_URL,
  FILE_BASE_URL,
  API_SERVER,
  // 轮询间隔（毫秒）
  POLL_INTERVAL: 1500,
  // 平台颜色
  PLATFORM_COLORS: {
    'YouTube': '#FF0000',
    'TikTok': '#000000',
    '抖音': '#161823',
    'B站': '#00A1D6',
    'Twitter/X': '#000000',
    'Instagram': '#E4405F',
    'Facebook': '#1877F2',
    'Reddit': '#FF4500',
    'Vimeo': '#1AB7EA',
    'Dailymotion': '#0066DC',
    '西瓜视频': '#FF4256',
    '微博': '#E6162D',
    '小红书': '#FF2442',
    '未知平台': '#5A6378',
  },
  PLATFORM_ICONS: {
    'YouTube': 'YT',
    'TikTok': 'TT',
    '抖音': 'DY',
    'B站': 'B',
    'Twitter/X': 'X',
    'Instagram': 'IG',
    'Facebook': 'FB',
    'Reddit': 'R',
    'Vimeo': 'V',
    'Dailymotion': 'DM',
    '西瓜视频': 'XG',
    '微博': 'WB',
    '小红书': 'XHS',
    '未知平台': '?',
  },
  STATUS_TEXT: {
    'pending': '等待中',
    'analyzing': '解析中',
    'downloading': '下载中',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消',
  },
}
