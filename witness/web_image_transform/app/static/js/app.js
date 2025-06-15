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
