# 广告工具（规则策略 / 分时调价）

「工具」菜单下提供两个广告自动化工具：广告规则策略与分时调价策略，用于按规则批量管理 SP 广告。

## 广告规则策略

### 入口

侧边栏：工具 → 广告规则策略（路由 `/tools/rule-strategy`）。

### 功能

- **规则组与规则管理**：将多条规则组织成规则组，按组应用到广告活动。
- **AutoRulePanel / AutoRuleDrawer**：规则的增删改与查看。
- **草稿箱**：`DraftBoxDrawer` / `DraftBoxPanel` 保存未生效的规则草稿，便于分批完善。
- **选择规则对话框**：`SelectRuleDialog` 从已有规则库挑选规则加入当前组。
- **RuleFormDialog**：规则表单。

### 后端端点

`/api/v1/ads/rule-strategy/*`：规则（`LxAdRule`）与规则组（`LxAdRuleGroup`）的 CRUD。

### 执行

规则配置完成后，通过「运行」按钮触发：

1. `POST /api/v2/ads/optimization-strategy/run/`：触发 `optimization_strategy_task`（匹配规则到目标）。
2. `POST /api/v2/ads/optimization-strategy/execute/`：触发 `optimization_execution_task`（执行匹配到的优化动作）。

两个任务均在 `single_thread_queue`（串行队列），加三层锁防御防止重复执行。任务运行中再次点击返回 409（`B0001`）。

## 分时调价策略

### 入口

侧边栏：工具 → 分时调价策略（路由 `/tools/ad-time-strategy`）。

### 功能

- `BiddingStrategyForm`：配置按时段（小时粒度）调整竞价百分比的策略。
- 策略绑定到广告活动后，系统按命中时段自动调整竞价。
- 支持按店铺、负责人、品类、标签等维度筛选适用范围。

### 后端端点

- `/api/v1/ads/time-pricing-strategy/*`：分时调价策略 CRUD（`LxTimePricingStrategy`）。
- `/api/v1/ads/time-pricing-strategy/shops`、`/managers`、`/assorts`、`/labels`：下拉选项。

### 执行

- 命中记录由 `ad_time_pricing_task`（`single_thread_queue`）生成并落 `ad_time_pricing_hit` 表。
- 实际调价由 `time_pricing_task`（`single_thread_queue`）执行。
- 两个任务均加锁防重复。
- 手动触发：`POST /api/v2/ads/time-pricing/execute/`。

## 其他广告执行操作

| 操作 | 触发接口 | 任务 | 队列 |
| --- | --- | --- | --- |
| 竞价调整 | `POST /api/v2/ads/bid-adjustment/run/` | `bid_adjustment_task` | single_thread_queue |
| 活动调整 | `POST /api/v2/ads/campaign-adjustment/run/` | `campaign_adjustment_task` | single_thread_queue |

## 注意事项

- 工具类任务调有 QPS 限制的领星 API，必须串行执行，禁止并发。
- 任务运行中再次点击「运行」会返回 409（任务正在执行中），需等待完成。
- 策略改动后需重新触发匹配才会生效。
