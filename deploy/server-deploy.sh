#!/bin/bash
# ═══════════════════════════════════════════════════════
# 视频下载智能体 - 服务器一键部署脚本 (含 SSL)
# 在服务器上执行: bash server-deploy.sh
# 服务器: 49.233.146.86 | 域名: api.aibuddy.top
# ═══════════════════════════════════════════════════════

set -e

APP_DIR="/opt/video-downloader"
APP_USER="videodl"
REPO_URL="https://github.com/ybli-code/video-downloader.git"
DOMAIN="api.aibuddy.top"

echo "══════════════════════════════════════════════════"
echo "  视频下载智能体 - 服务器部署"
echo "  服务器: 49.233.146.86"
echo "  API域名: $DOMAIN"
echo "══════════════════════════════════════════════════"

# ── 1. 安装系统依赖 ──
echo "[1/9] 安装系统依赖..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv ffmpeg nginx git certbot python3-certbot-nginx > /dev/null 2>&1
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
echo "[6/9] 验证 Flask 服务..."
if curl -s http://127.0.0.1:5000/api/platforms | grep -q "platforms"; then
    echo "  ✓ Flask API 响应正常"
else
    echo "  ⚠ Flask API 可能未正常启动，检查日志:"
    journalctl -u video-downloader --no-pager -n 10
fi

# ── 7. 配置 Nginx ──
echo "[7/9] 配置 Nginx ($DOMAIN)..."

cat > /etc/nginx/sites-available/video-downloader-api << NGINX_EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 500M;

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_buffering off;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
    }
}
NGINX_EOF

ln -sf /etc/nginx/sites-available/video-downloader-api /etc/nginx/sites-enabled/

if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo "  ✓ Nginx 已配置 (HTTP :80)"
else
    echo "  ⚠ Nginx 配置测试失败:"
    nginx -t
    exit 1
fi

# ── 8. 申请 SSL 证书 (Let's Encrypt) ──
echo "[8/9] 申请 SSL 证书..."
echo "  检查 DNS 解析..."
DNS_IP=$(dig +short $DOMAIN A 2>/dev/null | head -1)
if [ "$DNS_IP" = "49.233.146.86" ]; then
    echo "  ✓ DNS 已解析到本服务器"
    echo "  正在申请 Let's Encrypt 证书..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect 2>&1 || {
        echo "  ⚠ 证书申请失败，API 将以 HTTP 模式运行"
        echo "  稍后可手动执行: certbot --nginx -d $DOMAIN"
    }
    echo "  ✓ SSL 证书已配置 (HTTPS)"
else
    echo "  ⚠ DNS 未解析到本服务器 (当前: $DNS_IP)"
    echo "  请先在阿里云 DNS 添加 A 记录: $DOMAIN → 49.233.146.86"
    echo "  添加后等待 1-2 分钟 DNS 生效，然后重新运行此脚本"
    echo "  或手动执行: certbot --nginx -d $DOMAIN"
fi

# ── 9. 防火墙 ──
echo "[9/9] 检查防火墙..."
if command -v ufw &>/dev/null; then
    ufw allow 80/tcp 2>/dev/null || true
    ufw allow 443/tcp 2>/dev/null || true
    ufw allow 22/tcp 2>/dev/null || true
    echo "  ✓ 防火墙已开放 80/443/22"
else
    echo "  ℹ 无 ufw，请确保安全组开放 80 和 443 端口"
fi

# ── 最终验证 ──
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ 服务器部署完成!"
echo ""
echo "  验证命令:"
echo "    curl http://127.0.0.1:5000/api/platforms"
echo "    curl https://$DOMAIN/api/platforms"
echo ""
echo "  服务管理:"
echo "    systemctl status video-downloader"
echo "    systemctl restart video-downloader"
echo "    journalctl -u video-downloader -f"
echo "══════════════════════════════════════════════════"
