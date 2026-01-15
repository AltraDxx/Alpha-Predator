"""交易日和交易时间判断工具"""

from datetime import datetime, time
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def is_trading_day(dt: datetime = None) -> bool:
    """判断是否为交易日（周一至周五）
    
    注意：此函数不考虑节假日，如需精确判断需要接入交易日历
    
    Args:
        dt: 日期时间，默认当前时间
        
    Returns:
        是否为交易日
    """
    if dt is None:
        dt = datetime.now()
    
    # 周一=0, 周日=6，周六日不是交易日
    return dt.weekday() < 5


def is_trading_time(dt: datetime = None) -> bool:
    """判断是否在交易时间内
    
    A股交易时间：
    - 上午 9:30 - 11:30
    - 下午 13:00 - 15:00
    
    Args:
        dt: 日期时间，默认当前时间
        
    Returns:
        是否在交易时间内
    """
    if dt is None:
        dt = datetime.now()
    
    current_time = dt.time()
    
    # 上午交易时间
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    
    # 下午交易时间
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    return (
        (morning_start <= current_time <= morning_end) or
        (afternoon_start <= current_time <= afternoon_end)
    )


def is_market_open(dt: datetime = None) -> bool:
    """判断市场是否开盘
    
    Args:
        dt: 日期时间，默认当前时间
        
    Returns:
        市场是否开盘
    """
    if dt is None:
        dt = datetime.now()
    
    return is_trading_day(dt) and is_trading_time(dt)


def get_market_status() -> Tuple[str, str]:
    """获取市场状态
    
    Returns:
        (状态代码, 状态描述)
        状态代码: 'open', 'closed', 'pre_market', 'post_market'
    """
    now = datetime.now()
    current_time = now.time()
    
    if not is_trading_day(now):
        return ('closed', '休市（非交易日）')
    
    morning_start = time(9, 30)
    morning_end = time(11, 30)
    afternoon_start = time(13, 0)
    afternoon_end = time(15, 0)
    
    if current_time < time(9, 15):
        return ('closed', '未开盘')
    elif current_time < morning_start:
        return ('pre_market', '集合竞价')
    elif current_time <= morning_end:
        return ('open', '交易中（上午）')
    elif current_time < afternoon_start:
        return ('closed', '午间休市')
    elif current_time <= afternoon_end:
        return ('open', '交易中（下午）')
    else:
        return ('post_market', '已收盘')


def should_refresh_data() -> bool:
    """判断是否应该刷新数据
    
    只在交易日的交易时间内返回 True
    
    Returns:
        是否应该刷新数据
    """
    return is_market_open()
