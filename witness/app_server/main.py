from fastapi import FastAPI
from witness.app_server.api import v1_image # 确保这里的导入路径正确

app = FastAPI(
    title="Witness Image Processing API",
    description="用于通过 ComfyUI 处理图像的 API 服务。",
    version="0.1.0"
)

# 包含 v1 版本的图像处理 API 路由
app.include_router(v1_image.router, prefix="/api/v1/image", tags=["Image Processing V1"])

@app.get("/")
async def root():
    return {"message": "欢迎来到 Witness 图像处理 API 服务！请访问 /docs 查看 API 文档。"}

# 如果直接运行此文件，则启动 uvicorn 服务器 (主要用于开发)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)