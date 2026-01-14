# AkShare API 接口参考文档

> 本文档整理自 AkShare 源码，用于项目中的数据采集接口调用。
> 按照分析优先级排序：消息面 > 资金流向 > 技术形态 > 宏观流动性

---

## 1. 消息面数据（最高优先级）

### 1.1 个股新闻
```python
import akshare as ak

# 获取个股最近100条新闻
df = ak.stock_news_em(symbol="000001")
# 返回字段：关键词, 新闻标题, 新闻内容, 发布时间, 文章来源, 新闻链接
```

### 1.2 公告信息
```python
# 深交所公告
df = ak.stock_notice_cninfo(symbol="000001")
# 返回字段：公告标题, 公告时间, 公告类型, 公告链接
```

### 1.3 业绩预告
```python
# 业绩预告（东方财富）
df = ak.stock_yjyg_em(date="20241231")
# 返回字段：股票代码, 股票简称, 预告类型, 净利润变动幅度下限, 净利润变动幅度上限, 业绩变动原因

# 业绩快报
df = ak.stock_yjkb_em(date="20241231")
```

### 1.4 限售解禁
```python
# 限售解禁数据
df = ak.stock_restricted_release_queue_sina(symbol="600000")
# 返回字段：代码, 名称, 解禁日期, 解禁数量, 解禁股流通市值, 上市批次, 公告日期
```

### 1.5 股东增减持
```python
# 股东增减持明细
df = ak.stock_inner_trade_xq(symbol="000001")
# 返回字段：公告日期, 变动人, 变动类型, 变动数量, 成交价格
```

---

## 2. 资金流向数据

### 2.1 板块资金流向
```python
# 行业板块资金流向排名
df = ak.stock_sector_fund_flow_rank(indicator="今日")
# indicator: "今日", "5日", "10日"
# 返回字段：序号, 名称, 今日涨跌幅, 今日主力净流入-净额, 今日主力净流入-净占比, ...
```

### 2.2 个股资金流向
```python
# 单只股票资金流向
df = ak.stock_individual_fund_flow(stock="000001", market="sz")
# 返回字段：日期, 收盘价, 涨跌幅, 主力净流入-净额, 主力净流入-净占比, ...

# 个股资金流向排名
df = ak.stock_individual_fund_flow_rank(indicator="今日")
```

### 2.3 北向资金
```python
# 北向资金净流入（时间序列）
df = ak.stock_hsgt_north_net_flow_in_em(indicator="沪股通")
# indicator: "沪股通", "深股通", "北上"

# 北向资金增持个股排名
df = ak.stock_hsgt_hold_stock_em(market="北向", indicator="今日排行")

# 沪深港通持股
df = ak.stock_hsgt_individual_em(stock="002415")
```

### 2.4 融资融券
```python
# 融资融券余额（市场汇总）
df = ak.stock_margin_sse(start_date="20240101", end_date="20241231")

# 个股融资融券
df = ak.stock_margin_detail_szse(date="20241231")
```

### 2.5 龙虎榜
```python
# 龙虎榜详情
df = ak.stock_lhb_detail_em(start_date="20241201", end_date="20241231")
# 返回字段：序号, 代码, 名称, 收盘价, 涨跌幅, 龙虎榜净买额, ...

# 龙虎榜个股详情
df = ak.stock_lhb_stock_statistic_em(symbol="近一月")
```

---

## 3. 技术面数据

### 3.1 实时行情
```python
# A股实时行情
df = ak.stock_zh_a_spot_em()
# 返回字段：代码, 名称, 最新价, 涨跌幅, 涨跌额, 成交量, 成交额, 振幅, 最高, 最低, 今开, 昨收, 量比, 换手率, 市盈率, 市净率

# 指数实时行情
df = ak.stock_zh_index_spot_em()
```

### 3.2 K线历史数据
```python
# 个股历史K线（日线）
df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20240101", end_date="20241231", adjust="qfq")
# period: "daily", "weekly", "monthly"
# adjust: "qfq"(前复权), "hfq"(后复权), ""(不复权)
# 返回字段：日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
```

### 3.3 技术指标
```python
# 同花顺技术指标概念
df = ak.stock_rank_lxsz_ths()  # 连续上涨
df = ak.stock_rank_cxg_ths()   # 创新高
df = ak.stock_rank_cxfl_ths()  # 持续放量
```

### 3.4 涨停跌停
```python
# 涨停板数据
df = ak.stock_zt_pool_em(date="20241231")
# 返回字段：代码, 名称, 涨跌幅, 最新价, 涨停统计, 连板数, 首次封板时间, 最后封板时间, 封板资金, ...

# 跌停板数据
df = ak.stock_zt_pool_dtgc_em(date="20241231")

# 炸板数据
df = ak.stock_zt_pool_zbgc_em(date="20241231")
```

---

## 4. 宏观流动性数据

### 4.1 银行间拆借利率（Shibor）
```python
# Shibor 人民币利率
df = ak.rate_interbank(market="上海银行同业拆借市场", symbol="Shibor人民币", indicator="隔夜")
# indicator: "隔夜", "1周", "2周", "1月", "3月", "6月", "1年"
# 返回字段：报告日, 利率, 涨跌
```

### 4.2 货币供应量
```python
# M0/M1/M2 货币供应量
df = ak.macro_china_supply_of_money()
# 返回字段：统计时间, 货币和准货币(M2), M2同比增长, 货币(M1), M1同比增长, 流通中的现金(M0), M0同比增长
```

### 4.3 央行公开市场操作
```python
# 央行逆回购等操作
df = ak.macro_china_gksczj()
```

---

## 5. 基本面数据

### 5.1 财务摘要
```python
# 财务报表关键指标
df = ak.stock_financial_abstract(symbol="600000")
# 返回字段多维度：每股指标、盈利能力、成长能力、收益质量、财务风险、营运能力
```

### 5.2 三大报表
```python
# 资产负债表
df = ak.stock_financial_report_sina(stock="sh600600", symbol="资产负债表")

# 利润表
df = ak.stock_financial_report_sina(stock="sh600600", symbol="利润表")

# 现金流量表
df = ak.stock_financial_report_sina(stock="sh600600", symbol="现金流量表")
```

### 5.3 财务分析指标
```python
# 东方财富财务分析
df = ak.stock_financial_analysis_indicator_em(symbol="301389.SZ", indicator="按报告期")
```

### 5.4 分红配股
```python
# 历史分红
df = ak.stock_history_dividend()

# 分红配股详情
df = ak.stock_history_dividend_detail(symbol="000002", indicator="分红")
```

### 5.5 股东信息
```python
# 流通股东
df = ak.stock_circulate_stock_holder(symbol="600000")

# 主要股东
df = ak.stock_main_stock_holder(stock="600004")

# 基金持股
df = ak.stock_fund_stock_holder(symbol="600004")
```

### 5.6 估值指标
```python
# 市盈率/市净率
df = ak.stock_a_indicator_lg(symbol="000001")
# 返回字段：trade_date, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_mv

# A股估值表（全市场）
df = ak.stock_a_pe(market="全部A股")
```

---

## 6. 外部市场数据

### 6.1 汇率
```python
# 美元人民币汇率
df = ak.currency_boc_sina(symbol="美元")
```

### 6.2 商品行情
```python
# 黄金价格
df = ak.spot_golden_benchmark_sge()

# 原油价格
df = ak.futures_main_sina(symbol="SC0")  # 原油期货主力
```

---

## 7. 舆情与另类数据

### 7.1 热门股票排名
```python
# 东方财富人气榜
df = ak.stock_hot_rank_em()
# 返回字段：序号, 代码, 名称, 最新价, 涨跌幅, 排名, 排名变化
```

### 7.2 研报数据
```python
# 个股研报
df = ak.stock_research_report_em(symbol="601318")
# 返回字段：序号, 报告日期, 标题, 机构, 评级, ...
```

---

## 接口调用注意事项

1. **频率限制**：AkShare 会对高频请求进行限制，建议添加延时
2. **数据更新**：实时数据通常延迟 15-30 分钟
3. **字段变化**：AkShare 经常更新，字段名可能变化，需要做好兼容
4. **异常处理**：网络请求可能失败，需要做好重试和异常处理
