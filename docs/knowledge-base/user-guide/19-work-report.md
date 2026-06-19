# 工作汇报

「工作汇报」模块提供个人与团队的工作汇报统计，帮助管理层了解运营工作情况。后端端点前缀 `/api/v1/work-report`。

## 入口

侧边栏：工作汇报 → 我的汇报（路由 `/WorkReport/MyReport`）、工作汇报 → 团队汇报（路由 `/WorkReport/TeamReport`）。

## 我的汇报

- 展示当前用户提交的工作汇报列表。
- 点击单条查看详情（`ReportDrawer` 侧抽屉）。
- 字段以实际页面为准，通常包含汇报周期、内容摘要、关键指标等。

## 团队汇报

### 团队统计

`GET /work-report/team/stats`：汇总团队成员的汇报情况，管理者可按部门、时间范围筛选。

### 团队明细

`GET /work-report/team/stats/details`：查看具体成员的汇报详情。

### 列表与详情

- `GET /work-report/list`：汇报列表。
- `GET /work-report/detail`：单条汇报详情。

## 数据来源

工作汇报数据存储在后端 `work` 模型表（`api_v1/models/work.py`），由后端聚合统计后返回。
