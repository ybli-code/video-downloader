/**
 * Cloudflare Worker - 视频下载 API 反向代理
 *
 * 将微信小程序的 HTTPS 请求转发到你的服务器 HTTP API
 * 解决微信小程序要求 HTTPS + 域名备案的问题
 *
 * 部署步骤:
 * 1. 登录 Cloudflare Dashboard → Workers & Pages
 * 2. Create Worker → 粘贴此代码
 * 3. 修改下方 SERVER_ORIGIN 为你的服务器地址
 * 4. 保存并部署
 * 5. 在微信小程序后台配置 Worker URL 为合法域名
 */

// ════════════════ 配置区 ════════════════

// 你的服务器地址 (部署 Flask 后端的 IP:端口)
// 如果服务器在国内，直接用 IP；如果用了 Nginx，用 80 端口
const SERVER_ORIGIN = 'http://49.233.146.86:5000';

// ════════════════ 代理逻辑 ════════════════

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = SERVER_ORIGIN + url.pathname + url.search;

    // CORS 预检请求
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    // 构建转发请求
    const proxyHeaders = new Headers(request.headers);
    proxyHeaders.delete('host');
    proxyHeaders.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP') || '');
    proxyHeaders.set('X-Real-IP', request.headers.get('CF-Connecting-IP') || '');

    const proxyRequest = new Request(targetUrl, {
      method: request.method,
      headers: proxyHeaders,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
      redirect: 'follow',
    });

    try {
      const response = await fetch(proxyRequest);

      // 构建响应，添加 CORS 头
      const respHeaders = new Headers(response.headers);
      corsHeaders().forEach((v, k) => respHeaders.set(k, v));

      // 流式返回 (支持大文件下载)
      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: respHeaders,
      });

    } catch (err) {
      return new Response(JSON.stringify({
        error: '服务器连接失败',
        detail: err.message,
        server: SERVER_ORIGIN,
      }), {
        status: 502,
        headers: { 'Content-Type': 'application/json', ...corsHeaders() },
      });
    }
  },
};

function corsHeaders() {
  return new Headers({
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS, HEAD',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
    'Access-Control-Max-Age': '86400',
  });
}
