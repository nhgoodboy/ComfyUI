document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('upload-form');
    const imageInput = document.getElementById('image-input');
    const fileName = document.getElementById('file-name');
    const styleSelect = document.getElementById('style-select');
    const submitBtn = document.getElementById('submit-btn');

    const statusCard = document.getElementById('status-card');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const taskInfo = document.getElementById('task-info');

    const resultCard = document.getElementById('result-card');
    const originalImage = document.getElementById('original-image');
    const resultImage = document.getElementById('result-image');
    const downloadLink = document.getElementById('download-link');

    let socket;
    let reconnectInterval;
    let maxReconnectAttempts = 5;
    let reconnectAttempts = 0;

    // 1. 加载风格
    async function loadStyles() {
        try {
            const response = await fetch('/api/styles');
            if (!response.ok) {
                throw new Error('无法加载风格');
            }
            const styles = await response.json();
            
            styleSelect.innerHTML = '<option value="" disabled selected>选择一种艺术风格</option>';
            styles.forEach(style => {
                const option = document.createElement('option');
                option.value = style.id;
                option.textContent = style.name;
                styleSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Error fetching styles:', error);
            styleSelect.innerHTML = '<option value="" disabled selected>风格加载失败</option>';
        }
    }

    // 生成唯一的客户端ID用于WebSocket通信
    const clientId = `web-client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    // 2. 初始化WebSocket
    function setupWebSocket() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // 从模板中注入的全局变量获取主机地址，如果不存在则回退到当前位置
        const wsHost = window.WEBSOCKET_HOST || window.location.host;
        const wsUrl = `${wsProtocol}//${wsHost}/ws/${clientId}`;
        
        console.log(`尝试连接 WebSocket: ${wsUrl}`);
        
        try {
            socket = new WebSocket(wsUrl);

            socket.onopen = () => {
                console.log('WebSocket 连接成功');
                reconnectAttempts = 0; // 重置重连计数
                if (reconnectInterval) {
                    clearInterval(reconnectInterval);
                    reconnectInterval = null;
                }
            };

            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('收到 WebSocket 消息:', data);
                updateStatus(data);
            };

            socket.onclose = (event) => {
                console.log('WebSocket 连接关闭:', event.code, event.reason);
                attemptReconnect();
            };

            socket.onerror = (error) => {
                console.error('WebSocket 错误:', error);
            };
        } catch (error) {
            console.error('WebSocket 连接失败:', error);
            attemptReconnect();
        }
    }

    // 重连机制
    function attemptReconnect() {
        if (reconnectAttempts >= maxReconnectAttempts) {
            console.log('达到最大重连次数，停止重连');
            return;
        }

        if (reconnectInterval) {
            return; // 已经在重连中
        }

        reconnectAttempts++;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // 指数退避，最大30秒
        
        console.log(`${delay/1000}秒后尝试第 ${reconnectAttempts} 次重连...`);
        
        reconnectInterval = setTimeout(() => {
            console.log(`正在进行第 ${reconnectAttempts} 次重连...`);
            setupWebSocket();
            reconnectInterval = null;
        }, delay);
    }

    // 3. 更新状态
    function updateStatus(data) {
        statusCard.style.display = 'block';
        
        switch (data.status) {
            case 'UPLOADING':
            case 'UPLOADED':
            case 'QUEUED':
                progressFill.style.width = '5%';
                progressText.textContent = '5%';
                taskInfo.textContent = data.message || '正在准备...';
                break;
            case 'PROCESSING':
                const progress = parseFloat(data.progress || 0);
                progressFill.style.width = `${progress}%`;
                progressText.textContent = `${Math.round(progress)}%`;
                
                // 构建详细的状态信息
                let statusMessage = data.message || '正在处理中...';
                
                // 添加详细进度信息
                if (data.current_step !== undefined && data.total_steps !== undefined) {
                    statusMessage += ` (步骤 ${data.current_step}/${data.total_steps})`;
                }
                
                // 添加预估剩余时间
                if (data.estimated_remaining && data.estimated_remaining > 0) {
                    const minutes = Math.floor(data.estimated_remaining / 60);
                    const seconds = data.estimated_remaining % 60;
                    if (minutes > 0) {
                        statusMessage += ` - 预计剩余: ${minutes}分${seconds}秒`;
                    } else {
                        statusMessage += ` - 预计剩余: ${seconds}秒`;
                    }
                }
                
                // 添加当前处理节点信息（仅调试时显示）
                if (data.current_node && window.location.search.includes('debug=1')) {
                    statusMessage += ` [节点: ${data.current_node}]`;
                }
                
                taskInfo.textContent = statusMessage;
                
                // 添加调试信息到控制台
                if (data.current_step !== undefined && data.total_steps !== undefined) {
                    console.log(`进度详情: ${data.current_step}/${data.total_steps} (${progress.toFixed(1)}%)`);
                }
                break;
            case 'COMPLETED':
                progressFill.style.width = '100%';
                progressText.textContent = '100%';
                taskInfo.textContent = '处理完成！';
            
                if (data.result && data.result.output_files && data.result.output_files.length > 0) {
                    resultCard.style.display = 'block';
                    resultImage.src = data.result.output_files[0].url;
                    downloadLink.href = data.result.output_files[0].url;
                }
            
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-magic"></i> 再次转换';
                break;
            case 'FAILED':
                progressFill.style.width = '0%';
                progressText.textContent = '失败';
                taskInfo.textContent = `错误: ${data.message || data.details || '处理失败'}`;
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<i class="fas fa-magic"></i> 重新尝试';
                break;
            case 'UNKNOWN':
                taskInfo.textContent = data.message || '未知状态';
                console.warn('收到未知状态:', data);
                break;
            default:
                taskInfo.textContent = data.message || '等待任务开始...';
                console.log('收到状态更新:', data.status, data);
        }
    }

    // 4. 处理文件选择
    imageInput.addEventListener('change', () => {
        if (imageInput.files.length > 0) {
            fileName.textContent = imageInput.files[0].name;
            submitBtn.disabled = false;
        } else {
            fileName.textContent = '';
            submitBtn.disabled = true;
        }
    });

    // 5. 处理表单提交
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        if (!imageInput.files[0] || !styleSelect.value) {
            alert('请上传图片并选择风格。');
            return;
        }

        // 检查 WebSocket 连接状态
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket 未连接，尝试重新建立连接...');
            setupWebSocket();
            // 给连接一些时间建立
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            if (!socket || socket.readyState !== WebSocket.OPEN) {
                alert('WebSocket 连接失败，请刷新页面重试。');
                return;
            }
        }

        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 正在上传...';
        
        // Reset UI
        statusCard.style.display = 'none';
        resultCard.style.display = 'none';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';

        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        formData.append('style_id', styleSelect.value);
        formData.append('client_id', clientId);

        try {
            const response = await fetch('/api/transform', {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '上传失败');
            }

            const result = await response.json();
            console.log('Upload successful:', result);
            taskInfo.textContent = '图片上传成功，等待任务执行...';
            statusCard.style.display = 'block';

        } catch (error) {
            console.error('Error uploading file:', error);
            taskInfo.textContent = `上传错误: ${error.message}`;
            statusCard.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-magic"></i> 重新尝试';
        }
    });

    // 初始化
    loadStyles();
    setupWebSocket();
    
    // 页面卸载时清理
    window.addEventListener('beforeunload', () => {
        if (socket) {
            socket.close();
        }
        if (reconnectInterval) {
            clearTimeout(reconnectInterval);
        }
    });
}); 