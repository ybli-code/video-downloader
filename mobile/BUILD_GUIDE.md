# 视频下载 - 移动端构建指南

## 项目架构

```
mobile/
├── App.vue              # 全局入口 + 主题样式
├── main.js              # Vue 3 应用入口
├── index.html           # H5 入口模板
├── manifest.json        # UniApp 应用配置 (App/小程序/H5)
├── pages.json           # 页面路由 + tabBar 配置
├── vite.config.js       # Vite 构建配置
├── package.json         # 依赖管理
├── static/
│   └── icons/           # tabBar 图标
├── utils/
│   ├── config.js        # 全局配置 (BASE_URL/平台映射/状态映射)
│   └── api.js           # API 服务层 (请求封装/文件下载)
└── pages/
    ├── index/index.vue      # 首页: 链接输入 + 平台检测 + 下载
    ├── tasks/tasks.vue      # 任务页: 实时进度 + 文件管理
    ├── watermark/watermark.vue  # 去水印: 视频预览 + 触摸选区
    └── about/about.vue      # 关于页
```

## 支持平台

| 目标 | 编译命令 | 输出 |
|------|---------|------|
| H5 (网页) | `npm run build:h5` | `dist/build/h5/` |
| 微信小程序 | `npm run build:mp-weixin` | `dist/build/mp-weixin/` |
| Android App | `npm run build:app` | `dist/build/app/` |
| iOS App | HBuilderX 云打包 | `.ipa` |

## 环境准备

### 方式一: HBuilderX (推荐)

1. 下载安装 [HBuilderX](https://www.dcloud.io/hbuilderx.html) (选 App 开发版)
2. 用 HBuilderX 打开 `mobile/` 目录
3. 点击「运行」或「发行」选择目标平台

### 方式二: CLI 命令行

```bash
cd mobile/

# 安装依赖
npm install

# 开发模式
npm run dev:h5          # H5 开发服务器
npm run dev:mp-weixin   # 微信小程序开发

# 生产构建
npm run build:h5
npm run build:mp-weixin
npm run build:app
```

## 各平台配置说明

### H5

- 开发时自动代理 `/api` → `http://localhost:5000`
- 部署时需配置 Nginx 反向代理:
  ```nginx
  location /api {
      proxy_pass http://your-server:5000/api;
  }
  ```

### 微信小程序

1. 在 `manifest.json` 的 `mp-weixin.appid` 填入你的小程序 AppID
2. 编译后用微信开发者工具打开 `dist/build/mp-weixin/`
3. 在小程序管理后台配置服务器域名 (request合法域名)
4. `urlCheck: false` 仅用于开发，上线前需设为 `true`

### Android App

1. 用 HBuilderX 打开项目
2. 「发行」→「原生App-云打包」
3. 配置签名证书 (Keystore)
4. 选择 Android 平台，勾选需要的权限
5. 已配置权限: INTERNET / WRITE_EXTERNAL_STORAGE / READ_EXTERNAL_STORAGE

### iOS App

1. 需要 Apple Developer 账号
2. 在 `manifest.json` 配置 Bundle ID
3. HBuilderX 云打包或本地打包
4. 需在 Info.plist 配置相册访问权限描述

## 后端配置

移动端需连接后端 API 服务:

1. 启动后端:
   ```bash
   cd video-downloader/
   pip install -r requirements.txt
   python app.py
   ```

2. 修改 `utils/config.js` 中的服务器地址:
   ```javascript
   // 将 localhost:5000 改为你的服务器地址
   const BASE_URL = 'http://your-server-ip:5000/api'
   ```

3. 后端已启用 CORS (`flask-cors`)，支持跨域访问

## 条件编译说明

代码中使用 UniApp 条件编译适配不同平台:

```javascript
// #ifdef APP-PLUS
// 仅 App 端执行 (如保存到相册)
// #endif

// #ifdef MP-WEIXIN
// 仅微信小程序执行
// #endif

// #ifdef H5
// 仅 H5 执行 (如 window.open)
// #endif
```

## 功能对照

| 功能 | H5 | 微信小程序 | App |
|------|----|-----------|----|
| 链接输入 & 检测 | ✓ | ✓ | ✓ |
| 下载提交 | ✓ | ✓ | ✓ |
| 实时进度轮询 | ✓ | ✓ | ✓ |
| 视频预览 | ✓ | ✓ | ✓ |
| 触摸选区去水印 | ✓ | ✓ | ✓ |
| 保存到相册 | ✗ (浏览器下载) | ✓ | ✓ |
| 删除任务 | ✓ | ✓ | ✓ |
