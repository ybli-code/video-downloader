/**
 * API 服务层
 */
import config from './config.js'

const { BASE_URL, FILE_BASE_URL } = config

/**
 * 通用请求
 */
function request(url, options = {}) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...options.header,
      },
      success(res) {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(res.data || { error: `HTTP ${res.statusCode}` })
        }
      },
      fail(err) {
        reject({ error: err.errMsg || '网络请求失败' })
      },
    })
  })
}

export default {
  // ── 平台检测 ──
  detectPlatform(url) {
    return request('/detect', { method: 'POST', data: { url } })
  },

  // ── 提交下载 ──
  submitDownload(url) {
    return request('/download', { method: 'POST', data: { url } })
  },

  // ── 获取任务列表 ──
  getTasks() {
    return request('/tasks')
  },

  // ── 获取单个任务 ──
  getTask(taskId) {
    return request(`/tasks/${taskId}`)
  },

  // ── 删除任务 ──
  deleteTask(taskId) {
    return request(`/tasks/${taskId}`, { method: 'DELETE' })
  },

  // ── 去除水印 ──
  removeWatermark(taskId, x, y, w, h) {
    return request(`/tasks/${taskId}/watermark`, {
      method: 'POST',
      data: { x, y, w, h },
    })
  },

  // ── 获取平台列表 ──
  getPlatforms() {
    return request('/platforms')
  },

  // ── 获取文件下载 URL ──
  getFileUrl(taskId) {
    return `${FILE_BASE_URL}/${taskId}`
  },

  // ── 下载文件到本地（App 端）──
  downloadFile(taskId) {
    return new Promise((resolve, reject) => {
      const url = this.getFileUrl(taskId)
      // #ifdef APP-PLUS
      uni.downloadFile({
        url,
        success(res) {
          if (res.statusCode === 200) {
            // 保存到相册
            uni.saveVideoToPhotosAlbum({
              filePath: res.tempFilePath,
              success() {
                resolve({ saved: true, path: res.tempFilePath })
              },
              fail(err) {
                resolve({ saved: false, path: res.tempFilePath, error: err.errMsg })
              },
            })
          } else {
            reject({ error: '下载失败' })
          }
        },
        fail(err) {
          reject({ error: err.errMsg })
        },
      })
      // #endif

      // #ifdef MP-WEIXIN
      uni.downloadFile({
        url,
        success(res) {
          if (res.statusCode === 200) {
            uni.saveVideoToPhotosAlbum({
              filePath: res.tempFilePath,
              success() {
                resolve({ saved: true, path: res.tempFilePath })
              },
              fail(err) {
                resolve({ saved: false, path: res.tempFilePath, error: err.errMsg })
              },
            })
          } else {
            reject({ error: '下载失败' })
          }
        },
        fail(err) {
          reject({ error: err.errMsg })
        },
      })
      // #endif

      // #ifdef H5
      // H5 直接打开链接
      window.open(url, '_blank')
      resolve({ saved: false, path: url })
      // #endif
    })
  },

  // ── 粘贴板读取 ──
  async pasteFromClipboard() {
    return new Promise((resolve) => {
      uni.getClipboardData({
        success(res) {
          resolve(res.data || '')
        },
        fail() {
          resolve('')
        },
      })
    })
  },

  // ── Toast ──
  toast(message, type = 'none') {
    const icon = type === 'success' ? 'success' : type === 'error' ? 'error' : 'none'
    uni.showToast({ title: message, icon, duration: 2500 })
  },
}
