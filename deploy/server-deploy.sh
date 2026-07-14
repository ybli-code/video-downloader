#!/bin/bash
# ═══════════════════════════════════════════════════════
# 视频下载智能体 - 服务器一键部署脚本
# 在服务器上执行: bash server-deploy.sh
# 服务器: 49.233.146.86
# ═══════════════════════════════════════════════════════

set -e

APP_DIR="/opt/video-downloader"
APP_USER="videodl"
REPO_URL="https://github.com/ybli-code/video-downloader.git"

echo "══════════════════════════════════════════════════"
echo "  视频下载智能体 - 服务器部署"
echo "  服务器: 49.233.146.86"
echo "  域名: api.aibuddy.top"
echo "══════════════════════════════════════════════════"

# ── 1. 安装系统依赖 ──
echo "[1/8] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg nginx git > /dev/null 2>&1
echo "  ✓ Python3 + ffmpeg + nginx 已安装"

# ── 2. 创建专用用户 ──
echo "[2/8] 创建服务用户..."
if ! id -u $APP_USER &>/dev/null; then
    useradd -r -s /bin/false $APP_USER
fi
echo "  ✓ 用户 $APP_USER 已就绪"

# ── 3. 拉取代码 ──
echo "[3/8] 拉取代码..."
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull -q
else
    rm -rf $APP_DIR
    git clone -q $REPO_URL $APP_DIR
    cd $APP_DIR
fi
chown -R $APP_USER:$APP_USER $APP_DIR
echo "  ✓ 代码已部署到 $APP_DIR"

# ── 4. 创建虚拟环境 & 安装依赖 ──
echo "[4/8] 安装 Python 依赖..."
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER venv/bin/pip install -r requirements.txt -q
echo "  ✓ Python 依赖安装完成"

# ── 5. 创建 systemd 服务 ──
echo "[5/8] 配置 systemd 服务..."
cat > /etc/systemd/system/video-downloader.service << 'EOF'
[Unit]
Description=Video Downloader API
After=network.target

[Service]
Type=simple
User=videodl
Group=videodl
WorkingDirectory=/opt/video-downloader
ExecStart=/opt/video-downloader/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:5000 --timeout 300 --access-logfile - --error-logfile - app:app
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable video-downloader
systemctl restart video-downloader
sleep 2
echo "  ✓ Gunicorn 服务已启动 (127.0.0.1:5000)"

# ── 6. 验证 Flask 服务 ──
echo "[6/8] 验证 Flask 服务..."
if curl -s http://127.0.0.1:5000/api/platforms | grep -q "platforms"; then
    echo "  ✓ Flask API 响应正常"
else
    echo "  ⚠ Flask API 可能未正常启动，检查日志:"
    journalctl -u video-downloader --no-pager -n 10
fi

# ── 7. 配置 Nginx (不干扰现有网站) ──
echo "[7/8] 配置 Nginx (api.aibuddy.top)..."

# 写入新的 server block，不影响现有配置
cat > /etc/nginx/sites-available/video-downloader-api << 'NGINX_EOF'
server {
    listen 80;
    server_name api.aibuddy.top;

    client_max_body_size 500M;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/video-downloader-api /etc/nginx/sites-enabled/

if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo "  ✓ Nginx 已配置 (api.aibuddy.top → :5000)"
else
    echo "  ⚠ Nginx 配置测试失败，请检查:"
    nginx -t
fi

# ── 8. 防火墙 ──
echo "[8/8] 检查防火墙..."
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    ufw allow 22/tcp 2>/dev/null || true
    echo "  ✓ 防火墙已开放 80/443/22"
else
    echo "  ℹ 无 ufw，请确保安全组开放 80/443 端口"
fi

# ── 完成 ──
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ 服务器部署完成!"
echo ""
echo "  验证命令:"
echo "    curl http://127.0.0.1:5000/api/platforms"
echo "    curl -H 'Host: api.aibuddy.top' http://127.0.0.1/api/platforms"
echo ""
echo "  下一步 (在 Cloudflare 操作):"
echo "    1. DNS 添加 A 记录: api.aibuddy.top → 49.233.146.86"
echo "    2. 代理状态: 开启 (橙色云朵)"
echo "    3. SSL/TLS: 设为 Flexible 或 Full"
echo ""
echo "  然后验证:"
echo "    curl https://api.aibuddy.top/api/platforms"
echo "══════════════════════════════════════════════════"
