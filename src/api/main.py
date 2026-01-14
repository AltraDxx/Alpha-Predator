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
    
    运行时配置 API Key，无需修改 .env 文件。
    重启后失效。
    """
    import os
    
    provider = request.provider.lower()
    
    # 设置环境变量（运行时生效）
    if provider == "google":
        os.environ["GOOGLE_API_KEY"] = request.api_key
        _runtime_api_keys["google"] = request.api_key
    elif provider == "openai":
        os.environ["OPENAI_API_KEY"] = request.api_key
        _runtime_api_keys["openai"] = request.api_key
    elif provider == "qwen":
        os.environ["QWEN_API_KEY"] = request.api_key
        _runtime_api_keys["qwen"] = request.api_key
    else:
        raise HTTPException(status_code=400, detail=f"不支持的提供商: {provider}")
    
    # 重置配置和 LLM 实例，并切换到新配置的提供商
    from src.config import reload_settings, LLMProvider
    from src.ai.llm.factory import switch_llm_provider
    
    reload_settings()
    
    # 切换到新配置的提供商
    provider_enum = LLMProvider(provider)
    await switch_llm_provider(provider_enum)
    
    # 重新初始化业务组件以使用新配置
    app.state.alpha_predator = AlphaPredator()
    app.state.deep_dive = DeepDiveDiagnostic()
    
    logger.info(f"已配置 {provider} API Key")
    
    return {
        "success": True,
        "provider": provider,
        "message": f"{provider.upper()} API Key 已配置成功",
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
    """
    if not request.sectors:
        raise HTTPException(status_code=400, detail="请至少选择一个板块")
    
    try:
        predator: AlphaPredator = app.state.alpha_predator
        result = await predator.recommend_stocks(request.sectors)
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
