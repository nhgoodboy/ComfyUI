from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import requests
import websocket
import json
import uuid
import os
import threading
import time
from werkzeug.utils import secure_filename
import base64
from io import BytesIO
from PIL import Image

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
socketio = SocketIO(app, cors_allowed_origins="*")

# 确保上传和输出目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

class ComfyUIAPI:
    def __init__(self, server_address="127.0.0.1:6006"):
        self.server_address = server_address
        self.client_id = str(uuid.uuid4())
        self.current_task = None
    
    def submit_prompt(self, prompt):
        """提交绘图任务"""
        url = f"http://{self.server_address}/prompt"
        data = {
            "client_id": self.client_id,
            "prompt": prompt
        }
        try:
            response = requests.post(url, json=data)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_queue_status(self):
        """获取队列状态"""
        url = f"http://{self.server_address}/queue"
        try:
            response = requests.get(url)
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_image(self, filename, subfolder="", type="output"):
        """获取生成的图片"""
        url = f"http://{self.server_address}/view"
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": type
        }
        try:
            response = requests.get(url, params=params)
            return response.content
        except Exception as e:
            return None
    
    def upload_image(self, image_path):
        """上传图片到ComfyUI"""
        url = f"http://{self.server_address}/upload/image"
        files = {'image': open(image_path, 'rb')}
        data = {'overwrite': 'true'}
        try:
            response = requests.post(url, files=files, data=data)
            files['image'].close()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# 全局API实例
comfy_api = ComfyUIAPI()

def load_workflow():
    """加载工作流JSON"""
    with open('img_api.json', 'r', encoding='utf-8') as f:
        return json.load(f)

def modify_workflow(workflow, image_filename, positive_prompt=""):
    """修改工作流参数"""
    # 修改输入图像 - LoadImage节点
    if "1" in workflow:
        workflow["1"]["inputs"]["image"] = image_filename
    
    # 修改正面提示词 - easy positive节点
    if positive_prompt and "79" in workflow:
        workflow["79"]["inputs"]["positive"] = positive_prompt
    
    # 确保Florence2节点有图像输入
    if "76" in workflow:
        workflow["76"]["inputs"]["image"] = ["1", 0]
    
    # 确保LineArtPreprocessor节点有图像输入
    if "74" in workflow:
        workflow["74"]["inputs"]["image"] = ["1", 0]
    
    # 确保easy imageSize节点有图像输入
    if "47" in workflow:
        workflow["47"]["inputs"]["image"] = ["1", 0]
    
    # 确保VAEEncode节点有pixels输入
    if "72" in workflow:
        workflow["72"]["inputs"]["pixels"] = ["46", 0]  # 从ImageScaleToTotalPixels获取像素数据
    
    return workflow

def handle_websocket_messages(task_id):
    """处理WebSocket消息"""
    def on_message(ws, message):
        try:
            data = json.loads(message)
            
            # 发送进度更新到前端
            if data.get('type') == 'progress':
                progress_data = data.get('data', {})
                if progress_data.get('prompt_id') == task_id:
                    socketio.emit('progress', {
                        'value': progress_data.get('value', 0),
                        'max': progress_data.get('max', 100),
                        'percentage': int((progress_data.get('value', 0) / progress_data.get('max', 1)) * 100)
                    })
            
            # 任务完成
            elif data.get('type') == 'executed':
                exec_data = data.get('data', {})
                if exec_data.get('prompt_id') == task_id:
                    # 获取生成的图片
                    output = exec_data.get('output', {})
                    images = output.get('images', [])
                    
                    if images:
                        image_info = images[0]
                        image_data = comfy_api.get_image(
                            image_info['filename'],
                            image_info.get('subfolder', ''),
                            image_info.get('type', 'output')
                        )
                        
                        if image_data:
                            # 保存图片到本地
                            output_path = os.path.join(app.config['OUTPUT_FOLDER'], f"{task_id}.png")
                            with open(output_path, 'wb') as f:
                                f.write(image_data)
                            
                            # 转换为base64发送到前端
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                            
                            socketio.emit('completed', {
                                'success': True,
                                'image': f"data:image/png;base64,{image_base64}",
                                'filename': f"{task_id}.png"
                            })
                        else:
                            socketio.emit('completed', {
                                'success': False,
                                'error': '无法获取生成的图片'
                            })
                    else:
                        socketio.emit('completed', {
                            'success': False,
                            'error': '没有生成图片'
                        })
                        
        except Exception as e:
            socketio.emit('error', {'message': f'处理消息时出错: {str(e)}'})
    
    def on_error(ws, error):
        socketio.emit('error', {'message': f'WebSocket错误: {str(error)}'})
    
    def on_close(ws, close_status_code, close_msg):
        socketio.emit('info', {'message': 'WebSocket连接已关闭'})
    
    ws_url = f"ws://{comfy_api.server_address}/ws?clientId={comfy_api.client_id}"
    ws = websocket.WebSocketApp(
        ws_url,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    """生成图像"""
    try:
        # 检查是否有文件上传
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': '请选择图片文件'})
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': '请选择图片文件'})
        
        # 获取额外参数
        positive_prompt = request.form.get('positive_prompt', '')
        
        # 保存上传的文件
        filename = secure_filename(file.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(upload_path)
        
        # 上传图片到ComfyUI
        upload_result = comfy_api.upload_image(upload_path)
        if 'error' in upload_result:
            return jsonify({'success': False, 'error': f'上传图片失败: {upload_result["error"]}'})
        
        print(f"图片上传结果: {upload_result}")
        print(f"使用的文件名: {filename}")
        
        # 加载并修改工作流
        workflow = load_workflow()
        workflow = modify_workflow(workflow, filename, positive_prompt)
        
        print(f"修改后的工作流节点1: {workflow.get('1', {}).get('inputs', {})}")
        print(f"修改后的工作流节点76: {workflow.get('76', {}).get('inputs', {})}")
        print(f"修改后的工作流节点74: {workflow.get('74', {}).get('inputs', {})}")
        print(f"修改后的工作流节点72: {workflow.get('72', {}).get('inputs', {})}")
        print(f"修改后的工作流节点47: {workflow.get('47', {}).get('inputs', {})}")
        
        # 提交任务
        result = comfy_api.submit_prompt(workflow)
        
        if 'error' in result:
            return jsonify({'success': False, 'error': f'提交任务失败: {result["error"]}'})
        
        if result.get('node_errors'):
            return jsonify({'success': False, 'error': f'工作流错误: {result["node_errors"]}'})
        
        task_id = result['prompt_id']
        comfy_api.current_task = task_id
        
        # 启动WebSocket监听线程
        ws_thread = threading.Thread(target=handle_websocket_messages, args=(task_id,))
        ws_thread.daemon = True
        ws_thread.start()
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'message': '任务已提交，正在处理...'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'处理请求时出错: {str(e)}'})

@app.route('/queue')
def get_queue():
    """获取队列状态"""
    try:
        queue_status = comfy_api.get_queue_status()
        return jsonify(queue_status)
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download/<filename>')
def download_file(filename):
    """下载生成的图片"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """WebSocket连接处理"""
    emit('info', {'message': '已连接到服务器'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket断开处理"""
    print('客户端断开连接')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=6002) 