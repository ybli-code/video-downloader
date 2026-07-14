# 立即部署 - 三步上线

## 当前状态

| 项目 | 状态 |
|------|------|
| GitHub 仓库 | ✅ https://github.com/ybli-code/video-downloader |
| 服务器 | 49.233.146.86 (Port 80 已有网站运行) |
| 域名 aibuddy.top | ✅ 已解析到 49.233.146.86 |
| DNS 服务商 | 阿里云 DNS (hichina) |
| api.aibuddy.top | ❌ 尚未添加解析记录 |
| 小程序配置 | ✅ 已配置 API_SERVER = https://api.aibuddy.top |

---

## 第一步：阿里云 DNS 添加解析记录 (2分钟)

1. 登录 [阿里云 DNS 控制台](https://dns.console.aliyun.com)
2. 找到 `aibuddy.top` 域名 → 点击「解析设置」
3. 添加记录：

| 记录类型 | 主机记录 | 记录值 | TTL |
|---------|---------|-------|-----|
| A | api | 49.233.146.86 | 10分钟 |

4. 保存，等待 1-2 分钟生效
5. 验证：在终端执行 `nslookup api.aibuddy.top`，应返回 `49.233.146.86`

---

## 第二步：服务器部署 (5分钟)

在你自己的电脑终端执行（用你的 PEM 密钥登录服务器）：

```bash
ssh -i aibuddy.pem root@49.233.146.86
```

登录成功后，执行一条命令完成部署：

```bash
curl -sL https://raw.githubusercontent.com/ybli-code/video-downloader/main/deploy/server-deploy.sh | bash
```

或者手动执行：

```bash
apt-get update && apt-get install -y git
git clone https://github.com/ybli-code/video-downloader.git /tmp/vd
bash /tmp/vd/deploy/server-deploy.sh
```

脚本会自动完成：
- 安装 Python3 + ffmpeg + Nginx + Certbot
- 克隆代码到 /opt/video-downloader
- 创建 Gunicorn 服务 (systemd 常驻)
- 配置 Nginx 反向代理 (api.aibuddy.top → :5000)
- 申请 Let's Encrypt 免费 SSL 证书 (HTTPS)
- 开放防火墙端口

部署完成后验证：

```bash
# 在服务器上验证
curl http://127.0.0.1:5000/api/platforms

# 在你自己的电脑上验证
curl https://api.aibuddy.top/api/platforms
```

应返回 JSON 格式的平台列表。

---

## 第三步：编译并发布微信小程序

### 3.1 注册微信小程序 (如已有 AppID 跳过)

1. 访问 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 立即注册 → 选择「小程序」
3. 个人主体即可（免费）
4. 注册完成后，在「开发管理 → 开发设置」获取 **AppID**

### 3.2 配置合法域名

1. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com)
2. 开发管理 → 开发设置 → 服务器域名
3. **request 合法域名** 添加：`https://api.aibuddy.top`
4. **downloadFile 合法域名** 添加：`https://api.aibuddy.top`
5. 保存

### 3.3 编译小程序

1. 下载 [HBuilderX](https://www.dcloud.io/hbuilderx.html) (App 开发版)
2. 用 HBuilderX 打开 `mobile/` 目录
3. 修改 `manifest.json` 第 40 行，填入你的 AppID：
   ```json
   "appid": "你的微信小程序AppID",
   ```
4. 菜单 → 发行 → 小程序-微信
5. 填入 AppID → 点击「发行」
6. 编译完成后自动打开微信开发者工具

### 3.4 上传并提交审核

1. 在微信开发者工具中确认 AppID 正确
2. 点击右上角「上传」→ 版本号 `1.0.0` → 确定
3. 登录 [mp.weixin.qq.com](https://mp.weixin.qq.com)
4. 管理 → 版本管理 → 找到刚上传的版本
5. 点击「提交审核」
6. 审核通过后（通常 1-3 天）→ 点击「发布」

---

## 关键问题：ICP 备案

微信小程序要求 API 域名必须 **ICP 备案**。

你的 `aibuddy.top` 已解析到腾讯云服务器（49.233.146.86），腾讯云要求域名必须备案才能使用 80 端口。当前 port 80 可访问，说明 **域名很可能已备案**。

如果未备案：
- 在 [腾讯云备案系统](https://cloud.tencent.com/product/ba) 提交备案
- 个人备案通常 7-20 个工作日
- 备案期间无法通过微信审核

---

## 架构图

```
微信小程序 (用户手机)
    ↓ HTTPS
api.aibuddy.top (Let's Encrypt SSL)
    ↓ Nginx :443 → :5000
Gunicorn (Flask + yt-dlp + ffmpeg)
    ↓ 下载视频
各视频平台 (抖音/B站/小红书/...)
```

## 服务管理命令

```bash
# 查看服务状态
systemctl status video-downloader

# 重启服务
systemctl restart video-downloader

# 查看实时日志
journalctl -u video-downloader -f

# 更新代码
cd /opt/video-downloader && git pull && systemctl restart video-downloader
```
