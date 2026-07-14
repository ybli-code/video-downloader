# 视频下载 - 完整部署指南

## 部署架构

```
微信小程序 (用户手机)
    ↓ HTTPS 请求
Cloudflare Worker (提供 HTTPS 域名)
    ↓ HTTP 代理
你的服务器 (Flask + yt-dlp + ffmpeg)
    ↓ 下载视频
各视频平台 (抖音/B站/小红书/...)
```

### 为什么需要 Cloudflare Worker？

微信小程序强制要求 API 必须是 **HTTPS + 已备案域名**。Cloudflare Worker 提供：
- 自带 HTTPS（`*.workers.dev`）
- 全球 CDN 加速
- 免费额度（10万次请求/天）
- 无需服务器配置 SSL 证书

---

## 你需要提供的凭证/信息

| # | 需要什么 | 从哪里获取 | 用途 |
|---|---------|-----------|------|
| 1 | **服务器 IP + SSH 用户名 + PEM 密钥** | 你的云服务商 | SSH 登录服务器部署后端 |
| 2 | **微信小程序 AppID** | [mp.weixin.qq.com](https://mp.weixin.qq.com) 注册 | 编译小程序 |
| 3 | **Cloudflare 账号** | [dash.cloudflare.com](https://dash.cloudflare.com) | 部署 Worker |
| 4 | **GitHub 仓库地址**（可选） | github.com | 存放代码，方便服务器拉取 |

### 凭证获取详细说明

#### 1. 服务器 (已有 PEM 密钥)
- IP 地址：如 `43.135.xx.xx`
- SSH 用户名：通常 `root` 或 `ubuntu`
- PEM 密钥：你已有的 `.pem` 文件

#### 2. 微信小程序 AppID
- 访问 [mp.weixin.qq.com](https://mp.weixin.qq.com)
- 点击「立即注册」→ 选择「小程序」
- 完成注册后，在「开发管理 → 开发设置」找到 **AppID**
- 个人主体即可注册（免费）

#### 3. Cloudflare 账号
- 已有账号直接登录
- 进入 Workers & Pages 页面
- 首次使用会分配一个 `*.workers.dev` 子域名

#### 4. GitHub（可选）
- 创建仓库：`video-downloader`
- 用于服务器 `git pull` 更新代码

---

## 部署步骤

### 第一步：部署后端到服务器

```bash
# 在本地终端执行（用你的 PEM 密钥登录服务器）
ssh -i your-key.pem root@你的服务器IP

# 在服务器上执行：
apt-get update && apt-get install -y python3 python3-pip python3-venv ffmpeg nginx git

# 克隆代码（或用 scp 上传）
cd /opt
git clone https://github.com/你的用户名/video-downloader.git
cd video-downloader

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 测试运行
python app.py
# 看到 "正在启动..." 即成功，Ctrl+C 停止

# 或者直接运行一键脚本
bash deploy/server-deploy.sh
```

### 第二步：配置 Systemd 服务（后台常驻）

```bash
# 复制服务文件
cp deploy/video-downloader.service /etc/systemd/system/

# 启动服务
systemctl daemon-reload
systemctl enable video-downloader
systemctl start video-downloader

# 检查状态
systemctl status video-downloader
```

### 第三步：配置 Nginx（端口 80 → 5000）

```bash
# 复制 Nginx 配置
cp deploy/nginx-video-downloader.conf /etc/nginx/sites-available/video-downloader
ln -sf /etc/nginx/sites-available/video-downloader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# 重载 Nginx
nginx -t && systemctl reload nginx

# 验证 API 可访问
curl http://localhost/api/platforms
```

### 第四步：部署 Cloudflare Worker

#### 方式 A：网页部署（推荐，最简单）

1. 登录 [Cloudflare Dashboard](https://dash.cloudflare.com)
2. 左侧菜单 → **Workers & Pages**
3. 点击 **Create application** → **Create Worker**
4. 名称填 `video-downloader-api` → 点击 **Deploy**
5. 点击 **Edit code**
6. 删除默认代码，粘贴 `deploy/cloudflare-worker.js` 的内容
7. 修改第 19 行 `SERVER_ORIGIN`：
   ```javascript
   const SERVER_ORIGIN = 'http://你的服务器IP:5000';
   ```
   （如果配了 Nginx 端口 80，改为 `http://你的服务器IP`）
8. 点击 **Save and deploy**
9. 记下 Worker URL：`https://video-downloader-api.你的子域.workers.dev`

#### 方式 B：命令行部署

```bash
# 安装 wrangler CLI
npm install -g wrangler

# 登录
wrangler login

# 进入 deploy 目录
cd deploy/

# 修改 wrangler.toml 中的 SERVER_ORIGIN
# 修改 cloudflare-worker.js 中的 SERVER_ORIGIN

# 部署
wrangler deploy
```

### 第五步：验证 Worker

```bash
# 替换为你的 Worker URL
curl https://video-downloader-api.你的子域.workers.dev/api/platforms

# 应返回平台列表 JSON
```

### 第六步：配置小程序

1. 修改 `mobile/utils/config.js` 第 11 行：
   ```javascript
   const API_SERVER = 'https://video-downloader-api.你的子域.workers.dev'
   ```

2. 修改 `mobile/manifest.json` 第 40 行，填入你的 AppID：
   ```json
   "mp-weixin": {
       "appid": "你的微信小程序AppID",
   ```

3. 修改 `mobile/pages.json` 中的 `iconPath`，确保图标路径正确

### 第七步：编译微信小程序

#### 方式 A：HBuilderX（推荐）

1. 下载 [HBuilderX](https://www.dcloud.io/hbuilderx.html)（App 开发版）
2. 用 HBuilderX 打开 `mobile/` 目录
3. 菜单 → 发行 → 小程序-微信
4. 填入 AppID
5. 点击「发行」
6. 编译后自动打开微信开发者工具

#### 方式 B：CLI

```bash
cd mobile/
npm install
npm run build:mp-weixin
# 输出在 dist/build/mp-weixin/
```

### 第八步：微信开发者工具提交审核

1. 用 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html) 打开编译后的目录
2. 在右上角确认 AppID 正确
3. 点击「上传」→ 填写版本号 `1.0.0` → 确定
4. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com)
5. 管理 → 版本管理 → 找到刚上传的版本 → **提交审核**
6. 审核通过后（通常 1-3 天）→ **发布**

### 第九步：配置合法域名（审核前必须做）

在微信小程序后台配置服务器域名：

1. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 开发管理 → 开发设置 → 服务器域名
3. **request 合法域名** 添加：
   ```
   https://video-downloader-api.你的子域.workers.dev
   ```
4. **downloadFile 合法域名** 添加同样的 URL
5. 保存

---

## 常见问题

### Q: workers.dev 域名能通过微信审核吗？

A: 微信要求域名已 ICP 备案。`workers.dev` 是国际域名，**可能无法通过审核**。

**解决方案**（任选其一）：

1. **使用已备案域名**（最佳）
   - 在 Cloudflare 添加你的备案域名
   - Worker 绑定自定义域名（如 `api.yourdomain.com`）
   - 微信后台配置 `https://api.yourdomain.com`

2. **用 Cloudflare Tunnel 替代 Worker**
   - 在服务器安装 cloudflared
   - 绑定你的备案域名
   - 微信直接访问你的域名

3. **小程序开发模式**（仅测试用）
   - 微信开发者工具 → 详情 → 勾选「不校验合法域名」
   - 仅本地调试有效，无法发布上线

### Q: 视频下载超时怎么办？

A: Cloudflare Worker 免费版有 CPU 时间限制。如果下载大文件超时：
- 升级 Cloudflare Workers Paid（$5/月，50ms→30s CPU）
- 或改为服务器直接提供文件下载（需域名+SSL）

### Q: 服务器需要多少配置？

A: 最低配置：
- 1 核 CPU / 1GB 内存
- 10GB 磁盘（存视频）
- Python 3.10+ / ffmpeg
- 开放 80 端口

### Q: 如何更新代码？

```bash
# SSH 登录服务器
ssh -i your-key.pem root@服务器IP

cd /opt/video-downloader
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart video-downloader
```

---

## 部署检查清单

- [ ] 服务器 SSH 可登录
- [ ] 服务器已安装 Python3 + ffmpeg + Nginx
- [ ] Flask 后端在 :5000 运行
- [ ] Nginx 端口 80 反向代理到 :5000
- [ ] `curl http://服务器IP/api/platforms` 返回 JSON
- [ ] Cloudflare Worker 已部署
- [ ] Worker 中 SERVER_ORIGIN 已改为服务器 IP
- [ ] `curl https://worker-url/api/platforms` 返回 JSON
- [ ] `mobile/utils/config.js` 中 API_SERVER 已改为 Worker URL
- [ ] `mobile/manifest.json` 中已填入微信 AppID
- [ ] 小程序已编译
- [ ] 微信后台已配置合法域名
- [ ] 微信开发者工具中能正常请求 API
- [ ] 已上传代码到微信后台
- [ ] 已提交审核
