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
        
        console.log(`Attempting to connect WebSocket to: ${wsUrl}`);
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
            console.log('WebSocket connection established.');
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('WebSocket message received:', data);
            updateStatus(data);
        };

        socket.onclose = () => {
            console.log('WebSocket connection closed.');
            // Optional: try to reconnect
        };

        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
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
                const progress = parseFloat(data.progress || 0) * 100;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${Math.round(progress)}%`;
            taskInfo.textContent = data.message || '正在处理中...';
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
            taskInfo.textContent = `错误: ${data.message}`;
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-magic"></i> 重新尝试';
                break;
            default:
             taskInfo.textContent = data.message || '等待任务开始...';
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
}); 