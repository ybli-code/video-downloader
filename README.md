# 视频下载技能 (Video Downloader Skill)

> 多平台无水印视频下载智能体 — 给出链接，自动下载最高清无水印视频

## 概述

本技能接收各平台视频链接，自动识别平台并下载最高清的无水印视频。支持 12+ 平台，提供 Web 界面和命令行两种使用方式，并内置可视化水印区域选择去除功能。

## 支持平台

| 平台 | 无水印原理 | 最高画质 | 引擎 |
|---|---|---|---|
| YouTube | 平台视频流本身无水印 | 8K | yt-dlp (android+web 客户端) |
| TikTok | App API 获取 `play_addr`（无水印直链） | 原画 | yt-dlp |
| 抖音 | iesdouyin 分享页提取 `_ROUTER_DATA`，`playwm`→`play` | 原画 | 自研解析器 |
| B站 | 官方 API 获取 durl+DASH 双格式，选最高清 | 4K HDR | 自研解析器 |
| 小红书 | 页面解析 `sns-video` CDN 原始直链 | 原画 | 自研解析器 |
| Twitter/X | 平台视频流无水印 | 原画 | yt-dlp |
| Instagram | 平台视频流无水印 | 原画 | yt-dlp (私密内容需 Cookie) |
| Facebook | 平台视频流无水印 | 原画 | yt-dlp |
| Reddit | 平台视频流无水印 | 原画 | yt-dlp |
| Vimeo | 平台视频流无水印 | 原画 | yt-dlp |
| 西瓜视频 | 平台视频流无水印 | 原画 | yt-dlp |
| 微博 | 平台视频流无水印 | 原画 | yt-dlp |

## 快速开始

### 环境要求

- Python >= 3.9
- ffmpeg + ffprobe（音视频合并与去水印）

### 安装

```bash
cd video-downloader
pip install -r requirements.txt
# 系统依赖
apt install -y ffmpeg   # Linux
# brew install ffmpeg    # macOS
```

### 一键启动

```bash
./start.sh
```

### Web 模式

```bash
python app.py
# 浏览器访问 http://localhost:5000
```

### 命令行模式

```bash
python cli.py "https://www.youtube.com/watch?v=..."
python cli.py "https://www.douyin.com/video/..."
python cli.py "https://b23.tv/OVPCVEJ"
python cli.py "http://xhslink.com/o/4S2AK4qVKiw"
```

## API 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/download` | 提交下载任务 `{url: "链接"}` |
| GET | `/api/tasks` | 获取所有任务列表 |
| GET | `/api/tasks/{id}` | 获取单个任务详情 |
| DELETE | `/api/tasks/{id}` | 删除任务及文件 |
| GET | `/api/download/{id}` | 下载已完成的视频文件 |
| POST | `/api/tasks/{id}/watermark` | 去除水印 `{x,y,w,h}` |
| POST | `/api/detect` | 检测平台 `{url: "链接"}` |
| GET | `/api/platforms` | 获取支持的平台列表 |

### API 调用示例

```bash
# 提交下载
curl -X POST http://localhost:5000/api/download \
  -H "Content-Type: application/json" \
  -d '{"url":"https://v.douyin.com/wimBNibOjY0/"}'

# 查询任务状态
curl http://localhost:5000/api/tasks/{task_id}

# 下载文件
curl -O http://localhost:5000/api/download/{task_id}

# 去除水印 (坐标为视频实际像素)
curl -X POST http://localhost:5000/api/tasks/{task_id}/watermark \
  -H "Content-Type: application/json" \
  -d '{"x":10,"y":10,"w":100,"h":50}'
```

## 核心功能

### 1. 无水印下载

| 平台 | 技术 |
|---|---|
| 抖音 | 通过 `iesdouyin.com` 分享页提取 `_ROUTER_DATA`，将 `play_addr` 中的 `playwm` 替换为 `play` 获取无水印地址 |
| TikTok | yt-dlp 通过 App API 获取 `play_addr`（无水印直链），而非 `download_addr`（带水印） |
| 小红书 | 解析页面提取 `sns-video` CDN 上的原始视频直链 |
| B站 | 调用官方 API 获取视频流地址，视频本身无水印 |
| 其他 | yt-dlp 获取平台原始视频流，默认无水印 |

### 2. 最高清画质

- **抖音**：递归遍历 `_ROUTER_DATA`，收集所有视频流，按 `width * height` 降序选最高清
- **B站**：同时请求 `durl`（单文件）和 `DASH`（分离流）两种格式，对比实际分辨率后选更高清的；请求 `qn=127`（4K HDR）
- **小红书**：收集所有视频 URL，按质量标识（fmv2/hd）评分排序
- **yt-dlp 通用**：`format: bestvideo*+bestaudio/best` + `format_sort: [res, fps, br, size]`
- **YouTube**：`player_client: [android, web]` 双客户端获取最高清格式

### 3. 手动去水印

针对下载后仍残留水印的视频：

1. 在 Web 界面点击任务卡片的橡皮擦按钮
2. 弹出视频预览模态框
3. 拖拽框选水印区域，或点击预设位置（左上/右上/左下/右下/居中）
4. 点击「去除水印」，ffmpeg `delogo` 滤镜自动修复
5. 若 delogo 失败，自动回退到高斯模糊方案

### 4. 断线恢复

服务器重启后自动扫描 `downloads/` 目录，将已有视频文件恢复为已完成任务，避免重复下载。

## 项目结构

```
video-downloader/
├── skill.yaml              # 技能清单（平台/功能/API/依赖声明）
├── README.md               # 本文档
├── requirements.txt        # Python 依赖
├── start.sh                # 一键启动脚本
├── downloader.py            # 核心下载引擎
│   ├── Platform             #   平台枚举与检测
│   ├── DownloadTask         #   下载任务数据模型
│   ├── VideoDownloader      #   下载器主类
│   │   ├── submit()         #     提交下载任务
│   │   ├── _download_xiaohongshu()  #  小红书专用下载
│   │   ├── _download_douyin()       #  抖音专用下载
│   │   ├── _download_bilibili()     #  B站专用下载
│   │   ├── _build_ydl_opts()        #  yt-dlp 配置
│   │   └── remove_watermark()       #  去水印处理
│   └── downloader           #   全局单例
├── app.py                   # Flask Web 服务
│   ├── /api/download        #   提交下载
│   ├── /api/tasks           #   任务管理
│   ├── /api/download/{id}   #   文件下载
│   └── /api/tasks/{id}/watermark  # 去水印
├── cli.py                   # 命令行工具
├── templates/
│   └── index.html           # Web 界面
├── static/
│   ├── style.css            # 样式（暗色玻璃拟态）
│   └── app.js               # 前端逻辑（进度轮询+去水印交互）
└── downloads/               # 下载文件存储
```

## 技术架构

```
用户输入链接
      │
      ▼
┌─────────────┐
│  平台检测    │  URL 正则匹配 → Platform 枚举
└──────┬──────┘
       │
       ├── 抖音/小红书/B站 ──→ 自研解析器（httpx + 页面解析）
       │                         │
       │                         ├── 抖音: _ROUTER_DATA → play_addr → playwm→play
       │                         ├── B站: API → durl+DASH 双格式 → 选最高清
       │                         └── 小红书: sns-video CDN 直链
       │
       └── 其他平台 ──→ yt-dlp 引擎
                           │
                           ├── format: bestvideo*+bestaudio/best
                           └── format_sort: [res, fps, br, size]
       │
       ▼
┌─────────────┐
│  下载执行    │  后台线程 + 实时进度回调
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  后处理      │  ffmpeg 合并音视频（B站 DASH）
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  去水印(可选) │  ffmpeg delogo 滤镜 / 高斯模糊回退
└─────────────┘
```

## 注意事项

- 下载内容仅供个人学习存档使用，请遵守各平台服务条款及著作权法
- 抖音/小红书等平台签名算法更新频繁，逆向解析可能周期性失效
- Instagram 私密内容、部分平台会员内容需提供浏览器 Cookie
- 去水印功能用于处理下载后残留的水印，不能用于侵犯著作权

## 依赖

| 包 | 用途 |
|---|---|
| yt-dlp >= 2026.7.4 | YouTube/TikTok/Twitter 等平台视频下载引擎 |
| flask >= 3.0.0 | Web 服务框架 |
| httpx >= 0.27.0 | 抖音/小红书/B站 HTTP 请求 |
| ffmpeg | 音视频合并（B站 DASH）与去水印处理 |
| ffprobe | 视频分辨率/编码信息检测 |
