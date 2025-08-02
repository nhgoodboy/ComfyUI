/**
 * ComfyUI Workflow Test System - Frontend JavaScript Application
 */

class WorkflowTestSystem {
    constructor() {
        this.apiBase = '/api';
        this.wsUrl = `ws://${location.host}/ws`;
        this.sessionId = null;
        this.websocket = null;
        this.currentTask = null;
        this.workflows = [];
        this.taskHistory = [];
        this.autoScroll = true;
        
        // Initialize system
        this.init();
    }

    async init() {
        try {
            this.log('Initializing system...', 'info');
            
            // Initialize session
            await this.initSession();
            
            // Initialize WebSocket connection
            await this.initWebSocket();
            
            // Load workflows
            await this.loadWorkflows();
            
            // Bind events
            this.bindEvents();
            
            // Check system health
            await this.checkSystemHealth();
            
            this.log('System initialization complete', 'success');
            
        } catch (error) {
            this.log(`Initialization failed: ${error.message}`, 'error');
            console.error('Initialization error:', error);
        }
    }

    async initSession() {
        try {
            const response = await fetch(`${this.apiBase}/session`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.sessionId = result.data.session_id;
            
            // Update UI
            document.getElementById('session-id').textContent = this.sessionId.substring(0, 8) + '...';
            
            this.log(`Session created: ${this.sessionId}`, 'success');
            
        } catch (error) {
            this.log(`Session creation failed: ${error.message}`, 'error');
            throw error;
        }
    }

    async initWebSocket() {
        try {
            const wsUrl = `${this.wsUrl}/${this.sessionId}`;
            this.log(`Connecting WebSocket: ${wsUrl}`, 'info');
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.log('WebSocket connection established', 'success');
                this.updateConnectionStatus(true);
                
                // Start heartbeat
                this.startHeartbeat();
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    if (event.data === 'pong') {
                        return;
                    }
                    
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                    
                } catch (error) {
                    this.log(`WebSocket message parsing error: ${error.message}`, 'error');
                }
            };
            
            this.websocket.onclose = (event) => {
                this.log(`WebSocket connection closed: ${event.code}`, 'warning');
                this.updateConnectionStatus(false);
                
                // Auto reconnect
                if (event.code !== 1000) {
                    setTimeout(() => {
                        this.log('Attempting to reconnect WebSocket...', 'info');
                        this.initWebSocket();
                    }, 3000);
                }
            };
            
            this.websocket.onerror = (error) => {
                this.log(`WebSocket error: ${error}`, 'error');
                this.updateConnectionStatus(false);
            };
            
        } catch (error) {
            this.log(`WebSocket initialization failed: ${error.message}`, 'error');
            throw error;
        }
    }

    startHeartbeat() {
        setInterval(() => {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send('ping');
            }
        }, 30000);
    }

    handleWebSocketMessage(message) {
        this.log(`Received WebSocket message: ${message.type}`, 'info');
        
        switch (message.type) {
            case 'workflow_update':
            case 'task_update':  // 支持新的消息类型
                this.handleWorkflowUpdate(message);
                break;
            case 'task_completed':
                this.handleTaskCompleted(message);
                break;
            case 'task_failed':
                this.handleTaskFailed(message);
                break;
            case 'task_cancelled':
                this.handleTaskCancelled(message);
                break;
            default:
                this.log(`Unknown message type: ${message.type}`, 'warning');
        }
    }

    handleWorkflowUpdate(message) {
        // 使用标准的嵌套数据结构（与老项目一致）
        const taskData = message.data;
        const requestId = message.request_id;
        
        // 将顶层 request_id 添加到 taskData 中
        taskData.request_id = requestId;
        
        this.currentTask = taskData;
        
        // Update task info
        this.updateCurrentTaskInfo(taskData);
        
        // Update progress
        this.updateProgress(taskData.progress || 0, taskData.stage || '', taskData.message || '');
        
        // Log update
        this.log(`Task ${requestId} update: ${taskData.status} (${Math.round(taskData.progress || 0)}%)`, 'info');
        
        // Subscribe to updates
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'subscribe',
                request_id: requestId
            }));
        }
    }

    handleTaskCompleted(message) {
        const data = message.data;
        this.log(`Task ${data.request_id} completed`, 'success');
        
        // Update status
        this.updateCurrentTaskInfo(data);
        this.updateProgress(100, 'completed', 'Task completed');
        
        // Display results
        if (data.output_images && data.output_images.length > 0) {
            this.displayResults(data.output_images);
        }
        
        // Add to history
        this.addToTaskHistory(data);
        
        // Reset display after delay
        setTimeout(() => {
            this.currentTask = null;
            this.resetTaskDisplay();
        }, 3000);
    }

    handleTaskFailed(message) {
        const data = message.data;
        this.log(`Task ${data.request_id} failed: ${data.error_message}`, 'error');
        
        // Update status
        this.updateCurrentTaskInfo(data);
        this.updateProgress(0, 'failed', data.error_message || 'Task failed');
        
        // Add to history
        this.addToTaskHistory(data);
        
        // Reset display after delay
        setTimeout(() => {
            this.currentTask = null;
            this.resetTaskDisplay();
        }, 3000);
    }

    handleTaskCancelled(message) {
        const data = message.data;
        this.log(`Task ${data.request_id} cancelled`, 'warning');
        
        // Update status
        this.updateCurrentTaskInfo(data);
        this.updateProgress(0, 'cancelled', 'Task cancelled');
        
        // Add to history
        this.addToTaskHistory(data);
        
        // Reset display after delay
        setTimeout(() => {
            this.currentTask = null;
            this.resetTaskDisplay();
        }, 3000);
    }

    async loadWorkflows() {
        try {
            this.log('Loading workflows...', 'info');
            
            const response = await fetch(`${this.apiBase}/workflow/list`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (!result.success) {
                throw new Error('Failed to load workflows');
            }
            
            this.workflows = result.data.workflows || [];
            this.populateWorkflowSelect();
            
            this.log(`Loaded ${this.workflows.length} workflows`, 'success');
            
        } catch (error) {
            this.log(`Failed to load workflows: ${error.message}`, 'error');
            console.error('Workflow loading error:', error);
        }
    }

    populateWorkflowSelect() {
        const select = document.getElementById('workflow-select');
        select.innerHTML = '<option value="">Select workflow...</option>';
        
        this.workflows.forEach(workflow => {
            const option = document.createElement('option');
            option.value = workflow.workflow_id;
            option.textContent = `${workflow.name} (${workflow.estimated_time}s)`;
            option.title = workflow.description;
            select.appendChild(option);
        });
    }

    async onWorkflowChange() {
        const select = document.getElementById('workflow-select');
        const workflowId = select.value;
        
        if (!workflowId) {
            this.hideWorkflowInfo();
            this.clearParameterForm();
            return;
        }
        
        // Show workflow info
        const workflow = this.workflows.find(w => w.workflow_id === workflowId);
        if (workflow) {
            this.showWorkflowInfo(workflow);
        }
        
        // Load parameter schema
        await this.loadWorkflowSchema(workflowId);
        
        // Check if parameters are ready after loading schema
        this.checkParametersReady();
    }

    showWorkflowInfo(workflow) {
        const infoDiv = document.getElementById('workflow-info');
        const detailsDiv = document.getElementById('workflow-details');
        
        detailsDiv.innerHTML = `
            <h4>${workflow.name}</h4>
            <p><strong>Description:</strong> ${workflow.description}</p>
            <p><strong>Estimated time:</strong> ${workflow.estimated_time}s</p>
            <p><strong>Tags:</strong> ${workflow.tags.join(', ')}</p>
            <p><strong>Version:</strong> ${workflow.version}</p>
        `;
        
        infoDiv.style.display = 'block';
    }

    hideWorkflowInfo() {
        document.getElementById('workflow-info').style.display = 'none';
    }

    async loadWorkflowSchema(workflowId) {
        try {
            const response = await fetch(`${this.apiBase}/workflow/schema/${workflowId}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (!result.success) {
                throw new Error('Failed to load workflow schema');
            }
            
            this.generateParameterForm(result.data.parameters || {});
            
        } catch (error) {
            this.log(`Failed to load parameter schema: ${error.message}`, 'error');
            this.clearParameterForm();
        }
    }

    generateParameterForm(parameters) {
        const formDiv = document.getElementById('parameter-form');
        
        if (Object.keys(parameters).length === 0) {
            formDiv.innerHTML = '<p>This workflow requires no parameters</p>';
            return;
        }
        
        formDiv.innerHTML = '';
        
        Object.entries(parameters).forEach(([paramName, paramInfo]) => {
            const groupDiv = document.createElement('div');
            groupDiv.className = 'parameter-group';
            
            const label = document.createElement('label');
            label.textContent = `${paramName}${paramInfo.required ? ' *' : ''}`;
            label.setAttribute('for', `param-${paramName}`);
            
            let input;
            if (paramInfo.enum) {
                // Dropdown for enum values
                input = document.createElement('select');
                paramInfo.enum.forEach(value => {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value;
                    input.appendChild(option);
                });
            } else if (paramInfo.type === 'boolean') {
                // Checkbox for boolean values
                input = document.createElement('input');
                input.type = 'checkbox';
            } else if (paramInfo.type === 'number' || paramInfo.type === 'integer') {
                // Number input
                input = document.createElement('input');
                input.type = 'number';
                if (paramInfo.min !== undefined) input.min = paramInfo.min;
                if (paramInfo.max !== undefined) input.max = paramInfo.max;
            } else if (paramInfo.type === 'file') {
                // File input for image files
                input = document.createElement('input');
                input.type = 'file';
                
                // Set accepted file types based on validation
                if (paramInfo.validation && paramInfo.validation.accept) {
                    const acceptTypes = paramInfo.validation.accept.map(ext => `.${ext}`).join(',');
                    input.accept = acceptTypes;
                }
                
                // Add file selection preview
                input.addEventListener('change', (e) => {
                    this.handleFileSelection(e, paramName);
                });
            } else {
                // Text input for other types
                input = document.createElement('input');
                input.type = 'text';
            }
            
            input.id = `param-${paramName}`;
            input.name = paramName;
            
            // Set required attribute for required parameters
            if (paramInfo.required) {
                input.required = true;
            }
            
            if (paramInfo.default !== undefined) {
                if (paramInfo.type === 'boolean') {
                    input.checked = paramInfo.default;
                } else {
                    input.value = paramInfo.default;
                }
            }
            
            if (paramInfo.description) {
                input.title = paramInfo.description;
            }
            
            groupDiv.appendChild(label);
            groupDiv.appendChild(input);
            
            if (paramInfo.description) {
                const desc = document.createElement('small');
                desc.textContent = paramInfo.description;
                desc.style.color = '#666';
                groupDiv.appendChild(desc);
            }
            
            formDiv.appendChild(groupDiv);
        });
        
        // Check parameters after form generation
        this.checkParametersReady();
    }

    clearParameterForm() {
        document.getElementById('parameter-form').innerHTML = '<p>Please select a workflow</p>';
        // Disable execute button when parameters are cleared
        document.getElementById('execute-btn').disabled = true;
    }

    handleFileSelection(event, paramName) {
        const file = event.target.files[0];
        if (!file) {
            return;
        }

        // Show file info
        const input = event.target;
        const groupDiv = input.parentElement;
        
        // Remove previous preview if exists
        const existingPreview = groupDiv.querySelector('.file-preview');
        if (existingPreview) {
            existingPreview.remove();
        }

        // Create file preview
        const previewDiv = document.createElement('div');
        previewDiv.className = 'file-preview';
        previewDiv.style.marginTop = '10px';
        previewDiv.style.padding = '10px';
        previewDiv.style.border = '1px solid #ddd';
        previewDiv.style.borderRadius = '4px';
        previewDiv.style.backgroundColor = '#f9f9f9';

        // File info
        const fileInfo = document.createElement('div');
        fileInfo.innerHTML = `
            <strong>Selected file:</strong> ${file.name}<br>
            <strong>Size:</strong> ${(file.size / 1024 / 1024).toFixed(2)} MB<br>
            <strong>Type:</strong> ${file.type}
        `;
        previewDiv.appendChild(fileInfo);

        // Image preview for image files
        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.style.maxWidth = '200px';
            img.style.maxHeight = '200px';
            img.style.marginTop = '10px';
            img.style.border = '1px solid #ccc';
            img.style.borderRadius = '4px';
            
            const reader = new FileReader();
            reader.onload = (e) => {
                img.src = e.target.result;
            };
            reader.readAsDataURL(file);
            
            previewDiv.appendChild(img);
        }

        groupDiv.appendChild(previewDiv);
        
        this.log(`Selected file: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`, 'info');
        
        // Check if all parameters are ready after file selection
        this.checkParametersReady();
    }

    checkParametersReady() {
        const workflowSelect = document.getElementById('workflow-select');
        const executeBtn = document.getElementById('execute-btn');
        const formDiv = document.getElementById('parameter-form');
        
        // Check if workflow is selected
        if (!workflowSelect.value) {
            executeBtn.disabled = true;
            return;
        }
        
        // Check if all required parameters are filled
        const inputs = formDiv.querySelectorAll('input, select, textarea');
        let allParametersReady = true;
        
        for (const input of inputs) {
            // For required parameters
            if (input.hasAttribute('required') || input.name) {
                if (input.type === 'file') {
                    // Check if file is selected
                    if (!input.files || input.files.length === 0) {
                        allParametersReady = false;
                        break;
                    }
                } else if (input.type === 'checkbox') {
                    // Checkbox is always valid (can be checked or unchecked)
                    continue;
                } else {
                    // Check if text/number input has value
                    if (!input.value.trim()) {
                        allParametersReady = false;
                        break;
                    }
                }
            }
        }
        
        executeBtn.disabled = !allParametersReady;
    }

    async executeWorkflow() {
        try {
            const workflowId = document.getElementById('workflow-select').value;
            if (!workflowId) {
                throw new Error('Please select a workflow');
            }
            
            // Collect parameters (now async for file upload)
            const params = await this.collectParameters();
            
            // Generate request ID
            const requestId = `test_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            this.log(`Executing workflow: ${workflowId}, Request ID: ${requestId}`, 'info');
            
            // Send request
            const response = await fetch(`${this.apiBase}/workflow/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    workflow_id: workflowId,
                    params: params,
                    request_id: requestId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            if (!result.success) {
                throw new Error('Workflow execution failed');
            }
            
            this.currentTask = result.data;
            this.log(`Workflow submitted: ${requestId}`, 'success');
            
            // Subscribe to updates
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                this.websocket.send(JSON.stringify({
                    type: 'subscribe',
                    request_id: requestId
                }));
            }
            
            // Update UI
            this.updateCurrentTaskInfo(result.data);
            this.showProgress();
            this.updateExecuteButton(true);
            
        } catch (error) {
            this.log(`Workflow execution failed: ${error.message}`, 'error');
            console.error('Workflow execution error:', error);
        }
    }

    async collectParameters() {
        const params = {};
        const formDiv = document.getElementById('parameter-form');
        const inputs = formDiv.querySelectorAll('input, select, textarea');
        
        for (const input of inputs) {
            if (input.type === 'checkbox') {
                params[input.name] = input.checked;
            } else if (input.type === 'number') {
                params[input.name] = parseFloat(input.value) || 0;
            } else if (input.type === 'file') {
                // Handle file upload
                if (input.files && input.files[0]) {
                    const file = input.files[0];
                    // For now, we'll upload the file and get a URL
                    // This requires implementing file upload endpoint
                    const uploadedUrl = await this.uploadFile(file, input.name);
                    params[input.name] = uploadedUrl;
                } else {
                    throw new Error(`Please select a file for ${input.name}`);
                }
            } else {
                params[input.name] = input.value;
            }
        }
        
        return params;
    }

    async uploadFile(file, paramName) {
        try {
            this.log(`Uploading file: ${file.name}`, 'info');
            
            const formData = new FormData();
            formData.append('file', file);
            formData.append('param_name', paramName);
            
            const response = await fetch(`${this.apiBase}/files/upload`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Upload failed: HTTP ${response.status}`);
            }
            
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.error || 'Upload failed');
            }
            
            this.log(`File uploaded successfully: ${result.data.url}`, 'success');
            return result.data.url;
            
        } catch (error) {
            this.log(`File upload failed: ${error.message}`, 'error');
            throw error;
        }
    }

    async cancelCurrentTask() {
        if (!this.currentTask || !this.currentTask.request_id) {
            this.log('No active task to cancel', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`${this.apiBase}/workflow/cancel/${this.currentTask.request_id}`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.log(`Task cancellation requested: ${this.currentTask.request_id}`, 'info');
            
        } catch (error) {
            this.log(`Task cancellation failed: ${error.message}`, 'error');
        }
    }

    // UI update methods
    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('connection-status');
        const wsStatusElement = document.getElementById('ws-status');
        
        if (connected) {
            statusElement.textContent = 'Connected';
            statusElement.className = 'connected';
            wsStatusElement.textContent = 'Connected';
        } else {
            statusElement.textContent = 'Disconnected';
            statusElement.className = 'disconnected';
            wsStatusElement.textContent = 'Disconnected';
        }
    }

    updateCurrentTaskInfo(taskData) {
        const infoDiv = document.getElementById('current-task-info');
        
        if (!taskData) {
            infoDiv.innerHTML = '<p>No active task</p>';
            return;
        }
        
        infoDiv.innerHTML = `
            <div class="task-info fade-in">
                <h4>Task ID: ${taskData.request_id}</h4>
                <p><strong>Workflow:</strong> ${taskData.workflow_id}</p>
                <p><strong>Status:</strong> <span class="status-indicator ${taskData.status}"></span>${taskData.status}</p>
                <p><strong>Message:</strong> ${taskData.message || 'Processing...'}</p>
                ${taskData.estimated_remaining ? 
                    `<p><strong>Time remaining:</strong> ${taskData.estimated_remaining}s</p>` : ''
                }
            </div>
        `;
    }

    updateProgress(progress, stage, message) {
        const container = document.getElementById('progress-container');
        const fill = document.getElementById('progress-fill');
        const percentage = document.getElementById('progress-percentage');
        const stageElement = document.getElementById('progress-stage');
        const messageElement = document.getElementById('progress-message');
        
        container.style.display = 'block';
        fill.style.width = `${progress}%`;
        percentage.textContent = `${Math.round(progress)}%`;
        stageElement.textContent = stage;
        messageElement.textContent = message;
    }

    showProgress() {
        document.getElementById('progress-container').style.display = 'block';
    }

    hideProgress() {
        document.getElementById('progress-container').style.display = 'none';
    }

    resetTaskDisplay() {
        this.updateCurrentTaskInfo(null);
        this.hideProgress();
        this.updateExecuteButton(false);
    }

    updateExecuteButton(executing) {
        const executeBtn = document.getElementById('execute-btn');
        const cancelBtn = document.getElementById('cancel-btn');
        
        if (executing) {
            executeBtn.disabled = true;
            executeBtn.textContent = 'Executing...';
            cancelBtn.disabled = false;
        } else {
            executeBtn.disabled = false;
            executeBtn.textContent = 'Execute Workflow';
            cancelBtn.disabled = true;
        }
    }

    displayResults(outputImages) {
        const container = document.getElementById('results-container');
        
        container.innerHTML = '';
        
        outputImages.forEach((image, index) => {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'result-image fade-in';
            
            resultDiv.innerHTML = `
                <h4>Result ${index + 1}</h4>
                <img src="${image.url}" alt="Generated result" loading="lazy">
                <div class="result-actions">
                    <a href="${image.url}" target="_blank" class="btn btn-primary">View</a>
                    <button onclick="app.downloadImage('${image.url}', '${image.filename}')" 
                            class="btn btn-secondary">Download</button>
                </div>
                <p><small>File: ${image.filename} (${this.formatFileSize(image.size)})</small></p>
            `;
            
            container.appendChild(resultDiv);
        });
    }

    downloadImage(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = filename || 'output.png';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    addToTaskHistory(taskData) {
        this.taskHistory.unshift(taskData);
        
        // Limit history size
        if (this.taskHistory.length > 50) {
            this.taskHistory = this.taskHistory.slice(0, 50);
        }
        
        this.updateTaskHistoryDisplay();
    }

    updateTaskHistoryDisplay() {
        const listDiv = document.getElementById('task-list');
        const countElement = document.getElementById('task-count');
        
        countElement.textContent = this.taskHistory.length;
        
        if (this.taskHistory.length === 0) {
            listDiv.innerHTML = '<p>No task history</p>';
            return;
        }
        
        listDiv.innerHTML = '';
        
        this.taskHistory.forEach(task => {
            const itemDiv = document.createElement('div');
            itemDiv.className = `task-item ${task.status}`;
            
            const duration = task.completed_at && task.started_at ? 
                Math.round((new Date(task.completed_at) - new Date(task.started_at)) / 1000) : 0;
            
            itemDiv.innerHTML = `
                <div class="task-item-header">
                    <span>${task.request_id}</span>
                    <span class="status-indicator ${task.status}"></span>
                </div>
                <div class="task-item-details">
                    Workflow: ${task.workflow_id} | 
                    Status: ${task.status} | 
                    ${duration > 0 ? `Duration: ${duration}s` : ''}
                    ${task.error_message ? `| Error: ${task.error_message}` : ''}
                </div>
            `;
            
            listDiv.appendChild(itemDiv);
        });
    }

    // Utility methods
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    log(message, level = 'info') {
        const logOutput = document.getElementById('log-output');
        const timestamp = new Date().toLocaleTimeString();
        
        const logEntry = document.createElement('div');
        logEntry.className = `log-entry ${level}`;
        logEntry.innerHTML = `
            <span class="log-timestamp">[${timestamp}]</span> ${message}
        `;
        
        logOutput.appendChild(logEntry);
        
        // Auto scroll
        if (this.autoScroll) {
            logOutput.scrollTop = logOutput.scrollHeight;
        }
        
        // Limit log entries
        const entries = logOutput.children;
        if (entries.length > 500) {
            logOutput.removeChild(entries[0]);
        }
        
        console.log(`[${level.toUpperCase()}] ${message}`);
    }

    clearLog() {
        document.getElementById('log-output').innerHTML = '';
        this.log('Log cleared', 'info');
    }

    exportLog() {
        const logOutput = document.getElementById('log-output');
        const text = Array.from(logOutput.children).map(entry => entry.textContent).join('\n');
        
        const blob = new Blob([text], { type: 'text/plain' });
        const url = window.URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `workflow-test-log-${new Date().toISOString().slice(0, 19)}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        window.URL.revokeObjectURL(url);
        
        this.log('Log exported', 'success');
    }

    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        const btn = document.getElementById('auto-scroll-btn');
        
        if (this.autoScroll) {
            btn.classList.add('active');
            btn.textContent = 'Auto Scroll';
        } else {
            btn.classList.remove('active');
            btn.textContent = 'Manual Scroll';
        }
    }

    async checkSystemHealth() {
        try {
            const response = await fetch(`${this.apiBase}/system/health`);
            const result = await response.json();
            
            const statusElement = document.getElementById('system-status');
            
            if (result.success) {
                // 测试系统本身是健康的
                if (result.data.comfyui_server && result.data.comfyui_server.status === 'healthy') {
                    statusElement.textContent = 'System healthy';
                    statusElement.style.color = '#28a745';
                } else {
                    // ComfyUI不可用，但测试系统正常
                    statusElement.textContent = 'ComfyUI unavailable';
                    statusElement.style.color = '#ffc107';
                    this.log('ComfyUI server is not available, but test system is running', 'warning');
                }
            } else {
                statusElement.textContent = 'System unhealthy';
                statusElement.style.color = '#dc3545';
            }
            
        } catch (error) {
            document.getElementById('system-status').textContent = 'Status unknown';
            document.getElementById('system-status').style.color = '#dc3545';
            this.log(`Health check failed: ${error.message}`, 'error');
        }
    }

    async showSystemStats() {
        try {
            const response = await fetch(`${this.apiBase}/system/stats`);
            const result = await response.json();
            
            this.showModal('System Statistics', `
                <h4>Test System Stats</h4>
                <p><strong>Active sessions:</strong> ${result.data.test_system.sessions.active_sessions}</p>
                <p><strong>Total sessions:</strong> ${result.data.test_system.sessions.total_sessions}</p>
                <p><strong>Total requests:</strong> ${result.data.test_system.sessions.total_requests}</p>
                
                <h4>ComfyUI Server Stats</h4>
                <pre>${JSON.stringify(result.data.comfyui_server, null, 2)}</pre>
            `);
            
        } catch (error) {
            this.log(`Failed to get system stats: ${error.message}`, 'error');
        }
    }

    async showFileList() {
        try {
            const response = await fetch(`${this.apiBase}/files/output?limit=20`);
            const result = await response.json();
            
            let content = '<h4>Output Files</h4>';
            
            if (result.success && result.data.files.length > 0) {
                content += '<div style="max-height: 400px; overflow-y: auto;">';
                result.data.files.forEach(file => {
                    content += `
                        <div style="border-bottom: 1px solid #eee; padding: 8px 0;">
                            <strong>${file.filename}</strong><br>
                            <small>Size: ${this.formatFileSize(file.size)} | 
                            Created: ${new Date(file.created_time * 1000).toLocaleString()}</small><br>
                            <a href="${file.url}" target="_blank" class="btn btn-outline" style="margin-top: 5px;">View</a>
                        </div>
                    `;
                });
                content += '</div>';
                content += `<p><small>Total: ${result.data.total} files</small></p>`;
            } else {
                content += '<p>No files found</p>';
            }
            
            this.showModal('Output Files', content);
            
        } catch (error) {
            this.log(`Failed to load file list: ${error.message}`, 'error');
        }
    }

    showModal(title, content) {
        const modal = document.getElementById('modal');
        const titleElement = document.getElementById('modal-title');
        const bodyElement = document.getElementById('modal-body');
        
        titleElement.textContent = title;
        bodyElement.innerHTML = content;
        modal.style.display = 'flex';
    }

    hideModal() {
        document.getElementById('modal').style.display = 'none';
    }

    bindEvents() {
        // Workflow selection
        document.getElementById('workflow-select').addEventListener('change', () => {
            this.onWorkflowChange();
        });
        
        // Refresh workflows
        document.getElementById('refresh-workflows').addEventListener('click', () => {
            this.loadWorkflows();
        });
        
        // Execute workflow
        document.getElementById('execute-btn').addEventListener('click', () => {
            this.executeWorkflow();
        });
        
        // Cancel task
        document.getElementById('cancel-btn').addEventListener('click', () => {
            this.cancelCurrentTask();
        });
        
        // Clear log
        document.getElementById('clear-log-btn').addEventListener('click', () => {
            this.clearLog();
        });
        
        // Auto scroll toggle
        document.getElementById('auto-scroll-btn').addEventListener('click', () => {
            this.toggleAutoScroll();
        });
        
        // Export log
        document.getElementById('export-log-btn').addEventListener('click', () => {
            this.exportLog();
        });
        
        // Clear history
        document.getElementById('clear-history-btn').addEventListener('click', () => {
            this.taskHistory = [];
            this.updateTaskHistoryDisplay();
            this.log('Task history cleared', 'info');
        });
        
        // Quick actions
        document.getElementById('health-check-btn').addEventListener('click', () => {
            this.checkSystemHealth();
        });
        
        document.getElementById('system-stats-btn').addEventListener('click', () => {
            this.showSystemStats();
        });
        
        document.getElementById('list-files-btn').addEventListener('click', () => {
            this.showFileList();
        });
        
        // Modal controls
        document.querySelector('.modal-close').addEventListener('click', () => {
            this.hideModal();
        });
        
        document.getElementById('modal-cancel').addEventListener('click', () => {
            this.hideModal();
        });
        
        document.getElementById('modal-ok').addEventListener('click', () => {
            this.hideModal();
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key === 'Enter') {
                event.preventDefault();
                if (!document.getElementById('execute-btn').disabled) {
                    this.executeWorkflow();
                }
            } else if (event.ctrlKey && event.key === 'k') {
                event.preventDefault();
                this.clearLog();
            } else if (event.key === 'F5') {
                event.preventDefault();
                this.loadWorkflows();
            }
        });
        
        // Modal backdrop click
        document.getElementById('modal').addEventListener('click', (event) => {
            if (event.target.id === 'modal') {
                this.hideModal();
            }
        });
    }
}

// Global variable
let app;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    app = new WorkflowTestSystem();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (app && app.websocket) {
        app.websocket.close();
    }
});