from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from database_manager import import_csvs_to_postgres
from main import run_ai_pipeline

app = FastAPI(title="Data Insight AI Agent")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 1. 渲染模板是同步操作，改为 def
@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    """渲染前端主页"""
    return templates.TemplateResponse(request=request, name="index.html", context={"request": request})

# 2. Pandas 和 SQLAlchemy 是同步阻塞的，改为 def 让 FastAPI 放入线程池执行
@app.post("/api/import-db")
def import_db():
    """触发导入 CSV 到 Postgres"""
    return import_csvs_to_postgres()

# 3. CrewAI 的 kickoff() 和 subprocess 是同步阻塞的，必须改为 def
@app.post("/api/run-ai")
def run_ai():
    """触发 CrewAI 生成与 ETL 运行"""
    return run_ai_pipeline()

# 4. 文件读取是同步 I/O，改为 def
@app.get("/api/report-data")
def get_report_data():
    """前端拉取生成的 JSON 数据用于 ECharts 渲染"""
    file_path = "report_data.json"
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "报告尚未生成，请先执行 AI 调度流水线"}

if __name__ == "__main__":
    import uvicorn
    # 启动命令: python app.py
    uvicorn.run(app, host="0.0.0.0", port=8000)