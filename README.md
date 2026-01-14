# QuantumAlpha: AI 原生量化投研决策系统

机构级精度的跨平台桌面端智能投研工作台，通过大语言模型（LLM）与传统量化因子模型的深度融合，实现"黑盒化"阿尔法挖掘与"白盒化"深度归因分析。

## 功能特性

- **Alpha Predator（全市场阿尔法捕获）**：每日早盘定时推送与实时策略扫描
- **Deep Dive Diagnostic（个股深度诊疗）**：交互式多维度股票分析
- **多 LLM 支持**：支持 OpenAI、Google Gemini、自定义 LLM
- **双阶段时效优化**：预处理 + 增量更新，确保 9:30 前完成分析
- **容灾降级方案**：API 超时自动切换规则引擎

## 快速开始

### 1. 安装依赖

```bash
# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
pip install -e .
```

### 2. 配置 API

复制 `.env.example` 为 `.env` 并填入您的 API 密钥：

```bash
cp .env.example .env
```

### 3. 运行系统

```bash
# 启动后端服务
python -m src.main

# 或使用 uvicorn
uvicorn src.api.main:app --reload
```

## 项目结构

```
src/
├── data/           # 数据层：数据源接入
├── analysis/       # 分析模块：技术指标、多因子
├── ai/             # AI 模块：LLM、NLP、RAG
├── notification/   # 通知服务：Webhook、Email
├── core/           # 核心业务逻辑
└── api/            # API 服务
```

## 技术栈

- **后端**：Python 3.11+, FastAPI, Pydantic
- **数据源**：Tushare, AkShare
- **LLM**：OpenAI API, Google Generative AI
- **技术分析**：TA-Lib / ta
- **桌面端**：Tauri (Rust + Web)

## License

MIT
