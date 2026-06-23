# 智能数据分析 Agent - V3.2

本项目是一个面向结构化业务数据的智能数据分析 Agent 原型系统。用户可以上传 CSV 或 Excel 文件，并使用自然语言提出数据分析问题。系统会识别用户意图，选择对应的数据分析工具，执行 Pandas / SQL 确定性计算，生成 Matplotlib 图表，并调用 Claude API 基于真实计算结果生成业务解释。

项目核心思想是：

**确定性数据计算 + ReAct-style 工具调用 + 大模型业务解释**

系统不会让大模型直接编造数据结论，而是先由 Pandas / SQLite 完成可复核计算，再由 Claude 基于真实结果生成分析解释和建议。

---

## Online Demo

Streamlit 在线演示地址：

https://data-analysis-agent-swmpgzbvkvkj5eyqqbmhqr.streamlit.app/

---

## 核心能力

当前版本支持：

1. CSV / Excel 文件上传
2. 数据预览与字段类型识别
3. 缺失值分析
4. 数值字段描述性统计
5. 自然语言业务问题输入
6. ReAct-style Agent 工具路由
7. 分组聚合分析
8. Top N 排名分析
9. 时间趋势分析
10. 异常值检测
11. SQL 只读查询
12. 产品结构与销售贡献分析
13. 地区 × 渠道交叉分析
14. 客户效率分析
15. Matplotlib 图表展示
16. Claude API 基于真实结果生成业务解释
17. 工具调用日志与执行耗时展示
18. ConversationBufferMemory / fallback 多轮记忆
19. 意图识别评估脚本
20. 工具路由延迟测试脚本

---

## 技术栈

* Python
* Streamlit
* Pandas
* Matplotlib
* SQLite
* Anthropic Claude API
* LangChain-style tool routing
* ConversationBufferMemory / fallback memory
* python-dotenv
* openpyxl

---

## 项目结构

```text
data-analysis-agent/
├── app.py                         # Streamlit 前端入口
├── agent.py                       # Claude API 解释模块
├── tools.py                       # Pandas 数据分析工具
├── sql_tools.py                   # SQL 只读查询与安全校验
├── langchain_agent.py             # ReAct-style Agent 工具路由层
├── conversation_memory.py         # 多轮对话记忆 fallback 实现
├── eval_intent.py                 # 意图识别准确率评估
├── test_latency.py                # 工具路由延迟测试
├── test_langchain_agent.py        # Agent smoke test
├── test_memory.py                 # 多轮记忆测试
├── intent_eval_results.csv        # 意图识别评估结果
├── latency_test_results.csv       # 延迟测试结果
├── requirements.txt
├── README.md
├── PROJECT_EXPLANATION.md
├── .env.example
└── data/
    └── sample_sales.csv
```

---

## Agent 工作流程

用户输入自然语言问题后，系统执行以下流程：

1. 读取上传数据并识别字段类型
2. 识别用户问题的任务类型
3. 根据任务类型选择分析工具
4. 调用 Pandas 或 SQL 工具完成真实计算
5. 记录工具调用日志、输入字段、输出规模和执行耗时
6. 使用 Matplotlib 生成图表
7. 将真实计算结果传给 Claude API
8. 由 Claude 生成业务解释和建议
9. 将表格、图表、执行日志和解释展示在 Streamlit 页面中

---

## 已支持的业务分析场景

示例数据 `data/sample_sales.csv` 支持以下问题：

```text
分析产品结构和销售贡献。
分析地区和渠道的交叉表现。
分析不同产品的客户效率。
检测销售额是否存在异常值。
分析这个数据集有没有缺失值。
找出销售额最高的前3个产品。
按日期分析销售额趋势。
按地区汇总销售额。
```

---

## SQL 安全机制

项目提供 SQL 只读查询工具，上传数据会被临时注册为 SQLite 表 `sales_data`。

安全限制：

* 只允许 `SELECT` / `WITH` 查询
* 禁止 `INSERT`
* 禁止 `UPDATE`
* 禁止 `DELETE`
* 禁止 `DROP`
* 禁止 `ALTER`
* 禁止 `CREATE`
* 禁止其他破坏性 SQL 操作

---

## 意图识别评估

项目提供 `eval_intent.py`，用于评估 Agent 对自然语言问题的任务识别能力。

当前测试结果：

```text
Total cases: 34
Correct: 34
Accuracy: 100.00%
```

说明：该准确率基于项目自建的 34 条结构化数据分析问题测试集，用于评估当前 demo 数据场景下的任务识别与工具路由能力。

---

## 延迟测试

项目提供 `test_latency.py`，用于测试 Agent 工具路由与确定性 Pandas 分析流程的耗时。

当前测试结果：

```text
Total runs: 40
P95 latency: < 4 seconds
PASS: P95 tool-routing latency is within 4 seconds.
```

说明：该测试主要统计 Agent 工具路由与 Pandas / SQL 确定性计算耗时，不包含 Claude API 网络调用耗时。完整大模型解释耗时会受到网络状态和模型服务状态影响。

---

## 多轮记忆

项目提供 `conversation_memory.py`，实现轻量 fallback memory：

* 记录用户问题
* 记录 Agent 识别出的任务类型
* 记录调用工具
* 记录结果规模
* 记录执行耗时

如果运行环境安装了 LangChain memory 组件，系统可以使用 `ConversationBufferMemory`；否则使用 `SimpleConversationBufferMemory` 保证项目可运行。

---

## 本地运行方式

安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

配置环境变量：

```bash
cp .env.example .env
```

在 `.env` 中填写 Claude API Key：

```text
ANTHROPIC_API_KEY=your_api_key_here
```

启动应用：

```bash
python3 -m streamlit run app.py
```

---

## 测试命令

```bash
python3 -m py_compile app.py tools.py sql_tools.py langchain_agent.py conversation_memory.py eval_intent.py test_latency.py test_memory.py test_langchain_agent.py

python3 test_langchain_agent.py
python3 eval_intent.py
python3 test_latency.py
python3 test_memory.py
```

---

## 项目特点

本项目把数据分析流程拆成可控模块：

* Pandas / SQL 负责真实计算
* Matplotlib 负责可视化
* Agent 负责意图识别和工具路由
* Claude 负责业务解释
* Streamlit 负责交互展示

这样可以降低大模型幻觉风险，并提高数据分析结果的可复核性。

---

## 当前不足与后续改进

当前项目仍是面向面试和学习场景的原型系统，不是生产级数据分析平台。后续可继续优化：

1. 接入真实数据库和权限系统
2. 引入更完整的 LangChain AgentExecutor
3. 支持更复杂的多轮追问和上下文引用
4. 增加同比、环比、预测、Cohort、漏斗分析等业务工具
5. 增加更大规模的评估集
6. 增加用户登录、数据隔离和审计日志
7. 优化 Claude API 调用延迟与缓存机制



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
