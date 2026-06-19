# Listing 标签管理

「销售 → Listing 标签」维护商品标签字典，标签可在 Listing 列表中筛选与批量打标。后端端点前缀 `/api/v1/sales/listing/tags`。

## 页面入口

侧边栏：销售 → Listing 标签（路由 `/sales/listing-tag`）。

## 标签列表字段

| 字段 | 含义 |
| --- | --- |
| tagName | 标签名称 |
| type | 标签类型 |
| createByName | 创建人 |
| modifyByName | 最后编辑人 |
| color | 颜色（色块展示） |
| status | 状态：`normal`正常(绿) / `creating`创建中(黄) / `modifying`修改中(黄) / `deleting`删除中(红) |
| createTime / updateTime | 创建 / 更新时间 |

## 筛选条件

标签名称（模糊）、标签类型（多选）、状态（多选：创建中 / 正常 / 修改中 / 删除中）、创建人（模糊）。

## 新增标签

1. 点击「新增标签」→ 弹窗填写：
   - **标签名称**：1-100 字符，必填。活跃状态下名称唯一。
   - **标签颜色**：颜色选择器 + 8 预设色块（红 / 橙 / 黄 / 绿 / 青 / 蓝 / 紫 / 灰），必填，默认蓝色 `#409eff`。
2. 确认后创建，初始状态 `creating`，自动生成 `global_tag_id`（格式 `TAG_{id}`）。

## 编辑标签

- **仅允许修改颜色**，标签名称不可改。
- `creating` / `deleting` 状态拒绝编辑。
- 编辑后状态强制置 `normal`。

## 删除标签

- 单条删除或勾选后批量删除（`POST /tags/batch-delete`）。
- 软删除，状态置 `deleting`。
- 已绑定该标签的 Listing 会触发批量解绑同步。

## 状态说明

| 状态 | 含义 | 触发方式 |
| --- | --- | --- |
| creating | 创建中 | 新建标签时初始状态 |
| normal | 正常 | 编辑颜色后自动转为正常 |
| modifying | 修改中 | 当前流程不会设置此状态 |
| deleting | 删除中 | 删除 / 批量删除时 |

> 后端有 `update_status` 接口但前端未接入状态切换 UI。状态实际转换路径为：create → creating →（编辑颜色）→ normal →（删除）→ deleting。

## 与领星同步

标签的新增、删除、与 Listing 的绑定 / 解绑，均通过 Celery 任务异步同步到领星：

- `listing_tag_sync_task`：每 5 秒处理「创建中 / 删除中」的标签。
- `listing_tag_modify_task`：每 5 秒处理 `ListingTagModifyQueue` 中的新增 / 移除绑定关系。

这两个任务是高频轮询（schedule=5s），队列里超过 4 秒未消费的消息自动丢弃，避免堆积。

## 标签选项接口

- `GET /tags/options`：返回 `status=normal` 的全量标签（供 Listing 列表打标使用）。
- `GET /tags/type-options`：返回去重的标签类型列表。
