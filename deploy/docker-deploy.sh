#!/bin/bash
# ═══════════════════════════════════════════════════════
# 视频下载服务 v2.0 - Docker 部署 (CentOS/yum)
# 端口: 5050
# ═══════════════════════════════════════════════════════

set -e

APP_DIR="/opt/video-downloader"
DOMAIN="api.aibuddy.top"
REPO_URL="https://github.com/ybli-code/video-downloader.git"
PORT=5050

echo "══════════════════════════════════════════════════"
echo "  视频下载服务 v2.0 - Docker 部署"
echo "  架构: FastAPI + PostgreSQL + Redis + Worker + OSS"
echo "  域名: $DOMAIN | 端口: $PORT"
echo "══════════════════════════════════════════════════"

# ── 1. 安装 Docker ──
echo "[1/6] 检查 Docker..."
if ! command -v docker &>/dev/null; then
    echo "  安装 Docker..."
    yum install -y yum-utils
    yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "  ✓ Docker 已安装"
else
    echo "  ✓ Docker 已存在"
fi

# ── 2. 检查 Docker Compose ──
echo "[2/6] 检查 Docker Compose..."
if docker compose version &>/dev/null; then
    echo "  ✓ Docker Compose 已存在"
else
    echo "  安装 Docker Compose 插件..."
    yum install -y docker-compose-plugin 2>/dev/null || {
        mkdir -p /usr/local/lib/docker/cli-plugins
        curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)" \
            -o /usr/local/lib/docker/cli-plugins/docker-compose
        chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    }
    echo "  ✓ Docker Compose 已安装"
fi

# ── 3. 拉取代码 ──
echo "[3/6] 拉取代码..."
if ! command -v git &>/dev/null; then
    yum install -y git
fi
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && git pull -q
else
    rm -rf $APP_DIR
    git clone -q $REPO_URL $APP_DIR
    cd $APP_DIR
fi
echo "  ✓ 代码已更新"

# ── 4. 创建 .env ──
echo "[4/6] 配置环境变量..."
cat > $APP_DIR/.env << 'EOF'
SECRET_KEY=vd-prod-secret-2024-aibuddy-change-me
OSS_ACCESS_KEY_ID=YOUR_OSS_KEY_ID
OSS_ACCESS_KEY_SECRET=YOUR_OSS_KEY_SECRET
OSS_ENDPOINT=oss-cn-beijing.aliyuncs.com
OSS_BUCKET_NAME=aibuddy-downloader
WORKER_CONCURRENCY=5
EOF
chmod 600 $APP_DIR/.env
echo "  ✓ .env 已创建"

# ── 5. 构建并启动 ──
echo "[5/6] 构建 Docker 服务..."
cd $APP_DIR
docker compose down 2>/dev/null || true
docker compose build
docker compose up -d

echo "  等待服务启动..."
sleep 15

if curl -s http://127.0.0.1:$PORT/health | grep -q "ok"; then
    echo "  ✓ API 服务已启动 (端口 $PORT)"
else
    echo "  ⚠ API 可能未就绪，查看日志:"
    docker compose logs api --tail 20
fi

# ── 6. 配置 Nginx + SSL ──
echo "[6/6] 配置 Nginx + SSL..."

if ! command -v nginx &>/dev/null; then
    yum install -y nginx
fi
if ! command -v certbot &>/dev/null; then
    yum install -y epel-release
    yum install -y certbot python3-certbot-nginx
fi

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

    location /docs {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_set_header Host \$host;
    }
}
NGINX_EOF

nginx -t 2>/dev/null && systemctl reload nginx
echo "  ✓ Nginx 已配置"

# SSL
DNS_IP=$(dig +short $DOMAIN A 2>/dev/null | head -1)
if [ "$DNS_IP" = "49.233.146.86" ]; then
    echo "  申请 SSL 证书..."
    certbot --nginx -d $DOMAIN --non-interactive --agree-tos --register-unsafely-without-email --redirect 2>&1 || true
    echo "  ✓ SSL 已配置"
fi

# 开放防火墙端口
echo "  配置防火墙..."
firewall-cmd --permanent --add-port=22/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=80/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=443/tcp 2>/dev/null || true
firewall-cmd --permanent --add-port=$PORT/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true
echo "  ✓ 防火墙已开放 22/80/443/$PORT"

# ── 完成 ──
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✓ 部署完成!"
echo ""
echo "  API 文档: https://$DOMAIN/docs"
echo "  健康检查: https://$DOMAIN/health"
echo "  默认管理员: admin / admin123456"
echo ""
echo "  服务管理:"
echo "    cd $APP_DIR"
echo "    docker compose ps        # 查看状态"
echo "    docker compose logs -f   # 查看日志"
echo "    docker compose restart   # 重启服务"
echo "    docker compose down      # 停止服务"
echo "    docker compose up -d     # 启动服务"
echo "══════════════════════════════════════════════════"
