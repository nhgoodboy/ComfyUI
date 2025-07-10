class ImageTransformApp {
    constructor() {
        this.websocket = null;
        this.clientId = null;
        this.isProcessing = false;
        this.styles = [];
        
        this.init();
    }

    async init() {
        try {
            // 获取客户端ID
            this.clientId = document.body.dataset.clientId;
            console.log('客户端ID:', this.clientId);
            
            // 初始化WebSocket连接
            this.initWebSocket();
            
            // 加载可用风格
            await this.loadStyles();
            
            // 绑定事件
            this.bindEvents();
            
            console.log('应用初始化成功');
        } catch (error) {
            console.error('应用初始化失败:', error);
            this.showMessage('应用初始化失败: ' + error.message, 'error');
        }
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/${this.clientId}`;
        
        console.log('连接WebSocket:', wsUrl);
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket连接已建立');
            this.showMessage('实时连接已建立', 'success');
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
        
        this.websocket.onclose = () => {
            console.log('WebSocket连接已关闭');
            this.showMessage('实时连接已断开', 'warning');
            
            // 如果应用仍在运行，尝试重连
            if (!this.isShuttingDown) {
                setTimeout(() => this.initWebSocket(), 3000);
            }
        };
        
        this.websocket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.showMessage('连接错误，请刷新页面重试', 'error');
        };
    }

    async loadStyles() {
        try {
            console.log('加载可用风格...');
            const response = await fetch('/api/v1/styles');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.styles = data.styles || [];
            
            console.log('加载到风格数量:', this.styles.length);
            this.populateStyleSelect();
            
        } catch (error) {
            console.error('加载风格失败:', error);
            this.showMessage('加载风格失败: ' + error.message, 'error');
        }
    }

    populateStyleSelect() {
        const styleSelect = document.getElementById('styleSelect');
        if (!styleSelect) return;
        
        // 清空现有选项
        styleSelect.innerHTML = '<option value="">选择一个风格...</option>';
        
        // 添加风格选项
        this.styles.forEach(style => {
            const option = document.createElement('option');
            option.value = style.id;
            option.textContent = style.name;
            styleSelect.appendChild(option);
        });
        
        console.log('风格选择器已更新');
    }

    bindEvents() {
        // 文件选择
        const fileInput = document.getElementById('imageInput');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // 转换按钮
        const transformBtn = document.getElementById('transformBtn');
        if (transformBtn) {
            transformBtn.addEventListener('click', () => this.startTransform());
        }
        
        // 拖放功能
        const dropZone = document.getElementById('dropZone');
        if (dropZone) {
            dropZone.addEventListener('dragover', (e) => this.handleDragOver(e));
            dropZone.addEventListener('drop', (e) => this.handleDrop(e));
        }
    }

    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.displaySelectedImage(file);
        }
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('drag-over');
    }

    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('drag-over');
        
        const files = event.dataTransfer.files;
        if (files.length > 0) {
            const file = files[0];
            if (file.type.startsWith('image/')) {
                document.getElementById('imageInput').files = files;
                this.displaySelectedImage(file);
            } else {
                this.showMessage('请选择图像文件', 'error');
            }
        }
    }

    displaySelectedImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('imagePreview');
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
        };
        reader.readAsDataURL(file);
    }

    async startTransform() {
        if (this.isProcessing) {
            this.showMessage('已有任务在处理中，请等待完成', 'warning');
            return;
        }
        
        const fileInput = document.getElementById('imageInput');
        const styleSelect = document.getElementById('styleSelect');
        
        if (!fileInput.files[0]) {
            this.showMessage('请选择一张图片', 'error');
            return;
        }
        
        if (!styleSelect.value) {
            this.showMessage('请选择一个风格', 'error');
            return;
        }
        
        try {
            this.isProcessing = true;
            this.updateUI(true);
            
            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('style_id', styleSelect.value);
            
            console.log('开始图像转换...');
            
            const response = await fetch('/api/v1/transform', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP ${response.status}`);
            }
            
            const result = await response.json();
            console.log('转换请求成功:', result);
            
            this.showMessage('转换任务已启动，请等待处理完成...', 'info');
            
        } catch (error) {
            console.error('启动转换失败:', error);
            this.showMessage('启动转换失败: ' + error.message, 'error');
            this.isProcessing = false;
            this.updateUI(false);
        }
    }

    handleWebSocketMessage(data) {
        const status = data.status;
        const message = data.message;
        const progress = data.progress || 0;
        
        console.log(`任务状态: ${status}, 进度: ${progress}%, 消息: ${message}`);
        
        // 更新进度条
        this.updateProgress(progress);
        
        // 更新状态消息
        this.showMessage(message, this.getMessageType(status));
        
        // 处理完成或失败状态
        if (status === 'COMPLETED') {
            this.handleTaskCompleted(data);
        } else if (status === 'FAILED') {
            this.handleTaskFailed(data);
        }
    }

    handleTaskCompleted(data) {
        console.log('任务完成:', data);
        this.showMessage('图像转换完成！', 'success');
        this.isProcessing = false;
        this.updateUI(false);
        this.updateProgress(100);
        
        // 这里可以添加显示结果图像的逻辑
        // 如果服务器返回了结果URL，可以显示结果
        if (data.result_url) {
            this.displayResult(data.result_url);
        }
    }

    handleTaskFailed(data) {
        console.log('任务失败:', data);
        this.isProcessing = false;
        this.updateUI(false);
        this.updateProgress(0);
    }

    displayResult(resultUrl) {
        const resultContainer = document.getElementById('resultContainer');
        const resultImage = document.getElementById('resultImage');
        
        if (resultContainer && resultImage) {
            resultImage.src = resultUrl;
            resultContainer.style.display = 'block';
        }
    }

    updateProgress(progress) {
        const progressBar = document.querySelector('.progress-bar');
        const progressText = document.getElementById('progressText');
        
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
    }

    updateUI(processing) {
        const transformBtn = document.getElementById('transformBtn');
        const progressContainer = document.getElementById('progressContainer');
        
        if (transformBtn) {
            transformBtn.disabled = processing;
            transformBtn.textContent = processing ? '处理中...' : '开始转换';
        }
        
        if (progressContainer) {
            progressContainer.style.display = processing ? 'block' : 'none';
        }
        
        if (!processing) {
            this.updateProgress(0);
        }
    }

    getMessageType(status) {
        switch (status) {
            case 'COMPLETED':
                return 'success';
            case 'FAILED':
                return 'error';
            case 'PROCESSING':
            case 'RUNNING':
                return 'info';
            case 'QUEUED':
                return 'warning';
            default:
                return 'info';
        }
    }

    showMessage(message, type = 'info') {
        // 创建消息元素
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert alert-${type}`;
        messageDiv.textContent = message;
        
        // 添加到页面
        const container = document.getElementById('messageContainer') || document.body;
        container.appendChild(messageDiv);
        
        // 自动移除
        setTimeout(() => {
            if (messageDiv.parentNode) {
                messageDiv.parentNode.removeChild(messageDiv);
            }
        }, 5000);
        
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// 应用启动时初始化
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ImageTransformApp();
}); 