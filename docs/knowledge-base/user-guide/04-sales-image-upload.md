# 商品图片上传

「销售 → 商品图片上传」管理商品图片的上传记录、同步队列与 CSV 批量导入，图片最终同步到外部图片服务。后端端点前缀 `/api/v1/image-uploads`。

## 页面入口

侧边栏：销售 → 商品图片上传（路由 `/sales/imageupload`）。

## 图片组记录字段

| 字段 | 含义 |
| --- | --- |
| imageUrl | 图片缩略图（40×40，可预览） |
| imageGroup | 图片组（对应 SKU） |
| status | 状态：`normal`正常(绿) / `warning`警告(黄) / `error`错误(红) |
| cloudPath | Cloud 路径 |
| log | 日志（显示最后一行，点击查看完整日志） |

## 筛选条件

图片组（模糊）、状态（正常 / 警告 / 错误）。分页 10/20/50/100。

## 新增 / 编辑图片组

点击「新增」或行内「编辑」→ 弹窗填写：

- **图片组**（必填）：对应 SKU。
- **Cloud 路径**（可空）。

新增时若图片组已存在则自动转为更新。编辑时校验图片组唯一性。

## 同步到外部服务

- 单条同步：行内「同步」或「重新同步」→ `POST /image-uploads/<id>/sync`。
- 批量同步：勾选多行 → 「批量同步」→ `POST /image-uploads/batch_sync`。
- 同步逻辑：先 `PUT` 更新外部服务，404 则 `POST` 创建。成功追加日志「已提交同步队列」，失败追加错误信息。
- **注意**：同步操作只追加日志，不修改 `status` 字段。`status` 需外部回调或手动维护。

## 同步队列

点击「同步队列」→ 弹窗展示外部服务的同步队列（`GET /image-uploads/queue`，透传外部服务数据）：

- 表格列：序号、图片组（sku）、路径（local_path）。
- 支持按图片组客户端过滤，客户端分页。

## CSV 批量导入

1. 点击「上传」选择 `.csv` 文件。
2. 编码要求：UTF-8（含 BOM）优先，GBK 兜底。
3. 必需列：`图片组` 或 `imageGroup`（两者任一）。
4. 可选列：`Cloud 路径` 或 `cloudPath`。
5. 导入后按 `image_group` upsert（存在则更新 cloud_path，不存在则创建）。
6. 导入完成弹窗询问「立即同步」或「稍后处理」。

## 下载

点击「下载」前端拼 CSV（带 BOM），列：图片组 / 状态 / Cloud 路径 / 日志最后一行。

## 图片上传接口

`POST /image-uploads/upload_image`：上传图片文件 → Pillow 压缩至 60×60 → 保存到 `media/uploads/` → 返回 URL 与路径。

## 外部服务

地址由 `IMAGE_SYNC_URL` 配置（默认 `https://cloud.hanlis.cn:9898`），`verify=False` 跳过 SSL 校验。

## 注意事项

- `ImageUploadViewSet` 权限为 `AllowAny`（无鉴权），与项目规范不一致，属已知风险点。
- 同步操作不更新 status，仅追加 log。
- 大量同步耗时较长，可在同步队列中观察进度。
