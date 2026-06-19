# api_v1 接口总览

`api_v1` 承载业务 CRUD 接口，路由在 `backend-master/api_v1/urls.py`，根路径 `/api/v1/`（兼容 `/prod-api/` 别名）。统一响应 `{code, data, msg}`，成功 `code="00000"`；分页 `{total, list}`。

## 认证接口（`/auth/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/auth/login` | POST | 登录，返回 access_token / refresh_token |
| `/auth/refresh-token` | POST | 刷新 token |
| `/auth/logout` | POST | 登出 |
| `/auth/captcha` | GET | 图形验证码 |
| `/auth/sso-session` | GET | SSO session 状态 |

## 用户接口（`/users/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/users/me` | GET | 当前用户信息 + roles + perms（岗位聚合） |
| `/users/page` | GET | 用户分页（keywords/status/deptId/createTime） |
| `/users/<id>/form` | GET | 编辑回填 |
| `/users` | POST/PUT | 新增 / 修改（触发 NC 同步） |
| `/users/<id>/password/reset` | PUT | 重置密码（默认 123456） |
| `/users/profile` | GET/PUT | 个人资料 |
| `/users/password` | PUT | 修改密码（校验原密码） |
| `/users/avatar` | POST | 上传头像（≤5MB，压缩 512×512） |
| `/users/upload-image` | POST | 通用图片上传（≤2MB，生成缩略图） |
| `/users/options` | GET | 启用用户下拉 |
| `/users/mobile/code` | POST | 发送手机验证码 |
| `/users/mobile` | PUT | 绑定手机 |
| `/users/email/code` | POST | 发送邮箱验证码 |
| `/users/email` | PUT | 绑定邮箱 |

UserSerializer 输出：`id, username, nickname, mobile, avatar, email, deptId, deptName, positionId, positionName, adminLevel, adminLevelLabel, gender, status, createTime`。

## 销售 Listing 接口

### Listing（`/sales/product/listing`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/sales/product/listing` | GET | 分页查询（country/shopId/categoryType/pairStatus/listingStatus/owner/keywords/searchType/sort/order） |
| `/sales/product/listing/labels/upsert` | POST | 批量更新标签（写 `ListingTagModifyQueue`） |
| `/sales/product/listing/assort/upsert` | POST | 批量更新分类（`LxListingMeta.assort`） |
| `/sales/product/listing/remark/upsert` | POST | 单条备注 upsert |

### Listing 标签（`/sales/listing/tags`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/sales/listing/tags` | GET/POST | 列表 / 新增（初始 creating） |
| `/sales/listing/tags/<pk>` | GET/PUT/DELETE | 详情 / 编辑（仅颜色）/ 软删除 |
| `/sales/listing/tags/batch-delete` | POST | 批量软删除 |
| `/sales/listing/tags/<pk>/status` | PUT | 更新状态 |
| `/sales/listing/tags/type-options` | GET | 类型去重列表 |
| `/sales/listing/tags/options` | GET | status=normal 全量选项 |

### 图片上传（`/image-uploads`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/image-uploads/page` | GET | 分页（imageGroup/status） |
| `/image-uploads/<pk>/form` | GET | 单条详情 |
| `/image-uploads` | POST/PUT | 新增 / 更新（唯一性校验） |
| `/image-uploads/<pk>` | DELETE | 删除（pk 支持逗号分隔） |
| `/image-uploads/<pk>/sync` | POST | 单条同步 |
| `/image-uploads/batch_sync` | POST | 批量同步 |
| `/image-uploads/import_csv` | POST | CSV 导入（UTF-8 BOM / GBK） |
| `/image-uploads/queue` | GET | 外部同步队列 |
| `/image-uploads/upload_image` | POST | 图片上传（Pillow 60×60） |

> ⚠️ `ImageUploadViewSet` 权限为 `AllowAny`。

## 广告接口（`/ads/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/ads/campaigns` | POST | SP 广告活动列表（分页 + 指标 + 汇总 summary） |
| `/ads/campaigns/detail` | GET | 单条活动基础信息 |
| `/ads/options` | POST | 店铺 / 国家 / 竞价策略下拉 |
| `/ads/sku-options` | POST | SKU/ASIN 搜索下拉 |
| `/ads/enum-labels` | POST | 枚举标签映射（按 module） |
| `/ads/portfolios/options` | POST | 广告组合下拉 |
| `/ads/ad-groups` | POST | 广告组列表与聚合 |
| `/ads/ads` | POST | 投放列表与聚合 |
| `/ads/auto-targeting` | POST | 自动定向列表 |
| `/ads/auto-negative-targeting` | POST | 否定商品列表 |
| `/ads/keywords` | POST | 关键词列表 |
| `/ads/negative-keywords` | POST | 否定关键词列表 |
| `/ads/time-pricing-strategy/*` | — | 分时调价策略 CRUD + shops/managers/assorts/labels 下拉 |
| `/ads/rule-strategy/*` | — | 规则与规则组 CRUD |

指标字段（所有列表通用）：`adsSales, adsSalesPercent, directSales, adsOrders, directOrders, adsVolume, adsOrderPrice, acos, roas, cvr, impressions, impressionsPercent, clicks, clicksPercent, ctr, cpc, spends, spendsPercent, cpa`。枚举标签 module：`campaign_status, service_status, bidding_strategy, campaign_type, negative_match_type, keyword_match_type, negative_type, tags`。

## 统计接口（`/statistics/*`）

| 端点 | 方法 | 说明 |
| --- | --- | --- |
| `/statistics/lossmakingorders_sync` | POST | **当前 no-op**，仅返回 cache key |
| `/statistics/lossmakingorders_data` | POST | 按 `MonthlyLossOrder` 实时聚合查询 |
| `/statistics/monthly-loss` | GET/POST | 月度全量 CRUD |
| `/statistics/monthly-loss/<id>/form` | GET | 编辑回填 |
| `/statistics/monthly-loss/download` | GET/POST | 导出 XLSX（pandas 聚合 + 着色） |
| `/statistics/monthly-loss-first20/*` | — | 月度前 20 天，结构对称 |

`MonthlyLossSerializer` 输出：`id, image_url, msku, asin, parent_asin, store_country, product_name_sku, gross_profit, gross_margin, gross_margin_display, net_gross_margin, net_gross_margin_display, return_rate, return_rate_display, refund_amount_rate, refund_amount_rate_display, total_stock_fee, spend, spend_rate, spend_rate_display, sales, owner, month`。

亏损规则：cond1=毛利<0、cond2=退款率>0.15、cond3=广告费率>0.10。rule1=OR、rule2=AND、rule3=cond1+cond2+NOT cond3、rule4=cond1+cond3+NOT cond2。

## 系统管理接口

| 板块 | 端点 | 说明 |
| --- | --- | --- |
| 菜单 | `/menus/routes` | 动态路由树（超管全量 / 其他岗位 + 向上补全） |
| 菜单 | `/menus`、`/menus/tree`、`/menus/options` | 列表 / 树 / 下拉 |
| 菜单 | `/menus/<id>/form`、`/menus/<id>` | 编辑回填 / CRUD |
| 部门 | `/depts`、`/depts/tree`、`/depts/options` | 树 / CRUD / 下拉 |
| 岗位 | `/positions/page`、`/positions/options` | 分页 / 下拉 |
| 岗位 | `/positions`、`/positions/<id>/form` | CRUD |
| 岗位 | `/positions/<id>/menuIds`、`/positions/<id>/menus` | 查询 / 更新菜单权限 |
| 字典 | `/dicts/page`、`/dicts`、`/dicts/<id>/form` | 类型 CRUD |
| 字典 | `/dicts/<code>/items`、`/items/page`、`/items/options` | 字典项 CRUD / 下拉 |
| 配置 | `/configs/page`、`/configs`、`/configs/<id>/form` | CRUD |
| 配置 | `/configs/refresh-cache` | **占位实现**，直接返回成功 |
| 日志 | `/logs/page` | 操作日志分页（UA/IP 后端解析） |
| 日志 | `/logs/visit-trend` | 最近 7 天 PV/UV/IP 趋势 |
| 日志 | `/logs/visit-stats` | 今日 / 累计统计 + 同比增长率 |
| 通知 | `/notices/page`、`/notices/<id>/form` | 管理端列表 / 回填 |
| 通知 | `/notices`、`/notices/<id>/publish`、`/notices/<id>/revoke` | CRUD / 发布 / 撤回 |
| 通知 | `/notices/<id>/read`、`/notices/read-all`、`/notices/my-page` | 已读 / 全部已读 / 我的公告 |
| 通知 | `/notices/export` | 导出 XLSX |
| NC | `/nc/folder-tree/*` | 文件夹树 / 权限规则 |

## 其他接口

| 端点 | 说明 |
| --- | --- |
| `/shops/options`、`/shops/owners` | 店铺与负责人下拉 |
| `/crawler/*` | 采集类目 / 配置 / 日志（多数开放接口） |
| `/work-report/*` | 工作汇报统计 |
| `/weather/live` | 天气实况（高德 API） |
| `/codegen/*` | 代码生成器 |
