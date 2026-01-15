# Alpha Predator (阿尔法捕获者) 📈

Alpha Predator 是一个基于 AI 和大语言模型（LLM）的智能股票分析与交易辅助系统。它结合了传统量化指标、技术面分析、资金流向监控以及大模型的深度推理能力，旨在为投资者提供【可执行、可验证、可复盘】的交易决策支持。

## ✨ 核心功能

### 1. 🎯 Alpha Predator 市场扫描
全市场/自选股扫描引擎，基于多维度信号捕获交易机会：
- **量价形态**：识别各类技术突破、底部反转形态。
- **资金流向**：监控主力资金、北向资金的异常流动。
- **情绪分析**：通过 LLM 生成市场情绪与策略摘要。
- **实时监控**：在交易时间内自动刷新数据，捕捉盘中机会。

### 2. 🔍 Deep Dive 个股深度诊疗
对包括持仓股在内的任意标的进行全面“体检”：
- **六维诊断模型**：覆盖行业地位、多因子评分、技术形态、资金面、事件驱动及情景推演。
- **结论前置**：一目了然的操作建议（买入/持有/卖出）、目标价区间及止损位。
- **数据增强**：集成历史价格统计、公司公告、解禁信息及行业对比数据。
- **AI 深度推理**：利用 LLM (GPT, Gemini, Qwen 等) 综合各类硬数据生成专业研报。

### 3. 💼 智能持仓管理
- **可视化持仓**：清晰展示持仓盈亏、市值分布及可用资金。
- **自动建议**：根据用户配置的风险偏好（激进/平衡/保守）和资金规模，自动计算建议补仓/减仓数量。
- **交易时间优化**：系统智能识别 A 股交易时间，仅在开盘期间刷新数据，极大节省资源。

### 4. ⚙️ 灵活配置
- **多数据源支持**：
  - **Tushare** (推荐)：需配置 Token，提供更详尽的基本面数据。
  - **AkShare** (默认)：开源免费数据源，无需账号即可使用。
- **多 LLM 支持**：兼容 OpenAI, Google Gemini, 阿里通义千问 (Qwen) 等主流模型。

---

## 🚀 快速开始

### 环境依赖
- Python 3.9+
- Node.js 16+
- Tushare Token (可选，推荐)
- LLM API Key (必须，如阿里云 DashScope, OpenAI 等)

### 1. 后端安装

```bash
# 克隆项目
git clone https://github.com/yourusername/alpha-predator.git
cd alpha-predator

# 创建并激活虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 前端安装

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install
```

### 3. 运行系统

**启动后端服务**：
```bash
# 在项目根目录下
uvicorn src.api.main:app --reload --port 8000
```

**启动前端界面**：
```bash
# 在 frontend 目录下
npm run dev
```

访问 `http://localhost:5173` 即可开始使用。

---

## 🧠 分析思路与架构

本系统采用 **"数据驱动 + AI 决策"** 的双层架构：

1.  **数据层 (Data Layer)**：
    *   利用 `AkShare` 和 `Tushare` 接口采集清洗硬数据（行情、财务、新闻、资金流）。
    *   `TechnicalIndicators` 模块计算 MACD, KDJ, RSI, MA 等技术指标。
    *   `SignalDetector` 模块识别特定的量价形态。

2.  **决策层 (Decision Layer)**：
    *   将清洗后的结构化数据注入 `PromptTemplate`。
    *   `Prompt Engineer` 设计的 `QUANT_ANALYST_ROLE` (量化分析师角色) 引导 LLM 进行推理。
    *   输出遵循 CoT (Chain of Thought) 思维链，确保结论逻辑严密。

---

## 📚 参考与致谢

本项目的数据服务核心逻辑参考并使用了以下优秀的开源项目：

- **[AkShare](https://github.com/akfamily/akshare)**: 主要是用于获取 A 股实时行情、历史数据及各类衍生数据。AkShare 是一个非常强大的开源财经数据接口库。

---

## 📄 License

MIT License
