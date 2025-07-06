document.addEventListener('DOMContentLoaded', () => {
    // DOM元素获取
    const uploadForm = document.getElementById('upload-form');
    const imageInput = document.getElementById('image-input');
    const fileDropArea = document.querySelector('.file-drop-area');
    const fileLabel = document.getElementById('file-label');
    const filePreview = document.getElementById('file-preview');
    const styleSelect = document.getElementById('style-select');
    const submitBtn = document.getElementById('submit-btn');

    const statusCard = document.getElementById('status-card');
    const progressContainer = document.getElementById('progress-container');
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');

    const resultCard = document.getElementById('result-card');
    const originalImage = document.getElementById('original-image');
    const resultImage = document.getElementById('result-image');
    const downloadLink = document.getElementById('download-link');
    
    // 生成唯一的客户端ID用于WebSocket通信
    const clientId = `web-client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    let socket;

    // --- 功能函数 ---

    const setupWebSocket = () => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsProtocol}//${window.location.host}/ws/${clientId}`;
        
        socket = new WebSocket(wsUrl);

        socket.onopen = () => console.log('WebSocket connection established.');
        socket.onclose = () => console.log('WebSocket connection closed.');
        socket.onerror = (error) => console.error('WebSocket Error:', error);
        socket.onmessage = handleWebSocketMessage;
    };

    const handleWebSocketMessage = (event) => {
        const data = JSON.parse(event.data);
        updateStatus(data);
    };

    const updateStatus = (data) => {
        statusCard.style.display = 'block';
        statusMessage.textContent = data.message || '...';

        switch (data.status) {
            case 'UPLOADING':
            case 'UPLOADED':
            case 'QUEUED':
                progressContainer.style.display = 'block';
                progressBar.style.width = '5%';
                break;
            case 'PROCESSING':
                progressContainer.style.display = 'block';
                progressBar.style.width = `${(data.progress || 0) * 100}%`;
                break;
            case 'COMPLETED':
                progressContainer.style.display = 'none';
                statusMessage.textContent = '转换完成!';
                displayResult(data.result);
                break;
            case 'FAILED':
                progressContainer.style.display = 'none';
                statusMessage.style.color = 'var(--error-color)';
                statusMessage.textContent = `错误: ${data.message}`;
                submitBtn.disabled = false;
                break;
        }
    };

    const displayResult = (result) => {
        if (result && result.output_files && result.output_files.length > 0) {
            resultImage.src = result.output_files[0].url;
            downloadLink.href = result.output_files[0].url;
            resultCard.style.display = 'block';
            submitBtn.disabled = false;
        }
    };

    const fetchStyles = async () => {
        try {
            const response = await fetch('/api/styles');
            if (!response.ok) throw new Error('无法加载风格列表');
            const styles = await response.json();

            styleSelect.innerHTML = '<option value="" disabled selected>请选择一种风格</option>';
            styles.forEach(style => {
                const option = document.createElement('option');
                option.value = style.id;
                option.textContent = style.name;
                styleSelect.appendChild(option);
            });
        } catch (error) {
            console.error(error);
            styleSelect.innerHTML = '<option value="" disabled selected>加载风格失败</option>';
        }
    };

    const handleFileSelect = (file) => {
        if (file && file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                filePreview.innerHTML = `<img src="${e.target.result}" alt="图片预览">`;
                originalImage.src = e.target.result;
            };
            reader.readAsDataURL(file);
            validateForm();
        }
    };
    
    const validateForm = () => {
        submitBtn.disabled = !(imageInput.files.length > 0 && styleSelect.value);
    };

    // --- 事件监听 ---

    // 页面加载
    fetchStyles();
    setupWebSocket();

    // 表单提交
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        submitBtn.disabled = true;
        resultCard.style.display = 'none';
        
        const formData = new FormData();
        formData.append('image', imageInput.files[0]);
        formData.append('style_id', styleSelect.value);
        formData.append('client_id', clientId);

        updateStatus({ status: 'INIT', message: '正在准备上传...' });

        try {
            const response = await fetch('/api/transform', {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || '上传失败');
            }
            // 后续状态更新由WebSocket处理
        } catch (error) {
            updateStatus({ status: 'FAILED', message: error.message });
        }
    });

    // 文件输入
    imageInput.addEventListener('change', () => handleFileSelect(imageInput.files[0]));
    styleSelect.addEventListener('change', validateForm);

    // 拖拽上传
    fileDropArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        fileDropArea.classList.add('drag-over');
    });
    fileDropArea.addEventListener('dragleave', () => {
        fileDropArea.classList.remove('drag-over');
    });
    fileDropArea.addEventListener('drop', (e) => {
        e.preventDefault();
        fileDropArea.classList.remove('drag-over');
        const file = e.dataTransfer.files[0];
        imageInput.files = e.dataTransfer.files; // 关键：将文件放入input
        handleFileSelect(file);
    });
}); 