# data-insight

> 🤖 基于 CrewAI 的智能数据分析与报告生成系统 - 支持 Excel 与数据库双数据源 + 自定义 SQL

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![CrewAI](https://img.shields.io/badge/crewai-0.30+-green.svg)](https://github.com/joaomdmoura/crewai)
[![Pydantic](https://img.shields.io/badge/pydantic-2.0+-red.svg)](https://github.com/pydantic/pydantic)
[![PostgreSQL](https://img.shields.io/badge/postgresql-16+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Data-Insight 利用 CrewAI 多智能体协作框架，自动将海量数据（支持 Excel 文件或 PostgreSQL 数据库）转化为智能化的 HTML 数据报告。系统通过 AI 驱动的头脑风暴发现数据洞察，自动生成统计分析脚本，最终产出美观的可视化报告。

**🌟 核心亮点：支持自定义 SQL 查询，让数据分析师和开发者可以灵活控制数据抽取逻辑！**

---

## 📋 目录

- [✨ 核心特性](#-核心特性)
- [🏗 系统架构](#-系统架构)
- [🚀 快速开始](#-快速开始)
- [📖 使用指南](#-使用指南)
  - [Excel 数据源](#excel-数据源)
  - [PostgreSQL 数据源 - 表模式](#postgresql-数据源---表模式)
  - [PostgreSQL 数据源 - 自定义 SQL 模式](#postgresql-数据源---自定义-sql-模式)
  - [高级 SQL 使用场景](#高级-sql-使用场景)

---

## ✨ 核心特性

### 主要功能

| 功能 | 说明 |
|------|------|
| **📁 双数据源支持** | 无缝支持 Excel 文件（.xlsx/.xls）和 PostgreSQL 数据库 |
| **✍️ 自定义 SQL 查询** | 支持用户完全自定义 SQL 语句，灵活控制数据抽取逻辑 |
| **🧠 AI 智能头脑风暴** | 利用大语言模型自动识别分析维度和关键洞察方向 |
| **📊 智能采样机制** | 可配置的智能数据采样，支持随机种子实现可重现分析 |
| **📈 全量数据统计** | 自动生成并执行 Python 脚本，突破上下文窗口限制处理海量数据 |
| **📄 交互式 HTML 报告** | 生成包含图表和洞察的独立 HTML 报告文件 |
| **🤖 多智能体协作** | 基于 CrewAI 框架，不同阶段由专业智能体分工协作 |
| **🔄 端到端自动化** | 从原始数据到最终报告，全流程自动化处理 |
| **💾 数据缓存机制** | 支持缓存加速重复分析，避免重复数据库查询 |
| **🔍 SQL 智能校验** | 自动校验 SQL 语法安全性，防止危险操作 |


## 任务分工

---

| 模块 | 交付物 | 负责角色 | 目录 | 工作内容描述 |
|------|--------|----------|------|--------------|
| **模块一：需求原子化** | HTML Demo版本 + PRD产品方案 | 产品经理 | `m00/` | 将产品需求拆解为可独立开发、测试的原子化任务单元，输出交互Demo与PRD文档，作为后续开发的设计蓝本，并编写对应的“任务委托书”明确各任务边界。 |
| **模块二：接口契约锁定** | HTML模板 + JSON格式标注（JSON数据驱动格式） | 产品经理 | `m01/` | 将HTML Demo转换为数据驱动的JSON格式输出，通过HTML模板与JSON Schema标注，提前锁定前后端接口契约（字段、类型、必填/可选关系），实现接口定义与实现分离。 |
| **模块三：TDD循环生成** | 生产级标准JSON数据文件 + Python生成脚本 | 开发 | `m02/` | 以JSON契约、PRD和HTML模板为输入，采用测试驱动开发（TDD）模式：先编写测试用例，再实现Python脚本，最终通过测试验证并输出符合生产标准的JSON数据文件。 |
| **模块四：批判性验证** | JSON数据质量验证报告 | 业务 | `m03/` | 对模块三输出的JSON数据进行四层防御验证：①静态检查（格式/结构校验）②动态测试（业务逻辑测试）③人工审查（业务方抽样确认），确保数据准确性、完整性和一致性。 |
| **模块五：所有权确认** | README说明文档 | 业务 | `m04/` | 完成数据文档的知识沉淀工作，输出README文档，内容涵盖：橡皮鸭解释（逻辑自述）、Git提交署名记录、ADR架构决策记录，明确责任归属与设计决策依据。 |

---
## 快速开始
```bash
# 克隆项目仓库
git clone https://gitee.com/edgeright/data-insight.git
cd data-insight 


# 设置环境变量
export QWEN_API_KEY="your-qwen-api-key-here"
export BAIDU_API_KEY="your-baidu-api-key-here"

# PostgreSQL数据库
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_USER="postgres"
export POSTGRES_PASSWORD="your-password"
export POSTGRES_DATABASE="your-database"
```