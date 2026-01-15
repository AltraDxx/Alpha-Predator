"""QuantumAlpha API 服务

提供 RESTful API 接口，支持：
- 全市场策略分析 (Alpha Predator)
- 个股深度诊疗 (Deep Dive)
- LLM 配置管理
- 系统状态查询
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel, Field

from src.config import LLMProvider, get_settings
from src.core.alpha_predator import AlphaPredator
from src.core.deep_dive import DeepDiveDiagnostic


# ==================== 请求/响应模型 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    timestamp: str
    version: str


class AnalysisRequest(BaseModel):
    """分析请求"""
    trade_date: Optional[str] = Field(None, description="交易日期 (YYYYMMDD)")
    send_notification: bool = Field(False, description="是否发送通知")


class DiagnoseRequest(BaseModel):
    """诊疗请求"""
    ts_code: str = Field(..., description="股票代码 (如 000001.SZ)")


class LLMSwitchRequest(BaseModel):
    """LLM 切换请求"""
    provider: str = Field(..., description="LLM 提供商: openai, google, custom")


class ReportResponse(BaseModel):
    """报告响应"""
    success: bool
    title: str
    content: str
    trade_date: str
    generated_at: str
    stage: str = "full"
    is_fallback: bool = False


class QuickScanResponse(BaseModel):
    """快速扫描响应"""
    ts_code: str
    name: str
    industry: str
    signal: Optional[dict] = None
    technical: Optional[dict] = None


# ==================== 应用生命周期 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("QuantumAlpha API 启动中...")
    
    # 预加载组件
    app.state.alpha_predator = AlphaPredator()
    app.state.deep_dive = DeepDiveDiagnostic()
    
    logger.info("QuantumAlpha API 启动完成")
    yield
    
    logger.info("QuantumAlpha API 关闭")


# ==================== FastAPI 应用 ====================

app = FastAPI(
    title="QuantumAlpha API",
    description="AI 原生量化投研决策系统 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== API 路由 ====================

@app.get("/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now().isoformat(),
        version="0.1.0",
    )


@app.get("/api/config", tags=["系统"])
async def get_config():
    """获取当前配置"""
    settings = get_settings()
    return {
        "default_llm_provider": settings.default_llm_provider.value,
        "fallback_cutoff_time": settings.fallback_cutoff_time,
        "log_level": settings.log_level,
    }


def normalize_stock_code(code: str) -> str:
    """标准化股票代码
    
    输入数字代码，自动补全交易所后缀
    - 6开头 → .SH（上海）
    - 0/3开头 → .SZ（深圳）
    """
    code = code.strip().upper()
    
    # 已经是完整格式
    if "." in code:
        return code
    
    # 只有数字，补全后缀
    if code.isdigit() and len(code) == 6:
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith(("0", "3")):
            return f"{code}.SZ"
        elif code.startswith("8") or code.startswith("4"):
            return f"{code}.BJ"  # 北交所
    
    return code


@app.get("/api/stock/info", tags=["行情"])
async def get_stock_info(code: str = Query(..., description="股票代码，如 000001 或 000001.SZ")):
    """获取股票基本信息
    
    根据代码查询股票名称、行业等信息。
    支持只输入数字代码，自动识别交易所。
    """
    from src.data.sources.factory import get_data_source
    
    try:
        ts_code = normalize_stock_code(code)
        data_source = get_data_source()
        
        # 获取实时行情（包含名称）
        quote = data_source.get_realtime_quote(ts_code)
        
        if quote:
            return {
                "success": True,
                "data": {
                    "ts_code": ts_code,
                    "name": quote.get("name", ""),
                    "price": quote.get("price", 0),
                    "change_pct": quote.get("change", 0),
                    "industry": quote.get("industry", ""),
                },
            }
        
        # 如果实时行情没有，尝试从股票列表查找
        stock_list = data_source.get_stock_list()
        if not stock_list.empty:
            stock_code = ts_code.split(".")[0]
            matched = stock_list[stock_list["代码"] == stock_code]
            if not matched.empty:
                row = matched.iloc[0]
                return {
                    "success": True,
                    "data": {
                        "ts_code": ts_code,
                        "name": row.get("名称", ""),
                        "price": row.get("最新价", 0),
                        "change_pct": row.get("涨跌幅", 0),
                        "industry": "",
                    },
                }
        
        return {
            "success": False,
            "error": f"未找到股票: {code}",
        }
        
    except Exception as e:
        logger.error(f"查询股票信息失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/api/stock/quote", tags=["行情"])
async def get_stock_quote(ts_code: str = Query(..., description="股票代码")):
    """获取个股实时行情"""
    from src.data.sources.factory import get_data_source
    
    try:
        full_code = normalize_stock_code(ts_code)
        data_source = get_data_source()
        quote = data_source.get_realtime_quote(full_code)
        
        if quote:
            return {
                "success": True,
                "data": quote,
            }
        
        return {
            "success": False,
            "error": f"未获取到行情: {ts_code}",
        }
        
    except Exception as e:
        logger.error(f"查询行情失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.get("/api/market/realtime", tags=["行情"])
async def get_realtime_market():
    """获取实时市场行情
    
    返回主要指数的实时数据
    """
    from src.data.sources.factory import get_data_source
    
    try:
        data_source = get_data_source()
        
        # 获取指数实时行情
        index_df = data_source.get_index_spot()
        
        indices = []
        if not index_df.empty:
            # 查找主要指数（根据 AkShare 返回的实际代码和名称）
            target_indices = [
                {'name': '上证指数', 'code': '000001', 'keyword': '上证指数'},
                {'name': '上证50', 'code': '000016', 'keyword': '上证50'},
                {'name': '上证180', 'code': '000010', 'keyword': '上证180'},
            ]
            
            for target in target_indices:
                # 精确匹配代码
                mask = index_df['代码'] == target['code']
                matched = index_df[mask]
                if not matched.empty:
                    row = matched.iloc[0]
                    price = row.get('最新价', 0)
                    change = row.get('涨跌幅', 0)
                    vol = row.get('成交量', 0)
                    amt = row.get('成交额', 0)
                    indices.append({
                        'name': target['name'],
                        'code': str(row.get('代码', '')),
                        'price': float(price) if price else 0.0,
                        'change_pct': float(change) if change else 0.0,
                        'volume': int(vol) if vol else 0,
                        'amount': float(amt) if amt else 0.0,
                    })
        
        return {
            'success': True,
            'data': indices,
            'updated_at': datetime.now().isoformat(),
            'source': 'akshare' if data_source.is_akshare else 'tushare',
        }
        
    except Exception as e:
        logger.error(f"获取实时行情失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'data': [],
        }


@app.post("/api/llm/switch", tags=["系统"])
async def switch_llm(request: LLMSwitchRequest):
    """切换 LLM 提供商"""
    try:
        provider = LLMProvider(request.provider)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 LLM 提供商: {request.provider}. 可选: openai, google, qwen, custom"
        )
    
    from src.ai.llm.factory import switch_llm_provider
    await switch_llm_provider(provider)
    
    return {"success": True, "provider": provider.value}


class APIKeyConfigRequest(BaseModel):
    """API Key 配置请求"""
    provider: str = Field(..., description="LLM 提供商: openai, google, qwen")
    api_key: str = Field(..., description="API Key")


# 运行时 API Key 存储（内存中）
_runtime_api_keys: dict[str, str] = {}


@app.post("/api/config/apikey", tags=["系统"])
async def configure_api_key(request: APIKeyConfigRequest):
    """配置 API Key
    
    运行时配置 API Key，同时持久化到 .env 文件。
    重启后仍然有效。
    """
    import os
    from pathlib import Path
    
    provider = request.provider.lower()
    
    # 环境变量名称映射
    env_key_map = {
        "google": "GOOGLE_API_KEY",
        "openai": "OPENAI_API_KEY",
        "qwen": "QWEN_API_KEY",
    }
    
    if provider not in env_key_map:
        raise HTTPException(status_code=400, detail=f"不支持的提供商: {provider}")
    
    env_key = env_key_map[provider]
    
    # 1. 设置环境变量（运行时生效）
    os.environ[env_key] = request.api_key
    _runtime_api_keys[provider] = request.api_key
    
    # 2. 持久化到 .env 文件
    env_file = Path(".env")
    env_lines = []
    key_updated = False
    
    # 读取现有 .env 文件
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                # 跳过注释和空行
                if line.startswith("#") or not line.strip():
                    env_lines.append(line)
                    continue
                
                # 检查是否是目标 key
                if line.startswith(f"{env_key}="):
                    env_lines.append(f"{env_key}={request.api_key}\n")
                    key_updated = True
                else:
                    env_lines.append(line)
    
    # 如果 key 不存在，添加到末尾
    if not key_updated:
        env_lines.append(f"{env_key}={request.api_key}\n")
    
    # 写回文件
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(env_lines)
    
    logger.info(f"API Key 已保存到 .env 文件: {env_key}")
    
    # 3. 重置配置和 LLM 实例，并切换到新配置的提供商
    from src.config import reload_settings, LLMProvider
    from src.ai.llm.factory import switch_llm_provider
    
    reload_settings()
    
    # 切换到新配置的提供商
    provider_enum = LLMProvider(provider)
    await switch_llm_provider(provider_enum)
    
    # 重新初始化业务组件以使用新配置
    app.state.alpha_predator = AlphaPredator()
    app.state.deep_dive = DeepDiveDiagnostic()
    
    logger.info(f"已配置 {provider} API Key 并持久化保存")
    
    return {
        "success": True,
        "provider": provider,
        "message": f"{provider.upper()} API Key 已配置并保存",
        "persisted": True,
    }


@app.get("/api/config/providers", tags=["系统"])
async def get_available_providers():
    """获取可用的 LLM 提供商及其配置状态"""
    import os
    from src.ai.llm.factory import get_active_provider
    
    providers = [
        {
            "id": "google",
            "name": "Google Gemini",
            "configured": bool(os.environ.get("GOOGLE_API_KEY")),
        },
        {
            "id": "openai",
            "name": "OpenAI ChatGPT",
            "configured": bool(os.environ.get("OPENAI_API_KEY")),
        },
        {
            "id": "qwen",
            "name": "阿里通义千问",
            "configured": bool(os.environ.get("QWEN_API_KEY")),
        },
    ]
    
    # 使用运行时的激活提供商
    active_provider = get_active_provider()
    
    return {
        "providers": providers,
        "current": active_provider.value,
    }


@app.post("/api/alpha/analyze", response_model=ReportResponse, tags=["策略分析"])
async def analyze_market(request: AnalysisRequest):
    """全市场阿尔法分析
    
    执行 Alpha Predator 引擎，生成市场策略报告。
    """
    try:
        predator: AlphaPredator = app.state.alpha_predator
        report = await predator.generate_on_demand(request.trade_date)
        
        if request.send_notification:
            from src.notification.webhook import get_webhook_notifier
            notifier = get_webhook_notifier()
            await notifier.send_all(report.title, report.content[:2000])
        
        return ReportResponse(
            success=True,
            title=report.title,
            content=report.content,
            trade_date=report.trade_date,
            generated_at=report.generated_at.isoformat(),
            stage=report.stage,
            is_fallback=report.is_fallback,
        )
        
    except Exception as e:
        logger.error(f"市场分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/alpha/morning", response_model=ReportResponse, tags=["策略分析"])
async def run_morning_pipeline(send_notification: bool = False):
    """执行早盘流水线
    
    完整的双阶段流水线：预处理 -> 增量更新 -> 降级备选
    """
    try:
        predator: AlphaPredator = app.state.alpha_predator
        report = await predator.run_morning_pipeline(send_notification)
        
        return ReportResponse(
            success=True,
            title=report.title,
            content=report.content,
            trade_date=report.trade_date,
            generated_at=report.generated_at.isoformat(),
            stage=report.stage,
            is_fallback=report.is_fallback,
        )
        
    except Exception as e:
        logger.error(f"早盘流水线失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 分步分析接口 ====================

class SectorRecommendRequest(BaseModel):
    """股票推荐请求"""
    sectors: list[str] = Field(..., description="选中的板块列表")
    risk_preference: str = Field(default="balanced", description="风险偏好: aggressive, balanced, conservative")


@app.get("/api/analyze/sectors", tags=["分步分析"])
async def analyze_sectors():
    """第一步：分析热门板块
    
    返回当前市场热门板块及其资金流向分析。
    """
    try:
        predator: AlphaPredator = app.state.alpha_predator
        result = await predator.analyze_sectors()
        return result
        
    except Exception as e:
        logger.error(f"板块分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/stocks", tags=["分步分析"])
async def recommend_stocks(request: SectorRecommendRequest):
    """第二步：根据选定板块推荐股票
    
    用户选择感兴趣的板块后，推荐该板块内值得买入的股票。
    支持根据用户风险偏好调整推荐策略。
    """
    if not request.sectors:
        raise HTTPException(status_code=400, detail="请至少选择一个板块")
    
    # 验证风险偏好
    valid_risk = ["aggressive", "balanced", "conservative"]
    if request.risk_preference not in valid_risk:
        request.risk_preference = "balanced"
    
    try:
        predator: AlphaPredator = app.state.alpha_predator
        result = await predator.recommend_stocks(
            request.sectors, 
            risk_preference=request.risk_preference
        )
        return result
        
    except Exception as e:
        logger.error(f"股票推荐失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stock/diagnose", tags=["个股诊疗"])
async def diagnose_stock(request: DiagnoseRequest):
    """个股深度诊疗
    
    对指定股票进行全面"体检"，生成诊疗报告。
    """
    try:
        diagnostic: DeepDiveDiagnostic = app.state.deep_dive
        report = await diagnostic.diagnose(request.ts_code)
        
        if report is None:
            raise HTTPException(status_code=404, detail=f"未找到股票: {request.ts_code}")
        
        return {
            "success": True,
            "stock": {
                "ts_code": report.stock.ts_code,
                "name": report.stock.name,
                "industry": report.stock.industry,
            },
            "content": report.content,
            "technical_summary": report.technical_summary,
            "signal": report.signal,
            "generated_at": report.generated_at.isoformat(),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"个股诊疗失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stock/scan", response_model=QuickScanResponse, tags=["个股诊疗"])
async def quick_scan_stock(ts_code: str = Query(..., description="股票代码")):
    """快速扫描个股
    
    仅进行技术面扫描，不调用 LLM，速度较快。
    """
    try:
        diagnostic: DeepDiveDiagnostic = app.state.deep_dive
        result = await diagnostic.quick_scan(ts_code)
        
        return QuickScanResponse(
            ts_code=result["ts_code"],
            name=result["name"],
            industry=result["industry"],
            signal=result["signal"],
            technical=result["technical"],
        )
        
    except Exception as e:
        logger.error(f"快速扫描失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 错误处理 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "detail": str(exc)},
    )


# ==================== 用户偏好管理 ====================

class UserPreferencesRequest(BaseModel):
    """用户偏好请求"""
    risk_preference: str = Field(..., description="风险偏好: aggressive, balanced, conservative")


# 用户偏好存储（内存 + 文件持久化）
_user_preferences: dict = {}
_preferences_file = "user_preferences.json"


def _load_preferences():
    """加载用户偏好"""
    import json
    from pathlib import Path
    
    global _user_preferences
    pref_path = Path(_preferences_file)
    if pref_path.exists():
        try:
            with open(pref_path, "r", encoding="utf-8") as f:
                _user_preferences = json.load(f)
        except Exception as e:
            logger.warning(f"加载用户偏好失败: {e}")
            _user_preferences = {}


def _save_preferences():
    """保存用户偏好"""
    import json
    
    try:
        with open(_preferences_file, "w", encoding="utf-8") as f:
            json.dump(_user_preferences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"保存用户偏好失败: {e}")


# 启动时加载偏好
_load_preferences()


@app.get("/api/user/preferences", tags=["用户"])
async def get_user_preferences():
    """获取用户偏好"""
    return {
        "success": True,
        "preferences": _user_preferences,
    }


@app.post("/api/user/preferences", tags=["用户"])
async def set_user_preferences(request: UserPreferencesRequest):
    """设置用户偏好"""
    valid_risk = ["aggressive", "balanced", "conservative"]
    if request.risk_preference not in valid_risk:
        raise HTTPException(
            status_code=400, 
            detail=f"无效的风险偏好，可选: {valid_risk}"
        )
    
    _user_preferences["risk_preference"] = request.risk_preference
    _save_preferences()
    
    return {
        "success": True,
        "preferences": _user_preferences,
        "message": "偏好已保存",
    }


# ==================== 持仓管理 ====================

class PositionItem(BaseModel):
    """持仓项"""
    ts_code: str = Field(..., description="股票代码")
    name: str = Field("", description="股票名称")
    quantity: int = Field(..., description="持有数量（必须是100的整数倍）")
    cost_price: float = Field(..., description="成本价")


class PortfolioRequest(BaseModel):
    """持仓请求"""
    total_capital: float = Field(..., description="总投入资金")
    positions: list[PositionItem] = Field(default=[], description="持仓列表")


# 持仓数据（仅内存存储，前端负责持久化到 localStorage）
_portfolio: dict = {
    "total_capital": 0,
    "positions": [],
}


@app.get("/api/user/portfolio", tags=["用户"])
async def get_portfolio():
    """获取持仓（服务端缓存）"""
    return {
        "success": True,
        "portfolio": _portfolio,
    }


@app.post("/api/user/portfolio", tags=["用户"])
async def update_portfolio(request: PortfolioRequest):
    """更新持仓"""
    global _portfolio
    
    # 验证持仓数量是 100 的整数倍
    for pos in request.positions:
        if pos.quantity % 100 != 0:
            raise HTTPException(
                status_code=400,
                detail=f"持仓数量必须是100的整数倍: {pos.ts_code}"
            )
    
    _portfolio = {
        "total_capital": request.total_capital,
        "positions": [p.model_dump() for p in request.positions],
    }
    
    # 计算仓位占比
    for pos in _portfolio["positions"]:
        market_value = pos["quantity"] * pos["cost_price"]
        pos["market_value"] = market_value
        pos["weight"] = market_value / request.total_capital if request.total_capital > 0 else 0
    
    logger.info(f"更新持仓: {len(request.positions)} 只股票, 总资金 {request.total_capital}")
    
    return {
        "success": True,
        "portfolio": _portfolio,
    }


@app.get("/api/user/portfolio/analysis", tags=["用户"])
async def analyze_portfolio():
    """分析持仓"""
    if not _portfolio["positions"]:
        return {
            "success": False,
            "error": "暂无持仓数据",
        }
    
    # 获取持仓股票的实时行情
    from src.data.sources.factory import UnifiedDataSource
    data_source = UnifiedDataSource()
    
    analysis = []
    total_profit = 0
    
    for pos in _portfolio["positions"]:
        ts_code = pos["ts_code"]
        quote = data_source.get_realtime_quote(ts_code)
        
        if quote:
            current_price = quote.get("price", pos["cost_price"])
            profit = (current_price - pos["cost_price"]) * pos["quantity"]
            profit_pct = (current_price / pos["cost_price"] - 1) * 100 if pos["cost_price"] > 0 else 0
            
            analysis.append({
                "ts_code": ts_code,
                "name": pos.get("name", quote.get("name", "")),
                "quantity": pos["quantity"],
                "cost_price": pos["cost_price"],
                "current_price": current_price,
                "profit": profit,
                "profit_pct": profit_pct,
                "weight": pos.get("weight", 0),
            })
            total_profit += profit
    
    return {
        "success": True,
        "analysis": analysis,
        "total_profit": total_profit,
        "total_capital": _portfolio["total_capital"],
    }


@app.post("/api/user/portfolio/diagnose", tags=["用户"])
async def diagnose_portfolio(request: PortfolioRequest):
    """诊断持仓股票
    
    对用户持仓的每只股票进行深度诊断，给出买入/持有/卖出建议。
    适合每日开盘前使用。
    """
    if not request.positions:
        return {
            "success": False,
            "error": "暂无持仓数据",
        }
    
    from src.ai.llm import get_default_llm, LLMMessage
    from src.ai.llm.base import MessageRole
    from src.ai.llm.prompts import QUANT_ANALYST_ROLE
    
    try:
        llm = get_default_llm()
        
        # 采集每只持仓股的数据
        deep_dive: DeepDiveDiagnostic = app.state.deep_dive
        
        stock_data_list = []
        for pos in request.positions:
            ts_code = normalize_stock_code(pos.ts_code)
            stock_info = await deep_dive.get_stock_info(ts_code)
            stock_data = await deep_dive.collect_stock_data(ts_code)
            
            fundamental = deep_dive.format_fundamental_data(stock_data)
            technical = deep_dive.format_technical_data(stock_data)
            
            stock_data_list.append({
                "ts_code": ts_code,
                "name": stock_info.name if stock_info else pos.name,
                "quantity": pos.quantity,
                "cost_price": pos.cost_price,
                "fundamental": fundamental,
                "technical": technical,
            })
        
        # 计算可用资金
        total_market_value = sum(p.quantity * p.cost_price for p in request.positions)
        available_capital = request.total_capital - total_market_value
        
        # 构建 Prompt
        prompt = f"""请对以下持仓股票进行诊断，给出每只股票的操作建议：

## 持仓概况
- 总资产：{request.total_capital:,.0f} 元
- 持仓市值：{total_market_value:,.0f} 元
- 可用资金：{available_capital:,.0f} 元

## 持仓详情
"""
        for stock in stock_data_list:
            prompt += f"""
### {stock['name']} ({stock['ts_code']})
- 持有数量：{stock['quantity']} 股
- 成本价：{stock['cost_price']:.2f} 元

**基本面数据**
{stock['fundamental']}

**技术面数据**
{stock['technical']}
---
"""
        
        prompt += """
请为每只股票给出：
1. **操作建议**：买入 / 持有 / 减仓 / 卖出
2. **信号强度**：强 / 中 / 弱
3. **具体建议**：具体操作策略（如买入多少股、设置什么止损位）
4. **风险提示**：需要关注的风险点

输出格式：Markdown，每只股票一个单独的章节。
"""
        
        messages = [
            LLMMessage(role=MessageRole.SYSTEM, content=QUANT_ANALYST_ROLE),
            LLMMessage(role=MessageRole.USER, content=prompt),
        ]
        
        response = await llm.chat(messages)
        
        return {
            "success": True,
            "diagnosis": response.content,
            "stock_count": len(request.positions),
            "total_capital": request.total_capital,
            "available_capital": available_capital,
        }
        
    except Exception as e:
        logger.error(f"持仓诊断失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }
