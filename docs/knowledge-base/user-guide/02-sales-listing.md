# 商品 Listing 管理

「销售 → 商品 Listing」是管理在售商品的列表页，支持分页浏览、批量打标签、批量分类、编辑备注与查看核心指标。后端端点 `GET /api/v1/sales/product/listing`。

## 页面入口

侧边栏：销售 → 商品 Listing（路由 `/sales/listing`）。

## 列表字段

所有字段由后端完成格式化与枚举翻译，前端直接展示。

| 字段 | 含义 | 备注 |
| --- | --- | --- |
| image | 商品缩略图 | hover 放大 |
| seller_sku | MSKU | 与店铺 ID 复合唯一 |
| fnsku | FNSKU | |
| local_name / local_sku | 品名 / 本地 SKU | 拼接展示 |
| shop_name | 店铺名称 | |
| country_code | 国家 | |
| assort | 分类 | 来自 `LxListingMeta` |
| status | 上架状态 | `1`在售（绿）/ `0`停售（灰）/ 已删除（红） |
| asin / parent_asin | ASIN / 父 ASIN | 双击复制 |
| global_tags | 全局标签 | 标签列表 + 编辑图标 |
| item_name | 标题 | 双击复制 |
| fulfillment_channel_type | 配送方式 | FBM / FBA |
| seller_brand | 亚马逊品牌 | |
| price / landed_price / listing_price | 价格 / 总价 / 优惠价 | 带货币符号 |
| afn_fulfillable_quantity | FBA 可售库存 | |
| yesterday_volume | 昨日销量 | |
| total_volume | 7 天销量 | 字段名易误解，verbose_name 是「销量 7 天」 |
| fourteen_volume / thirty_volume | 14 天 / 30 天销量 | |
| average_seven/fourteen/thirty_volume | 7/14/30 日日均销量 | |
| yesterday/seven/fourteen/thirty_amount | 昨日/7/14/30 天销售额 | 带货币符号 |
| seller_rank | 大类排名 | |
| small_rank | 小类排名 | 从 JSON 数组取 rank 最小值 |
| seller_category | 大类类目 | |
| gross_profit_display | 毛利润 | 带货币符号，负数红色 |
| gross_margin_display | 毛利率 | 百分比，取 `LxOrderProfit` 最新一条 |
| review_num / last_star | 评论数 / 星级 | |
| open_date_display | 商品创建时间 | |
| on_sale_time | 开售时间 | |
| first_order_time | 首单时间 | |
| principal_info | 负责人 | 数组，显示 realname |
| remarks | 备注 | 双击编辑 |

> 数据源迁移遗留：`b2b_price` / `fba_fee` / `referral_fee` / 广告费系列 / `small_category` / `pair_type` 等字段当前为空或 0（`LxListingData` 迁移后未保留），页面上显示但暂不可用。

## 筛选条件

全部多选 + 全选交互：

| 筛选项 | 说明 | 可选值 |
| --- | --- | --- |
| 国家 | 多选，联动过滤店铺 | 系统已有站点 |
| 店铺 | 多选，下拉带搜索 | 按已选国家过滤 |
| Listing 状态 | 多选 | 在售(on) / 停售(off) / 已删除(deleted) |
| 配对状态 | 多选 | 已配对(paired) / 未配对(unpaired) |
| 分类 | 多选 | 饰品 / 普货 / 正常服装 / 情趣服装 / 其他 / 无 |
| 负责人 | 多选 | `ShopsAPI.getOwners()` |
| 新建时间 | 日期范围 | |
| 搜索 | 类型 + 关键词 | SKU(sku) / MSKU(seller_sku) / ASIN(asin) / 标签(tag) |

查询参数缓存到 localStorage。支持 Shift + 点击区间多选。

## 排序

| 排序字段 | 实际排序 |
| --- | --- |
| createTime | open_date_display |
| msku | seller_sku |
| skuName | local_sku, local_name |
| salesYesterday | yesterday_volume |
| rank | seller_rank |
| openTime | on_sale_time |
| firstOrderTime | first_order_time |

分页 50/100/200 条/页。

## 批量打标签

1. 勾选多行 → 点击「批量设置标签」。
2. 弹窗中搜索并选择标签（带颜色圆点）。
3. 点击「添加」为选中商品追加标签，或「删除」移除标签。
4. 确认后调 `POST /sales/product/listing/labels/upsert`，计算新旧标签差集，新增 / 移除的标签写入 `ListingTagModifyQueue` 由 Celery 异步同步到领星。

## 批量分类

1. 勾选多行 → 点击「批量设置分类」。
2. 选择目标分类（饰品 / 普货 / 正常服装 / 情趣服装 / 其他 / 无）。
3. 确认后调 `POST /sales/product/listing/assort/upsert`，按 `listing_data_id` 更新 `LxListingMeta.assort`。

## 编辑标签（单条）

点击标签列编辑图标 → 弹窗中增删标签 → 保存。同批量打标签逻辑。

## 编辑备注

双击备注列 → 弹出输入框 → 确认后调 `POST /sales/product/listing/remark/upsert`，写入 `LxListingMeta.remark_text`。

## 利润指标口径

- 数据源：`LxOrderProfit`，按 `listing_id` 查询，取每个 Listing 最新一条（按 `report_date` 降序）。
- `gross_profit`：毛利润金额，展示为 `$ 12.34` 格式。
- `gross_margin`：毛利率（0-1 小数），展示为 `12.34%`。
- 所有金额 / 百分比由后端格式化，前端不做换算。
