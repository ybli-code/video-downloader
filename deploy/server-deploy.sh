#!/bin/bash
# ═══════════════════════════════════════════════════════
# 视频下载智能体 - 服务器部署脚本 (CentOS/yum)
# 服务器: 49.233.146.86 | 端口: 5050 | 域名: api.aibuddy.top
# ═══════════════════════════════════════════════════════

set -e

APP_DIR="/opt/video-downloader"
APP_USER="videodl"
REPO_URL="https://github.com/ybli-code/video-downloader.git"
DOMAIN="api.aibuddy.top"
PORT=5050

echo "══════════════════════════════════════════════════"
echo "  视频下载智能体 - 服务器部署"
echo "  服务器: 49.233.146.86 | 端口: $PORT"
echo "  API域名: $DOMAIN"
echo "══════════════════════════════════════════════════"

# ── 1. 安装系统依赖 ──
echo "[1/9] 安装系统依赖..."
yum install -y epel-release
yum install -y python3 python3-pip ffmpeg nginx git certbot python3-certbot-nginx
echo "  ✓ Python3 + ffmpeg + nginx + certbot 已安装"

# ── 2. 创建专用用户 ──
echo "[2/9] 创建服务用户..."
if ! id -u $APP_USER &>/dev/null; then
    useradd -r -s /bin/false $APP_USER
fi
echo "  ✓ 用户 $APP_USER 已就绪"

# ── 3. 拉取代码 ──
echo "[3/9] 拉取代码..."
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull -q
else
    rm -rf $APP_DIR
    git clone -q $REPO_URL $APP_DIR
fi
chown -R $APP_USER:$APP_USER $APP_DIR
echo "  ✓ 代码已部署到 $APP_DIR"

# ── 4. 创建虚拟环境 & 安装依赖 ──
echo "[4/9] 安装 Python 依赖..."
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER venv/bin/pip install --upgrade pip -q
sudo -u $APP_USER venv/bin/pip install -r requirements.txt -q
echo "  ✓ Python 依赖安装完成"

# ── 5. 创建 systemd 服务 ──
echo "[5/9] 配置 systemd 服务..."
cat > /etc/systemd/system/video-downloader.service << EOF
[Unit]
Description=Video Downloader API
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:$PORT --timeout 300 --access-logfile - --error-logfile - app:app
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
echo "  ✓ Gunicorn 服务已启动 (127.0.0.1:$PORT)"

# ── 6. 验证 Flask 服务 ──
echo "[6/9] 验证服务..."
if curl -s http://127.0.0.1:$PORT/api/platforms | grep -q "platforms"; then
    echo "  ✓ API 响应正常"
else
    echo "  ⚠ 检查日志:"
    journalctl -u video-downloader --no-pager -n 10
fi

# ── 7. 配置 Nginx ──
echo "[7/9] 配置 Nginx ($DOMAIN)..."

cat > /etc/nginx/conf.d/video-downloader-api.conf << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 500M;

    location /api/ {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
    }
}
NGINX_EOF

nginx -t 2>/dev/null && systemctl reload nginx
echo "  ✓ Nginx 已配置"

# ── 8. SSL 证书 ──
echo "[8/9] 申请 SSL 证书..."
DNS_IP=$(dig +short $DOMAIN A 2>/dev/null | head -1)
if [ "$DNS_IP" = "49.233.146.86" ]; then
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect 2>&1 || {
        echo "  ⚠ 证书申请失败，稍后执行: certbot --nginx -d $DOMAIN"
    }
    echo "  ✓ SSL 已配置"
else
    echo "  ⚠ DNS 未解析到本服务器 (当前: $DNS_IP)"
fi

# ── 9. 防火墙 ──
echo "[9/9] 配置防火墙..."
firewall-cmd --permanent --add-port=22/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=$PORT/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true
echo "  ✓ 防火墙已开放 22/80/443/$PORT"

echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ 部署完成!"
echo "  API: https://$DOMAIN/api/platforms"
echo "  文档: https://$DOMAIN/docs"
echo "══════════════════════════════════════════════════"
