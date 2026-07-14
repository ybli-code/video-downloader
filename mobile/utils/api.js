/**
 * API 服务层 v2 - 带 JWT 鉴权
 */
import config from './config.js'

const { BASE_URL } = config

// ── Token 管理 ──
const ACCESS_TOKEN_KEY = 'vd_access_token'
const REFRESH_TOKEN_KEY = 'vd_refresh_token'
const USER_INFO_KEY = 'vd_user_info'

function getToken() {
  return uni.getStorageSync(ACCESS_TOKEN_KEY) || ''
}

function setTokens(accessToken, refreshToken) {
  uni.setStorageSync(ACCESS_TOKEN_KEY, accessToken)
  uni.setStorageSync(REFRESH_TOKEN_KEY, refreshToken)
}

function clearTokens() {
  uni.removeStorageSync(ACCESS_TOKEN_KEY)
  uni.removeStorageSync(REFRESH_TOKEN_KEY)
  uni.removeStorageSync(USER_INFO_KEY)
}

function saveUser(user) {
  uni.setStorageSync(USER_INFO_KEY, JSON.stringify(user))
}

export function getUser() {
  const data = uni.getStorageSync(USER_INFO_KEY)
  return data ? JSON.parse(data) : null
}

export function isLoggedIn() {
  return !!getToken()
}

export function logout() {
  clearTokens()
  uni.reLaunch({ url: '/pages/login/login' })
}

// ── 通用请求 (带鉴权) ──
async function request(url, options = {}) {
  const token = getToken()
  const headers = {
    'Content-Type': 'application/json',
    ...options.header,
  }
  if (token && !options.noAuth) {
    headers['Authorization'] = `Bearer ${token}`
  }

  return new Promise((resolve, reject) => {
    uni.request({
      url: BASE_URL + url,
      method: options.method || 'GET',
      data: options.data || {},
      header: headers,
      success(res) {
        // 401 → 尝试刷新 token
        if (res.statusCode === 401 && !options.noAuth && !options._retry) {
          refreshTokenAndRetry(url, options).then(resolve).catch(reject)
          return
        }
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

// ── Token 刷新 ──
async function refreshTokenAndRetry(url, options) {
  const refreshToken = uni.getStorageSync(REFRESH_TOKEN_KEY)
  if (!refreshToken) {
    logout()
    return Promise.reject({ error: '请先登录' })
  }

  try {
    const res = await new Promise((resolve, reject) => {
      uni.request({
        url: BASE_URL + '/auth/refresh',
        method: 'POST',
        data: { refresh_token: refreshToken },
        header: { 'Content-Type': 'application/json' },
        success: resolve,
        fail: reject,
      })
    })

    if (res.statusCode === 200 && res.data.access_token) {
      uni.setStorageSync(ACCESS_TOKEN_KEY, res.data.access_token)
      // 重试原请求
      return request(url, { ...options, _retry: true })
    } else {
      logout()
      return Promise.reject({ error: '登录已过期' })
    }
  } catch (e) {
    logout()
    return Promise.reject({ error: '请重新登录' })
  }
}

export default {
  // ── 认证 ──
  register(username, email, password) {
    return request('/auth/register', {
      method: 'POST',
      data: { username, email, password },
      noAuth: true,
    })
  },

  login(account, password) {
    return request('/auth/login', {
      method: 'POST',
      data: { account, password },
      noAuth: true,
    })
  },

  getProfile() {
    return request('/auth/me')
  },

  // ── 平台检测 (无需登录) ──
  detectPlatform(url) {
    return request('/detect', { method: 'POST', data: { url }, noAuth: true })
  },

  getPlatforms() {
    return request('/platforms', { noAuth: true })
  },

  // ── 下载任务 ──
  submitDownload(url) {
    return request('/download', { method: 'POST', data: { url } })
  },

  getTasks(page = 1, size = 20) {
    return request(`/tasks?page=${page}&size=${size}`)
  },

  getTask(taskId) {
    return request(`/tasks/${taskId}`)
  },

  deleteTask(taskId) {
    return request(`/tasks/${taskId}`, { method: 'DELETE' })
  },

  // ── 下载文件 ──
  async getDownloadUrl(taskId) {
    const res = await request(`/download/${taskId}`)
    return res.url
  },

  async downloadFile(taskId) {
    const url = await this.getDownloadUrl(taskId)
    return new Promise((resolve, reject) => {
      // #ifdef APP-PLUS
      uni.downloadFile({
        url,
        header: { 'Authorization': `Bearer ${getToken()}` },
        success(res) {
          if (res.statusCode === 200) {
            uni.saveVideoToPhotosAlbum({
              filePath: res.tempFilePath,
              success() { resolve({ saved: true }) },
              fail(err) { resolve({ saved: false, error: err.errMsg }) },
            })
          } else { reject({ error: '下载失败' }) }
        },
        fail(err) { reject({ error: err.errMsg }) },
      })
      // #endif

      // #ifdef MP-WEIXIN
      uni.downloadFile({
        url,
        success(res) {
          if (res.statusCode === 200) {
            uni.saveVideoToPhotosAlbum({
              filePath: res.tempFilePath,
              success() { resolve({ saved: true }) },
              fail(err) { resolve({ saved: false, error: err.errMsg }) },
            })
          } else { reject({ error: '下载失败' }) }
        },
        fail(err) { reject({ error: err.errMsg }) },
      })
      // #endif

      // #ifdef H5
      window.open(url, '_blank')
      resolve({ saved: false, path: url })
      // #endif
    })
  },

  // ── 去水印 ──
  removeWatermark(taskId, x, y, w, h) {
    return request(`/tasks/${taskId}/watermark`, {
      method: 'POST',
      data: { x, y, w, h },
    })
  },

  // ── 配额 ──
  getQuota() {
    return request('/quota')
  },

  // ── 粘贴板 ──
  pasteFromClipboard() {
    return new Promise((resolve) => {
      uni.getClipboardData({
        success(res) { resolve(res.data || '') },
        fail() { resolve('') },
      })
    })
  },

  // ── Toast ──
  toast(message, type = 'none') {
    const icon = type === 'success' ? 'success' : type === 'error' ? 'error' : 'none'
    uni.showToast({ title: message, icon, duration: 2500 })
  },

  // ── Token 工具 ──
  setTokens,
  saveUser,
  getToken,
  isLoggedIn,
  logout,
}
