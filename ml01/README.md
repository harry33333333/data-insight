# HTML to JSON 驱动转换工具

> 🤖 基于 CrewAI 的智能 HTML 页面改造工具，自动将静态 HTML 转换为 JSON 数据驱动格式

## 功能简介

本工具使用 CrewAI 多智能体框架和阿里云通义千问大模型，能够自动分析 HTML 页面结构，提取所有静态数据（数字、文本、图表配置等），并将其改造为完全 JSON 数据驱动的动态页面。

### 核心功能

- ✅ **智能数据提取**：自动识别并提取 HTML 中的所有静态内容
- ✅ **JSON 数据绑定**：将所有数据结构化存储到 JSON 中
- ✅ **动态渲染脚本**：自动生成 JavaScript 渲染逻辑
- ✅ **图表初始化**：支持 ECharts 图表的动态初始化
- ✅ **样式保持**：完整保留原有页面的样式和布局
- ✅ **UTF-8 编码支持**：完整支持中文内容的读写

---

## 环境要求

- Python 3.12+
- CrewAI 框架
- 阿里云通义千问 API Key

---

## 安装与配置

### 1. 安装依赖

```bash
# 安装项目依赖
uv sync
```

### 2. 配置环境变量

```bash
# 设置阿里云通义千问 API Key
export QWEN_API_KEY="your-qwen-api-key-here"
```

---

## 使用方法

### 基础用法

```python
from main import process_html

# 转换 HTML 文件
result = process_html(
    html_file="demo.html",
    instruction="请保持原有样式不变"
)

print(result)
```

### 命令行运行

```bash
# 在 ml01 目录下运行
cd d:\repo\data-insight\ml01
uv run python main.py
```

### 参数说明

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `html_file` | str | ✅ | 要处理的 HTML 文件路径 |
| `instruction` | str | ❌ | 转换过程中的额外指令（默认为空） |

---

## 工作流程

工具执行以下步骤完成 HTML 改造：

1. **读取源文件**：使用 UTF8FileReader 工具读取 HTML 文件
2. **智能分析**：AI Agent 分析页面结构，识别所有静态数据
3. **数据提取**：将数字、文本、图表配置等提取到 JSON 结构
4. **HTML 改造**：替换静态内容为空白占位符，保留样式结构
5. **脚本生成**：编写 DOMContentLoaded 渲染脚本
6. **文件保存**：使用 UTF8FileWriter 工具保存为 `index.html`

---

## 输出结果

生成的 `index.html` 包含：

### 1. JSON 数据块

```html
<script type="application/json" id="jsonData">
{
  "reportTitle": "用户原声反馈分析报告",
  "totalDemand": 153,
  "statusInsight": "近一周需求响应速度有所提升",
  ...
}
</script>
```

### 2. 空白占位符 HTML

```html
<!-- 所有静态内容已替换为空白占位符 -->
<span id="reportTitle"></span>
<span id="totalDemand"></span>
<tbody id="submitterTable"></tbody>
```

### 3. 自动渲染脚本

```javascript
document.addEventListener('DOMContentLoaded', function() {
  const jsonData = JSON.parse(document.getElementById('jsonData').textContent);
  
  // 填充所有数据
  document.getElementById('reportTitle').textContent = jsonData.reportTitle;
  document.getElementById('totalDemand').textContent = jsonData.totalDemand;
  
  // 初始化图表
  echarts.init(document.getElementById('statusChart')).setOption({
    series: [{ type: 'pie', data: jsonData.charts.status }]
  });
});
```

---

## 自定义工具

### UTF8FileReaderTool

以 UTF-8 编码读取文件内容，解决中文编码问题。

```python
class UTF8FileReaderTool(BaseTool):
    name: str = "UTF8FileReader"
    description: str = "以 UTF-8 编码读取文件内容"
    
    def _run(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
```

### UTF8FileWriterTool

以 UTF-8 编码写入文件，自动创建父目录。

```python
class UTF8FileWriterTool(BaseTool):
    name: str = "UTF8FileWriter"
    description: str = "以 UTF-8 编码写入文件"
    
    def _run(self, file_path: str, content: str) -> str:
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"✅ 已保存：{file_path}"
```

---

## Agent 配置

### HTML 转换专家

```python
agent = Agent(
    role='HTML转换专家',
    goal='将HTML页面改造为JSON数据驱动',
    backstory='你擅长HTML分析和数据提取',
    verbose=True,
    llm=llm,
    tools=[utf8_reader, utf8_writer]
)
```

---

## 示例场景

### 输入：静态 HTML 报告

```html
<h1>销售数据分析报告</h1>
<p>数据周期：2024-01-01 至 2024-12-31</p>
<div class="stat-card">
  <span class="number">153</span>
  <span class="label">总需求数</span>
</div>
```

### 输出：JSON 驱动页面

```html
<h1><span id="reportTitle"></span></h1>
<p>数据周期：<span id="dataPeriod"></span></p>
<div class="stat-card">
  <span class="number"><span id="totalDemand"></span></span>
  <span class="label">总需求数</span>
</div>

<script type="application/json" id="jsonData">
{
  "reportTitle": "销售数据分析报告",
  "dataPeriod": "2024-01-01 至 2024-12-31",
  "totalDemand": 153
}
</script>

<script>
document.addEventListener('DOMContentLoaded', function() {
  const jsonData = JSON.parse(document.getElementById('jsonData').textContent);
  document.getElementById('reportTitle').textContent = jsonData.reportTitle;
  document.getElementById('dataPeriod').textContent = jsonData.dataPeriod;
  document.getElementById('totalDemand').textContent = jsonData.totalDemand;
});
</script>
```

---

## 技术栈

- **CrewAI**：多智能体协作框架
- **阿里云通义千问**：LLM 模型（qwen-plus）
- **Pydantic**：数据校验和工具定义
- **ECharts**：图表渲染库（支持动态初始化）

---

## 注意事项

1. **API Key 配置**：必须设置 `QWEN_API_KEY` 环境变量
2. **文件编码**：所有文件读写使用 UTF-8 编码
3. **样式保持**：工具会完整保留原有 CSS 样式
4. **图表支持**：需要确保 ECharts 库已引入
5. **占位符规范**：HTML 中所有动态内容使用空白占位符或 `{{placeholder}}` 标记

---

## 扩展建议

### 支持更多数据源

可扩展支持数据库、CSV、JSON API 等数据源：

```python
# 示例：从数据库获取数据
config = AnalysisConfig(
    data_source_type="database",
    database_config=DatabaseConfig(...)
)
```

### 自定义渲染逻辑

可根据需求修改渲染脚本，支持：
- 条件渲染
- 数据过滤
- 动态样式调整
- 用户交互响应

---

## 许可证

MIT License

---

## 作者

Data-Insight Team

---

**🌟 如果这个工具对你有帮助，请给个 Star！**