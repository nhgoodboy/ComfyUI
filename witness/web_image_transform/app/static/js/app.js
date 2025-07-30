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
        this.userId = null;
        this.isProcessing = false;
        this.styles = [];
        this.currentTask = null;
        this.apiBase = '/api';
        this.originalImagePreviewUrl = null;  // 保存原始图片预览URL
        this.originalImage1PreviewUrl = null; // 保存第一张图片预览URL
        this.originalImage2PreviewUrl = null; // 保存第二张图片预览URL
        this.currentUploadMode = 'single'; // 'single' 或 'dual'

        this.init();
    }

    generateRequestId() {
        return 'req-' + Date.now() + '-' + Math.random().toString(36).substring(2, 11);
    }

    async init() {
        try {
            console.log('=== 应用初始化开始 ===');

            // 获取会话信息（包含用户ID）
            console.log('获取会话信息...');
            await this.getSessionInfo();

            // 初始化WebSocket连接
            console.log('初始化WebSocket连接...');
            this.initWebSocket();

            // 加载可用风格
            console.log('加载可用风格...');
            await this.loadStyles();

            // 绑定事件
            console.log('绑定事件...');
            this.bindEvents();

            // 初始化按钮状态
            console.log('初始化按钮状态...');
            this.updateUploadMode(); // 添加这行来初始化上传模式
            this.updateSubmitButton();

            console.log('=== 应用初始化成功 ===');
        } catch (error) {
            console.error('=== 应用初始化失败 ===', error);
            this.showError('应用初始化失败: ' + error.message);
        }
    }

    async getSessionInfo() {
        try {
            const response = await fetch(`${this.apiBase}/session`);
            if (response.ok) {
                const sessionInfo = await response.json();
                console.log('会话信息:', sessionInfo);
                this.userId = sessionInfo.user_id;  // 使用user_id而不是session_id
                console.log('用户ID:', this.userId);
            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
        } catch (error) {
            console.error('获取会话信息失败:', error);
            // 如果获取失败，重试一次
            try {
                console.log('重试获取会话信息...');
                const retryResponse = await fetch(`${this.apiBase}/session`);
                if (retryResponse.ok) {
                    const sessionInfo = await retryResponse.json();
                    console.log('重试成功，会话信息:', sessionInfo);
                    this.userId = sessionInfo.user_id;
                    console.log('用户ID:', this.userId);
                } else {
                    throw new Error('重试也失败了');
                }
            } catch (retryError) {
                console.error('重试获取会话信息也失败:', retryError);
                // 最后的备用方案：生成临时ID并尝试通过重置端点同步到后端
                this.userId = 'user-' + Date.now() + '-' + Math.random().toString(36).substring(2, 11);
                console.log('生成临时用户ID:', this.userId);

                // 尝试通过重置端点同步到后端
                try {
                    await fetch(`${this.apiBase}/session/reset`);
                    console.log('已尝试同步用户ID到后端');
                } catch (syncError) {
                    console.warn('同步用户ID到后端失败:', syncError);
                }
            }
        }
    }

    initWebSocket() {
        try {
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}${this.apiBase}/ws/${this.userId}`;

            console.log('连接WebSocket:', wsUrl);
            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log('WebSocket连接已建立');
                this.updateConnectionStatus(true);
            };

            this.websocket.onmessage = (event) => {
                try {
                    // 忽略心跳消息
                    if (event.data === 'pong') {
                        return;
                    }

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
        if (data.type === 'task_update' && data.request_id) {
            this.handleTaskUpdate(data);
        }
    }

    handleTaskUpdate(data) {
        // 使用标准的嵌套数据结构
        const taskData = data.data;
        const requestId = taskData.request_id;
        console.log(`任务更新 - ${data.request_id} (request_id: ${requestId}): ${taskData.status} (${taskData.progress}%) - ${taskData.message}`);

        // 将request_id添加到taskData中，方便后续方法使用
        taskData.request_id = data.request_id;
        console.log('DEBUG: 设置taskData.request_id为:', taskData.request_id);

        // 更新当前任务状态
        if (this.currentTask && this.currentTask.request_id === data.request_id) {
            this.currentTask = { ...this.currentTask, ...taskData };
        }

        // 更新UI
        this.updateProgressUI(taskData);

        // 处理不同状态
        switch (taskData.status) {
            case 'downloading':
                this.updateStatus(`下载中: ${taskData.message}`, 'info');
                break;

            case 'downloaded':
                this.updateStatus('图片下载完成，开始转换...', 'info');
                break;

            case 'processing':
                this.updateStatus(`转换中: ${taskData.message}`, 'info');
                break;

            case 'completed':
                console.log('URGENT DEBUG: 调用handleTaskCompleted，taskData.request_id =', taskData.request_id);
                this.handleTaskCompleted(taskData);
                break;

            case 'download_failed':
                this.handleTaskFailed(taskData, '图片下载失败');
                break;

            case 'processing_failed':
                this.handleTaskFailed(taskData, '图像转换失败');
                break;

            default:
                this.updateStatus(taskData.message || '任务状态未知', 'info');
        }
    }

    handleTaskCompleted(data) {
        this.updateStatus('转换完成！', 'success');
        this.updateProgressUI({ progress: 100, stage: 'completed', message: '转换完成' });

        // 调试：打印data内容
        console.log('handleTaskCompleted 收到的data:', data);
        console.log('data.request_id:', data.request_id);

        // 检查是否有结果数据
        if (data.result) {
            console.log('收到任务结果:', data.result);

            // 检查旧格式的output_images
            if (data.result.output_images && data.result.output_images.length > 0) {
                const outputImage = data.result.output_images[0];
                // 使用保存的原始图片预览URL
                this.displayResultImage(this.originalImagePreviewUrl || data.result.files?.input || '', outputImage.url);
            }
            // 检查新格式的files
            else if (data.result.files && data.result.files.output) {
                const outputFiles = data.result.files.output;
                if (outputFiles.length > 0) {
                    // 使用保存的原始图片预览URL，而不是服务器的input URL
                    this.displayResultImage(this.originalImagePreviewUrl || data.result.files.input || '', outputFiles[0]);
                }
            }
            else {
                // 任务完成但没有图片结果
                console.log('任务已完成，无图片结果');
                this.updateStatus('图像转换完成！请查看输出目录', 'success');
                this.hideProgress();
            }
        } else {
            // 如果WebSocket消息中没有结果，显示完成状态
            console.log('任务已完成，无结果数据');
            this.updateStatus('图像转换完成！请查看输出目录', 'success');
            this.hideProgress();
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
            console.log('开始加载风格列表...');
            this.showLoading('正在加载风格列表...');

            const response = await fetch(`${this.apiBase}/styles`);
            console.log('风格API响应状态:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            this.styles = await response.json();
            console.log('获取到风格数据:', this.styles);
            this.populateStyleSelect();
            this.hideLoading();

            console.log('风格列表加载完成:', this.styles.length, '个风格');
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
            
            // 添加数据属性标识是否需要双图片
            if (style.id === 'person_scene_merge') {
                option.setAttribute('data-dual-image', 'true');
            }

            // 默认选中黏土模型
            if (style.id === 'clay_style_transform') {
                option.selected = true;
            }

            styleSelect.appendChild(option);
        });
    }

    bindEvents() {
        // 单图片文件选择事件
        const fileInput = document.getElementById('image-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                this.handleFileSelect(e, 'single');
            });
        }

        // 双图片文件选择事件
        const file1Input = document.getElementById('image1-input');
        if (file1Input) {
            file1Input.addEventListener('change', (e) => {
                this.handleFileSelect(e, 'dual', 1);
            });
        }

        const file2Input = document.getElementById('image2-input');
        if (file2Input) {
            file2Input.addEventListener('change', (e) => {
                this.handleFileSelect(e, 'dual', 2);
            });
        }

        // 表单提交事件
        const form = document.getElementById('upload-form');
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
                this.updateUploadMode();
                this.updateSubmitButton();
                this.updateStyleInfo();
            });
        }

        // 拖放事件 - 为所有上传区域初始化
        const dropZones = document.querySelectorAll('.upload-area');
        dropZones.forEach((dropZone, index) => {
            if (dropZone.getAttribute('for') === 'image-input') {
                this.initDropZone(dropZone, 'single');
            } else if (dropZone.getAttribute('for') === 'image1-input') {
                this.initDropZone(dropZone, 'dual', 1);
            } else if (dropZone.getAttribute('for') === 'image2-input') {
                this.initDropZone(dropZone, 'dual', 2);
            }
        });
    }

    initDropZone(dropZone, mode = 'single', imageIndex = null) {
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
                let fileInput;
                if (mode === 'single') {
                    fileInput = document.getElementById('image-input');
                } else if (mode === 'dual') {
                    fileInput = document.getElementById(`image${imageIndex}-input`);
                }
                
                if (fileInput) {
                    fileInput.files = files;
                    this.handleFileSelect({ target: fileInput }, mode, imageIndex);
                }
            }
        });
    }

    updateUploadMode() {
        const styleSelect = document.getElementById('style-select');
        const selectedOption = styleSelect.selectedOptions[0];
        
        if (selectedOption && selectedOption.getAttribute('data-dual-image') === 'true') {
            this.currentUploadMode = 'dual';
            // 显示双图片上传区域，隐藏单图片区域
            document.getElementById('single-upload-group').style.display = 'none';
            document.getElementById('dual-upload-group').style.display = 'block';
        } else {
            this.currentUploadMode = 'single';
            // 显示单图片上传区域，隐藏双图片区域
            document.getElementById('single-upload-group').style.display = 'block';
            document.getElementById('dual-upload-group').style.display = 'none';
        }
        
        // 清理之前的文件选择
        this.clearAllFileSelections();
    }

    clearAllFileSelections() {
        // 清理所有文件输入
        const inputs = ['image-input', 'image1-input', 'image2-input'];
        inputs.forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.value = '';
            }
        });
        
        // 清理文件名显示
        const fileNames = ['file-name', 'file1-name', 'file2-name'];
        fileNames.forEach(id => {
            const span = document.getElementById(id);
            if (span) {
                span.textContent = '';
                span.style.color = '';
                span.style.fontWeight = '';
            }
        });
        
        // 清理预览图片
        const previews = ['image-preview', 'image1-preview', 'image2-preview'];
        previews.forEach(id => {
            const preview = document.getElementById(id);
            if (preview) {
                preview.style.display = 'none';
                preview.innerHTML = '';
            }
        });
        
        // 清理预览URL
        this.originalImagePreviewUrl = null;
        this.originalImage1PreviewUrl = null;
        this.originalImage2PreviewUrl = null;
    }

    handleFileSelect(event, mode = 'single', imageIndex = null) {
        console.log('=== 文件选择事件触发 ===');
        console.log('模式:', mode, '图片索引:', imageIndex);
        const file = event.target.files[0];
        console.log('选择的文件:', file);

        if (!file) {
            console.log('没有选择文件');
            return;
        }

        console.log('文件信息:', {
            name: file.name,
            size: file.size,
            type: file.type,
            lastModified: file.lastModified
        });

        // 验证文件类型
        if (!file.type.startsWith('image/')) {
            console.error('文件类型无效:', file.type);
            this.showError('请选择图片文件');
            return;
        }

        // 验证文件大小 (10MB)
        if (file.size > 10 * 1024 * 1024) {
            console.error('文件大小超限:', file.size);
            this.showError('文件大小不能超过10MB');
            return;
        }

        console.log('文件验证通过，显示预览...');
        // 显示预览
        this.displayImagePreview(file, mode, imageIndex);
        this.updateSubmitButton();

        console.log('文件选择处理完成 ✓');
    }

    displayImagePreview(file, mode = 'single', imageIndex = null) {
        const reader = new FileReader();
        reader.onload = (e) => {
            let previewContainer, fileNameSpan;
            
            if (mode === 'single') {
                // 保存原始图片预览URL
                this.originalImagePreviewUrl = e.target.result;
                previewContainer = document.getElementById('image-preview');
                fileNameSpan = document.getElementById('file-name');
            } else if (mode === 'dual') {
                // 保存双图片预览URL
                if (imageIndex === 1) {
                    this.originalImage1PreviewUrl = e.target.result;
                    previewContainer = document.getElementById('image1-preview');
                    fileNameSpan = document.getElementById('file1-name');
                } else if (imageIndex === 2) {
                    this.originalImage2PreviewUrl = e.target.result;
                    previewContainer = document.getElementById('image2-preview');
                    fileNameSpan = document.getElementById('file2-name');
                }
            }

            if (previewContainer) {
                previewContainer.style.display = 'block';
                previewContainer.innerHTML = `
                    <div style="border: 2px dashed #ddd; padding: 15px; border-radius: 8px; background-color: #f9f9f9;">
                        <img src="${e.target.result}" alt="预览图片" style="max-width: 100%; max-height: 200px; border-radius: 4px;">
                        <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">
                            <strong>${file.name}</strong><br>
                            大小: ${(file.size / 1024 / 1024).toFixed(2)}MB
                        </p>
                    </div>
                `;
            }

            // 更新文件名显示
            if (fileNameSpan) {
                fileNameSpan.textContent = `已选择: ${file.name}`;
                fileNameSpan.style.color = '#28a745';
                fileNameSpan.style.fontWeight = 'bold';
            }
        };
        reader.readAsDataURL(file);
    }

    async handleSubmit() {
        if (this.isProcessing) {
            return;
        }

        const styleSelect = document.getElementById('style-select');
        if (!styleSelect.value) {
            this.showError('请选择转换风格');
            return;
        }

        // 根据上传模式检查文件
        let files = [];
        if (this.currentUploadMode === 'single') {
            const fileInput = document.getElementById('image-input');
            if (!fileInput.files[0]) {
                this.showError('请选择图片文件');
                return;
            }
            files.push(fileInput.files[0]);
        } else if (this.currentUploadMode === 'dual') {
            const file1Input = document.getElementById('image1-input');
            const file2Input = document.getElementById('image2-input');
            
            if (!file1Input.files[0]) {
                this.showError('请上传第一张图片');
                return;
            }
            if (!file2Input.files[0]) {
                this.showError('请上传第二张图片');
                return;
            }
            
            files.push(file1Input.files[0]);
            files.push(file2Input.files[0]);
        }

        try {
            this.isProcessing = true;
            this.updateSubmitButton();
            this.clearResults();
            this.showProgress();

            // 生成request_id
            const requestId = this.generateRequestId();
            console.log('生成request_id:', requestId);

            const formData = new FormData();
            
            // 根据模式添加文件
            if (this.currentUploadMode === 'single') {
                formData.append('file', files[0]);
            } else if (this.currentUploadMode === 'dual') {
                formData.append('file1', files[0]);
                formData.append('file2', files[1]);
            }
            
            formData.append('style_id', styleSelect.value);
            formData.append('request_id', requestId);
            formData.append('user_id', this.userId);  // 添加user_id

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
            this.updateStatus(`任务已创建: ${result.request_id}`, 'success');

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

    displayResultImage(originalUrl, resultUrl) {
        const resultCard = document.getElementById('result-card');
        const originalImage = document.getElementById('original-image');
        const resultImage = document.getElementById('result-image');
        const downloadLink = document.getElementById('download-link');

        // 根据当前上传模式显示原始图片
        let displayOriginalUrl = originalUrl;
        if (this.currentUploadMode === 'dual') {
            // 对于双图片模式，显示合并后的预览或使用第一张图片
            displayOriginalUrl = this.originalImage1PreviewUrl || originalUrl;
        } else {
            displayOriginalUrl = this.originalImagePreviewUrl || originalUrl;
        }

        if (originalImage && displayOriginalUrl) {
            originalImage.src = displayOriginalUrl;
        }

        if (resultImage && resultUrl) {
            resultImage.src = resultUrl;
        }

        if (downloadLink && resultUrl) {
            downloadLink.href = resultUrl;
        }

        if (resultCard) {
            resultCard.style.display = 'block';
        }

        // 隐藏进度卡片
        this.hideProgress();
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
        // 修复进度条ID匹配问题
        const progressBar = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        const taskInfo = document.getElementById('task-info');

        if (progressBar) {
            progressBar.style.width = `${data.progress || 0}%`;
        }

        if (progressText) {
            progressText.textContent = `${Math.round(data.progress || 0)}%`;
        }

        if (taskInfo) {
            let stageText = '';
            switch (data.stage) {
                case 'download':
                    stageText = '下载阶段';
                    break;
                case 'transform':
                case 'processing':
                    stageText = '转换阶段';
                    break;
                case 'completed':
                    stageText = '完成';
                    break;
                default:
                    stageText = data.stage || '';
            }

            taskInfo.textContent = `${stageText} - ${data.message || ''}`;
        }
    }

    updateSubmitButton() {
        const submitBtn = document.getElementById('submit-btn');
        const styleSelect = document.getElementById('style-select');

        if (submitBtn) {
            let hasRequiredFiles = false;
            const hasStyle = styleSelect && styleSelect.value;
            
            if (this.currentUploadMode === 'single') {
                const fileInput = document.getElementById('image-input');
                hasRequiredFiles = fileInput && fileInput.files[0];
            } else if (this.currentUploadMode === 'dual') {
                const file1Input = document.getElementById('image1-input');
                const file2Input = document.getElementById('image2-input');
                hasRequiredFiles = file1Input && file1Input.files[0] && 
                                 file2Input && file2Input.files[0];
            }
            
            const canSubmit = hasRequiredFiles && hasStyle && !this.isProcessing;

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
        // 修复容器ID匹配问题
        const progressContainer = document.getElementById('status-card');
        if (progressContainer) {
            progressContainer.style.display = 'block';
        }
    }

    hideProgress() {
        const progressContainer = document.getElementById('status-card');
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

        // 同时清理新的结果卡片
        const resultCard = document.getElementById('result-card');
        if (resultCard) {
            resultCard.style.display = 'none';
        }

        // 注意：不要清理 originalImagePreviewUrl，因为在显示结果时还需要用到
        // this.originalImagePreviewUrl = null;
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