# 首页仪表盘

登录后默认进入首页仪表盘。**重要**：当前仪表盘大部分组件为硬编码 Mock 数据，尚未接入真实后端 API，仅天气为真实数据。以下如实描述现状。

## 仪表盘组成

| 组件 | 数据状态 | 说明 |
| --- | --- | --- |
| DashboardHeader | 真实（天气） | 问候语 + 天气实况 + 静态社交链接 |
| InventoryOverview | Mock | 库存概览，占位数据 |
| RealTimeAds | Mock | 实时广告，占位数据 |
| RealTimeSales | Mock | 实时销量，占位数据 |
| ReplenishmentRecommendation | Mock | 补货建议，占位数据 |
| ReviewStatistics | Mock | 评论统计，占位数据 |
| SettlementProfit | Mock | 结算利润，占位数据 |
| StorePerformance | Mock | 店铺绩效，占位数据 |

> 当前仪表盘**没有**店铺切换、日期范围选择、刷新控制功能（这些在 DashboardHeader 中均未实现）。

## DashboardHeader（真实数据）

- **问候语**：按时段显示（6-8 晨起、8-12 上午好、12-18 下午好、18-24 晚上好、其余晚安），带用户昵称。
- **天气实况**：调用 `GET /api/v1/weather/live`（高德天气 API，默认城市 440605 佛山南海区），展示「{city} {weather}，气温{temperature}℃，{winddirection}风{windpower}级」。
- **右侧**：仓库 / 文档 / 视频三个静态图标区（Gitee / GitHub / 掘金 / B 站），当前链接为空。

## InventoryOverview（库存概览，Mock）

- 顶部切换：数量 / 货值。
- 左侧环形饼图：FBA 仓 / 海外仓 / 本地仓 / AWD 仓四段（当前均 0）。
- 图例：在库 / 在途（当前显示 `----`）。
- 右侧表格：在库 / 在途两行 × 四仓列（当前均为 `-`）。

## RealTimeAds（实时广告，Mock）

5 个指标卡（当前占位）：广告花费、广告销售额、广告订单量、ACOS、ACoAS。每个含昨日对比值。

- ACOS = 广告花费 / 广告销售额。
- ACoAS = 广告花费 / 总销售额。

## RealTimeSales（实时销量，Mock）

- 时区切换：今日 / 昨日 / 近 24h。
- 5 个指标卡（当前占位）：销量、销售额、订单量、平均售价、取消订单数。

## ReplenishmentRecommendation（补货建议，Mock）

- 筛选：仅看我关注（复选框）、补货类型（ASIN / 父 ASIN / MSKU / SKU）。
- 表格列：紧急程度 / 补货类型 / 正常 / 加急 / 断货风险。
- 3 行：需采购、需本地发货、需海外仓发货（当前均 0）。
- **后端无对应 service**，推荐逻辑尚未实现。

## ReviewStatistics（评论统计，Mock）

两个分区：review（蓝边）+ feedback（橙边），各含：

- 今日新增、迷你柱状图（15 天趋势）、中差评、删评、改评。

## SettlementProfit（结算利润，Mock）

- 时间范围：昨日 / 前 7 天 / 前 30 天 / 自定义。
- 4 个指标卡：平台收入、平台支出、毛利润、毛利率（当前显示 `------`）。
- 图表：7 天柱状图 + 4 段饼图（广告 / 采购 / 物流 / 佣金，当前均 0）。

## StorePerformance（店铺绩效，Mock）

7 项绩效指标（当前占位）：

| 指标 | 目标值 |
| --- | --- |
| FBA 订单缺陷率 | < 1% |
| FBM 订单缺陷率 | < 1% |
| 发票缺陷率 | < 5% |
| 政策合规性 | < 0 |
| 迟发率 | < 4% |
| 预配送取消率 | < 2.5% |
| 有效追踪率 | > 95% |

## 天气 API

`GET /api/v1/weather/live`，后端 `WeatherViewSet.live`，走高德 API（`AMAP_KEY` / `AMAP_CITY` / `AMAP_BASE` 配置）。
