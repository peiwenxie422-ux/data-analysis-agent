# 智能数据分析 Agent - V2.1

本项目是一个面向结构化业务数据的智能数据分析 Agent。用户可以上传 CSV 或 Excel 文件，并使用自然语言提出数据分析问题。系统会先读取数据、识别字段类型，再根据问题类型调用对应的数据分析工具，最后在 Streamlit 页面中展示真实计算结果、图表和 Claude 生成的业务解释。

## Online Demo

Streamlit 在线演示地址：

https://data-analysis-agent-swmpgzbvkvkj5eyqqbmhqr.streamlit.app/

## 核心设计思想

本项目采用“确定性计算 + 大模型解释”的架构：

- Pandas 负责真实的数据计算
- Matplotlib 负责图表展示
- Claude API 负责理解自然语言问题，并基于真实计算结果生成业务解释
- Streamlit 负责文件上传、交互界面和结果展示

这样可以避免大模型直接编造数据结论，使分析结果更加可控、可复核、可解释。

## 当前功能

当前版本支持以下功能：

1. CSV / Excel 文件上传
2. 数据预览
3. 字段类型识别
4. 缺失值分析
5. 数值字段描述性统计
6. 自然语言问题输入
7. 规则式意图识别
8. 分组聚合分析
9. Top N 分析
10. 时间趋势分析
11. 异常值检测
12. 图表展示
13. Claude API 基于真实结果生成业务解释

## 支持的问题示例

上传示例数据 `data/sample_sales.csv` 后，可以尝试以下问题：

1. 按地区统计销售额，并判断哪个地区表现最好。
2. 找出销售额最高的前 3 个产品。
3. 按日期分析销售额趋势。
4. 检测销售额是否存在异常值。
5. 分析这个数据集有没有缺失值。

## 技术栈

- Python
- Streamlit
- Pandas
- Matplotlib
- Anthropic Claude API
- python-dotenv
- openpyxl

## 项目结构

```text
data-analysis-agent/
├── app.py
├── agent.py
├── tools.py
├── requirements.txt
├── README.md
├── PROJECT_EXPLANATION.md
├── .env.example
├── .gitignore
├── data/
│   └── sample_sales.csv
└── tests/
