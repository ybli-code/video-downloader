/**
 * Cloudflare Worker - 视频下载 API 反向代理
 * 转发到服务器端口 5050
 */

const SERVER_ORIGIN = 'http://49.233.146.86:5050';

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const targetUrl = SERVER_ORIGIN + url.pathname + url.search;

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(),
      });
    }

    const proxyHeaders = new Headers(request.headers);
    proxyHeaders.delete('host');
    proxyHeaders.set('X-Forwarded-For', request.headers.get('CF-Connecting-IP') || '');

    const proxyRequest = new Request(targetUrl, {
      method: request.method,
      headers: proxyHeaders,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : undefined,
      redirect: 'follow',
    });

    try {
      const response = await fetch(proxyRequest);
      const respHeaders = new Headers(response.headers);
      corsHeaders().forEach((v, k) => respHeaders.set(k, v));

      return new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: respHeaders,
      });
    } catch (err) {
      return new Response(JSON.stringify({
        error: '服务器连接失败',
        detail: err.message,
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
