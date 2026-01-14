"""Prompt 模板管理

包含量化分析师角色设定和各类分析任务的 Prompt 模板。
基于 Chain-of-Thought (CoT) 和 Role-Playing 技术。
"""

from dataclasses import dataclass
from string import Template
from typing import Optional


# ==================== 系统角色定义 ====================

QUANT_ANALYST_ROLE = """你是一名为顶级对冲基金工作的资深量化研究员，擅长结合宏观流动性与微观技术形态进行多维度分析，负责生成【可执行、可验证、可复盘】的交易前研究结论。


【核心分析原则】
1. 结论优先级：消息面（政策/业绩/突发事件）> 资金流向 > 技术形态 > 宏观流动性。重大消息可一票否决其他信号
2. 当不同信号出现冲突时，必须明确指出冲突来源，并说明最终采用哪一类信号及原因
3. 禁止在数据缺失的情况下进行主观补全或常识推断，数据不足必须明确标注为“无法判断”

【分析与表达约束】
- 所有判断必须明确标注为：利多 / 中性 / 利空
- 每一个结论需至少对应一条可验证的数据或事实
- 不允许使用模糊表述（如“可能”“或许”“偏向”），除非用于风险情景推演
- 技术指标必须说明时间周期（如日线/周线）

【输出规范】
- 使用 Markdown 格式输出，结构清晰
- 关键数据必须以表格形式呈现
- 策略建议必须具备可交易性（方向、仓位、风控）
- 风险提示需区分：系统性风险 / 标的特异风险

【失败处理】
- 若核心数据不足以支持结论，必须输出【数据不足，策略观望】并说明缺失项
"""


# ==================== 分析任务 Prompt 模板 ====================

@dataclass
class PromptTemplate:
    """Prompt 模板"""
    name: str
    system_prompt: str
    user_template: Template
    description: str


# 早盘策略分析模板
ALPHA_PREDATOR_TEMPLATE = PromptTemplate(
    name="alpha_predator",
    description="全市场阿尔法捕获 - 早盘策略分析",
    system_prompt=QUANT_ANALYST_ROLE,
    user_template=Template("""# 今日市场分析任务

## 日期
$trade_date

## 市场数据输入

### 1. 宏观与资金面
$macro_data

### 2. 指数表现
$index_data

### 3. 北向资金
$northbound_data

### 4. 集合竞价特征 (9:15-9:25)
$auction_data

### 5. 当日重大新闻/事件
$news_data

## 分析要求

请基于以上数据，完成以下分析并生成研报：

1. **核心综述**：市场运行特征概览，日内阿尔法驱动力分析
2. **宏观量化环境**：流动性水位评估，货币政策解读，是否构成【方向性约束】
3. **资金面分析**：北向资金流向、行业偏好，是否形成【可交易信号】
4. **技术面分析**：指数 MACD/KDJ 状态，关键支撑阻力位，是否【确认或否定】资金判断
5. 若信号冲突，明确说明冲突并给出裁决
6. **策略建议**：
   - 组合配置权重建议
   - 重点关注板块/个股
   - 风控阈值设定
7. **风险提示**：当日需警惕的风险因素

## 强制输出要求（必须严格遵守）
在报告最前部，必须输出【今日交易结论摘要】：

### 今日结论卡片
| 项目 | 结论 |
|----|----|
| 市场方向 | 明确看多 / 中性 / 看空 |
| 核心驱动因素 | 不超过3条 |
| 主要做多方向 | 板块 / 指数 / 资产 |
| 明确回避方向 | 板块 / 风格 |
| 建议总仓位 | 0%–100% |
| 关键风险触发条件 | 明确数值或事件 |

---



输出格式参考附录中的研报样例风格。"""),
)


# 增量更新模板（集合竞价后快速修正）
INCREMENTAL_UPDATE_TEMPLATE = PromptTemplate(
    name="incremental_update",
    description="集合竞价后增量更新",
    system_prompt=QUANT_ANALYST_ROLE,
    user_template=Template("""# 集合竞价增量更新

## 预处理报告摘要
$pre_report_summary

## 集合竞价实时数据 (9:25-9:30)
$auction_realtime

### 关键变化
- 今日开盘价: $open_price
- 竞价量能: $auction_volume
- 量比: $volume_ratio
- 高开低开幅度: $gap_pct

## 更新要求

仅针对【最终策略建议】部分进行快速修正：
1. 基于最新竞价数据，调整今日策略方向
2. 更新重点关注标的
3. 调整风控参数

【更新约束】
- 不允许推翻原有市场方向判断，除非出现以下任一情况：
  1. 高开/低开幅度超过 ±2%
  2. 集合竞价量能较前一交易日显著异常（≥150%）
- 所有调整必须明确指出【由哪一项竞价指标触发】
- 若竞价数据不足以改变原结论，明确说明“维持原策略”


保持简洁。"""),
)


# 个股深度诊疗模板
DEEP_DIVE_TEMPLATE = PromptTemplate(
    name="deep_dive",
    description="个股深度诊疗分析",
    system_prompt=QUANT_ANALYST_ROLE,
    user_template=Template("""# 个股深度诊疗

## 标的信息
- 股票代码: $ts_code
- 股票名称: $stock_name
- 所属行业: $industry

## 基本面数据
$fundamental_data

## 技术面数据
$technical_data

## 资金面数据
$capital_data

## 近期事件
$events_data

## 分析要求

请对该股票进行全面"体检"，输出以下内容：

### 1. 行业地位分析
- Alpha/Beta 分离度评估
- 相对行业强弱

### 2. 多因子评分
| 因子类型 | 评分(1-10) | 说明 |
|---------|-----------|------|
| 价值因子 | | |
| 成长因子 | | |
| 动量因子 | | |
| 质量因子 | | |

### 2.1【多因子评分规则】
- 评分基于同行业横向比较（至少5只可比标的）
- 评分需说明：处于行业前20% / 中位 / 后20%


### 3. 技术形态诊断
- 当前所处阶段（筑底/上升/横盘/下跌）
- 关键支撑位与阻力位
- MACD/KDJ 信号状态

### 4. 事件驱动监控
- 近期解禁情况
- 股东增减持动态
- 重组/定增进展

### 5. 综合评级
- **评级**: Buy / Hold / Sell
- **目标价区间**: 
- **持仓建议周期**: 

### 5.1【综合评级约束】
- Buy：需至少满足“资金面 + 技术面”双重确认
- Hold：信号冲突或趋势不明
- Sell：趋势明确向下或重大负面事件

### 6. 情景推演
| 情景 | 触发条件 | 目标位 | 概率 |
|-----|---------|-------|------|
| 上涨情景 | | | |
| 中性情景 | | | |
| 下跌情景 | | | |

### 7. 风险提示
明确列出该股票的主要风险因素。"""),
)


# 规则引擎降级输出模板（当 LLM 超时时使用）
FALLBACK_TEMPLATE = """# 竞价异动快报 (规则引擎模式)

> ⚠️ 注意：本报告由规则引擎自动生成，未经 AI 润色

## 生成时间
{timestamp}

## 高开异动榜 (高开 > 3% 且 量比 > 5)
{high_open_list}

## 板块资金净流入 TOP5
{sector_inflow_top5}

## 北向资金动态
{northbound_summary}

---
*本报告基于硬编码规则生成，仅供参考。详细分析请等待 AI 报告。*
"""


# 板块分析模板 - 输出结构化 JSON
SECTOR_ANALYSIS_TEMPLATE = PromptTemplate(
    name="sector_analysis",
    description="热门板块分析 - 输出结构化数据",
    system_prompt=QUANT_ANALYST_ROLE,
    user_template=Template("""# 今日板块分析任务

## 日期
$trade_date

## 市场数据

### 板块资金流向
$sector_flow_data

### 大盘指数
$index_data

### 北向资金
$north_flow_data

## 分析要求

请分析当前市场热门板块，找出最值得关注的板块。

【输出格式要求】
你必须严格按照以下 JSON 格式输出，不要输出任何其他内容：

```json
{
  "market_summary": "今日市场整体点评（不超过100字）",
  "market_direction": "看多/中性/看空",
  "sectors": [
    {
      "name": "板块名称",
      "change_pct": 2.35,
      "money_flow": 12.5,
      "hot_level": "高/中/低",
      "signal": "利多/中性/利空",
      "reason": "推荐理由（不超过50字）"
    }
  ],
  "risk_warning": "风险提示"
}
```

【约束】
- sectors 数组按推荐优先级排序，最多返回 8 个板块
- money_flow 单位为亿元，正数表示净流入，负数表示净流出
- 必须给出明确的 signal 判断，禁止模糊表述
"""),
)


# 股票推荐模板 - 输出结构化 JSON
STOCK_RECOMMENDATION_TEMPLATE = PromptTemplate(
    name="stock_recommendation",
    description="个股推荐 - 输出结构化数据",
    system_prompt=QUANT_ANALYST_ROLE,
    user_template=Template("""# 个股推荐任务

## 日期
$trade_date

## 用户选择的板块
$selected_sectors

## 板块内股票数据

### 实时行情
$stock_quotes

### 资金流向
$stock_money_flow

### 技术指标
$stock_technicals

## 推荐要求

请在用户选择的板块中，推荐最值得买入的股票。

【输出格式要求】
你必须严格按照以下 JSON 格式输出，不要输出任何其他内容：

```json
{
  "analysis_summary": "整体分析点评（不超过100字）",
  "recommendations": [
    {
      "rank": 1,
      "ts_code": "000001.SZ",
      "name": "股票名称",
      "sector": "所属板块",
      "signal": "买入",
      "score": 85,
      "current_price": 12.50,
      "buy_price": 12.00,
      "sell_price": 15.00,
      "stop_loss_price": 11.00,
      "position_strategy": {
        "initial_pct": 30,
        "add_condition": "回调至12.0附近加仓20%",
        "max_pct": 50
      },
      "hold_period": "5-10个交易日",
      "entry_timing": "建议回调至支撑位12.0附近分批建仓",
      "reasons": [
        "消息面：公司发布利好公告...",
        "资金面：主力净流入 2.3 亿",
        "技术面：MACD 日线金叉，均线多头排列"
      ],
      "risk_factors": [
        "大盘系统性回调风险",
        "板块轮动风险"
      ]
    }
  ],
  "risk_warning": "投资有风险，以上建议仅供参考，不构成投资建议"
}
```

【字段说明】
- buy_price: 建议买入价位（预计在此价位附近买入较为合适）
- sell_price: 目标卖出价位（预期股价可能到达的位置）
- stop_loss_price: 止损价位（跌破此价位建议止损）
- position_strategy: 仓位策略
  - initial_pct: 初始底仓比例（0-100）
  - add_condition: 加仓条件和比例说明
  - max_pct: 最大仓位占比

【约束】
- recommendations 数组按推荐优先级排序，最多返回 5 只股票
- score 评分范围 0-100，代表综合推荐强度
- 仓位策略必须根据个股走势特点制定，不能所有股票相同
- signal 只能为：买入 / 观望 / 回避
- reasons 至少包含 2 条可验证的理由，消息面理由优先展示
- 若数据不足无法给出推荐，返回空的 recommendations 数组并在 analysis_summary 中说明原因
"""),
)


def get_prompt_template(name: str) -> Optional[PromptTemplate]:
    """获取 Prompt 模板
    
    Args:
        name: 模板名称
        
    Returns:
        模板对象，未找到返回 None
    """
    templates = {
        "alpha_predator": ALPHA_PREDATOR_TEMPLATE,
        "incremental_update": INCREMENTAL_UPDATE_TEMPLATE,
        "deep_dive": DEEP_DIVE_TEMPLATE,
        "sector_analysis": SECTOR_ANALYSIS_TEMPLATE,
        "stock_recommendation": STOCK_RECOMMENDATION_TEMPLATE,
    }
    return templates.get(name)


def render_prompt(template: PromptTemplate, **kwargs) -> str:
    """渲染 Prompt
    
    Args:
        template: 模板对象
        **kwargs: 模板变量
        
    Returns:
        渲染后的 Prompt 字符串
    """
    return template.user_template.safe_substitute(**kwargs)
