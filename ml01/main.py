from crewai import Agent, Task, Crew, Process
from crewai_files import File
from llm import aliyun_llm
from crewai_tools import FileReadTool
from crewai.tools import BaseTool
import os
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
print(project_root)
sys.path.insert(0, str(project_root))

class UTF8FileReaderTool(BaseTool):
    name: str = "UTF8FileReader"
    description: str = "以 UTF-8 编码读取文件内容"

    def _run(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return content

    async def _arun(self, file_path: str) -> str:
        return self._run(file_path)


class UTF8FileWriterTool(BaseTool):
    name: str = "UTF8FileWriter"
    description: str = "以 UTF-8 编码写入文件"

    def _run(self, file_path: str, content: str) -> str:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 已保存：{file_path}"


def process_html(html_file: str, instruction: str = "") -> str:
    """
    将 HTML 转换为 JSON 驱动格式（一步完成）

    参数:
        html_file: 要处理的 HTML 文件路径
        instruction: 转换过程中的额外指令

    返回:
        str: 改造后包含 JSON 数据绑定的完整 HTML 代码
    """
    # 初始化 LLM 并配置
    llm = aliyun_llm.AliyunLLM(
        model="qwen-plus",
        api_key=os.getenv("QWEN_API_KEY"),
        region="cn",  # 可选值: "cn", "intl", "finance"
    )

    # 创建工具实例
    utf8_writer = UTF8FileWriterTool()
    utf8_reader = UTF8FileReaderTool()

    # 创建 HTML 转换专家代理
    agent = Agent(
        role='HTML转换专家',
        goal='将HTML页面改造为JSON数据驱动',
        backstory='你擅长HTML分析和数据提取',
        verbose=True,
        llm=llm,
        tools=[
            utf8_reader,
            utf8_writer,
        ]
    )

    # 定义转换任务
    task = Task(
        description=f"""
        请处理HTML页面，将其改造为完全JSON数据驱动的页面：

        任务：
        1. **彻底提取所有静态数据**到JSON：
           - 所有数字（统计卡片、表格数据、百分比等）
           - 所有文本内容（标题、标签、描述、洞察分析等）
           - 所有日期和数据周期信息
           - 所有图表数据
           - 所有表格数据
           - 所有列表数据
           - 所有综合建议内容

        2. **HTML改造要求（关键）**：
           - **禁止在HTML中保留任何硬编码的数值或文本**
           - 所有需要渲染的内容位置，使用以下两种方式之一：
             * 空白占位符：<span id="xxx"></span>
             * 占位标记：<span id="xxx">{{xxx}}</span>
           - 保持原有样式和布局结构不变
           - 示例：
             ❌ 错误：<span id="totalCount">153</span>
             ✅ 正确：<span id="totalCount"></span>
             ❌ 错误：<span id="name">傅x</span>
             ✅ 正确：<span id="name"></span>
           - 表格行、列表项等使用 <tbody id="xxx"></tbody> 或 <div id="xxx"></div>

        3. **JSON数据结构**：
           - 使用 <script type="application/json" id="jsonData"> 存储数据
           - JSON结构清晰、层次分明
           - 包含所有需要渲染的数据字段

        4. **渲染脚本要求**：
           - 在 DOMContentLoaded 事件时自动执行渲染
           - 覆盖所有HTML中的占位符内容
           - 动态生成所有表格行、列表项
           - 初始化所有ECharts图表
           - 确保渲染后页面与原HTML外观完全一致

        5. **重要**：使用 UTF8FileWriter 工具将完整的改造后HTML代码写入 index.html 文件

        鮰外要求：{instruction}

        处理步骤：
        - 首先使用 UTF8FileReader 工具读取源HTML文件（文件路径: {html_file}）
        - 仔细分析所有静态内容，包括数字、文本、HTML标签内的内容
        - 将所有静态内容提取到JSON结构中
        - 改造HTML，用id标记所有动态内容位置
        - 编写完整的渲染脚本
        - 使用 UTF8FileWriter 工具保存到 index.html
        - 确保 index.html 文件被成功写入

        **关键要求**：HTML中不能有任何硬编码的数值或文本，所有内容都必须通过JSON渲染！
        """,
        agent=agent,
        expected_output="改造后的完整HTML文件已保存为 index.html，所有数据已提取到JSON",
        input_files={"source": File(source=html_file)},
    )

    # 执行转换工作流
    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential
    )

    return crew.kickoff()


# 使用示例
if __name__ == "__main__":
    result = process_html("demo.html", "请保持原有样式不变")
    print(result)