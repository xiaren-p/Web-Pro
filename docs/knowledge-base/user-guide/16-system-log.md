# 操作与访问日志

「系统 → 日志」记录用户操作与访问行为，供审计与趋势分析。后端端点前缀 `/api/v1/logs`。

## 页面入口

侧边栏：系统 → 日志（路由 `/system/log`）。

## 日志列表

### 表格列

| 列 | 说明 |
| --- | --- |
| 操作时间 | createTime |
| 操作人 | operator |
| 日志模块 | module |
| 日志内容 | content（= action） |
| IP 地址 | ip |
| 地区 | region（后端解析：本机 / 内网 / 未知） |
| 浏览器 | browser（后端解析：Edge / Opera / Chrome / Firefox / Safari） |
| 终端系统 | os（后端解析：Windows / Android / iOS / iPadOS / macOS / Linux） |
| 执行时间(ms) | executionTime（= elapsed_ms） |

UA / IP 在后端解析为可读字符串，前端直接渲染。

### 搜索

日志内容关键字（匹配 module / action / operator / ip）、操作时间范围。

### 说明

- 日志列表纯只读查询，无新增 / 编辑 / 删除。
- **注意**：当前业务操作写日志调用已移除（user_view 等模块可见 `write_log removed` 注释），日志页数据来源取决于历史数据或其他模块是否写入。

## 访问趋势

`GET /logs/visit-trend`：最近 7 天访问趋势，按日聚合：

- PV = 操作日志总条数。
- UV = 去重操作人数。
- IP = 去重 IP 数。
- 缺失日期补 0，日期格式 YYYY-MM-DD，直接喂 ECharts。

## 访问统计

`GET /logs/visit-stats`：今日 / 累计统计与同比增长率：

- `todayUvCount` / `totalUvCount` / `uvGrowthRate`
- `todayPvCount` / `totalPvCount` / `pvGrowthRate`
- 昨日为 0 今日有值视为 100%，均为 0 视为 0%。

访问趋势 / 统计接口由首页仪表盘或其他统计页消费，日志页本身未调用。
