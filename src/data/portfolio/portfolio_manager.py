"""用户持仓管理模块

支持：
- 手动导入持仓（CSV/Excel）
- 持仓盈亏计算
- 与诊疗模块联动
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Optional
import json

import pandas as pd
from loguru import logger


@dataclass
class Position:
    """持仓数据模型"""
    ts_code: str                   # 股票代码
    stock_name: str                # 股票名称
    quantity: int                  # 持仓数量
    cost_price: float              # 成本价
    current_price: float = 0.0     # 当前价
    market_value: float = 0.0      # 市值
    profit: float = 0.0            # 盈亏金额
    profit_ratio: float = 0.0      # 盈亏比例
    buy_date: Optional[date] = None  # 买入日期
    
    def update_price(self, current_price: float):
        """更新当前价格并计算盈亏"""
        self.current_price = current_price
        self.market_value = self.quantity * current_price
        cost_value = self.quantity * self.cost_price
        self.profit = self.market_value - cost_value
        self.profit_ratio = (self.profit / cost_value * 100) if cost_value > 0 else 0
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "ts_code": self.ts_code,
            "stock_name": self.stock_name,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "profit": self.profit,
            "profit_ratio": self.profit_ratio,
            "buy_date": self.buy_date.isoformat() if self.buy_date else None,
        }


class PortfolioManager:
    """持仓管理器"""
    
    def __init__(self, data_dir: Optional[Path] = None):
        """初始化持仓管理器
        
        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = data_dir or Path("data/portfolio")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.positions: dict[str, Position] = {}
        self._load_positions()
        
        logger.info(f"持仓管理器初始化，当前持仓: {len(self.positions)} 只")
    
    def _get_save_path(self) -> Path:
        """获取保存路径"""
        return self.data_dir / "positions.json"
    
    def _load_positions(self):
        """加载已保存的持仓"""
        save_path = self._get_save_path()
        if save_path.exists():
            try:
                with open(save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        pos = Position(
                            ts_code=item["ts_code"],
                            stock_name=item["stock_name"],
                            quantity=item["quantity"],
                            cost_price=item["cost_price"],
                            current_price=item.get("current_price", 0),
                            market_value=item.get("market_value", 0),
                            profit=item.get("profit", 0),
                            profit_ratio=item.get("profit_ratio", 0),
                            buy_date=date.fromisoformat(item["buy_date"]) if item.get("buy_date") else None,
                        )
                        self.positions[pos.ts_code] = pos
                logger.info(f"加载持仓: {len(self.positions)} 只")
            except Exception as e:
                logger.error(f"加载持仓失败: {e}")
    
    def _save_positions(self):
        """保存持仓到文件"""
        try:
            data = [pos.to_dict() for pos in self.positions.values()]
            with open(self._get_save_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"保存持仓: {len(self.positions)} 只")
        except Exception as e:
            logger.error(f"保存持仓失败: {e}")
    
    def add_position(
        self,
        ts_code: str,
        stock_name: str,
        quantity: int,
        cost_price: float,
        buy_date: Optional[date] = None,
    ) -> Position:
        """添加持仓
        
        Args:
            ts_code: 股票代码
            stock_name: 股票名称
            quantity: 持仓数量
            cost_price: 成本价
            buy_date: 买入日期
            
        Returns:
            持仓对象
        """
        if ts_code in self.positions:
            # 已有持仓，更新（加仓）
            existing = self.positions[ts_code]
            total_cost = existing.quantity * existing.cost_price + quantity * cost_price
            total_quantity = existing.quantity + quantity
            existing.quantity = total_quantity
            existing.cost_price = total_cost / total_quantity if total_quantity > 0 else 0
            position = existing
        else:
            position = Position(
                ts_code=ts_code,
                stock_name=stock_name,
                quantity=quantity,
                cost_price=cost_price,
                buy_date=buy_date or date.today(),
            )
            self.positions[ts_code] = position
        
        self._save_positions()
        logger.info(f"添加持仓: {ts_code} {stock_name} x{quantity} @{cost_price}")
        return position
    
    def remove_position(self, ts_code: str, quantity: Optional[int] = None) -> bool:
        """移除持仓（卖出）
        
        Args:
            ts_code: 股票代码
            quantity: 卖出数量，None 表示全部卖出
            
        Returns:
            是否成功
        """
        if ts_code not in self.positions:
            logger.warning(f"持仓不存在: {ts_code}")
            return False
        
        if quantity is None or quantity >= self.positions[ts_code].quantity:
            del self.positions[ts_code]
        else:
            self.positions[ts_code].quantity -= quantity
        
        self._save_positions()
        logger.info(f"移除持仓: {ts_code} x{quantity or 'all'}")
        return True
    
    def import_from_csv(self, file_path: str | Path) -> int:
        """从 CSV 文件导入持仓
        
        CSV 格式要求列：
        - ts_code / 股票代码
        - stock_name / 股票名称
        - quantity / 持仓数量
        - cost_price / 成本价
        - buy_date / 买入日期（可选）
        
        Args:
            file_path: CSV 文件路径
            
        Returns:
            导入数量
        """
        try:
            df = pd.read_csv(file_path)
            return self._import_from_dataframe(df)
        except Exception as e:
            logger.error(f"导入 CSV 失败: {e}")
            return 0
    
    def import_from_excel(self, file_path: str | Path, sheet_name: str = "Sheet1") -> int:
        """从 Excel 文件导入持仓
        
        Args:
            file_path: Excel 文件路径
            sheet_name: 工作表名称
            
        Returns:
            导入数量
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            return self._import_from_dataframe(df)
        except Exception as e:
            logger.error(f"导入 Excel 失败: {e}")
            return 0
    
    def _import_from_dataframe(self, df: pd.DataFrame) -> int:
        """从 DataFrame 导入持仓"""
        # 列名映射
        column_map = {
            "股票代码": "ts_code",
            "代码": "ts_code",
            "股票名称": "stock_name",
            "名称": "stock_name",
            "持仓数量": "quantity",
            "数量": "quantity",
            "成本价": "cost_price",
            "买入价": "cost_price",
            "买入日期": "buy_date",
            "日期": "buy_date",
        }
        
        df = df.rename(columns=column_map)
        
        count = 0
        for _, row in df.iterrows():
            try:
                ts_code = str(row.get("ts_code", ""))
                if not ts_code:
                    continue
                
                # 确保代码格式正确
                if "." not in ts_code:
                    # 自动补充后缀
                    if ts_code.startswith("6"):
                        ts_code = f"{ts_code}.SH"
                    else:
                        ts_code = f"{ts_code}.SZ"
                
                self.add_position(
                    ts_code=ts_code,
                    stock_name=str(row.get("stock_name", "")),
                    quantity=int(row.get("quantity", 0)),
                    cost_price=float(row.get("cost_price", 0)),
                    buy_date=pd.to_datetime(row.get("buy_date")).date() if pd.notna(row.get("buy_date")) else None,
                )
                count += 1
            except Exception as e:
                logger.warning(f"跳过行: {e}")
        
        logger.info(f"导入持仓: {count} 只")
        return count
    
    def update_prices(self, price_data: dict[str, float]):
        """批量更新当前价格
        
        Args:
            price_data: {ts_code: current_price}
        """
        for ts_code, price in price_data.items():
            if ts_code in self.positions:
                self.positions[ts_code].update_price(price)
        
        self._save_positions()
    
    def get_all_positions(self) -> list[Position]:
        """获取所有持仓"""
        return list(self.positions.values())
    
    def get_position(self, ts_code: str) -> Optional[Position]:
        """获取指定股票的持仓"""
        return self.positions.get(ts_code)
    
    def get_summary(self) -> dict:
        """获取持仓汇总"""
        total_cost = sum(p.quantity * p.cost_price for p in self.positions.values())
        total_value = sum(p.market_value for p in self.positions.values())
        total_profit = sum(p.profit for p in self.positions.values())
        
        return {
            "position_count": len(self.positions),
            "total_cost": total_cost,
            "total_value": total_value,
            "total_profit": total_profit,
            "total_profit_ratio": (total_profit / total_cost * 100) if total_cost > 0 else 0,
        }
    
    def format_for_llm(self) -> str:
        """格式化持仓数据，供 LLM 分析使用"""
        if not self.positions:
            return "当前无持仓"
        
        lines = ["## 当前持仓\n"]
        lines.append("| 股票 | 代码 | 数量 | 成本价 | 现价 | 盈亏 |")
        lines.append("|------|------|------|--------|------|------|")
        
        for pos in self.positions.values():
            profit_str = f"+{pos.profit:.2f}" if pos.profit >= 0 else f"{pos.profit:.2f}"
            lines.append(
                f"| {pos.stock_name} | {pos.ts_code} | {pos.quantity} | "
                f"{pos.cost_price:.2f} | {pos.current_price:.2f} | {profit_str} ({pos.profit_ratio:+.2f}%) |"
            )
        
        summary = self.get_summary()
        lines.append(f"\n**汇总**：总市值 {summary['total_value']:.2f}，总盈亏 {summary['total_profit']:.2f} ({summary['total_profit_ratio']:+.2f}%)")
        
        return "\n".join(lines)
    
    def get_codes_for_diagnosis(self) -> list[str]:
        """获取所有持仓股票代码，用于批量诊疗"""
        return list(self.positions.keys())
