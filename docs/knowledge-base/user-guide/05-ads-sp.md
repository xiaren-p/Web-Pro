# SP 广告管理

「广告 → SP 广告」是管理亚马逊 Sponsored Products 广告的核心模块，包含广告列表页与多 Tab 详情页，覆盖活动、广告组、投放、关键词、否定词、自动定向全维度数据，并支持通过 Excel 批量创建广告并提交到领星。

## 列表页

### 入口

侧边栏：广告 → SP 广告（路由 `/ads/sp`）。后端端点 `POST /api/v1/ads/campaigns`。

### 筛选条件

| 筛选项 | 说明 | 可选值 |
| --- | --- | --- |
| 国家 | 多选，选后联动过滤店铺 | 系统已有站点去重 |
| 店铺 | 多选，下拉带搜索 | `LxAdsProfile.profile_id` |
| 日期范围 | 默认近 30 天 | `date_start` / `date_end` |
| 广告组合 | 多选，含「未设置」 | `portfolio_id`，`-1`=未设置 |
| ASIN/MSKU 查询 | 选搜索类型 + 输入 | `sku`=按 ASIN/MSKU，`parent_asin`=按父 ASIN |
| 状态 | 活动状态 | `enabled`已启用 / `paused`已暂停 / `archived`已归档 |
| 服务状态 | 投放服务状态 | 见下文服务状态枚举 |
| 竞价策略 | 竞价方式 | `legacyForSales`只降低 / `autoForSales`提高和降低 / `manual`固定 / `ruleBased`基于规则 |
| 活动标签 | 多选 | 商品标签动态去重 |
| 负责人 | 多选 | uid 列表 |
| 活动名称 | 模糊搜索 | 同时匹配活动名、活动 ID、店铺 sid |
| 广告类型 | SP/SB/SD | `sponsoredProducts` 等 |
| 只看超预算 | 勾选后追加 `CAMPAIGN_OUT_OF_BUDGET` | — |

### 指标区（顶部汇总卡）

从 `summary` 汇总行取值，默认置顶 4 个，可自选最多 4 个置顶，其余折叠：

| 指标 | 含义 | 计算口径 |
| --- | --- | --- |
| clicks | 点击（总和） | `Sum(clicks)` |
| spends | 花费（总和） | `Sum(cost)`，带货币符号 |
| adsSales | 广告销售额（总和） | `Sum(sales)`，带货币符号 |
| acos | ACoS（平均） | `cost / sales × 100%` |
| impressions | 曝光量（总和） | `Sum(impressions)` |
| ctr | CTR（平均） | `clicks / impressions × 100%` |
| cpc | CPC（平均） | `cost / clicks`，带货币符号 |
| cvr | CVR（平均） | `orders / clicks × 100%` |
| roas | ROAS（总和） | `sales / cost` |
| directSales | 直接销售额（总和） | `Sum(same_sales)` |
| adsOrders | 广告订单（总和） | `Sum(orders)` |
| directOrders | 直接订单（总和） | `Sum(same_orders)` |
| cpa | CPA（平均） | `cost / orders`，带货币符号 |
| adsOrderPrice | 广告笔单价（平均） | `sales / orders`，带货币符号 |
| adsVolume | 广告销量（总和） | `Sum(units)` |
| impressionsPercent | 曝光占比 | `impressions / 全量 × 100%` |
| clicksPercent | 点击占比 | `clicks / 全量 × 100%` |
| spendsPercent | 花费占比 | `spends / 全量 × 100%` |
| adsSalesPercent | 广告销售额占比 | `sales / 全量 × 100%` |

> `indirectSales` / `indirectOrders` / `dpv` / `brandedSearch` 后端 summary 未提供，前端显示 `-`。

### 表格列

**固定左列**：选择框、有效（state 开关）、类型（SP + `[自动]`/`[手动]`）、店铺/国家、广告活动名（链接到详情页）。

**动态列**（可通过列配置抽屉控制可见性，默认全开）：

| 分类 | 列 | 说明 | 可排序 |
| --- | --- | --- | --- |
| 设置 | 服务状态 | 中文标签 + 徽标颜色 | 否 |
| 设置 | 竞价策略 | 中文 | 否 |
| 设置 | 广告组合 | 组合名 | 否 |
| 设置 | 预算 | 每日预算 | 是 |
| 设置 | 开始日期 | | 是 |
| 设置 | 标签 | 商品标签 | 否 |
| 转化 | IS | 搜索首页份额（列表页固定 `---`） | 是 |
| 转化 | 广告销售额 / 占比 | | 是 |
| 转化 | 直接销售额 | | 是 |
| 转化 | 广告订单 / 直接订单 | | 是 |
| 转化 | ACoS / ROAS / CVR | | 是 |
| 转化 | 广告笔单价 / 广告销量 | | 是 |
| 业绩 | 曝光量 / 曝光% | | 是 |
| 业绩 | 点击 / 点击% | | 是 |
| 业绩 | CTR / CPC | | 是 |
| 业绩 | 花费 / 花费% | | 是 |
| 业绩 | CPA | | 是 |

**固定右列**：分析按钮。

**染色规则**：ACoS < 10% 绿、> 30% 红；ROAS / CVR > 0 绿、< 0 红。默认按曝光量降序。分页 25/50/100/250 条/页。

### 服务状态枚举

| 原始值 | 中文 | 颜色 |
| --- | --- | --- |
| `CAMPAIGN_STATUS_ENABLED` | 投放中 | 绿 |
| `CAMPAIGN_PAUSED` | 广告活动已暂停 | 黄 |
| `CAMPAIGN_ARCHIVED` | 广告活动已归档 | 红 |
| `CAMPAIGN_OUT_OF_BUDGET` | 超预算 | 红 |
| `CAMPAIGN_INCOMPLETE` | 不完整 | 红 |
| `ADVERTISER_PAYMENT_FAILURE` | 广告账号付款失败 | 红 |
| `LANDING_PAGE_NOT_AVAILABLE` | 着陆页失效 | 红 |
| `PORTFOLIO_OUT_OF_BUDGET` | 超预算（组合） | 红 |
| `AD_GROUP_STATUS_ENABLED` / `AD_STATUS_LIVE` / `TARGETING_CLAUSE_STATUS_LIVE` | 投放中 | 绿 |
| `AD_GROUP_PAUSED` / `AD_PAUSED` / `TARGETING_CLAUSE_PAUSED` | 已暂停 | 黄 |
| `AD_GROUP_ARCHIVED` / `AD_ARCHIVED` / `TARGETING_CLAUSE_ARCHIVED` | 已归档 | 红 |
| `NOT_BUYABLE` | 商品不可售 | 红 |
| `INELIGIBLE` | 不符合资格 | 红 |
| `AD_POLICING_SUSPENDED` | 违规暂停 | 红 |
| `AD_POLICING_PENDING_REVIEW` | 广告审核中 | 黄 |

### 货币格式化

- 货币符号来自 `LxAdsProfile.currency_code` → `LxExchangeRate.icon`。
- 列表页涉及多货币时统一换算到 USD 参考货币后做占比；详情页单一货币无换算。
- 所有金额由后端格式化为带符号字符串（如 `€123.45`），前端直接展示。

## 详情页（多 Tab）

点击列表活动名进入详情页（路由 `/ads/sp/detail`），通过 `GET /ads/campaigns/detail` 加载面包屑（活动名、投放类型、状态、类型）。Tab 切换持久化到 localStorage。

### Tab「广告组」（`AdGroupsPanel`）

后端 `POST /ads/ad-groups`。

| 字段 | 含义 |
| --- | --- |
| ad_group_id | 广告组 ID |
| name | 广告组名称 |
| state | 状态（enabled/paused/archived） |
| service_status_label | 服务状态中文 |
| portfolio_name | 广告组合名 |
| campaign_name / campaign_state | 父活动名 / 状态 |
| default_bid | 默认竞价 |
| product | 该组下广告商品数量 |
| created_at | 创建时间 |
| + 全套指标字段 | 同列表页指标 |

筛选：日期范围、状态、广告组名模糊。操作：勾选、列配置。默认竞价可编辑输入框（TODO 占位，未联调后端）。

### Tab「广告」（`AdsPanel`）

后端 `POST /ads/ads`。

| 字段 | 含义 |
| --- | --- |
| ad_id | 商品广告 ID |
| asin / msku | ASIN / MSKU |
| image_url | 商品图片（悬浮预览大图） |
| title | 商品标题 |
| price | 价格 |
| rating / reviews | 星级 / 评分数 |
| stock | 可售库存 |
| state / service_status* | 状态 / 服务状态 |
| portfolio_name | 广告组合 |
| campaign_name / adgroup_name | 父活动 / 父广告组 |
| created_at | 创建时间 |
| + 全套指标字段 | |

筛选：日期范围、状态、ASIN 或 MSKU 模糊。商品标签筛选为占位未实现。

### Tab「投放」— 按投放类型分流

**MANUAL 手动 → 关键词面板（`KeywordPanel`）**，后端 `POST /ads/keywords`：

| 字段 | 含义 |
| --- | --- |
| keyword_id | 关键词 ID |
| keyword_text | 关键词文本 |
| match_type / match_type_label | 匹配类型：`exact`精准 / `broad`广泛 / `phrase`词组 |
| bid | 竞价 |
| state / service_status* | 状态 / 服务状态 |
| bidding_strategy | 父活动竞价策略 |
| portfolio_name | 广告组合 |
| campaign_name / adgroup_name | 父活动 / 父广告组 |
| created_at | 创建时间 |
| + 全套指标字段 | |

筛选：日期范围、状态、匹配类型、关键词文本模糊。分析按钮打开抽屉展示花费 / 广告销售额 / 广告订单 / ACoS。

**AUTO 自动 → 自动定向面板（`AutoTargetingPanel`）**，后端 `POST /ads/auto-targeting`：

| 字段 | 含义 |
| --- | --- |
| target_id | 商品定位 ID |
| targeting_text | 自动定向组名 |
| state / service_status* | 状态 / 服务状态 |
| bid | 竞价（可编辑，TODO 占位） |
| bidding_strategy | 父活动竞价策略 |
| portfolio_name | 广告组合 |
| campaign_name / adgroup_name | 父活动 / 父广告组 |
| created_at | 创建时间 |
| + 全套指标字段 | |

筛选：日期范围、状态。AUTO 广告的 4 个自动定向组：紧密匹配 / 同类匹配 / 宽泛匹配 / 关联匹配。

### Tab「否定投放」— 按投放类型分流

**MANUAL → 否定关键词面板（`NegativeKeywordPanel`）**，后端 `POST /ads/negative-keywords`：

| 字段 | 含义 |
| --- | --- |
| keyword_id | 否定投放 ID |
| keyword_text | 否定关键词文本 |
| match_type / match_type_label | `negativeExact`否定精准 / `negativePhrase`否定词组 |
| state | 状态（enabled/archived，无 paused） |
| + 否定指标 | 仅 spends / adsSales / adsOrders / acos |

筛选：日期范围、状态、匹配类型、否定关键词模糊。

**AUTO → 否定容器（`AutoNegativePanel`）含两个子 Tab**：

- 子 Tab「否定关键词」→ 同上 `NegativeKeywordPanel`。
- 子 Tab「否定商品」（`AutoNegativeTargetingPanel`），后端 `POST /ads/auto-negative-targeting`：

| 字段 | 含义 |
| --- | --- |
| target_id | 否定投放 ID |
| state | 状态（enabled/archived） |
| exp_type / exp_type_label | `negativeAsin`否定 ASIN / `negativeBrand`否定品牌 |
| exp_value | 否定内容（ASIN 或品牌名） |
| portfolio_name / campaign_name / adgroup_name | 归属信息 |
| + 否定指标 | |

筛选：日期范围、状态、否定类型、ASIN 或品牌模糊。

### Tab「用户搜索词」

当前为占位未实现。

## 广告创建 / 上传

点击「上传广告」打开 `AdUploadDialog`（两步式弹窗：表单 → 解析结果）。

### 上传表单字段

| 字段 | 控件 | 说明 |
| --- | --- | --- |
| 文件 | 拖拽上传 | 仅 `.xlsx`，最大 20MB，限 1 个 |
| 广告类型 | 单选 | `all`都创建 / `auto`仅自动 / `manual`仅手动（默认 all） |
| 投放国家模式 | 开关 | 开=按表需求（自动读 Excel 站点子表）/ 关=手动指定 |
| 国家 | 卡片网格 | DE/UK/FR/IT/ES/NL/SE/PL/BE/US/CA/MX/BR/JP/AU/SA/AE/IN/SG/TR |
| 每日预算 | 数字输入 | 默认 1，min 0.01 |
| 广告组默认竞价 | 数字输入 | 默认 0.12 |
| PL 每日预算 | 数字输入 | 默认 2（条件展示） |
| SE 每日预算 | 数字输入 | 默认 9（条件展示） |
| 紧密匹配竞价 | 数字输入 | 默认 0.12 |
| 同类匹配竞价 | 数字输入 | 默认 0.10 |
| 宽泛匹配竞价 | 数字输入 | 默认 0.10 |
| 关联匹配竞价 | 数字输入 | 默认 0.10 |

### Excel 格式要求

- 主表 `Sheet1` 必需列：店铺名、广告活动名称、SKU。
- 各国家站点子表（子表名 = 两位大写国家代码，如 DE/UK）含关键词块：`START <活动名>` → 表头行（关键词、月搜索量）→ 数据行 → `END`。
- 活动名自动拼接 ` AUTO` / ` MANU` 后缀区分类型。

### 关键词匹配规则

- 单个单词（仅字母 / 数字 / 下划线 / 横杠）或月搜索量 > 10000 → `exact`（精准匹配）。
- 其余 → `broad`（广泛匹配）。
- 关键词 > 10 个单词跳过（Amazon 限制）。

### 提交流程

1. 前端 `POST /api/v2/ads/upload/`（multipart，含文件 + 竞价参数 + 国家预算 JSON）。
2. 后端解析 Excel → 按（店铺 × 活动 × 国家）三维展开 → 校验合规 → `PENDING` 状态落库。
3. 返回成功 / 失败 / 跳过统计与失败明细。
4. 队列记录由提交服务异步处理（需手动触发提交，见下文）。

## 广告上传队列

点击「上传队列」打开 `AdQueueDrawer`，后端 `GET /api/v2/ads/queue/`。

### 队列状态

| 值 | 名称 | 颜色 |
| --- | --- | --- |
| 0 | 失败 | 红 |
| 1 | 队列中 | 蓝 |
| 2 | 成功 | 绿 |
| 3 | 异常 | 橙 |

`PENDING`（队列中）始终置顶，其余按创建时间倒序。普通用户仅看自己的记录，管理员可查看所有人的。

### 操作

- **重试**：将 `FAILED` / `ANOMALY` 重置为 `PENDING`，断点续跑（跳过已完成步骤）。
- **批量删除**：选中后批量删除。
- **手动提交**：`POST /api/v2/ads/submit/` 同步触发批量提交到领星。

### 提交机制（重要）

> 提交任务 `submit_pending_campaigns_task` 虽已注册 Celery 路由，但**未在 Beat 调度中注册**，不会自动定时提交。实际提交路径是 HTTP `/api/v2/ads/submit/` **手动同步触发**。提交时若任务已在跑则返回 409。

提交到领星分 4 步（每步完成立即落库 `step_ids`，支持断点续跑）：

1. 创建广告活动（`campaign_id`）。
2. 创建广告组（`ad_group_id`，名称固定为当天日期 `DD/MM/YYYY`）。
3. 创建广告投放（每个 SKU 一条 `productAdId`）。
4. 创建关键词（仅 MANUAL，JSON 格式提交）。

## 指标聚合方式

统一策略「1 次 SQL GROUP BY + Python 两轮遍历」：

- 第一轮：DB 端 `GROUP BY <id>` + `Sum()` 聚合，Python 累加得到全量合计作为百分比分母。
- 第二轮：逐行计算 ACoS / ROAS / CVR / CTR / CPC / CPA / 笔单价及各占比。
- 否定投放仅含花费 / 销售额 / 订单 / ACoS（无曝光 / 点击类）。
