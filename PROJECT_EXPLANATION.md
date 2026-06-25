# 智能数据分析 Agent 开发与部署项目说明 - V3.3

## 1. 项目定位

本项目是一个面向结构化业务数据的智能数据分析 Agent 原型系统。用户可以上传 CSV 或 Excel 文件，并通过自然语言提出数据分析问题。系统会自动识别问题意图，选择对应的数据分析工具，完成数据提取、清洗、分析、图表展示和业务解释。

当前版本已经从早期 MVP 升级为 V3.3，补强了以下能力：

- ReAct-style Agent 工具路由层
- SQL 只读查询工具
- 工具调用日志和执行耗时展示
- ConversationBufferMemory / fallback 多轮记忆
- 意图识别评估脚本
- 工具路由延迟测试脚本
- Streamlit Cloud 部署支持

项目核心思想是：让 Pandas / SQLite 完成确定性计算，让 Claude API 基于真实结果生成业务解释，避免大模型直接编造数据结论。

---

## 2. 系统架构

### 2.1 Streamlit 交互层

文件：app.py

负责文件上传、数据预览、字段类型展示、缺失值分析、数值统计、自然语言问题输入、结果展示、图表展示、Agent 执行日志展示和 Claude 解释展示。

### 2.2 Agent 工具路由层

文件：langchain_agent.py

该模块实现了 ReAct-style 的工具路由逻辑，核心流程是：

Thought：判断用户想做什么分析  
Action：选择合适的数据分析工具  
Observation：获取工具返回的真实计算结果

当前注册的工具包括：

- product_mix_analysis
- channel_region_matrix
- customer_efficiency_analysis
- groupby_aggregate
- top_n
- trend_analysis
- missing_value_summary
- period_comparison_analysis
- trend_forecast_analysis
- outlier_detection
- readonly_sql_query

### 2.3 数据分析工具层

文件：tools.py

负责具体的数据分析计算，包括分组聚合、Top N、时间趋势、缺失值分析、IQR 异常值检测、产品销售贡献、地区渠道交叉表现和客户效率分析。

### 2.4 SQL 查询层

文件：sql_tools.py

系统会将上传的数据临时注册为 SQLite 表 sales_data，并支持只读 SQL 查询。安全限制包括只允许 SELECT / WITH，禁止 INSERT、UPDATE、DELETE、DROP、ALTER、CREATE 等危险操作。

### 2.5 Claude 业务解释层

文件：agent.py

Claude API 不直接计算数据，而是接收 Pandas / SQL 已经算好的结果，并生成核心发现、业务解释、风险提示和后续建议。

### 2.6 多轮记忆层

文件：conversation_memory.py

项目实现了 SimpleConversationBufferMemory，用于保存多轮分析上下文，包括用户问题、任务类型、调用工具、结果规模和执行耗时。如果环境支持 LangChain memory 组件，可扩展到 ConversationBufferMemory。

---

## 3. 支持的业务场景

当前版本支持 8+ 类业务分析场景：

- groupby：分组聚合分析
- top_n：Top N 排名分析
- trend：时间趋势分析
- missing：缺失值分析
- outlier：异常值检测
- product_mix：产品结构与销售贡献分析
- channel_region：地区 × 渠道交叉分析
- customer_efficiency：客户效率分析
- sql：SQL 只读查询

---

## 4. 工具调用日志

Streamlit 页面会展示 Agent 执行日志，包括：

- status
- task_type
- tool_description
- group_col
- value_col
- date_col
- result_shape
- elapsed_seconds
- pipeline

这使 Agent 的分析链路更加透明，便于调试和面试展示。

---

## 5. 评估与测试

### 5.1 Agent 工具路由测试

运行命令：

python3 test_langchain_agent.py

测试结果：

All langchain_agent tests passed.

### 5.2 意图识别准确率测试

运行命令：

python3 eval_intent.py

当前结果：

Total cases: 44  
Correct: 44  
Accuracy: 100.00%  
No failed cases.

说明：该结果基于项目自建的 44 条结构化数据分析问题测试集，主要评估当前 demo 数据场景下的任务识别和工具路由能力。

### 5.3 延迟测试

运行命令：

python3 test_latency.py

当前结果：

Total runs: 55  
P95 latency: < 4 seconds  
PASS: P95 tool-routing latency is within 4 seconds.

说明：该测试统计的是 Agent 工具路由与 Pandas / SQL 确定性计算耗时，不包含 Claude API 网络调用耗时。完整大模型解释时间会受网络状态和模型服务状态影响。

### 5.4 多轮记忆测试

运行命令：

python3 test_memory.py

测试结果：

Memory test passed.

---

## 6. 和简历描述的对应关系

| 简历描述 | 项目对应实现 |
|---|---|
| Python / LangChain / Claude API / Streamlit | Python、Streamlit、Claude API、ReAct-style Agent 层 |
| LangChain ReAct 框架 | langchain_agent.py 中实现 ReAct-style Thought-Action-Observation 工具路由 |
| Python 代码执行器 | 当前以 Pandas 工具函数形式执行确定性数据分析逻辑 |
| SQL 查询模块 | sql_tools.py，支持 SQLite 只读查询 |
| Matplotlib 可视化工具链 | app.py 中使用 Matplotlib 生成图表 |
| Claude API | agent.py 中调用 Claude 基于真实计算结果生成解释 |
| ConversationBufferMemory | conversation_memory.py fallback memory，支持 LangChain memory 兼容设计 |
| 8+ 类业务场景 | groupby、top_n、trend、missing、outlier、product_mix、channel_region、customer_efficiency、sql |
| 意图识别准确率 | eval_intent.py，34 条测试样本，当前准确率 100% |
| Streamlit Cloud 部署 | 项目支持 Streamlit Cloud 在线部署 |
| 响应时延控制 | test_latency.py，工具路由与确定性分析 P95 < 4 秒 |

---

## 7. 面试讲解版本

这个项目是一个面向结构化业务数据的智能数据分析 Agent。用户上传 CSV 或 Excel 后，可以用自然语言提出问题，系统会先识别任务类型，例如产品结构分析、地区渠道交叉分析、客户效率分析、异常值检测、缺失值分析、Top N 和趋势分析。

底层计算不是直接让大模型生成，而是由 Pandas 和 SQLite 只读 SQL 工具完成确定性计算，再用 Matplotlib 生成图表。Claude API 主要负责基于真实计算结果生成业务解释和建议。

为了让 Agent 的执行过程更可解释，我加入了工具调用日志，展示任务类型、调用工具、输入字段、输出规模和执行耗时。同时我还补了意图识别评估脚本、延迟测试脚本和多轮记忆模块，用来验证项目不是只停留在 demo 层面。

当前版本仍然是原型系统，不是生产级 BI 平台，但已经打通了结构化数据分析 Agent 的核心流程。

---

## 8. 当前不足

当前项目已经具备完整 demo 和面试展示能力，但仍有改进空间：

1. ReAct 工具路由目前是轻量实现，不是完整生产级 AgentExecutor。
2. Python 代码执行器目前以预设 Pandas 工具函数为主，没有开放任意代码执行。
3. 意图识别评估集规模仍较小，后续可扩展到更多真实业务问题。
4. Claude API 响应耗时受网络和模型服务状态影响。
5. 当前没有用户登录、权限分层和数据隔离机制。
6. 当前只支持上传文件，没有接入企业级数仓或 BI 系统。
7. 当前多轮记忆主要保存执行摘要，还没有实现复杂上下文推理。


---

## 当前边界与面试表述建议

本项目可以表述为“基于 LangChain/ReAct 思想的轻量多工具数据分析 Agent 原型”。更严谨地说，当前主流程是 ReAct-style 工具路由，不是完整生产级 LangChain AgentExecutor。

项目中的 Python 执行能力不是开放任意代码执行，而是封装好的受控 Pandas 分析工具函数，包括聚合、Top N、趋势、同比/环比、简单预测、异常检测等。这样能避免任意代码执行风险，也便于测试和部署。

SQL 模块使用 SQLite 内存表，并通过只读校验限制为 SELECT / WITH 查询，避免写入、删除和结构修改操作。

评估口径建议说明为：当前自建意图识别评估集覆盖 44 条结构化数据分析问题，当前测试准确率 100%；工具路由与确定性分析流程 P95 小于 4 秒。该延迟不包含 Claude API 网络调用耗时。

## Phase 2 面试补强说明

本阶段在不破坏既有 V3.3 功能的基础上，补齐了简历中更容易被追问的三类能力：

1. 安全 Python / Pandas 执行能力：通过 `python_sandbox.py` 提供受控代码执行器，使用 AST 白名单校验，不开放任意系统命令、文件读写、导入、`eval` 或 `exec`。
2. 显式多步分析链路：通过 `analysis_pipeline.py` 记录数据画像、工具规划、工具执行、图表规划、解释准备等步骤，更贴近“自主规划分析链路”的简历表述。
3. 可选 LangChain AgentExecutor：通过 `langchain_executor_agent.py` 提供真正 `AgentExecutor` 后端构建入口。默认线上主流程仍保留轻量 ReAct-style 路由，以保证 Streamlit Cloud 稳定性和低延迟。

面试中建议这样表达：项目主流程是稳定的 ReAct-style 多工具路由；同时提供可选 LangChain AgentExecutor 后端用于展示框架兼容性。Python 执行能力是受控 Pandas sandbox，不是开放任意 Python exec。

## V3.3 面试补充说明

V3.3 不是重写系统，而是在现有 V3.2 面试抗压版基础上做稳定性增强。当前项目仍应谨慎表述为“基于 Streamlit、Pandas、SQLite、Claude API 的结构化数据分析 Agent 原型系统”。

本阶段新增的稳定性能力包括：

- 对上传数据展示行数、列数、总单元格数和内存占用，便于解释大文件处理边界。
- 对大文件预览做固定抽样，降低页面渲染压力，但确定性分析仍基于完整数据。
- 对 SQL、安全 Python sandbox、字段缺失、参数错误等异常进行用户友好提示。
- 更新 Streamlit 表格展示参数，减少未来版本兼容风险。

面试中可以强调：该系统不是开放任意 Python 执行器，而是受控 Pandas 工具函数和 AST 校验 sandbox；也不是企业级 BI 平台，而是一个可解释、可评估、可部署的数据分析 Agent 原型。
