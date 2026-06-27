# Smart Data Analysis Agent

A Streamlit-based AI data analysis Agent prototype with tool-based reasoning, SQL-safe querying, guardrails, memory, evaluation, and latency testing.

## Online Demo

https://data-analysis-agent-swmpgzbvkvkj5eyqqbmhqr.streamlit.app/

## Project Overview

This project demonstrates how an AI assistant can help users explore structured CSV / Excel data by combining deterministic data analysis tools with LLM-assisted business explanation.

Instead of sending all data directly to an LLM, the system separates data computation, tool routing, SQL-style querying, guardrails, memory, and natural-language explanation into different modules.

## Core Highlights

- Streamlit web interface for interactive dataset upload and analysis
- Pandas / SQLite deterministic computation for structured data analysis
- ReAct-style Agent routing for tool selection and orchestration
- SQL read-only safety mechanism for controlled query execution
- Matplotlib chart generation for visual analysis
- Conversation memory for simple multi-turn context
- Data guardrails and sandboxing attempts for safer execution
- Intent evaluation and latency testing for measurable demo quality
- Unit tests covering key project modules

## Architecture

```text
User question / uploaded dataset
↓
Streamlit UI
↓
Intent recognition / Agent router
↓
Pandas tools / SQL tools / analysis pipeline
↓
Guardrails / memory / error handling
↓
LLM-assisted business explanation
↓
User-facing result
```

## Evaluation Results

### Intent Recognition Evaluation

The project includes `eval_intent.py` for evaluating task recognition and tool-routing behavior.

```text
Total cases: 44
Correct: 44
Accuracy: 100.00%
```

This result is based on the project-specific demo evaluation set, not a general benchmark.

### Latency Test

The project includes latency testing for tool routing and deterministic Pandas / SQLite analysis.

```text
Total runs: 55
P95 latency: < 4 seconds
PASS: P95 tool-routing latency is within 4 seconds.
```

The latency result focuses on tool routing and deterministic analysis, excluding external LLM network latency.

## Project Structure

```text
app.py                         Streamlit frontend
agent.py                       LLM-assisted explanation layer
tools.py                       Pandas analysis tools
sql_tools.py                   SQL-style query and safety logic
langchain_agent.py             Agent-style routing logic
langchain_executor_agent.py    Tool execution workflow
analysis_pipeline.py           Reusable analysis pipeline
conversation_memory.py         Simple conversation memory
data_guardrails.py             Data validation and guardrails
python_sandbox.py              Controlled Python execution attempt
eval_intent.py                 Intent evaluation script
test_*.py                      Unit tests
data/sample_sales.csv          Sample dataset
```

## Local Setup

```bash
git clone https://github.com/peiwenxie422-ux/data-analysis-agent.git
cd data-analysis-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Safety Notes

- API keys should be stored in environment variables, not hardcoded in source files
- Use sample or public datasets for demonstration
- LLM outputs should be treated as assisted explanations and reviewed by humans
- Sandbox and guardrail modules are prototype-level safety components, not production-grade security guarantees

## Limitations

- This is a portfolio prototype, not a production enterprise analytics platform
- It should not be used with confidential customer data without further security review
- The evaluation set is project-specific and should not be interpreted as a general benchmark
- Production use would require authentication, monitoring, stronger sandboxing, logging, cost control, and deployment hardening
