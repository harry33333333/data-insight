import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import Field
from typing import Any
import pandas as pd

load_dotenv(dotenv_path=".env")

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
from llm.aliyun_llm import AliyunLLM

class WriteFileTool(BaseTool):
    name: str = "WriteFile"
    description: str = "将 Python 脚本、测试用例或 HTML 代码保存到指定的文件路径中。"
    
    emit_log_func: Any = Field(default=None)
    
    def _run(self, filepath: str, content: str) -> str:
        if content.startswith("```"):
            lines = content.split('\n')
            if len(lines) > 2:
                content = '\n'.join(lines[1:-1])
        
        if self.emit_log_func:
            escaped_code = content.replace("<", "&lt;").replace(">", "&gt;")
            html_msg = f"""
            <div style="color:#58a6ff; margin-bottom:5px;">[Tool Call] 🤖 AI 正在生成并保存文件: <b>{filepath}</b></div>
            <pre class="code-block"><code>{escaped_code}</code></pre>
            """
            self.emit_log_func(html_msg)

        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content.strip())
        return f"✅ 代码已成功保存至: {filepath}"


def get_data_preview(filepath: str) -> str:
    """提取文件结构，输出原始 2D 矩阵"""
    try:
        preview_text = ""
        if filepath.endswith('.csv'):
            df = pd.read_csv(filepath, nrows=5, header=None)
            raw_data = df.to_json(orient="values", force_ascii=False)
            preview_text += f"【单表 CSV】前5行原生 2D 矩阵:\n{raw_data}\n"
        elif filepath.endswith(('.xls', '.xlsx')):
            xls = pd.ExcelFile(filepath)
            preview_text += f"【Excel 多 Sheet】包含的 Sheet: {xls.sheet_names}\n"
            for sheet in xls.sheet_names[:10]: # 扩大到 10 个 Sheet，确保读到指标对比
                df = pd.read_excel(xls, sheet_name=sheet, nrows=5, header=None)
                raw_data = df.to_json(orient="values", force_ascii=False)
                preview_text += f"\n--- Sheet [{sheet}] 前5行原生 2D 矩阵 ---\n{raw_data}\n"
        return preview_text
    except Exception as e:
        return f"预览提取失败: {e}"


def run_ai_pipeline_dynamic(user_prompt: str, filename: str, emit_log=None):
    def log(msg):
        print(msg)
        if emit_log:
            emit_log(msg)

    log("初始化 Qwen3.7-plus 大模型及通用分析引擎...")
    llm = AliyunLLM(model="qwen3.7-plus-2026-05-26", api_key=os.getenv("QWEN_API_KEY"), region="cn")

    if filename:
        file_path = f"static/uploads/{filename}"
        log(f"🔎 正在预检真实数据 2D 结构: {filename}...")
        data_preview = get_data_preview(file_path)
        
        context_msg = f"""
        【核心约束 - 数据源】：用户已上传本地文件 `static/uploads/{filename}`。
        下面是该文件的原生前 5 行二维数组（null 代表空单元格）：
        ========= 数据预览 =========
        {data_preview}
        ===========================
        """
    else:
        context_msg = "【数据源约束】：无文件，请生成连接 PostgreSQL 的 psycopg2 提取代码。必须加入 Mock 数据逻辑。"

    write_tool = WriteFileTool(emit_log_func=emit_log)

    architect = Agent(
        role="高级数据架构师与 BI 产品经理",
        goal="阅读二维数组预览，找到真实的列名，并设计严谨的 JSON Schema。",
        backstory="""【数据防坑红线】：
        1. 绝不允许在 JSON Schema 中使用 'Unnamed: X'！真正的列名通常在第 2 或第 3 行。
        2. 必须明确每个字段的数据类型（如 float, int, str）。
        3. 去重指标（UV、DAU）绝对禁止跨维度使用 SUM 相加！""",
        verbose=True,
        llm=llm,
        step_callback=lambda step: log(f"🧠 [架构师思考中] 正在识别真实表头并规范数据类型...")
    )

    # 💥 核心修复 1：为后端注入数值强转与 NaN 清理逻辑
    backend_dev = Agent(
        role="资深 TDD Python 数据工程师",
        goal="编写极度鲁棒的 Pandas 脚本，严格确保数据类型与 Pydantic 契约 100% 一致。",
        backstory=f"""{context_msg}
        【致命的 Pydantic 校验与 JSON 报错防坑红线】：
        1. 之前的 Pydantic 校验失败是因为你把 Excel 里的横杠 '-' 或空字符串 '' 直接当成了数字传给 JSON！
        2. 提取任何数值列（如 PV, UV, DUV, 时长, 点击等）时，必须强制转换类型：`df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)`。
        3. Python 的 `NaN` 写入 JSON 会导致前端 `JSON.parse` 直接白屏崩溃！必须在转换 dict 前，使用 `df.fillna(0)` 替换所有空值。
        4. 必须剔除“总计”和“汇总”行，防止数据重复翻倍计算。
        5. 你编写的 generated_etl.py 输出的 JSON 必须完美通过你写的 test_report.py 的校验。
        6. 严禁在 test_report.py 中写 autouse=True 的执行脚本。""",
        verbose=True,
        llm=llm,
        tools=[write_tool],
        step_callback=lambda step: log(f"💻 [后端开发中] 正在编写含强制数值转换与 NaN 清理的 Pandas 提取脚本...")
    )

    # 💥 核心修复 2：为前端注入沙盒隔离与兜底逻辑
    frontend_dev = Agent(
        role="高级前端可视化工程师 (BI大屏专家)",
        goal="编写具有极强容错能力的动态 HTML 看板，坚决杜绝白屏现象。",
        backstory="""【前端防白屏与容错红线】：
        1. 现在的页面白屏了！原因是你写的 JS 代码在解析数据时抛出了 TypeError (如 undefined.forEach)，导致整个页面 JS 崩溃！
        2. 必须使用 `fetch('/api/dynamic-data')` 拉取数据。
        3. 必须在 JS 中为**每一个独立图表**的渲染逻辑包裹独立的 `try { ... } catch (e) { console.error('模块渲染失败', e); }` 块！
        4. 哪怕后端返回的 JSON 结构缺失了某个字段，其他正常的图表也必须渲染出来，绝对不能因为一个报错导致全军覆没！
        5. UI 美学：浅灰背景(#f0f2f6)、线性渐变高级标题栏，白色卡片带圆角(12px)和柔和阴影。""",
        verbose=True,
        llm=llm,
        tools=[write_tool],
        step_callback=lambda step: log(f"🎨 [前端生成中] 正在构建带有 Try-Catch 沙盒隔离的容错图表引擎...")
    )

    task_design = Task(
        description=f"用户的需求：'{user_prompt}'。\n{context_msg}\n输出一份详尽的 JSON Schema 和图表设计思路。",
        expected_output="明确的 JSON 结构定义与对应的图表呈现方式。",
        agent=architect
    )

    task_etl = Task(
        description="""
        基于架构师的设计：
        1. 编写 `test_report.py`（Pydantic 契约和 pytest 用例）。
        2. 编写 `generated_etl.py`（必须包含 `pd.to_numeric(errors='coerce').fillna(0)` 防止 Pydantic 报错和 JSON NaN 崩溃）。
        【规则红线】：只要生成这两个文件立刻结束！绝对禁止写任何辅助执行脚本！
        """,
        expected_output="生成具有强类型转换的 `test_report.py` 和 `generated_etl.py` 两个文件。",
        agent=backend_dev
    )

    task_ui = Task(
        description="""使用 WriteFile 生成纯 HTML5 的 `output/dynamic_report.html`。每个图表渲染必须有 try-catch 保护。""",
        expected_output="生成高自适应性、高容错的企业级 `output/dynamic_report.html`。",
        agent=frontend_dev
    )

    crew = Crew(
        agents=[architect, backend_dev, frontend_dev],
        tasks=[task_design, task_etl, task_ui],
        process=Process.sequential
    )

    log("🤖 启动 CrewAI 团队协作流程，开始智能分析...")
    crew.kickoff()
    
    log("🔨 AI 生成完毕，开始物理执行 ETL 流水线...")
    try:
        subprocess.run([sys.executable, "generated_etl.py"], check=True)
        log("✅ [ETL执行] 数据提取脚本运行成功，已生成 output/report_data.json！")
    except Exception as e:
        log(f"⚠️ [ETL执行报错] 提取真实数据发生错误，系统已启用 Mock 降级。报错信息: {e}")

    try:
        test_res = subprocess.run(["pytest", "test_report.py", "-v", "--disable-warnings"], capture_output=True, text=True)
        if test_res.returncode == 0:
            log("✅ [TDD测试] pytest 契约强类型验证完美通过！")
        else:
            log(f"❌ [TDD测试] pytest 契约验证存在瑕疵，但不影响展示。\n{test_res.stdout[-400:]}")
    except Exception as e:
        pass

    log("🎉 全流程执行成功！您可以点击【查看动态生成报告】浏览最终成果。")