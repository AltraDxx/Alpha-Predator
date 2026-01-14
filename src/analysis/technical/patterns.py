"""K线形态识别模块

识别常见的 K 线反转与持续形态：
- 反转形态：早晨之星、黄昏之星、穿头破脚、身怀六甲
- 持续形态：三连阳、三连阴
- 特殊形态：九阳神功、七仙女下凡
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


class PatternType(str, Enum):
    """形态类型"""
    BULLISH = "bullish"      # 看涨
    BEARISH = "bearish"      # 看跌
    NEUTRAL = "neutral"      # 中性


@dataclass
class PatternResult:
    """形态识别结果"""
    name: str               # 形态名称
    name_en: str            # 英文名称
    pattern_type: PatternType  # 形态类型
    confidence: float       # 置信度 (0-1)
    description: str        # 形态描述
    position: int           # 在 DataFrame 中的位置索引
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "name_en": self.name_en,
            "type": self.pattern_type.value,
            "confidence": self.confidence,
            "description": self.description,
            "position": self.position,
        }


class PatternRecognizer:
    """K线形态识别器"""
    
    def __init__(self, df: pd.DataFrame):
        """初始化
        
        Args:
            df: 包含 OHLC 数据的 DataFrame
        """
        self.df = df.copy()
        self.df.columns = self.df.columns.str.lower()
        self._validate()
    
    def _validate(self):
        """验证数据"""
        required = ["open", "high", "low", "close"]
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"缺少必要列: {missing}")
    
    def _body_size(self, idx: int) -> float:
        """计算实体大小"""
        return abs(self.df["close"].iloc[idx] - self.df["open"].iloc[idx])
    
    def _is_bullish(self, idx: int) -> bool:
        """是否阳线"""
        return self.df["close"].iloc[idx] > self.df["open"].iloc[idx]
    
    def _is_bearish(self, idx: int) -> bool:
        """是否阴线"""
        return self.df["close"].iloc[idx] < self.df["open"].iloc[idx]
    
    def _is_doji(self, idx: int, threshold: float = 0.1) -> bool:
        """是否十字星（实体很小）"""
        body = self._body_size(idx)
        total_range = self.df["high"].iloc[idx] - self.df["low"].iloc[idx]
        if total_range == 0:
            return True
        return body / total_range < threshold
    
    def _avg_body_size(self, lookback: int = 10) -> float:
        """计算平均实体大小"""
        if len(self.df) < lookback:
            lookback = len(self.df)
        bodies = [self._body_size(i) for i in range(-lookback, 0)]
        return np.mean(bodies) if bodies else 0
    
    def morning_star(self, idx: int = -1) -> Optional[PatternResult]:
        """识别早晨之星（看涨反转）
        
        形态定义：
        1. 第一日：长阴线
        2. 第二日：跳空低开的小星线（十字星或小实体）
        3. 第三日：阳线，收盘价进入第一根阴线实体
        """
        if len(self.df) < 3:
            return None
        
        # 转换为正索引
        if idx < 0:
            idx = len(self.df) + idx
        if idx < 2:
            return None
        
        day1, day2, day3 = idx - 2, idx - 1, idx
        avg_body = self._avg_body_size()
        
        # 条件1：第一天是长阴线
        if not self._is_bearish(day1):
            return None
        if self._body_size(day1) < avg_body * 0.8:
            return None
        
        # 条件2：第二天是小星线（跳空低开）
        if self._body_size(day2) > avg_body * 0.3:
            return None
        # 跳空：第二天最高价低于第一天收盘价
        if self.df["high"].iloc[day2] > self.df["close"].iloc[day1]:
            return None
        
        # 条件3：第三天是阳线，收盘进入第一天实体
        if not self._is_bullish(day3):
            return None
        if self.df["close"].iloc[day3] <= (self.df["open"].iloc[day1] + self.df["close"].iloc[day1]) / 2:
            return None
        
        return PatternResult(
            name="早晨之星",
            name_en="Morning Star",
            pattern_type=PatternType.BULLISH,
            confidence=0.75,
            description="经典的底部反转形态，空头力竭、多头反击",
            position=idx,
        )
    
    def evening_star(self, idx: int = -1) -> Optional[PatternResult]:
        """识别黄昏之星（看跌反转）
        
        形态定义：
        1. 第一日：长阳线
        2. 第二日：跳空高开的小星线
        3. 第三日：阴线，收盘价进入第一根阳线实体
        """
        if len(self.df) < 3:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < 2:
            return None
        
        day1, day2, day3 = idx - 2, idx - 1, idx
        avg_body = self._avg_body_size()
        
        # 条件1：第一天是长阳线
        if not self._is_bullish(day1):
            return None
        if self._body_size(day1) < avg_body * 0.8:
            return None
        
        # 条件2：第二天是小星线（跳空高开）
        if self._body_size(day2) > avg_body * 0.3:
            return None
        if self.df["low"].iloc[day2] < self.df["close"].iloc[day1]:
            return None
        
        # 条件3：第三天是阴线，收盘进入第一天实体
        if not self._is_bearish(day3):
            return None
        if self.df["close"].iloc[day3] >= (self.df["open"].iloc[day1] + self.df["close"].iloc[day1]) / 2:
            return None
        
        return PatternResult(
            name="黄昏之星",
            name_en="Evening Star",
            pattern_type=PatternType.BEARISH,
            confidence=0.75,
            description="经典的顶部反转形态，多头力竭、空头反击",
            position=idx,
        )
    
    def engulfing_bullish(self, idx: int = -1) -> Optional[PatternResult]:
        """识别看涨吞没（穿头破脚）"""
        if len(self.df) < 2:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < 1:
            return None
        
        day1, day2 = idx - 1, idx
        
        # 第一天阴线，第二天阳线
        if not self._is_bearish(day1) or not self._is_bullish(day2):
            return None
        
        # 第二天实体完全包含第一天实体
        if (self.df["open"].iloc[day2] >= self.df["close"].iloc[day1] or
            self.df["close"].iloc[day2] <= self.df["open"].iloc[day1]):
            return None
        
        return PatternResult(
            name="看涨吞没",
            name_en="Bullish Engulfing",
            pattern_type=PatternType.BULLISH,
            confidence=0.7,
            description="阳线完全吞没前一日阴线，多头强势反击",
            position=idx,
        )
    
    def engulfing_bearish(self, idx: int = -1) -> Optional[PatternResult]:
        """识别看跌吞没"""
        if len(self.df) < 2:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < 1:
            return None
        
        day1, day2 = idx - 1, idx
        
        # 第一天阳线，第二天阴线
        if not self._is_bullish(day1) or not self._is_bearish(day2):
            return None
        
        # 第二天实体完全包含第一天实体
        if (self.df["open"].iloc[day2] <= self.df["close"].iloc[day1] or
            self.df["close"].iloc[day2] >= self.df["open"].iloc[day1]):
            return None
        
        return PatternResult(
            name="看跌吞没",
            name_en="Bearish Engulfing",
            pattern_type=PatternType.BEARISH,
            confidence=0.7,
            description="阴线完全吞没前一日阳线，空头强势打压",
            position=idx,
        )
    
    def harami_bullish(self, idx: int = -1) -> Optional[PatternResult]:
        """识别看涨孕线（身怀六甲）"""
        if len(self.df) < 2:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < 1:
            return None
        
        day1, day2 = idx - 1, idx
        
        # 第一天长阴线，第二天小阳线被包含
        if not self._is_bearish(day1) or not self._is_bullish(day2):
            return None
        
        # 第二天实体被第一天实体包含
        if (self.df["close"].iloc[day2] >= self.df["open"].iloc[day1] or
            self.df["open"].iloc[day2] <= self.df["close"].iloc[day1]):
            return None
        
        return PatternResult(
            name="看涨孕线",
            name_en="Bullish Harami",
            pattern_type=PatternType.BULLISH,
            confidence=0.6,
            description="大阴线后出现被包含的小阳线，下跌动能衰竭",
            position=idx,
        )
    
    def consecutive_yang(self, idx: int = -1, count: int = 3) -> Optional[PatternResult]:
        """识别连续阳线
        
        Args:
            idx: 结束位置
            count: 连阳数量
        """
        if len(self.df) < count:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < count - 1:
            return None
        
        # 检查连续阳线
        for i in range(count):
            if not self._is_bullish(idx - count + 1 + i):
                return None
        
        # 检查收盘价是否依次升高
        closes = [self.df["close"].iloc[idx - count + 1 + i] for i in range(count)]
        if not all(closes[i] < closes[i + 1] for i in range(len(closes) - 1)):
            return None
        
        name = f"{count}连阳"
        if count == 9:
            name = "九阳神功"
        elif count == 7:
            name = "七连阳"
        
        return PatternResult(
            name=name,
            name_en=f"{count} Consecutive Yang",
            pattern_type=PatternType.BULLISH,
            confidence=min(0.5 + count * 0.05, 0.9),
            description=f"连续{count}根阳线收高，多头强势",
            position=idx,
        )
    
    def consecutive_yin(self, idx: int = -1, count: int = 3) -> Optional[PatternResult]:
        """识别连续阴线（如七仙女下凡）"""
        if len(self.df) < count:
            return None
        
        if idx < 0:
            idx = len(self.df) + idx
        if idx < count - 1:
            return None
        
        for i in range(count):
            if not self._is_bearish(idx - count + 1 + i):
                return None
        
        closes = [self.df["close"].iloc[idx - count + 1 + i] for i in range(count)]
        if not all(closes[i] > closes[i + 1] for i in range(len(closes) - 1)):
            return None
        
        name = f"{count}连阴"
        if count == 7:
            name = "七仙女下凡"
        
        return PatternResult(
            name=name,
            name_en=f"{count} Consecutive Yin",
            pattern_type=PatternType.BEARISH,
            confidence=min(0.5 + count * 0.05, 0.9),
            description=f"连续{count}根阴线收低，空头强势",
            position=idx,
        )
    
    def scan_all_patterns(self, idx: int = -1) -> list[PatternResult]:
        """扫描所有支持的形态
        
        Args:
            idx: 扫描位置
            
        Returns:
            识别到的形态列表
        """
        patterns = []
        
        # 扫描各种形态
        checkers = [
            self.morning_star,
            self.evening_star,
            self.engulfing_bullish,
            self.engulfing_bearish,
            self.harami_bullish,
            lambda i: self.consecutive_yang(i, 3),
            lambda i: self.consecutive_yang(i, 5),
            lambda i: self.consecutive_yang(i, 7),
            lambda i: self.consecutive_yang(i, 9),
            lambda i: self.consecutive_yin(i, 3),
            lambda i: self.consecutive_yin(i, 5),
            lambda i: self.consecutive_yin(i, 7),
        ]
        
        for checker in checkers:
            result = checker(idx)
            if result:
                patterns.append(result)
        
        # 按置信度排序
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        return patterns
