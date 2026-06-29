import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool

load_dotenv(dotenv_path=".env")

# 引入项目顶层 llm 模块
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
from llm.aliyun_llm import AliyunLLM

class WritePythonCodeTool(BaseTool):
    name: str = "WritePythonCode"
    description: str = "将 Python 代码保存为 generated_etl.py 文件"
    
    def _run(self, code: str) -> str:
        if code.startswith("```python"):
            code = code[9:]
        if code.endswith("```"):
            code = code[:-3]
        with open("generated_etl.py", "w", encoding="utf-8") as f:
            f.write(code.strip())
        return "✅ 代码已保存"

def run_ai_pipeline():
    # 使用你指定的 qwen3.7-plus 模型
    llm = AliyunLLM(
        model="qwen3.7-plus", 
        api_key=os.getenv("QWEN_API_KEY"),
        region="cn"
    )

    data_analyst = Agent(
        role="高级数据架构师",
        goal="分析数据库表结构，指导如何通过 SQL 或 Pandas 获取 PV、UV、用户分层等数据。",
        backstory="你精通 PostgreSQL 数据库，擅长规划海量数据的多表联合和聚合运算逻辑。",
        verbose=True,
        llm=llm
    )

    python_engineer = Agent(
        role="资深 Python 开发工程师",
        goal="编写一个名为 generated_etl.py 的脚本。该脚本需连接 PostgreSQL，执行聚合统计，并将结果严格按照 schema.py 格式导出为 report_data.json。",
        backstory="你精通 psycopg2、pandas 和 Pydantic。你写的代码总是能在本地无错误运行，并输出完美的 JSON。",
        verbose=True,
        llm=llm,
        tools=[WritePythonCodeTool()]
    )

    analyze_task = Task(
        description="""
        业务目标：将 PostgreSQL 数据库中以 'user_behavior_' 开头的表（由你同事刚导入）进行汇总。
        我们需要计算：
        1. Overview: 总 DAU, UV, PV, 平均时长。
        2. PV排行 (pv_ranks): 各模块 PV 前五。
        3. 用户分层 (user_layers): 提取各个分层（高频、低频）的人数。
        给出技术实现步骤。
        """,
        expected_output="数据处理策略文档",
        agent=data_analyst
    )

    code_task = Task(
        description="""
        根据架构师的策略，编写 `generated_etl.py`。
        
        【环境与连接避坑要求】：
        1. 必须在代码最开头添加 `os.environ['PGCLIENTENCODING'] = 'UTF8'`，防止 Windows 下 psycopg2 报错乱码。
        2. 读取数据库名的环境变量必须严格使用 `POSTGRES_DATABASE`（绝对不要使用 POSTGRES_DB）。
        3. 动态发现的表名包含中文（如 `user_behavior_用户行为...`），在拼接 SQL 时，表名必须用双引号包裹，例如 `FROM "{table_name}"`。
        
        【最高优先级 - 数据契约】：
        无论数据库是否连接成功，最终输出的 JSON 必须严格、完全符合以下字段结构（禁止自己发明字段名，必须一模一样）：
        - overview 对象包含: dau (int), uv (int), pv (int), avg_duration (float)
        - pv_ranks 数组，每个元素包含: domain (str), page_name (str), uv (int), pv (int)
        - user_layers 数组，每个元素包含: domain (str), layer (str), user_count (int)
        
        【降级与 Mock 逻辑】：
        如果连接失败、表字段不匹配或 SQL 执行报错，请直接捕获异常并启用 Mock 降级逻辑。
        Mock 数据必须严格使用上述契约的字段名！对于契约中要求但数据库可能没有的字段（如 domain），请编造合理的默认值（如 "主站"）。
        
        结果必须使用 json.dump 写入 `report_data.json` (ensure_ascii=False)，并使用 WritePythonCode 工具保存。
        """,
        expected_output="一份保存成功、可直接运行的 Python 脚本，且 JSON 字段名与契约 100% 匹配。",
        agent=python_engineer
    )

    crew = Crew(agents=[data_analyst, python_engineer], tasks=[analyze_task, code_task], process=Process.sequential)
    print("🤖 启动 CrewAI (qwen3.7-plus) 进行头脑风暴与代码生成...")
    crew.kickoff()

    print("🔨 执行生成的 ETL 脚本...")
    try:
        subprocess.run([sys.executable, "generated_etl.py"], check=True)
        print("✅ report_data.json 生成完毕！")
    except Exception as e:
        return {"status": "error", "message": f"生成的代码执行出错: {e}"}

    print("🧪 运行 TDD 测试验证...")
    test_res = subprocess.run(["pytest", "test_report.py", "-v", "--disable-warnings"])
    if test_res.returncode == 0:
        return {"status": "success", "message": "全流程执行成功，数据已生成并测试通过！"}
    else:
        return {"status": "error", "message": "测试未通过，数据格式不符合契约！"}

if __name__ == "__main__":
    run_ai_pipeline()