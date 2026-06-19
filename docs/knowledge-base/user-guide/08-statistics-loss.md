# 亏损订单统计

「统计 → 亏损订单」提供月度亏损订单报表，支持月度全部亏损与月度前 20 天亏损两种视图，可筛选、排序与下载 Excel。

## 入口

侧边栏：统计 → 亏损订单（路由 `/statistics/lossmakingorders`）。

## 数据说明

- 数据存储在 `MonthlyLossOrder`（月度全量）与 `MonthlyLossOrderFirst20`（月度前 20 天）两张表。
- **这两张表在系统内无写入代码**，数据由外部注入（admin 手工或外部 ETL）。
- `lossmakingorders_sync` 接口当前是**空操作（no-op）**，不触发领星拉取，仅返回一个缓存 key 和时间戳。历史 `OrderProfitCache` 模型已废弃。

## 字段说明

| 字段 | 含义 | 格式 |
| --- | --- | --- |
| image | 商品图片 | 36×36 |
| msku | MSKU | 多行，双击复制 |
| asin | ASIN | 多行，双击复制 |
| parent_asin | 父 ASIN | 多行 |
| store_country | 店铺 / 国家 | 两行展示 |
| product_name_sku | 品名 / SKU | 多行 tooltip |
| gross_profit | 毛利润 | 带货币符号，可排序 |
| gross_margin | 毛利率 | 百分比，可排序 |
| net_gross_margin | 净毛利率 | 百分比，可排序 |
| return_rate | 退货率 | 百分比，可排序 |
| refund_amount_rate | 退款率 | 百分比，可排序 |
| total_stock_fee | 仓储费 | 带货币符号，可排序 |
| spend | 广告费 | 带货币符号，可排序 |
| spend_rate | 广告费率 | 百分比，可排序 |
| owner / principal_names | 负责人 | |

比率字段在后端序列化器中由小数 `×100` 格式化为 `xx.xx%` 字符串。

## 筛选条件

| 筛选项 | 说明 | 可选值 |
| --- | --- | --- |
| 店铺 | 多选，含全选 | 系统店铺列表 |
| 币种 | 单选 | 原币种 / CNY / USD / EUR / JPY / AUD / CAD / MXN / GBP / INR / AED / SGD / SAR / BRL / SEK / PLN / TRY / HKD |
| Listing 负责人 | 多选，含全选 | 系统负责人列表 |
| 下单时间 | 日期范围 | 快捷：今天 / 昨天 / 最近 7 天 / 最近 30 天 / 本月 / 上月 / 今年 / 去年 |
| 规则 | 单选 | 规则一 ~ 规则四（见下文） |
| 搜索 | MSKU | 一行一项，最多 2000 行 |

## 亏损界定规则

三个基础条件：

- **cond1**：毛利润 < 0
- **cond2**：退款率 > 15%（存储为小数 0.15）
- **cond3**：广告费率 > 10%（存储为小数 0.10）

| 规则 | 逻辑 | 说明 |
| --- | --- | --- |
| 规则一（rule1） | cond1 OR cond2 OR cond3 | 满足任一条件 |
| 规则二（rule2） | cond1 AND cond2 AND cond3 | 三者同时满足 |
| 规则三（rule3） | cond1 AND cond2 AND NOT cond3 | 毛利负 + 退款高，不看广告 |
| 规则四（rule4） | cond1 AND cond3 AND NOT cond2 | 毛利负 + 广告高，不看退款 |

MSKU 列按命中规则着色：rule2 红、rule3 绿、rule4 金。

## 月度亏损（全部）

后端 `MonthlyLossViewSet`，端点 `/api/v1/statistics/monthly-loss/*`：

- `GET` 列表（分页 + month / owner 过滤）。
- `POST` 新增、`PUT` 编辑、`DELETE` 批量删除（逗号分隔 ID）。
- `GET /<id>/form` 编辑回填。
- `GET/POST /download` 导出 Excel。

## 月度前 20 天亏损

后端 `MonthlyLossFirst20ViewSet`，端点 `/api/v1/statistics/monthly-loss-first20/*`，CRUD 结构与月度全量对称。

### 前 20 天口径

- `MonthlyLossOrderFirst20` 表仅存每月**前 20 天**（1-20 日）的亏损订单聚合数据。
- **用途**：月初早期预警——在月末全月数据出来前，先用前 20 天快照做对比。
- **下载对比口径**：仅支持单月输入，导出时取「本月前 20 天」（First20 表）vs「上月整月」（全量表）并列对比，每个指标输出 Prev（上月）/ Cur（本月前 20 天）两列。

## 下载导出

### 月度全量下载

- 端点 `GET/POST /statistics/monthly-loss/download`。
- 参数：owner、time（如 `202510-202512` 或 `202510`）、store、batch_size。
- 聚合（pandas）：按 `(msku, asin, parent_asin, store_country, month)` 分组，sales / 毛利 / 仓储费 / 广告费 = sum，各比率 = mean。
- XLSX 结构：6 基本列 + 9 指标组 × N 月列。
- 单元格着色：毛利<0 且退款>15% 且广告率>10% → 红；毛利<0 且退款>15% 且广告率≤10% → 绿；毛利<0 且退款≤15% 且广告率>10% → 黄。
- 文件名 `monthly_loss_{起始月}{结束月}.xlsx`。

### 前 20 天对比下载

- 端点 `POST /statistics/monthly-loss-first20/download`。
- 仅支持单月，自动算上月，输出 Prev / Cur 两列。
- 文件名 `monthly_loss_first20_compare_{本月}.xlsx`。

## 接口说明

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/statistics/lossmakingorders_sync` | POST | 当前 no-op，仅返回 cache key |
| `/statistics/lossmakingorders_data` | POST | 按 `MonthlyLossOrder` 实时聚合查询 |
| `/statistics/monthly-loss/*` | CRUD | 月度全量 |
| `/statistics/monthly-loss-first20/*` | CRUD | 月度前 20 天 |
