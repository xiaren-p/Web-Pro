# 图片同步队列模块：外部 API 依赖移除 → 内部模型

## Context（背景）

「销售 → 商品图片上传」板块中的「图片同步队列」模块，目前后端 `ImageUploadViewSet` 的三个 action（`queue` / `sync` / `batch_sync`）全部依赖外部 API `https://cloud.hanlis.cn:9898/update_image/sku`：

- `queue`：`GET` 外部 API 拉取同步队列数据，前端再做 `sku→imageGroup`、`local_path→cloudPath` 字段映射 + 客户端分页过滤（违反"数据出口最终成形原则"）。
- `sync` / `batch_sync`：`PUT/POST` 外部 API 推送 `{sku, local_path, status:1}`。

目标：**完全移除外部 API 依赖**，新建内部 `ImageSyncQueue` 模型承载同步队列，sync 改为 upsert 内部记录，queue 改为查询内部表并后端分页。前端移除字段映射与客户端分页。

用户已确认：① 完全移除外部 API ② 新建独立模型。

---

## 涉及文件清单

### 后端（`backend-master/`）

| 操作 | 文件路径 | 说明 |
| ---- | -------- | ---- |
| 新建 | `api_v1/models/file/image_sync_queue.py` | `ImageSyncQueue` 模型（表 `sys_image_sync_queue`） |
| 改 | `api_v1/models/file/__init__.py` | 导出 `ImageSyncQueue` |
| 改 | `api_v1/models/__init__.py` | 导出 `ImageSyncQueue`、`ImageSyncStatus` |
| 新建 | `api_v1/serializers/image_sync_queue.py` | `ImageSyncQueueSerializer`（camelCase 输出） |
| 改 | `api_v1/serializers/__init__.py` | 导出 `ImageSyncQueueSerializer` |
| 新建 | `api_v1/services/lingxing/image_sync_queue_service.py` | 同步队列业务逻辑（upsert / 批量 upsert / 分页查询） |
| 改 | `api_v1/services/lingxing/__init__.py` | 导出 service 函数 |
| 改 | `api_v1/views/lingxing/sales/listing/image_view.py` | 重写 `queue`/`sync`/`batch_sync` 三个 action，移除 `requests` 外部调用 |
| 改 | `backend_master/settings.py` | 移除 `IMAGE_SYNC_URL` 配置（第 42、82 行） |

### 前端（`vue3-element-admin-master/`）

| 操作 | 文件路径 | 说明 |
| ---- | -------- | ---- |
| 改 | `src/api/imageUpload/index.ts` | `getQueue` 改为支持分页参数，返回 `PageResult`；新增 `ImageSyncQueueVO` 类型 |
| 改 | `src/views/sales/imageupload/components/SyncQueueDialog.vue` | 移除前端字段映射与客户端分页/过滤，改用后端分页 |

### 文档（`docs/knowledge-base/`）

| 操作 | 文件路径 | 说明 |
| ---- | -------- | ---- |
| 改 | `user-guide/04-sales-image-upload.md` | 更新同步队列描述（内部模型替代外部服务）、移除外部服务章节 |

---

## 详细实现

### Task 1：新建 `ImageSyncQueue` 模型

**文件**：`api_v1/models/file/image_sync_queue.py`

遵循 CLAUDE.md §5.1.y Model 优雅书写铁律（模块顶部 docstring、类 docstring、字段多行展开、`verbose_name` 关键字参数、`TextChoices` 枚举、`Meta` 三件套、`__str__` 类型注解）。

```python
"""图片同步队列表（sys_image_sync_queue）。"""
from django.db import models

from api_v1.models._base import TimeStampedModel


class ImageSyncStatus(models.TextChoices):
    """图片同步状态枚举。"""

    PENDING = "pending", "待同步"
    SUCCESS = "success", "同步成功"
    FAILED = "failed", "同步失败"


class ImageSyncQueue(TimeStampedModel):
    """图片同步队列记录。

    记录需要同步的图片组（SKU）及其路径，替代原外部 API
    cloud.hanlis.cn:9898 的队列存储职责。
    """

    sku = models.CharField(
        max_length=255,
        verbose_name="图片组 SKU",
    )

    local_path = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="本地路径",
    )

    status = models.CharField(
        max_length=20,
        choices=ImageSyncStatus.choices,
        default=ImageSyncStatus.PENDING,
        verbose_name="同步状态",
    )

    error_msg = models.TextField(
        blank=True,
        default="",
        verbose_name="错误信息",
    )

    class Meta:
        db_table = "sys_image_sync_queue"
        verbose_name = "图片同步队列"
        verbose_name_plural = "图片同步队列"
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"ImageSyncQueue<{self.sku}>"
```

**字段映射关系**（外部 API → 内部模型）：
- 外部 `sku` → `ImageSyncQueue.sku`（= `ImageUpload.image_group`）
- 外部 `local_path` → `ImageSyncQueue.local_path`（= `ImageUpload.cloud_path`）
- 外部 `status: 1` → `ImageSyncQueue.status = PENDING`

### Task 2：注册模型导出

**`api_v1/models/file/__init__.py`**：追加导出
```python
from api_v1.models.file.image_sync_queue import ImageSyncQueue, ImageSyncStatus
# __all__ 追加 'ImageSyncQueue', 'ImageSyncStatus'
```

**`api_v1/models/__init__.py`**：在 file 板块导入区追加
```python
from api_v1.models.file.image_sync_queue import ImageSyncQueue, ImageSyncStatus
# __all__ 追加 'ImageSyncQueue', 'ImageSyncStatus'
```

### Task 3：新建 Serializer

**文件**：`api_v1/serializers/image_sync_queue.py`

遵循"数据出口最终成形原则"——后端直接输出 camelCase 字段，前端不再做映射。

```python
"""图片同步队列序列化器。"""
from rest_framework import serializers

from api_v1.models import ImageSyncQueue


class ImageSyncQueueSerializer(serializers.ModelSerializer):
    """图片同步队列序列化器（前端 camelCase 字段适配）。"""

    imageGroup = serializers.CharField(source="sku")
    cloudPath = serializers.CharField(source="local_path")
    errorMsg = serializers.CharField(source="error_msg", read_only=True)
    createTime = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = ImageSyncQueue
        fields = ["id", "imageGroup", "cloudPath", "status", "errorMsg", "createTime"]
```

**`api_v1/serializers/__init__.py`**：在 file 板块区追加导出
```python
from api_v1.serializers.image_sync_queue import ImageSyncQueueSerializer
# __all__ 追加 "ImageSyncQueueSerializer"
```

### Task 4：新建 Service

**文件**：`api_v1/services/lingxing/image_sync_queue_service.py`

遵循"胖 Service / 瘦 Controller"原则，将跨表 upsert 业务逻辑收拢到 service。

```python
"""图片同步队列业务服务。"""
import logging

from django.utils import timezone

from api_v1.models import ImageSyncQueue
from api_v1.models.file.image_upload import ImageSyncStatus

logger = logging.getLogger(__name__)


def upsert_sync_task(image_upload) -> tuple[bool, str]:
    """根据 ImageUpload 记录 upsert 同步队列。

    存在相同 sku 的队列记录则更新 local_path 并重置状态为 PENDING，
    不存在则创建新记录。同时向 ImageUpload.log 追加操作日志。

    Args:
        image_upload: ImageUpload 模型实例。

    Returns:
        tuple[bool, str]: (是否成功, 日志行)。
    """
    # ... update_or_create + 日志追加


def batch_upsert_sync_tasks(image_uploads: list) -> list[dict]:
    """批量 upsert 同步队列。

    Args:
        image_uploads: ImageUpload 实例列表。

    Returns:
        list[dict]: 每条结果 {id, success, msg}。
    """
    # ... 循环调用 upsert_sync_task


def get_queue_queryset(query_params: dict):
    """根据查询参数构建同步队列 queryset。

    Args:
        query_params: 含 imageGroup（可选）、pageNum、pageSize。

    Returns:
        QuerySet: 过滤后的 ImageSyncQueue 查询集。
    """
    # ... filter by imageGroup
```

**`api_v1/services/lingxing/__init__.py`**：导出 service 函数。

### Task 5：重写 View 的三个 action

**文件**：`api_v1/views/lingxing/sales/listing/image_view.py`

移除 `import requests`、`from urllib.parse import quote` 等外部 API 相关导入。

#### 5.1 `queue` action（第 309-328 行重写）

改为查询内部 `ImageSyncQueue` 表，支持 `imageGroup` 过滤 + 后端分页，用 `ImageSyncQueueSerializer` 序列化输出：

```python
@action(detail=False, methods=['get'])
def queue(self, request):
    """查询内部图片同步队列（分页 + imageGroup 过滤）。"""
    qs = ImageSyncQueue.objects.all()
    image_group = request.query_params.get('imageGroup')
    if image_group:
        qs = qs.filter(sku__icontains=image_group)

    page = self.paginate_queryset(qs)
    if page is not None:
        serializer = ImageSyncQueueSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    serializer = ImageSyncQueueSerializer(qs, many=True)
    return drf_ok({'list': serializer.data, 'total': qs.count()})
```

#### 5.2 `sync` action（第 103-161 行重写）

改为调用 `upsert_sync_task` service，移除 `requests.put/post`：

```python
@action(detail=True, methods=['post'])
def sync(self, request, pk=None):
    """同步单个图片组到内部同步队列。"""
    instance = self.get_object()
    success, log_line = upsert_sync_task(instance)
    if success:
        return drf_ok({"msg": "Sync success", "log": log_line})
    return drf_error(f"Sync failed: {log_line}")
```

#### 5.3 `batch_sync` action（第 250-307 行重写）

改为调用 `batch_upsert_sync_tasks`，移除 `requests.put/post`：

```python
@action(detail=False, methods=['post'])
def batch_sync(self, request):
    """批量同步到内部同步队列。"""
    ids = request.data.get('ids', [])
    # ... ids 解析
    queryset = self.get_queryset().filter(id__in=ids)
    results = batch_upsert_sync_tasks(list(queryset))
    return drf_ok(results)
```

### Task 6：移除 settings 中的 `IMAGE_SYNC_URL`

**文件**：`backend_master/settings.py`

- 第 42 行：移除 `IMAGE_SYNC_URL=(str, 'https://cloud.hanlis.cn:9898'),`
- 第 82 行：移除 `IMAGE_SYNC_URL = env('IMAGE_SYNC_URL')`

> ⚠️ 如 `.env` 文件中有 `IMAGE_SYNC_URL` 变量，可一并清理（非必须，不影响运行）。

### Task 7：前端 API 改造

**文件**：`src/api/imageUpload/index.ts`

`getQueue` 改为支持分页 + `imageGroup` 过滤参数，返回 `PageResult`：

```ts
export interface ImageSyncQueueVO {
  id: string;
  imageGroup: string;
  cloudPath: string;
  status: string;
  errorMsg: string;
  createTime: string;
}

export interface ImageSyncQueueQuery extends PageQuery {
  imageGroup?: string;
}

// getQueue 改为：
getQueue(params: ImageSyncQueueQuery) {
  return request<any, PageResult<ImageSyncQueueVO[]>>({
    url: `${IMAGE_UPLOAD_BASE_URL}/queue`,
    method: "get",
    params,
  });
},
```

### Task 8：前端 SyncQueueDialog 改造

**文件**：`src/views/sales/imageupload/components/SyncQueueDialog.vue`

移除前端字段映射（`sku→imageGroup`、`local_path→cloudPath`）和客户端分页/过滤逻辑，改用后端分页：

- `handleQueueQuery` 调用 `ImageUploadAPI.getQueue(queryParams)`，直接使用返回的 `data.list` / `data.total`。
- 移除 `rawList.map(...)` 映射代码。
- 移除客户端 `filter` + `slice` 分页代码。
- 表格列绑定直接用 `imageGroup`、`cloudPath`（后端已返回 camelCase）。

### Task 9：更新知识库文档

**文件**：`docs/knowledge-base/user-guide/04-sales-image-upload.md`

- 第 3 行：移除"图片最终同步到外部图片服务"描述，改为内部同步队列。
- 第 32-37 行"同步到外部服务"：改为"同步到内部队列"，移除 PUT/POST 外部 API 描述。
- 第 39-44 行"同步队列"：移除"透传外部服务数据"和"客户端过滤、客户端分页"，改为"后端分页查询内部同步队列表"。
- 第 63-65 行"外部服务"：整段移除（不再有外部服务）。
- 第 69 行"已知风险点"中的 `AllowAny` 备注：保留（本次不修改权限）。

### Task 10：给出服务器端迁移命令（不执行，仅输出）

按 CLAUDE.md §1.8，迁移文件不上传 Git，AI 只给出命令：

```bash
# 1. 在服务器项目根目录（backend-master/）下生成迁移
python manage.py makemigrations api_v1 --name create_image_sync_queue

# 2. 应用迁移
python manage.py migrate api_v1

# 3. 重启 Django Web 服务
sudo systemctl restart <django-service>

# （如遇表已存在等冲突）
# python manage.py migrate api_v1 --fake
```

---

## 验证方案

### 后端验证

1. **迁移生成**：本地 `python manage.py makemigrations api_v1` 应生成 `0094_create_image_sync_queue.py`（仅本地验证，不上传）。
2. **迁移应用**：本地 `python manage.py migrate` 成功建表。
3. **runserver 启动**：`python manage.py runserver` 无报错。
4. **接口测试**：
   - `GET /api/v1/image-uploads/queue?pageNum=1&pageSize=10` → 返回 `{code:"00000", data:{list:[], total:0}}`
   - `POST /api/v1/image-uploads/<id>/sync` → upsert 队列记录 + 返回成功
   - `POST /api/v1/image-uploads/batch_sync` `{ids:[...]}` → 批量 upsert + 返回结果列表
   - `GET /api/v1/image-uploads/queue?imageGroup=xxx` → 过滤生效
   - 确认 **不再有任何对 `cloud.hanlis.cn:9898` 的请求**

### 前端验证

1. `pnpm run type-check`（vue-tsc）无类型错误。
2. `pnpm run lint:eslint` 无 lint 错误。
3. 点击「同步队列」→ 弹窗正常展示数据，分页生效，搜索生效。
4. 点击「同步」/「批量同步」→ 操作成功，日志追加"已提交同步队列"。

---

## 风险与影响声明

1. **行为变更**：sync 操作不再有实际的外部推送效果，仅写入内部队列表。若 `cloud.hanlis.cn:9898` 外部服务仍在承担真正的图片处理职责，移除后该处理链路将断开。**用户已确认完全移除**。
2. **历史队列数据**：外部 API 中的现有队列数据不会迁移到内部模型（新表初始为空）。如需迁移需手动处理。
3. **权限**：`ImageUploadViewSet` 当前 `permission_classes = [AllowAny]`，本次不修改（铁律 3：只碰必须碰的），已在文档中标注为已知风险点。
4. **`.env` 清理**：`.env` 中的 `IMAGE_SYNC_URL` 变量移除为可选操作，不影响运行（`env()` 已移除）。
