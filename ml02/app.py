from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import queue
import threading
import json
from main import run_ai_pipeline_dynamic

app = FastAPI(title="Data Insight AI Agent - Dynamic Stream")

os.makedirs("static/uploads", exist_ok=True)
os.makedirs("templates", exist_ok=True)
os.makedirs("output", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

log_queue = queue.Queue()

class AIRequest(BaseModel):
    prompt: str
    filename: str = ""

def emit_log(msg: str):
    log_queue.put(msg)

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    file_location = f"static/uploads/{file.filename}"
    with open(file_location, "wb+") as file_object:
        file_object.write(file.file.read())
    return {"filename": file.filename}

def event_stream():
    """SSE 生成器：使用 JSON 序列化保证多行代码格式不乱"""
    while True:
        try:
            msg = log_queue.get(timeout=30)
            # 将消息包装进 JSON，防止换行符截断 SSE 协议
            payload = json.dumps({"message": msg})
            yield f"data: {payload}\n\n"
            
            if "🎉 全流程执行成功" in msg or "报告生成完毕" in msg or "❌ 系统崩溃" in msg:
                break
        except queue.Empty:
            payload = json.dumps({"message": "[Heartbeat] AI 思考中..."})
            yield f"data: {payload}\n\n"

@app.get("/api/stream")
def stream_logs():
    return StreamingResponse(event_stream(), media_type="text/event-stream")

def run_ai_task(prompt: str, filename: str):
    try:
        run_ai_pipeline_dynamic(prompt, filename, emit_log)
    except Exception as e:
        emit_log(f"❌ 系统崩溃: {str(e)}")

@app.post("/api/run-ai-dynamic")
def run_ai(req: AIRequest):
    threading.Thread(target=run_ai_task, args=(req.prompt, req.filename)).start()
    return {"status": "started"}

@app.get("/api/view-report")
def view_report():
    report_path = "output/dynamic_report.html"
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>报告尚未生成或生成失败</h1>")

@app.get("/api/dynamic-data")
def get_dynamic_data():
    data_path = "output/report_data.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "JSON 数据尚未生成"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)