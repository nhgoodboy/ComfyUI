// 图像风格变换测试平台前端脚本

console.log("图像变换测试平台脚本已加载");

// 启动健康检查轮询

const statusDot = document.getElementById("api-status");
const statusText = document.getElementById("api-status-text");

async function checkApi() {
  try {
    const res = await fetch("/health", { cache: "no-store" });
    if (res.ok) {
      const data = await res.json();
      if (data.status === "healthy") {
        statusDot.classList.remove("offline");
        statusDot.classList.add("online");
        statusText.textContent = "正常";
        return;
      }
    }
    // 若返回非 200 或状态字段非 healthy
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
    statusText.textContent = "异常";
  } catch (e) {
    // 网络或解析错误
    statusDot.classList.remove("online");
    statusDot.classList.add("offline");
    statusText.textContent = "异常";
    console.error("健康检查失败", e);
  }
}

// 首次立即检查
checkApi();
// 每 5 秒轮询一次
setInterval(checkApi, 5000);

// ================= 新增: 图像上传与变换逻辑 =================
(() => {
  // 全局状态
  const state = {
    selectedFile: null,
    fileInfo: null,
    taskId: null,
    ws: null,
    reconnectCount: 0,
    progress: 0,
    history: JSON.parse(localStorage.getItem("history") || "[]"),
  };

  // ======== DOM 元素 ========
  const $ = (id) => document.getElementById(id);
  const fileInput = $("file-input");
  const uploadArea = $("upload-area");
  const configSection = $("config-section");
  const progressSection = $("progress-section");
  const resultSection = $("result-section");
  const originalImg = $("original-image");
  const resultImg = $("result-image");
  const progressFill = $("progress-fill");
  const progressText = $("progress-text");
  const progressPercent = $("progress-percent");
  const transformBtn = $("transform-btn");
  const strengthSlider = $("strength-slider");
  const strengthValue = $("strength-value");
  const styleSelect = $("style-select");
  const customPrompt = $("custom-prompt");
  const taskIdSpan = $("task-id");
  const processingTime = $("processing-time");
  const usedStyle = $("used-style");
  const downloadBtn = $("download-btn");
  const historyList = $("history-list");
  const errorToast = $("error-toast");
  const errorMsg = $("error-message");
  const successToast = $("success-toast");
  const successMsg = $("success-message");
  const previewImg = $("preview-image");
  const logModal = $("log-modal");
  const logContainer = $("log-container");
  const statsModal = $("stats-modal");
  const statsContainer = $("stats-container");

  // ======== 初始化 ========
  function initApp() {
    bindEvents();
    renderHistory();
  }

  function bindEvents() {
    fileInput.addEventListener("change", handleFileSelected);

    // 拖放上传
    uploadArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadArea.classList.add("dragover");
    });
    uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("dragover"));
    uploadArea.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadArea.classList.remove("dragover");
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files[0]) {
        handleFile(dt.files[0]);
      }
    });

    transformBtn.addEventListener("click", startTransform);

    strengthSlider.addEventListener("input", () => {
      strengthValue.textContent = strengthSlider.value;
    });

    downloadBtn.addEventListener("click", () => {
      if (state.resultUrl) {
        window.open(state.resultUrl, "_blank");
      }
    });

    // Footer links (anchors have inline onclick, ensure global funcs exist)
    window.showLogs = showLogs;
    window.closeLogs = closeLogs;
    window.showStats = showStats;
    window.closeStats = closeStats;

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        closeLogs();
        closeStats();
      }
    });
  }

  // ======== 文件选择 & 上传 ========
  function handleFileSelected(e) {
    const file = e.target.files[0];
    if (file) handleFile(file);
  }

  function handleFile(file) {
    // 校验
    if (!/\.(jpg|jpeg|png|webp)$/i.test(file.name)) {
      return toastError("仅支持 JPG/PNG/WebP 图片");
    }
    if (file.size > 10 * 1024 * 1024) {
      return toastError("文件大小超过 10MB 限制");
    }

    state.selectedFile = file;
    previewImage(file);
    uploadFile(file);
  }

  function previewImage(file) {
    const url = URL.createObjectURL(file);
    originalImg.src = url;
    if (previewImg) {
      previewImg.src = url;
      previewImg.style.display = "block";
    }
  }

  async function uploadFile(file) {
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("/api/upload", {
        method: "POST",
        body: fd,
      });
      const data = await res.json();
      if (res.ok && data.success) {
        state.fileInfo = data;
        toastSuccess("上传成功，配置参数后点击开始变换");
        showSection("config");
      } else {
        throw new Error(data.error || "上传失败");
      }
    } catch (err) {
      console.error(err);
      toastError(`上传失败: ${err.message}`);
    }
  }

  // ======== 启动变换 ========
  async function startTransform() {
    if (!state.fileInfo) return toastError("请先上传图片");

    try {
      transformBtn.disabled = true;
      const payload = {
        filename: state.fileInfo.filename,
        style_type: styleSelect.value,
        custom_prompt: customPrompt.value || null,
        strength: parseFloat(strengthSlider.value),
      };
      const res = await fetch("/api/transform", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (res.ok && data.success) {
        state.taskId = data.task_id;
        taskIdSpan.textContent = state.taskId;
        showSection("progress");
        connectWS();
      } else {
        throw new Error(data.error || "任务提交失败");
      }
    } catch (err) {
      console.error(err);
      toastError(err.message);
      transformBtn.disabled = false;
    }
  }

  // ======== WebSocket ========
  function connectWS() {
    if (!state.taskId) return;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const wsUrl = `${protocol}://${location.host}/ws`;
    state.ws = new WebSocket(wsUrl);

    state.ws.addEventListener("open", () => {
      state.reconnectCount = 0;
      state.ws.send(JSON.stringify({ type: "subscribe", task_id: state.taskId }));
    });

    state.ws.addEventListener("message", handleWsMessage);

    state.ws.addEventListener("close", () => {
      if (state.progress < 100 && state.reconnectCount < 3) {
        state.reconnectCount += 1;
        setTimeout(connectWS, 1000 * state.reconnectCount);
      } else if (state.progress < 100) {
        // 退回轮询
        pollTaskStatus();
      }
    });

    state.ws.addEventListener("error", () => state.ws.close());
  }

  function handleWsMessage(evt) {
    try {
      const msg = JSON.parse(evt.data);
      if (msg.type === "progress" && msg.task_id === state.taskId) {
        updateProgress(msg.progress, msg.message);
      } else if (msg.type === "completed" && msg.task_id === state.taskId) {
        state.progress = 100;
        updateProgress(100, "处理完成");
        handleCompleted(msg.output_url, msg.duration);
      } else if (msg.type === "error" && msg.task_id === state.taskId) {
        toastError(msg.message || "任务失败");
        resetInterface();
      }
    } catch (e) {
      console.warn("WS message parse error", e);
    }
  }

  // ======== 轮询 ========
  async function pollTaskStatus() {
    try {
      const res = await fetch(`/api/task/${state.taskId}`);
      if (!res.ok) throw new Error("无法获取任务状态");
      const data = await res.json();
      if (data.status === "completed") {
        handleCompleted(data.output_url, data.duration);
      } else if (data.status === "failed") {
        toastError(data.error_message || "任务失败");
        resetInterface();
      } else {
        updateProgress(data.progress, data.message);
        setTimeout(pollTaskStatus, 2000);
      }
    } catch (err) {
      console.error(err);
      setTimeout(pollTaskStatus, 5000);
    }
  }

  // ======== 进度 & 完成 ========
  function updateProgress(percent, message) {
    state.progress = percent;
    progressFill.style.width = `${percent}%`;
    progressPercent.textContent = `${percent.toFixed(0)}%`;
    progressText.textContent = message;
  }

  function handleCompleted(outputUrl, duration) {
    state.resultUrl = outputUrl;
    resultImg.src = outputUrl;
    processingTime.textContent = `${duration.toFixed(1)}s`;
    usedStyle.textContent = styleSelect.options[styleSelect.selectedIndex].text;
    downloadBtn.disabled = false;

    addToHistory({
      original: originalImg.src,
      result: outputUrl,
      style: styleSelect.value,
      time: Date.now(),
      duration,
    });

    showSection("result");
    toastSuccess("变换完成！");
    if (state.ws) state.ws.close();
  }

  // ======== 历史记录 ========
  function addToHistory(item) {
    state.history.unshift(item);
    state.history = state.history.slice(0, 20); // 最多保留20项
    localStorage.setItem("history", JSON.stringify(state.history));
    renderHistory();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    if (state.history.length === 0) {
      historyList.innerHTML = `<div class="history-empty"><i class="fas fa-inbox"></i><p>暂无处理记录</p></div>`;
      return;
    }
    state.history.forEach((h) => {
      const div = document.createElement("div");
      div.className = "history-item";
      div.innerHTML = `
        <img src="${h.result}" alt="result" />
        <span>${new Date(h.time).toLocaleString()}</span>
      `;
      div.addEventListener("click", () => {
        originalImg.src = h.original;
        resultImg.src = h.result;
        processingTime.textContent = `${(h.duration || 0).toFixed(1)}s`;
        usedStyle.textContent = h.style;
        showSection("result");
      });
      historyList.appendChild(div);
    });
  }

  // ======== UI 辅助 ========
  function showSection(name) {
    // upload 区域无需隐藏
    configSection.style.display = name === "config" ? "block" : "none";
    progressSection.style.display = name === "progress" ? "block" : "none";
    resultSection.style.display = name === "result" ? "block" : "none";
  }

  window.resetInterface = function () {
    transformBtn.disabled = false;
    showSection("upload");
    progressFill.style.width = "0%";
    progressPercent.textContent = "0%";
    progressText.textContent = "准备中...";
    downloadBtn.disabled = true;
    state.selectedFile = null;
    state.fileInfo = null;
    state.taskId = null;
    state.progress = 0;
    if (previewImg) {
      previewImg.style.display = "none";
      previewImg.src = "";
    }
    if (state.ws) state.ws.close();
  };

  // ======== Toast ========
  function toastError(msg) {
    errorMsg.textContent = msg;
    errorToast.style.display = "flex";
    setTimeout(() => (errorToast.style.display = "none"), 5000);
  }
  function toastSuccess(msg) {
    successMsg.textContent = msg;
    successToast.style.display = "flex";
    setTimeout(() => (successToast.style.display = "none"), 3000);
  }
  window.hideError = () => (errorToast.style.display = "none");
  window.hideSuccess = () => (successToast.style.display = "none");

  // ======== 日志与系统统计 ========
  async function showLogs() {
    if (logModal) logModal.style.display = "flex";
    if (logContainer) {
      logContainer.innerHTML = '<div class="log-loading"><i class="fas fa-spinner fa-spin"></i> 加载日志中...</div>';
      try {
        const res = await fetch("/api/logs?limit=200");
        if (!res.ok) throw new Error("无法获取日志");
        const data = await res.json();
        const logs = data.logs || data || [];
        const html = Array.isArray(logs)
          ? logs.map((l) => `<div class="log-line">${l}</div>`).join("")
          : `<pre>${JSON.stringify(logs, null, 2)}</pre>`;
        logContainer.innerHTML = html;
      } catch (err) {
        console.error(err);
        logContainer.innerHTML = `<div class="log-error">获取日志失败: ${err.message}</div>`;
      }
    }
  }

  function closeLogs() {
    if (logModal) logModal.style.display = "none";
  }

  async function showStats() {
    if (statsModal) statsModal.style.display = "flex";
    if (statsContainer) {
      statsContainer.innerHTML = '<div class="stats-loading"><i class="fas fa-spinner fa-spin"></i> 加载统计中...</div>';
      try {
        const res = await fetch("/api/stats");
        if (!res.ok) throw new Error("无法获取统计信息");
        const data = await res.json();
        const html = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        statsContainer.innerHTML = html;
      } catch (err) {
        console.error(err);
        statsContainer.innerHTML = `<div class="stats-error">获取统计失败: ${err.message}</div>`;
      }
    }
  }

  function closeStats() {
    if (statsModal) statsModal.style.display = "none";
  }

  // ======== 启动 ========
  document.addEventListener("DOMContentLoaded", initApp);
})();
