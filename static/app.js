/**
 * 视频下载智能体 - 前端逻辑
 */

// ────────── 平台图标颜色映射 ──────────
const PLATFORM_COLORS = {
    'YouTube': '#FF0000',
    'TikTok': '#000000',
    '抖音': '#161823',
    'B站': '#00A1D6',
    'Twitter/X': '#000000',
    'Instagram': '#E4405F',
    'Facebook': '#1877F2',
    'Reddit': '#FF4500',
    'Vimeo': '#1AB7EA',
    'Dailymotion': '#0066DC',
    '西瓜视频': '#FF4256',
    '微博': '#E6162D',
    '小红书': '#FF2442',
    '未知平台': '#5A6378',
};

const PLATFORM_ICONS = {
    'YouTube': 'YT', 'TikTok': 'TT', '抖音': 'DY', 'B站': 'B',
    'Twitter/X': 'X', 'Instagram': 'IG', 'Facebook': 'FB',
    'Reddit': 'R', 'Vimeo': 'V', 'Dailymotion': 'DM',
    '西瓜视频': 'XG', '微博': 'WB', '小红书': 'XHS', '未知平台': '?',
};

// ────────── 状态文本映射 ──────────
const STATUS_TEXT = {
    'pending': '等待中',
    'analyzing': '解析中',
    'downloading': '下载中',
    'processing': '处理中',
    'completed': '已完成',
    'failed': '失败',
    'cancelled': '已取消',
};

// ────────── DOM 元素 ──────────
const $ = (sel) => document.querySelector(sel);
const urlInput = $('#urlInput');
const downloadBtn = $('#downloadBtn');
const taskList = $('#taskList');
const emptyState = $('#emptyState');
const taskCount = $('#taskCount');
const platformHint = $('#platformHint');
const platformHintText = $('#platformHintText');
const platformChips = $('#platformChips');
const toastContainer = $('#toastContainer');

// ────────── 轮询管理 ──────────
let pollInterval = null;
let activeTaskIds = new Set();

// ────────── 初始化 ──────────
function init() {
    loadPlatforms();
    bindEvents();
    fetchTasks();

    // 粘贴板检测
    urlInput.addEventListener('paste', () => {
        setTimeout(() => detectPlatform(), 50);
    });
}

// ────────── 事件绑定 ──────────
function bindEvents() {
    downloadBtn.addEventListener('click', handleDownload);
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleDownload();
    });
    urlInput.addEventListener('input', debounce(() => detectPlatform(), 300));
}

// ────────── 平台检测 ──────────
async function detectPlatform() {
    const url = urlInput.value.trim();
    if (!url) {
        platformHint.style.display = 'none';
        return;
    }

    try {
        const res = await fetch('/api/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await res.json();

        if (data.supported) {
            platformHint.style.display = 'flex';
            platformHintText.textContent = `检测到平台: ${data.platform} - 点击下载即可获取无水印视频`;
        } else {
            platformHint.style.display = 'flex';
            platformHintText.textContent = `未识别的平台，将尝试通用下载器`;
        }
    } catch (e) {
        // 静默失败
    }
}

// ────────── 提交下载 ──────────
async function handleDownload() {
    const url = urlInput.value.trim();
    if (!url) {
        showToast('请输入视频链接', 'error');
        urlInput.focus();
        return;
    }

    downloadBtn.disabled = true;
    const originalContent = downloadBtn.innerHTML;
    downloadBtn.innerHTML = '<div class="spinner"></div><span>提交中...</span>';

    try {
        const res = await fetch('/api/download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await res.json();

        if (data.success) {
            showToast(`已开始下载: ${data.task.platform}`, 'success');
            urlInput.value = '';
            platformHint.style.display = 'none';
            activeTaskIds.add(data.task.task_id);
            renderTask(data.task);
            startPolling();
        } else {
            showToast(data.error || '下载失败', 'error');
        }
    } catch (e) {
        showToast('网络错误，请重试', 'error');
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = originalContent;
    }
}

// ────────── 获取任务列表 ──────────
async function fetchTasks() {
    try {
        const res = await fetch('/api/tasks');
        const data = await res.json();

        if (data.tasks.length === 0) {
            emptyState.style.display = 'flex';
            taskList.innerHTML = '';
            taskList.appendChild(emptyState);
            taskCount.textContent = '0 个任务';
            return;
        }

        emptyState.style.display = 'none';
        taskCount.textContent = `${data.tasks.length} 个任务`;

        // 渲染所有任务
        taskList.innerHTML = '';
        data.tasks.forEach(task => {
            renderTask(task, false);
            if (['pending', 'analyzing', 'downloading', 'processing'].includes(task.status)) {
                activeTaskIds.add(task.task_id);
            }
        });

        if (activeTaskIds.size > 0) {
            startPolling();
        }
    } catch (e) {
        console.error('获取任务失败:', e);
    }
}

// ────────── 轮询活跃任务 ──────────
function startPolling() {
    if (pollInterval) return;

    pollInterval = setInterval(async () => {
        if (activeTaskIds.size === 0) {
            stopPolling();
            return;
        }

        try {
            const res = await fetch('/api/tasks');
            const data = await res.json();

            data.tasks.forEach(task => {
                if (activeTaskIds.has(task.task_id)) {
                    renderTask(task, true);

                    // 如果任务已完成或失败，移出活跃列表
                    if (['completed', 'failed', 'cancelled'].includes(task.status)) {
                        activeTaskIds.delete(task.task_id);
                        if (task.status === 'completed') {
                            showToast(`下载完成: ${task.title || '视频'}`, 'success');
                        } else if (task.status === 'failed') {
                            showToast(`下载失败: ${task.error}`, 'error');
                        }
                    }
                }
            });

            if (activeTaskIds.size === 0) {
                stopPolling();
            }
        } catch (e) {
            console.error('轮询失败:', e);
        }
    }, 1000);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// ────────── 渲染任务卡片 ──────────
function renderTask(task, updateOnly = false) {
    let card = document.getElementById(`task-${task.task_id}`);

    if (!card) {
        emptyState.style.display = 'none';
        card = document.createElement('div');
        card.id = `task-${task.task_id}`;
        card.className = `task-card status-${task.status}`;
        taskList.prepend(card);
    }

    card.className = `task-card status-${task.status}`;

    const statusText = STATUS_TEXT[task.status] || task.status;
    const platformColor = PLATFORM_COLORS[task.platform] || '#5A6378';
    const platformIcon = PLATFORM_ICONS[task.platform] || '?';

    const isActive = ['pending', 'analyzing', 'downloading', 'processing'].includes(task.status);

    // 缩略图
    let thumbHtml = '';
    if (task.thumbnail) {
        thumbHtml = `<img class="task-thumb" src="${escapeHtml(task.thumbnail)}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex';">
                     <div class="task-thumb-placeholder" style="display:none;">${getVideoIcon()}</div>`;
    } else {
        thumbHtml = `<div class="task-thumb-placeholder">${getVideoIcon()}</div>`;
    }

    // 状态标签
    let badgeHtml = '';
    if (isActive) {
        badgeHtml = `<span class="task-status-badge status-badge-${task.status}">
                        <span class="spinner"></span>${statusText}
                     </span>`;
    } else if (task.status === 'completed') {
        badgeHtml = `<span class="task-status-badge status-badge-completed">${getCheckIcon()}${statusText}</span>`;
    } else if (task.status === 'failed') {
        badgeHtml = `<span class="task-status-badge status-badge-failed">${statusText}</span>`;
    }

    // 进度条
    let progressHtml = '';
    if (isActive || task.status === 'completed') {
        const progressClass = task.status === 'completed' ? 'completed' : task.status;
        const progressWidth = task.status === 'completed' ? 100 : task.progress;
        progressHtml = `
            <div class="task-progress">
                <div class="progress-bar-wrapper">
                    <div class="progress-bar">
                        <div class="progress-fill ${progressClass}" style="width: ${progressWidth}%"></div>
                    </div>
                    <span class="progress-percent">${progressWidth.toFixed(0)}%</span>
                </div>
                ${isActive ? `
                <div class="progress-detail">
                    ${task.speed ? `<span>${getSpeedIcon()} ${task.speed}</span>` : ''}
                    ${task.eta ? `<span>${getClockIcon()} 剩余 ${task.eta}</span>` : ''}
                    ${task.file_size_str ? `<span>${getSizeIcon()} ${task.file_size_str}</span>` : ''}
                </div>` : ''}
            </div>
        `;
    }

    // 错误信息
    let errorHtml = '';
    if (task.status === 'failed' && task.error) {
        errorHtml = `<div class="task-error">${getAlertIcon()} ${escapeHtml(task.error)}</div>`;
    }

    // 操作按钮
    let actionsHtml = '';
    if (task.status === 'completed') {
        actionsHtml = `
            <button class="task-action-btn btn-download" onclick="downloadFile('${task.task_id}')" title="下载文件">
                ${getDownloadIcon()}
            </button>
            <button class="task-action-btn btn-watermark" onclick="openWatermarkModal('${task.task_id}')" title="去除水印">
                ${getEraserIcon()}
            </button>
            <button class="task-action-btn btn-delete" onclick="deleteTask('${task.task_id}')" title="删除">
                ${getTrashIcon()}
            </button>
        `;
    } else if (task.status === 'failed') {
        actionsHtml = `
            <button class="task-action-btn btn-delete" onclick="deleteTask('${task.task_id}')" title="删除">
                ${getTrashIcon()}
            </button>
        `;
    }

    card.innerHTML = `
        <div class="task-header">
            ${thumbHtml}
            <div class="task-info">
                <div class="task-title">${escapeHtml(task.title || task.url)}</div>
                <div class="task-meta">
                    <span class="task-platform">
                        <span class="platform-chip-icon" style="background:${platformColor}">${platformIcon}</span>
                        ${escapeHtml(task.platform)}
                    </span>
                    ${task.author ? `<span class="task-author">${getUserIcon()} ${escapeHtml(task.author)}</span>` : ''}
                    ${task.duration ? `<span class="task-duration">${getClockIcon()} ${task.duration}</span>` : ''}
                    ${task.watermark_free ? `<span class="watermark-free-tag">${getShieldIcon()} 无水印</span>` : ''}
                    ${badgeHtml}
                </div>
            </div>
            <div class="task-actions">${actionsHtml}</div>
        </div>
        ${progressHtml}
        ${errorHtml}
    `;
}

// ────────── 下载文件 ──────────
function downloadFile(taskId) {
    window.open(`/api/download/${taskId}`, '_blank');
}

// ────────── 删除任务 ──────────
async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务及其文件吗？')) return;

    try {
        const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
        if (res.ok) {
            const card = document.getElementById(`task-${taskId}`);
            if (card) {
                card.style.animation = 'slideIn 0.2s ease reverse';
                setTimeout(() => card.remove(), 200);
            }
            activeTaskIds.delete(taskId);
            showToast('已删除', 'info');

            // 检查是否还有任务
            setTimeout(() => {
                if (taskList.children.length === 0) {
                    emptyState.style.display = 'flex';
                    taskList.appendChild(emptyState);
                    taskCount.textContent = '0 个任务';
                } else {
                    const count = taskList.querySelectorAll('.task-card').length;
                    taskCount.textContent = `${count} 个任务`;
                }
            }, 250);
        }
    } catch (e) {
        showToast('删除失败', 'error');
    }
}

// ────────── 加载平台列表 ──────────
async function loadPlatforms() {
    try {
        const res = await fetch('/api/platforms');
        const data = await res.json();

        platformChips.innerHTML = '';
        data.platforms.forEach(p => {
            const chip = document.createElement('div');
            chip.className = 'platform-chip';
            chip.innerHTML = `
                <span class="platform-chip-icon" style="background:${p.color}">${p.icon}</span>
                <span>${p.name}</span>
            `;
            platformChips.appendChild(chip);
        });
    } catch (e) {
        // 使用默认列表
        const defaults = [
            { name: 'YouTube', icon: 'YT', color: '#FF0000' },
            { name: 'TikTok', icon: 'TT', color: '#000000' },
            { name: '抖音', icon: 'DY', color: '#161823' },
            { name: 'B站', icon: 'B', color: '#00A1D6' },
            { name: 'Twitter/X', icon: 'X', color: '#000000' },
            { name: 'Instagram', icon: 'IG', color: '#E4405F' },
        ];
        platformChips.innerHTML = '';
        defaults.forEach(p => {
            const chip = document.createElement('div');
            chip.className = 'platform-chip';
            chip.innerHTML = `
                <span class="platform-chip-icon" style="background:${p.color}">${p.icon}</span>
                <span>${p.name}</span>
            `;
            platformChips.appendChild(chip);
        });
    }
}

// ────────── Toast 通知 ──────────
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = '';
    switch (type) {
        case 'success': icon = getCheckIcon(); break;
        case 'error': icon = getAlertIcon(); break;
        default: icon = getInfoIcon(); break;
    }

    toast.innerHTML = `<span class="toast-icon">${icon}</span><span>${escapeHtml(message)}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ────────── 工具函数 ──────────
function debounce(fn, delay) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ────────── SVG 图标 ──────────
function getVideoIcon() {
    return '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>';
}
function getDownloadIcon() {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>';
}
function getTrashIcon() {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>';
}
function getCheckIcon() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>';
}
function getAlertIcon() {
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
}
function getInfoIcon() {
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';
}
function getUserIcon() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>';
}
function getClockIcon() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
}
function getSpeedIcon() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>';
}
function getSizeIcon() {
    return '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
}
function getShieldIcon() {
    return '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>';
}
function getEraserIcon() {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 20H9L4 15a2 2 0 0 1 0-2.83l9.17-9.17a2 2 0 0 1 2.83 0l5 5a2 2 0 0 1 0 2.83L11 20"/><line x1="8" y1="8" x2="16" y2="16"/></svg>';
}

// ────────── 去水印功能 ──────────

let wmState = {
    taskId: null,
    videoW: 0,
    videoH: 0,
    displayScale: 1,
    selX: 0,
    selY: 0,
    selW: 0,
    selH: 0,
    isDragging: false,
    dragStartX: 0,
    dragStartY: 0,
};

function openWatermarkModal(taskId) {
    const task = downloader_cache[taskId];
    if (!task) {
        // 从服务器获取
        fetch(`/api/tasks/${taskId}`)
            .then(r => r.json())
            .then(t => {
                downloader_cache[taskId] = t;
                buildWatermarkModal(t);
            });
    } else {
        buildWatermarkModal(task);
    }
}

function buildWatermarkModal(task) {
    // 移除已有的模态框
    const existing = document.getElementById('wmModalOverlay');
    if (existing) existing.remove();

    wmState.taskId = task.task_id;

    const overlay = document.createElement('div');
    overlay.id = 'wmModalOverlay';
    overlay.className = 'wm-modal-overlay';

    overlay.innerHTML = `
        <div class="wm-modal" onclick="event.stopPropagation()">
            <div class="wm-modal-header">
                <h3>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--warning)">
                        <path d="M20 20H9L4 15a2 2 0 0 1 0-2.83l9.17-9.17a2 2 0 0 1 2.83 0l5 5a2 2 0 0 1 0 2.83L11 20"/>
                    </svg>
                    去除水印
                </h3>
                <button class="wm-modal-close" onclick="closeWatermarkModal()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <p class="wm-modal-desc">
                在视频画面上拖拽框选水印区域，或点击下方预设位置快速选择。选好后点击「去除水印」按钮。
            </p>
            <div class="wm-presets">
                <button class="wm-preset-btn" onclick="setPreset('tl')">↖ 左上角</button>
                <button class="wm-preset-btn" onclick="setPreset('tr')">↗ 右上角</button>
                <button class="wm-preset-btn" onclick="setPreset('bl')">↙ 左下角</button>
                <button class="wm-preset-btn" onclick="setPreset('br')">↘ 右下角</button>
                <button class="wm-preset-btn" onclick="setPreset('center')">⊙ 正中间</button>
            </div>
            <div class="wm-video-container" id="wmVideoContainer">
                <video id="wmVideo" src="/api/download/${task.task_id}" muted controls preload="metadata"></video>
                <div class="wm-select-overlay" id="wmOverlay"></div>
                <div class="wm-selection-box" id="wmSelBox" style="display:none;"></div>
            </div>
            <div class="wm-coords">
                <div class="wm-coord-item"><span class="wm-coord-label">X:</span><span class="wm-coord-value" id="wmCoordX">0</span></div>
                <div class="wm-coord-item"><span class="wm-coord-label">Y:</span><span class="wm-coord-value" id="wmCoordY">0</span></div>
                <div class="wm-coord-item"><span class="wm-coord-label">宽:</span><span class="wm-coord-value" id="wmCoordW">0</span></div>
                <div class="wm-coord-item"><span class="wm-coord-label">高:</span><span class="wm-coord-value" id="wmCoordH">0</span></div>
                <div class="wm-coord-item" style="margin-left:auto;"><span class="wm-coord-label">视频:</span><span class="wm-coord-value" id="wmVideoSize">--</span></div>
            </div>
            <div id="wmProcessing" style="display:none;"></div>
            <div class="wm-modal-actions">
                <button class="wm-btn-cancel" onclick="closeWatermarkModal()">取消</button>
                <button class="wm-btn-apply" id="wmApplyBtn" onclick="applyWatermark()" disabled>
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                    <span>去除水印</span>
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) closeWatermarkModal();
    });

    // 等待视频加载后初始化
    const video = document.getElementById('wmVideo');
    video.addEventListener('loadedmetadata', () => {
        initWatermarkSelection();
    });
}

function initWatermarkSelection() {
    const video = document.getElementById('wmVideo');
    const overlay = document.getElementById('wmOverlay');
    const container = document.getElementById('wmVideoContainer');

    // 获取视频实际尺寸和显示尺寸
    wmState.videoW = video.videoWidth;
    wmState.videoH = video.videoHeight;

    // 计算显示缩放比
    const rect = video.getBoundingClientRect();
    wmState.displayScale = rect.width / wmState.videoW;

    // 设置 overlay 范围
    overlay.style.left = rect.left - container.getBoundingClientRect().left + 'px';
    overlay.style.top = rect.top - container.getBoundingClientRect().top + 'px';
    overlay.style.width = rect.width + 'px';
    overlay.style.height = rect.height + 'px';

    document.getElementById('wmVideoSize').textContent = `${wmState.videoW}x${wmState.videoH}`;

    // 鼠标拖拽选区
    overlay.addEventListener('mousedown', startDrag);
    overlay.addEventListener('touchstart', startDrag, { passive: false });
    document.addEventListener('mousemove', onDrag);
    document.addEventListener('touchmove', onDrag, { passive: false });
    document.addEventListener('mouseup', endDrag);
    document.addEventListener('touchend', endDrag);
}

function startDrag(e) {
    e.preventDefault();
    const overlay = document.getElementById('wmOverlay');
    const rect = overlay.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;

    wmState.isDragging = true;
    wmState.dragStartX = point.clientX - rect.left;
    wmState.dragStartY = point.clientY - rect.top;
    wmState.selX = wmState.dragStartX;
    wmState.selY = wmState.dragStartY;
    wmState.selW = 0;
    wmState.selH = 0;

    updateSelectionBox();
}

function onDrag(e) {
    if (!wmState.isDragging) return;
    e.preventDefault();

    const overlay = document.getElementById('wmOverlay');
    const rect = overlay.getBoundingClientRect();
    const point = e.touches ? e.touches[0] : e;

    let curX = point.clientX - rect.left;
    let curY = point.clientY - rect.top;

    // 限制在 overlay 范围内
    curX = Math.max(0, Math.min(curX, rect.width));
    curY = Math.max(0, Math.min(curY, rect.height));

    wmState.selX = Math.min(wmState.dragStartX, curX);
    wmState.selY = Math.min(wmState.dragStartY, curY);
    wmState.selW = Math.abs(curX - wmState.dragStartX);
    wmState.selH = Math.abs(curY - wmState.dragStartY);

    updateSelectionBox();
}

function endDrag() {
    if (!wmState.isDragging) return;
    wmState.isDragging = false;

    // 如果选区太小，忽略
    if (wmState.selW < 5 || wmState.selH < 5) {
        document.getElementById('wmSelBox').style.display = 'none';
        wmState.selW = 0;
        wmState.selH = 0;
        updateCoords();
        return;
    }
    updateCoords();
}

function updateSelectionBox() {
    const box = document.getElementById('wmSelBox');
    const overlay = document.getElementById('wmOverlay');
    const container = document.getElementById('wmVideoContainer');
    const overlayRect = overlay.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();

    box.style.display = 'block';
    box.style.left = (overlayRect.left - containerRect.left + wmState.selX) + 'px';
    box.style.top = (overlayRect.top - containerRect.top + wmState.selY) + 'px';
    box.style.width = wmState.selW + 'px';
    box.style.height = wmState.selH + 'px';

    // 显示坐标标签
    const realW = Math.round(wmState.selW / wmState.displayScale);
    const realH = Math.round(wmState.selH / wmState.displayScale);
    box.setAttribute('data-label', `${realW}x${realH}`);

    updateCoords();
}

function updateCoords() {
    // 将显示坐标转换为视频实际坐标
    const realX = Math.round(wmState.selX / wmState.displayScale);
    const realY = Math.round(wmState.selY / wmState.displayScale);
    const realW = Math.round(wmState.selW / wmState.displayScale);
    const realH = Math.round(wmState.selH / wmState.displayScale);

    document.getElementById('wmCoordX').textContent = realX;
    document.getElementById('wmCoordY').textContent = realY;
    document.getElementById('wmCoordW').textContent = realW;
    document.getElementById('wmCoordH').textContent = realH;

    // 启用/禁用按钮
    const btn = document.getElementById('wmApplyBtn');
    btn.disabled = (realW < 5 || realH < 5);
}

function setPreset(position) {
    const margin = 0.02; // 边距 2%
    const vw = wmState.videoW;
    const vh = wmState.videoH;
    const wmW = Math.round(vw * 0.25); // 水印默认宽度 25%
    const wmH = Math.round(vh * 0.10); // 水印默认高度 10%
    const offsetX = Math.round(vw * margin);
    const offsetY = Math.round(vh * margin);

    let realX, realY;

    switch (position) {
        case 'tl': realX = offsetX; realY = offsetY; break;
        case 'tr': realX = vw - wmW - offsetX; realY = offsetY; break;
        case 'bl': realX = offsetX; realY = vh - wmH - offsetY; break;
        case 'br': realX = vw - wmW - offsetX; realY = vh - wmH - offsetY; break;
        case 'center': realX = Math.round((vw - wmW) / 2); realY = Math.round((vh - wmH) / 2); break;
    }

    // 转换为显示坐标
    wmState.selX = realX * wmState.displayScale;
    wmState.selY = realY * wmState.displayScale;
    wmState.selW = wmW * wmState.displayScale;
    wmState.selH = wmH * wmState.displayScale;

    updateSelectionBox();
}

async function applyWatermark() {
    const realX = Math.round(wmState.selX / wmState.displayScale);
    const realY = Math.round(wmState.selY / wmState.displayScale);
    const realW = Math.round(wmState.selW / wmState.displayScale);
    const realH = Math.round(wmState.selH / wmState.displayScale);

    if (realW < 5 || realH < 5) {
        showToast('请先选择水印区域', 'error');
        return;
    }

    // 显示处理中
    const btn = document.getElementById('wmApplyBtn');
    const processing = document.getElementById('wmProcessing');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner"></div><span>处理中...</span>';
    processing.style.display = 'flex';
    processing.className = 'wm-processing';
    processing.innerHTML = '<div class="spinner"></div>正在使用 ffmpeg 去除水印，请稍候...';

    try {
        const res = await fetch(`/api/tasks/${wmState.taskId}/watermark`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ x: realX, y: realY, w: realW, h: realH }),
        });
        const data = await res.json();

        if (data.success) {
            showToast('水印去除成功！', 'success');
            closeWatermarkModal();
            // 刷新任务列表
            fetchTasks();
        } else {
            showToast(data.error || '去水印失败', 'error');
            btn.disabled = false;
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg><span>去除水印</span>';
            processing.style.display = 'none';
        }
    } catch (e) {
        showToast('网络错误', 'error');
        btn.disabled = false;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg><span>去除水印</span>';
        processing.style.display = 'none';
    }
}

function closeWatermarkModal() {
    const overlay = document.getElementById('wmModalOverlay');
    if (overlay) overlay.remove();
    // 清理事件监听
    document.removeEventListener('mousemove', onDrag);
    document.removeEventListener('touchmove', onDrag);
    document.removeEventListener('mouseup', endDrag);
    document.removeEventListener('touchend', endDrag);
}

// 任务缓存（用于去水印模态框）
const downloader_cache = {};

// ────────── 启动 ──────────
init();
