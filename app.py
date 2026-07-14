#!/usr/bin/env python3
"""
视频下载智能体 - Web 服务
基于 Flask + yt-dlp，提供 RESTful API 和 Web 界面
支持 Web / 移动 App / 微信小程序 多端访问
"""

import os
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

from downloader import downloader, detect_platform, Platform

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['JSON_AS_ASCII'] = False
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# 跨域支持：允许移动 App 和小程序访问 API
CORS(app, resources={r"/api/*": {"origins": "*"}})


# ──────────────────────────── 页面路由 ────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


# ──────────────────────────── API 路由 ────────────────────────────

@app.route('/api/detect', methods=['POST'])
def api_detect():
    """检测 URL 对应的平台"""
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': '请提供视频链接'}), 400

    platform = detect_platform(url)
    return jsonify({
        'url': url,
        'platform': platform.value,
        'supported': platform != Platform.UNKNOWN,
    })


@app.route('/api/download', methods=['POST'])
def api_download():
    """提交下载任务"""
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    if not url:
        return jsonify({'error': '请提供视频链接'}), 400

    try:
        task = downloader.submit(url)
        return jsonify({
            'success': True,
            'task': task.to_dict(),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'创建下载任务失败: {str(e)}'}), 500


@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """获取所有下载任务"""
    tasks = downloader.get_all_tasks()
    return jsonify({
        'tasks': [t.to_dict() for t in tasks],
        'total': len(tasks),
    })


@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_task_detail(task_id):
    """获取单个下载任务详情"""
    task = downloader.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(task.to_dict())


@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    """删除下载任务及文件"""
    success = downloader.delete_task(task_id)
    if not success:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify({'success': True})


@app.route('/api/download/<task_id>')
def api_download_file(task_id):
    """下载已完成的视频文件"""
    file_path = downloader.get_file_path(task_id)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': '文件不存在或尚未下载完成'}), 404

    filename = os.path.basename(file_path)
    # 生成友好的下载文件名
    task = downloader.get_task(task_id)
    if task and task.title:
        ext = os.path.splitext(filename)[1]
        download_name = f"{task.title}{ext}"
    else:
        download_name = filename

    # 处理中文文件名
    try:
        return send_file(
            file_path,
            as_attachment=True,
            download_name=download_name,
        )
    except Exception:
        return send_file(file_path, as_attachment=True, download_name=filename)


@app.route('/api/tasks/<task_id>/watermark', methods=['POST'])
def api_remove_watermark(task_id):
    """去除视频指定区域的水印"""
    task = downloader.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task.status != 'completed':
        return jsonify({'error': '视频尚未下载完成，无法去除水印'}), 400

    data = request.get_json(silent=True) or {}
    x = int(data.get('x', 0))
    y = int(data.get('y', 0))
    w = int(data.get('w', 0))
    h = int(data.get('h', 0))

    if w <= 0 or h <= 0:
        return jsonify({'error': '水印区域宽高必须大于 0'}), 400

    try:
        output_path = downloader.remove_watermark(task_id, x, y, w, h)
        task = downloader.get_task(task_id)
        return jsonify({
            'success': True,
            'task': task.to_dict(),
        })
    except FileNotFoundError as e:
        return jsonify({'error': str(e)}), 404
    except Exception as e:
        return jsonify({'error': f'去水印失败: {str(e)}'}), 500


@app.route('/api/platforms', methods=['GET'])
def api_platforms():
    """获取支持的平台列表"""
    platforms = [
        {'name': p.value, 'icon': icon, 'color': color}
        for p, icon, color in SUPPORTED_PLATFORMS
    ]
    return jsonify({'platforms': platforms})


SUPPORTED_PLATFORMS = [
    (Platform.YOUTUBE,      'YT',   '#FF0000'),
    (Platform.TIKTOK,       'TT',   '#000000'),
    (Platform.DOUYIN,       'DY',   '#161823'),
    (Platform.BILIBILI,     'B',    '#00A1D6'),
    (Platform.TWITTER,      'X',    '#000000'),
    (Platform.INSTAGRAM,    'IG',   '#E4405F'),
    (Platform.FACEBOOK,     'FB',   '#1877F2'),
    (Platform.REDDIT,       'R',    '#FF4500'),
    (Platform.VIMEO,        'V',    '#1AB7EA'),
    (Platform.DAILYMOTION,  'DM',   '#0066DC'),
    (Platform.IXIGUA,       'XG',   '#FF4256'),
    (Platform.WEIBO,        'WB',   '#E6162D'),
    (Platform.XIAOHONGSHU,  'XHS',  '#FF2442'),
]


# ──────────────────────────── 启动 ────────────────────────────

if __name__ == '__main__':
    print("=" * 50)
    print("  视频下载智能体 - 正在启动...")
    print("  访问地址: http://localhost:5050")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5050, debug=True, threaded=True)
