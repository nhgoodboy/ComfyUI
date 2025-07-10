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
            
            // 初始化按钮状态
            this.updateSubmitButton();
            
            console.log('应用初始化成功');
        } catch (error) {
            console.error('应用初始化失败:', error);
            this.showMessage('应用初始化失败: ' + error.message, 'error');
        }
    }

    initWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/${this.clientId}`;
        
        console.log('初始化WebSocket连接');
        console.log('客户端ID:', this.clientId);
        console.log('WebSocket URL:', wsUrl);
        
        this.websocket = new WebSocket(wsUrl);
        
        this.websocket.onopen = () => {
            console.log('WebSocket连接已建立');
            console.log('WebSocket readyState:', this.websocket.readyState);
            this.showMessage('实时连接已建立', 'success');
        };
        
        this.websocket.onmessage = (event) => {
            try {
                console.log('WebSocket原始消息:', event.data);
                const data = JSON.parse(event.data);
                console.log('WebSocket解析后消息:', data);
                this.handleWebSocketMessage(data);
            } catch (error) {
                console.error('解析WebSocket消息失败:', error, 'raw data:', event.data);
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
        console.log('风格数据:', this.styles);
        this.populateStyleSelect();
            
        } catch (error) {
            console.error('加载风格失败:', error);
            this.showMessage('加载风格失败: ' + error.message, 'error');
        }
    }

    populateStyleSelect() {
        const styleSelect = document.getElementById('style-select');
        if (!styleSelect) {
            console.error('找不到风格选择器元素 #style-select');
            return;
        }
        
        // 清空现有选项
        styleSelect.innerHTML = '<option value="">选择一个风格...</option>';
        
        // 添加风格选项
        this.styles.forEach(style => {
            const option = document.createElement('option');
            option.value = style.id;
            option.textContent = style.name;
            styleSelect.appendChild(option);
        });
        
        // 添加变化事件监听器
        styleSelect.addEventListener('change', () => {
            console.log('风格已选择:', styleSelect.value);
            this.updateSubmitButton();
        });
        
        console.log('风格选择器已更新，添加了', this.styles.length, '个选项');
        console.log('当前选择器内容:', styleSelect.innerHTML);
    }

    bindEvents() {
        // 文件选择
        const fileInput = document.getElementById('image-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        }
        
        // 转换按钮
        const transformBtn = document.getElementById('submit-btn');
        if (transformBtn) {
            transformBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.startTransform();
            });
        }
        
        // 拖放功能
        const dropZone = document.querySelector('.upload-area');
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
                document.getElementById('image-input').files = files;
                this.displaySelectedImage(file);
            } else {
                this.showMessage('请选择图像文件', 'error');
            }
        }
    }

    displaySelectedImage(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById('original-image');
            const resultCard = document.getElementById('result-card');
            const fileName = document.getElementById('file-name');
            
            if (preview) {
                preview.src = e.target.result;
                preview.style.display = 'block';
                console.log('图片预览已设置');
            }
            
            // 显示结果卡片以显示预览
            if (resultCard) {
                resultCard.style.display = 'block';
                console.log('结果卡片已显示');
            }
            
            // 显示文件名
            if (fileName) {
                fileName.textContent = `已选择: ${file.name}`;
                fileName.style.display = 'block';
            }
            
            // 启用转换按钮
            this.updateSubmitButton();
        };
        reader.readAsDataURL(file);
    }

    async startTransform() {
        if (this.isProcessing) {
            this.showMessage('已有任务在处理中，请等待完成', 'warning');
            return;
        }
        
        const fileInput = document.getElementById('image-input');
        const styleSelect = document.getElementById('style-select');
        
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

    handleWebSocketMessage(wsMessage) {
        console.log('收到WebSocket原始消息:', wsMessage);
        
        // 直接处理任务数据（新格式）：{status: 'running', task_id: '...', progress: 88}
        let taskData;
        if (wsMessage.type === 'task_update') {
            // 旧格式：{type: 'task_update', data: {...}}
            taskData = wsMessage.data;
        } else if (wsMessage.status) {
            // 新格式：直接的任务数据 {status: 'running', task_id: '...', progress: 88}
            taskData = wsMessage;
        } else {
            console.log('忽略未知消息格式:', wsMessage);
            return;
        }
        
        const status = taskData.status;
        const message = taskData.message || `任务状态: ${status}`;
        const progress = taskData.progress || 0;
        
        console.log(`任务状态: ${status}, 进度: ${progress}%, 消息: ${message}`);
        console.log('任务数据:', taskData);
        
        // 更新进度条
        this.updateProgress(progress);
        
        // 更新状态消息
        this.showMessage(message, this.getMessageType(status));
        
        // 处理完成或失败状态
        if (status === 'completed') {
            this.handleTaskCompleted(taskData);
        } else if (status === 'failed') {
            this.handleTaskFailed(taskData);
        }
    }

    handleTaskCompleted(taskData) {
        console.log('任务完成:', taskData);
        this.showMessage('图像转换完成！', 'success');
        this.isProcessing = false;
        this.updateUI(false);
        this.updateProgress(100);
        
        // 处理结果数据
        if (taskData.result && taskData.result.output_files) {
            console.log('找到输出文件:', taskData.result.output_files);
            
            // 寻找最优先的输出图片（通常是 img_type: 'output'）
            const outputFiles = taskData.result.output_files;
            let bestFile = null;
            
            // 优先选择 output 类型的文件
            for (const file of outputFiles) {
                if (file.img_type === 'output') {
                    bestFile = file;
                    break;
                }
            }
            
            // 如果没有 output 类型，选择优先级最高的文件
            if (!bestFile && outputFiles.length > 0) {
                bestFile = outputFiles.reduce((prev, current) => {
                    return (prev.priority || 0) > (current.priority || 0) ? prev : current;
                });
            }
            
            if (bestFile) {
                console.log('选择输出文件:', bestFile);
                this.displayResult(bestFile.url);
            } else {
                console.warn('没有找到可用的输出文件');
                this.showMessage('转换完成，但未找到结果文件', 'warning');
            }
        } else {
            console.warn('任务完成但没有结果数据');
            this.showMessage('转换完成，但未返回结果数据', 'warning');
        }
    }

    handleTaskFailed(data) {
        console.log('任务失败:', data);
        this.isProcessing = false;
        this.updateUI(false);
        this.updateProgress(0);
    }

    displayResult(resultUrl) {
        console.log('显示结果图片:', resultUrl);
        
        const resultContainer = document.getElementById('result-card');
        const resultImage = document.getElementById('result-image');
        const downloadLink = document.getElementById('download-link');
        
        if (resultImage) {
            resultImage.src = resultUrl;
            resultImage.style.display = 'block';
            resultImage.onload = () => {
                console.log('结果图片加载成功');
            };
            resultImage.onerror = () => {
                console.error('结果图片加载失败:', resultUrl);
                this.showMessage('结果图片加载失败', 'error');
            };
        } else {
            console.error('找不到结果图片元素 #result-image');
        }
        
        if (downloadLink) {
            downloadLink.href = resultUrl;
            downloadLink.style.display = 'inline-block';
        }
        
        if (resultContainer) {
            resultContainer.style.display = 'block';
            console.log('结果卡片已显示');
        } else {
            console.error('找不到结果容器元素 #result-card');
        }
    }

    updateProgress(progress) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        if (progressFill) {
            progressFill.style.width = `${progress}%`;
        }
        
        if (progressText) {
            progressText.textContent = `${Math.round(progress)}%`;
        }
    }

    updateUI(processing) {
        const transformBtn = document.getElementById('submit-btn');
        const progressContainer = document.getElementById('status-card');
        
        if (transformBtn) {
            transformBtn.disabled = processing;
            transformBtn.innerHTML = processing ? '<i class="fas fa-spinner fa-spin"></i> 处理中...' : '<i class="fas fa-magic"></i> 开始转换';
        }
        
        if (progressContainer) {
            progressContainer.style.display = processing ? 'block' : 'none';
        }
        
        // 更新任务信息
        const taskInfo = document.getElementById('task-info');
        if (taskInfo) {
            taskInfo.textContent = processing ? '正在处理...' : '等待任务开始...';
        }
        
        if (!processing) {
            this.updateProgress(0);
        }
    }

    getMessageType(status) {
        switch (status) {
            case 'completed':
                return 'success';
            case 'failed':
                return 'error';
            case 'processing':
            case 'running':
                return 'info';
            case 'pending':
            case 'queued':
            case 'uploading':
            case 'uploaded':
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
    
    updateSubmitButton() {
        const fileInput = document.getElementById('image-input');
        const styleSelect = document.getElementById('style-select');
        const submitBtn = document.getElementById('submit-btn');
        
        if (submitBtn && fileInput && styleSelect) {
            const hasFile = fileInput.files && fileInput.files.length > 0;
            const hasStyle = styleSelect.value && styleSelect.value !== '';
            
            submitBtn.disabled = !(hasFile && hasStyle);
            
            console.log('按钮状态更新:', {
                hasFile,
                hasStyle,
                disabled: submitBtn.disabled
            });
        }
    }
}

// 应用启动时初始化
document.addEventListener('DOMContentLoaded', () => {
    window.app = new ImageTransformApp();
}); 