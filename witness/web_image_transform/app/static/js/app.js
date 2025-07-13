/**
 * 基于RPC接口的图像转换应用
 * 
 * 功能特点：
 * - 支持RPC风格的后端接口
 * - 多阶段任务监控（下载+转换）
 * - 实时WebSocket状态推送
 * - 标准化文件命名
 */

class ImageTransformApp {
    constructor() {
        this.websocket = null;
        this.clientId = null;
        this.isProcessing = false;
        this.styles = [];
        this.currentTask = null;
        this.apiBase = '/api';
        
        this.init();
    }

    async init() {
        try {
            // 生成客户端ID
            this.clientId = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            console.log('客户端ID:', this.clientId);
            
            // 获取会话信息
            await this.getSessionInfo();
            
            // 初始化WebSocket连接
            this.initWebSocket();
            
            // 加载可用风格
            await this.loadStyles();
            
            // 绑定事件
            this.bindEvents();
            
            // 初始化按钮状态
            this.updateSubmitButton();
            
            console.log('应用初始化成功');
        } catch (error) {
            console.error('应用初始化失败:', error);
            this.showError('应用初始化失败: ' + error.message);
        }
    }

    async getSessionInfo() {
        try {
            const response = await fetch(`${this.apiBase}/session`);
            if (response.ok) {
                const sessionInfo = await response.json();
                console.log('会话信息:', sessionInfo);
                this.sessionId = sessionInfo.session_id;
            }
        } catch (error) {
            console.warn('获取会话信息失败:', error);
        }
    }

    initWebSocket() {
        try {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}${this.apiBase}/ws/${this.clientId}`;
            
            console.log('连接WebSocket:', wsUrl);
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                this.updateConnectionStatus(true);
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('收到WebSocket消息:', data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error('解析WebSocket消息失败:', error);
                }
            };

            this.websocket.onclose = (event) => {
                console.log('WebSocket连接已关闭:', event.code, event.reason);
                this.updateConnectionStatus(false);
                
                // 如果不是正常关闭，尝试重连
                if (event.code !== 1000) {
                    setTimeout(() => {
                        console.log('尝试重新连接WebSocket...');
                        this.initWebSocket();
                    }, 3000);
                }
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket错误:', error);
                this.updateConnectionStatus(false);
            };

            // 定期发送心跳
            this.heartbeatInterval = setInterval(() => {
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.websocket.send('ping');
                }
            }, 30000);

        } catch (error) {
            console.error('WebSocket初始化失败:', error);
        }
    }

    handleWebSocketMessage(data) {
        if (data.type === 'task_update' && data.task_id) {
            this.handleTaskUpdate(data);
        }
    }

    handleTaskUpdate(data) {
        console.log(`任务更新 - ${data.task_id}: ${data.status} (${data.progress}%) - ${data.message}`);
        
        // 更新当前任务状态
        if (this.currentTask && this.currentTask.task_id === data.task_id) {
            this.currentTask = { ...this.currentTask, ...data };
        }

        // 更新UI
        this.updateProgressUI(data);

        // 处理不同状态
        switch (data.status) {
            case 'downloading':
                this.updateStatus(`下载中: ${data.message}`, 'info');
                break;
            
            case 'downloaded':
                this.updateStatus('图片下载完成，开始转换...', 'info');
                break;
            
            case 'processing':
                this.updateStatus(`转换中: ${data.message}`, 'info');
                break;
            
            case 'completed':
                this.handleTaskCompleted(data);
                break;
            
            case 'download_failed':
                this.handleTaskFailed(data, '图片下载失败');
                break;
            
            case 'processing_failed':
                this.handleTaskFailed(data, '图像转换失败');
                break;
            
            default:
                this.updateStatus(data.message || '任务状态未知', 'info');
        }
    }

    handleTaskCompleted(data) {
        this.updateStatus('转换完成！', 'success');
        this.updateProgressUI({ progress: 100, message: '转换完成' });
        
        // 获取转换结果
        if (data.result && data.result.output_images && data.result.output_images.length > 0) {
            const outputImage = data.result.output_images[0];
            this.displayResult(outputImage.url);
        } else {
            // 如果WebSocket消息中没有结果，主动获取
            this.getTaskResult(data.task_id);
        }
        
        this.isProcessing = false;
        this.updateSubmitButton();
    }

    handleTaskFailed(data, errorType) {
        const errorMessage = `${errorType}: ${data.message || '未知错误'}`;
        this.updateStatus(errorMessage, 'error');
        this.showError(errorMessage);
        
        this.isProcessing = false;
        this.updateSubmitButton();
        this.hideProgress();
    }

    async loadStyles() {
        try {
            this.showLoading('正在加载风格列表...');
            
            const response = await fetch(`${this.apiBase}/styles`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.styles = await response.json();
            this.populateStyleSelect();
            this.hideLoading();
            
            console.log('风格列表加载完成:', this.styles.length);
        } catch (error) {
            console.error('加载风格列表失败:', error);
            this.hideLoading();
            this.showError('加载风格列表失败: ' + error.message);
        }
    }

    populateStyleSelect() {
        const styleSelect = document.getElementById('style-select');
        if (!styleSelect) return;

        styleSelect.innerHTML = '<option value="">请选择风格</option>';
        
        this.styles.forEach(style => {
            const option = document.createElement('option');
            option.value = style.id;
            option.textContent = `${style.name} (预计${style.estimated_time}秒)`;
            option.title = style.description;
            styleSelect.appendChild(option);
        });
    }

    bindEvents() {
        // 文件选择事件
        const fileInput = document.getElementById('image-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e);
            });
        }

        // 表单提交事件
        const form = document.getElementById('transform-form');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.handleSubmit();
            });
        }

        // 风格选择事件
        const styleSelect = document.getElementById('style-select');
        if (styleSelect) {
            styleSelect.addEventListener('change', () => {
                this.updateSubmitButton();
                this.updateStyleInfo();
            });
        }

        // 拖放事件
        const dropZone = document.getElementById('drop-zone');
        if (dropZone) {
            this.initDropZone(dropZone);
        }
    }

    initDropZone(dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                const fileInput = document.getElementById('image-input');
                if (fileInput) {
                    fileInput.files = files;
                    this.handleFileSelect({ target: fileInput });
                }
            }
        });
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (!file) return;

        // 验证文件类型
        if (!file.type.startsWith('image/')) {
            this.showError('请选择图片文件');
            return;
        }

        // 验证文件大小 (10MB)
        if (file.size > 10 * 1024 * 1024) {
            this.showError('文件大小不能超过10MB');
            return;
        }

        // 显示预览
        this.displayImagePreview(file);
        this.updateSubmitButton();

        console.log('文件已选择:', file.name, '大小:', (file.size / 1024 / 1024).toFixed(2) + 'MB');
    }

    displayImagePreview(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const previewContainer = document.getElementById('image-preview');
            if (previewContainer) {
                previewContainer.innerHTML = `
                    <img src="${e.target.result}" alt="预览图片" style="max-width: 100%; max-height: 300px;">
                    <p>文件: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)}MB)</p>
                `;
                previewContainer.style.display = 'block';
            }
        };
        reader.readAsDataURL(file);
    }

    async handleSubmit() {
        if (this.isProcessing) {
            return;
        }

        const fileInput = document.getElementById('image-input');
        const styleSelect = document.getElementById('style-select');

        if (!fileInput.files[0]) {
            this.showError('请选择图片文件');
            return;
        }

        if (!styleSelect.value) {
            this.showError('请选择转换风格');
            return;
        }

        try {
            this.isProcessing = true;
            this.updateSubmitButton();
            this.clearResults();
            this.showProgress();

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('style_id', styleSelect.value);

            this.updateStatus('正在提交转换任务...', 'info');

            const response = await fetch(`${this.apiBase}/transform`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            this.currentTask = result;

            console.log('转换任务已创建:', result);
            this.updateStatus(`任务已创建: ${result.task_id}`, 'success');

        } catch (error) {
            console.error('提交转换任务失败:', error);
            this.showError('提交转换任务失败: ' + error.message);
            this.isProcessing = false;
            this.updateSubmitButton();
            this.hideProgress();
        }
    }

    async getTaskResult(taskId) {
        try {
            const response = await fetch(`${this.apiBase}/tasks/${taskId}/result`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data.output_images && result.data.output_images.length > 0) {
                    const outputImage = result.data.output_images[0];
                    this.displayResult(outputImage.url);
                }
            }
        } catch (error) {
            console.error('获取任务结果失败:', error);
        }
    }

    displayResult(imageUrl) {
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.innerHTML = `
                <div class="result-image">
                    <h3>转换结果</h3>
                    <img src="${imageUrl}" alt="转换结果" style="max-width: 100%; border: 1px solid #ddd; border-radius: 4px;">
                    <div class="result-actions">
                        <a href="${imageUrl}" target="_blank" class="btn btn-primary">查看原图</a>
                        <button onclick="app.downloadImage('${imageUrl}')" class="btn btn-secondary">下载图片</button>
                    </div>
                </div>
            `;
            resultContainer.style.display = 'block';
        }
    }

    downloadImage(imageUrl) {
        const link = document.createElement('a');
        link.href = imageUrl;
        link.download = 'transformed_image.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    updateProgressUI(data) {
        const progressBar = document.getElementById('progress-bar');
        const progressText = document.getElementById('progress-text');

        if (progressBar) {
            progressBar.style.width = `${data.progress || 0}%`;
        }

        if (progressText) {
            let stageText = '';
            switch (data.stage) {
                case 'download':
                    stageText = '下载阶段';
                    break;
                case 'transform':
                    stageText = '转换阶段';
                    break;
                default:
                    stageText = data.stage || '';
            }
            
            progressText.textContent = `${stageText} - ${Math.round(data.progress || 0)}% - ${data.message || ''}`;
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submit-btn');
        const fileInput = document.getElementById('image-input');
        const styleSelect = document.getElementById('style-select');

        if (submitBtn) {
            const hasFile = fileInput && fileInput.files[0];
            const hasStyle = styleSelect && styleSelect.value;
            const canSubmit = hasFile && hasStyle && !this.isProcessing;

            submitBtn.disabled = !canSubmit;
            submitBtn.textContent = this.isProcessing ? '处理中...' : '开始转换';
        }
    }

    updateStyleInfo() {
        const styleSelect = document.getElementById('style-select');
        const styleInfo = document.getElementById('style-info');

        if (styleInfo && styleSelect) {
            const selectedStyle = this.styles.find(s => s.id === styleSelect.value);
            if (selectedStyle) {
                styleInfo.innerHTML = `
                    <h4>${selectedStyle.name}</h4>
                    <p>${selectedStyle.description}</p>
                    <p><strong>预计时间:</strong> ${selectedStyle.estimated_time}秒</p>
                    <p><strong>标签:</strong> ${selectedStyle.tags.join(', ')}</p>
                `;
                styleInfo.style.display = 'block';
            } else {
                styleInfo.style.display = 'none';
            }
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = connected ? '已连接' : '未连接';
            statusElement.className = connected ? 'status-connected' : 'status-disconnected';
        }
    }

    showProgress() {
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }

    hideProgress() {
        const progressContainer = document.getElementById('progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
    }

    clearResults() {
        const resultContainer = document.getElementById('result-container');
        if (resultContainer) {
            resultContainer.style.display = 'none';
            resultContainer.innerHTML = '';
        }
    }

    updateStatus(message, type = 'info') {
        const statusElement = document.getElementById('status-message');
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `status-message status-${type}`;
            
            // 自动隐藏成功消息
            if (type === 'success') {
                setTimeout(() => {
                    statusElement.textContent = '';
                    statusElement.className = 'status-message';
                }, 3000);
            }
        }
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    showError(message) {
        this.updateStatus(message, 'error');
        
        // 也可以使用更明显的错误提示
        if (window.alert) {
            alert('错误: ' + message);
        }
    }

    showLoading(message) {
        this.updateStatus(message, 'info');
    }

    hideLoading() {
        const statusElement = document.getElementById('status-message');
        if (statusElement) {
            statusElement.textContent = '';
            statusElement.className = 'status-message';
        }
    }

    destroy() {
        // 清理资源
        if (this.websocket) {
            this.websocket.close();
        }
        
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }
    }
}

// 全局应用实例
let app;

// 页面加载完成后初始化应用
document.addEventListener('DOMContentLoaded', () => {
    app = new ImageTransformApp();
});

// 页面卸载时清理资源
window.addEventListener('beforeunload', () => {
    if (app) {
        app.destroy();
    }
});