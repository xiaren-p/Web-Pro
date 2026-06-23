"""图片同步队列核心业务服务（image_sync_service）。

职责：
  1. 从 NC（美工部【产品图片】）下载编号图片（1-7.jpg）。
  2. 调领星 API 搜索 listing、预上传图片、比较并更新 listing 图片。
  3. 维护 ImageSyncQueue 状态与 ImageUpload 日志。

参考来源：外部自动化项目 new_picture_upload/template.py。
"""
import json
import logging
import time
from io import BytesIO
from typing import Any

import imagehash
import requests
from django.utils import timezone
from PIL import Image

from api_v1.models import ImageSyncQueue, ImageUpload
from api_v1.models.file.image_sync_queue import ImageSyncStatus
from api_v1.models.file.image_upload import ImageUploadStatus
from api_v1.services.nc.nc_api_client import NcApiClient
from api_v2.services.nc_sku_path_search import search_nc_sku_paths
from api_v2.services.qinglong_env_service import get_cached_env

logger = logging.getLogger(__name__)

# 领星 API 基础地址
_LX_BASE = "https://gw.lingxingerp.com"

# 编号图片文件名前缀
_NUMBERED_INDICES = list(range(1, 8))

# 图片扩展名优先级
_IMAGE_EXTS_ORDERED = (".jpg", ".jpeg", ".png", ".webp")


# ------------------------------------------------------------------ #
#  领星鉴权                                                          #
# ------------------------------------------------------------------ #

def _build_lingxing_headers() -> dict[str, str]:
    """构建领星 API 请求头。

    从青龙同步缓存 LX_ERP_HEADERS 读取 x-ak-* 与 auth-token，
    合并浏览器基础头。缓存未命中时返回空 dict。

    Returns:
        dict[str, str]: 请求头字典；空 dict 表示缓存不可用。
    """
    cached = get_cached_env("LX_ERP_HEADERS")
    if not cached:
        logger.warning("[ImageSync][build_headers] LX_ERP_HEADERS 缓存未命中")
        return {}
    try:
        xak: dict[str, str] = json.loads(cached)
    except (json.JSONDecodeError, TypeError):
        logger.error("[ImageSync][build_headers] LX_ERP_HEADERS JSON 解析失败", exc_info=True)
        return {}
    base: dict[str, str] = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json;charset=UTF-8",
        "origin": "https://erp.lingxing.com",
        "referer": "https://erp.lingxing.com/",
        "ak-client-type": "web",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"
        ),
    }
    return {**base, **xak}


# ------------------------------------------------------------------ #
#  NC 路径解析                                                        #
# ------------------------------------------------------------------ #

def _get_art_dept_nc_info() -> tuple[NcApiClient, str, str] | None:
    """获取美工部 NC Group Folder 的连接信息与挂载点。

    查找部门名称含"美工"的 DEPT_ADMIN 群组，获取 mount_point。

    Returns:
        tuple: (NcApiClient, admin_user, mount_point)；失败返回 None。
    """
    from api_v1.models.nc.nc_group import NcGroup, NcGroupType

    try:
        nc_group = NcGroup.objects.filter(
            group_type=NcGroupType.DEPT_ADMIN,
            dept__name__icontains="美工",
        ).select_related("dept").first()
        if not nc_group:
            logger.error("[ImageSync][get_nc_info] 未找到美工部 DEPT_ADMIN 群组")
            return None
        client = NcApiClient.from_settings()
        admin_user = NcApiClient._read_config("NC_ADMIN_USER")
        # 获取 mount_point：先取同部门 DEPT 群组的 folder_id
        dept_ng = NcGroup.objects.filter(
            dept_id=nc_group.dept_id, group_type=NcGroupType.DEPT,
        ).first()
        if not dept_ng or not dept_ng.folder_id:
            logger.error("[ImageSync][get_nc_info] DEPT 群组缺少 folder_id")
            return None
        folders = client.list_group_folders()
        info = folders.get(dept_ng.folder_id)
        if not info:
            logger.error("[ImageSync][get_nc_info] NC 中未找到 Group Folder")
            return None
        mount_point = info.get("mount_point", "").strip("/")
        return client, admin_user, mount_point
    except Exception:
        logger.error("[ImageSync][get_nc_info] 获取 NC 信息异常", exc_info=True)
        return None


def _build_product_image_dav_path(
    admin_user: str, mount_point: str, local_path: str,
) -> str:
    """构造【产品图片】目录下的 WebDAV 路径。

    Args:
        admin_user (str): NC 管理员用户名。
        mount_point (str): Group Folder 挂载点名称。
        local_path (str): 相对于【产品图片】的子路径，可为空。

    Returns:
        str: 完整 WebDAV 路径。
    """
    base = f"/remote.php/dav/files/{admin_user}/{mount_point}/【产品图片】"
    if local_path:
        clean = local_path.strip("\\/")
        return f"{base}/{clean}/"
    return f"{base}/"


# ------------------------------------------------------------------ #
#  NC 图片下载                                                        #
# ------------------------------------------------------------------ #

def _find_numbered_file(
    entries: list[dict], index: int,
) -> dict | None:
    """从目录条目中查找指定编号的图片文件。

    Args:
        entries (list[dict]): list_dav_entries 的返回值。
        index (int): 编号（1-7）。

    Returns:
        dict | None: 匹配的条目；未找到返回 None。
    """
    for entry in entries:
        if entry.get("is_collection"):
            continue
        name = entry.get("name", "")
        for ext in _IMAGE_EXTS_ORDERED:
            if name.lower() == f"{index}{ext}":
                return entry
    return None


def _download_nc_numbered_images(
    client: NcApiClient, dav_path: str,
) -> tuple[list[tuple[str, str | None]] | None, dict[int, bytes] | None]:
    """下载 NC 目录下的编号图片（1-7）。

    对应 template.py 的 find_local_numbered_images + 下载逻辑。

    Args:
        client (NcApiClient): NC 客户端。
        dav_path (str): WebDAV 目录路径。

    Returns:
        tuple: (pre_uploaded, local_map)；主图缺失时返回 (None, None)。
            pre_uploaded: [("1.jpg", None), ...] 占位列表。
            local_map: {index: bytes} 编号到二进制的映射。
    """
    entries = client.list_dav_entries(dav_path)
    local_map: dict[int, bytes] = {}
    for idx in _NUMBERED_INDICES:
        entry = _find_numbered_file(entries, idx)
        if not entry:
            continue
        try:
            data = client.download_dav_file(entry["href"])
            local_map[idx] = data
        except RuntimeError:
            logger.warning("[ImageSync][download_nc] 下载 %d 号图片失败", idx)
    if 1 not in local_map:
        logger.warning("[ImageSync][download_nc] 主图 1 不存在: %s", dav_path)
        return None, None
    pre_uploaded: list[tuple[str, str | None]] = []
    for idx in _NUMBERED_INDICES:
        if idx in local_map:
            pre_uploaded.append((f"{idx}.jpg", None))
    return pre_uploaded, local_map


def _extract_proxy_images(attributes: dict) -> dict[int, dict]:
    """从 proxy API 响应的 attributes 中提取图片数据。

    提取 main_product_image_locator 与 other_product_image_locator_1~8，
    每个字段为列表，元素含 media_location 与 marketplace_id。

    Args:
        attributes (dict): proxy 响应 data.attributes 字典。

    Returns:
        dict[int, dict]: {位置: {"media_location": str, "marketplace_id": str}}。
                         位置 0 = 主图，1-8 = 副图。
    """
    result: dict[int, dict] = {}
    main = attributes.get("main_product_image_locator")
    if isinstance(main, list) and main:
        result[0] = main[0]
    for i in range(1, 9):
        slot = attributes.get(f"other_product_image_locator_{i}")
        if isinstance(slot, list) and slot:
            result[i] = slot[0]
    return result


def _upload_to_upload_center(
    headers: dict[str, str], file_bytes: bytes, filename: str,
) -> str | None:
    """上传图片到领星上传中心，最多重试 3 次。

    对应 template.py 的 upload_file_to_upload_center()。

    Args:
        headers (dict[str, str]): 领星请求头。
        file_bytes (bytes): 图片二进制内容。
        filename (str): 上传文件名。

    Returns:
        str | None: 成功返回 URL，否则 None。
    """
    url = f"{_LX_BASE}/upload-center/upload/file"
    upload_headers = {
        k: v for k, v in headers.items() if k.lower() != "content-type"
    }
    for attempt in range(1, 4):
        try:
            resp = requests.post(
                url,
                headers=upload_headers,
                files={"multipartFile": (filename, file_bytes, "image/jpeg")},
                data={"serviceId": "erp-vue"},
                timeout=60,
            )
            if resp.status_code != 200:
                logger.warning("[ImageSync][upload_center] attempt=%d status=%d", attempt, resp.status_code)
                time.sleep(1)
                continue
            data = resp.json().get("data") or {}
            uploaded_url = data.get("url")
            if uploaded_url:
                return uploaded_url
            return None
        except Exception:
            logger.error("[ImageSync][upload_center] attempt=%d 异常", attempt, exc_info=True)
            time.sleep(1)
    return None


def _build_edit_payload(
    resolved_urls: list[tuple[str, str | None]],
    product_type: str,
    msku: str,
    store_id: int,
    marketplace_id: str,
) -> dict:
    """构造 listing edit API 的请求体。

    Args:
        resolved_urls (list[tuple]): 最终图片 URL 列表 [(name, url), ...]。
        product_type (str): 产品类型（来自 proxy 响应）。
        msku (str): MSKU。
        store_id (int): 店铺 ID。
        marketplace_id (str): Marketplace ID（来自 LxShops）。

    Returns:
        dict: edit API 请求体。
    """
    mp = {"marketplace_id": marketplace_id}
    amazon_data: dict[str, list] = {}
    main_url = resolved_urls[0][1] if resolved_urls else None
    amazon_data["main_product_image_locator"] = [
        {**mp, "media_location": main_url or ""},
    ]
    for i in range(1, 9):
        url = resolved_urls[i][1] if i < len(resolved_urls) else None
        amazon_data[f"other_product_image_locator_{i}"] = [
            {**mp, "media_location": url or ""},
        ]
    amazon_data["swatch_product_image_locator"] = [
        {**mp, "media_location": ""},
    ]
    return {
        "amazon_data": amazon_data,
        "product_type": product_type,
        "msku": msku,
        "store_id": store_id,
        "req_time_sequence": "/listing-publish-api/api/amazon/listing/edit$$1",
    }


def _process_listing_record(
    headers: dict[str, str],
    record,
    sku: str,
    marketplace_id: str,
    local_map: dict[int, bytes],
    pre_uploaded: list[tuple[str, str | None]],
) -> dict | None:
    """处理单条 listing 记录：proxy 获取当前图片 → 比较 → edit 更新。

    Args:
        headers (dict[str, str]): 领星请求头。
        record: LxListingData 记录。
        sku (str): SKU。
        marketplace_id (str): 该记录对应的 marketplace_id。
        local_map (dict[int, bytes]): NC 图片二进制映射。
        pre_uploaded (list[tuple]): 预上传结果。

    Returns:
        dict | None: 失败时返回错误信息 dict，成功返回 None。
    """
    sid = record.sid
    proxy_payload = {
        "store_id": sid,
        "sku": sku,
        "query": {"includedData": "productTypes,attributes,summaries"},
        "path": "/listings/2021-08-01/items/{seller_id}/{sku}",
        "req_time_sequence": "/listing-publish-api/api/amazon/proxy$$5",
    }
    try:
        resp = requests.post(
            f"{_LX_BASE}/listing-publish-api/api/amazon/proxy",
            json=proxy_payload, headers=headers, timeout=15,
        )
        if resp.status_code != 200:
            return {"sku": sku, "shop": sid, "code": resp.status_code, "msg": "proxy failed"}
        resp_json = resp.json()
        data = (resp_json.get("data") or {})
        attrs = data.get("attributes") or {}
        # productTypes 可能在 data.attributes 或 data 顶层
        product_types = (attrs.get("productTypes") or data.get("productTypes") or [])
        if not product_types:
            logger.warning("[ImageSync][proxy] productTypes 为空 sid=%s keys=%s",
                           sid, list(data.keys()))
            return {"sku": sku, "shop": sid, "code": 0, "msg": "proxy 未返回 productTypes"}
        product_type = product_types[0].get("productType", "")
        proxy_images = _extract_proxy_images(attrs)
    except Exception:
        logger.error("[ImageSync][proxy] 异常 sid=%s", sid, exc_info=True)
        return {"sku": sku, "shop": sid, "code": 0, "msg": "proxy exception"}
    final_urls = _resolve_final_image_urls(proxy_images, local_map, pre_uploaded)
    edit_payload = _build_edit_payload(final_urls, product_type, sku, sid, marketplace_id)
    last_err: dict | None = None
    for attempt in range(1, 4):
        try:
            resp = requests.post(
                f"{_LX_BASE}/listing-publish-api/api/amazon/listing/edit",
                json=edit_payload, headers=headers, timeout=15,
            )
            if resp.status_code != 200:
                last_err = {"sku": sku, "shop": sid, "code": resp.status_code, "msg": "edit http error"}
                time.sleep(1)
                continue
            j = resp.json()
            code = int(j.get("code", 0)) if str(j.get("code", "")).isdigit() else 0
            msg = str(j.get("msg", j))
            if code == 1 or "成功" in msg:
                return None
            last_err = {"sku": sku, "shop": sid, "code": code, "msg": msg}
            time.sleep(1)
        except Exception:
            logger.error("[ImageSync][edit] attempt=%d 异常", attempt, exc_info=True)
            last_err = {"sku": sku, "shop": sid, "code": 0, "msg": "edit exception"}
            time.sleep(1)
    return last_err


# ------------------------------------------------------------------ #
#  图片比较                                                           #
# ------------------------------------------------------------------ #

def _pil_from_source(source: bytes | str) -> Image.Image:
    """从 bytes 或 URL 加载 PIL Image。

    Args:
        source (bytes | str): 图片二进制或 URL。

    Returns:
        Image.Image: RGB 格式的 PIL 图像。

    Raises:
        ValueError: 加载失败时抛出。
    """
    if isinstance(source, bytes):
        return Image.open(BytesIO(source)).convert("RGB")
    resp = requests.get(source, timeout=15)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


def _are_images_visually_same(
    img_a: bytes | str, img_b: bytes | str,
    hash_size: int = 8, max_total_diff: int = 1,
) -> bool:
    """判断两张图片在视觉与颜色上是否一致。

    移植自 image_compare.py 的 are_images_visually_same_color()。
    对 RGB 三通道分别计算 dHash，比较差异总和。

    Args:
        img_a (bytes | str): 图片 A（bytes 或 URL）。
        img_b (bytes | str): 图片 B（bytes 或 URL）。
        hash_size (int): dHash 尺寸，默认 8。
        max_total_diff (int): 最大允许差异总和，默认 1。

    Returns:
        bool: 视觉一致返回 True。
    """
    try:
        a = _pil_from_source(img_a)
        b = _pil_from_source(img_b)
        ra, ga, ba = (imagehash.dhash(ch, hash_size=hash_size) for ch in a.split())
        rb, gb, bb = (imagehash.dhash(ch, hash_size=hash_size) for ch in b.split())
        total = (ra - rb) + (ga - gb) + (ba - bb)
        return total <= max_total_diff
    except Exception:
        logger.error("[ImageSync][compare] 图片比较异常", exc_info=True)
        return False


# ------------------------------------------------------------------ #
#  预上传与最终 URL 决策                                               #
# ------------------------------------------------------------------ #

def _preupload_numbered_images(
    headers: dict[str, str], local_map: dict[int, bytes],
) -> tuple[list[tuple[str, str | None]], dict[int, bytes]] | tuple[None, None]:
    """预上传编号图片到领星上传中心。

    对应 template.py 的 preupload_local_numbered_images()。

    Args:
        headers (dict[str, str]): 领星请求头。
        local_map (dict[int, bytes]): {编号: 图片二进制}。

    Returns:
        tuple: (pre_uploaded, local_map)；主图上传失败返回 (None, None)。
    """
    pre_uploaded: list[tuple[str, str | None]] = []
    for idx in sorted(local_map.keys()):
        name = f"{idx}.jpg"
        uploaded = _upload_to_upload_center(headers, local_map[idx], name)
        if idx == 1 and not uploaded:
            logger.error("[ImageSync][preupload] 主图 1.jpg 上传失败，停止")
            return None, None
        pre_uploaded.append((name, uploaded))
    return pre_uploaded, local_map


def _resolve_final_image_urls(
    proxy_images: dict[int, dict],
    local_map: dict[int, bytes],
    pre_uploaded: list[tuple[str, str | None]],
) -> list[tuple[str, str | None]]:
    """根据 proxy 已有图片与 NC 图片比较结果决定最终 URL 列表。

    覆盖 slot 1-8：
    - proxy 有图 + NC 有图 → 比较，相同保留旧图，不同用 NC
    - proxy 有图 + NC 无图 → 保留旧图
    - proxy 无图 + NC 有图 → 用 NC
    - proxy 无图 + NC 无图 → 空串

    Args:
        proxy_images (dict[int, dict]): proxy 返回的图片数据
                                        {位置: {media_location, marketplace_id}}。
        local_map (dict[int, bytes]): NC 图片二进制映射。
        pre_uploaded (list[tuple]): 预上传结果。

    Returns:
        list[tuple[str, str | None]]: 最终 [(name, url), ...]，slot 1-8。
    """
    pre_map: dict[int, str | None] = {}
    for name, url in pre_uploaded:
        pre_map[int(name.split(".")[0])] = url
    result: list[tuple[str, str | None]] = []
    for idx in range(1, 9):
        name = f"{idx}.jpg"
        proxy_img = proxy_images.get(idx)
        proxy_url = (proxy_img or {}).get("media_location", "")
        nc_bytes = local_map.get(idx)
        if proxy_url and nc_bytes:
            same = _are_images_visually_same(proxy_url, nc_bytes)
            result.append((name, proxy_url if same else pre_map.get(idx)))
        elif proxy_url:
            result.append((name, proxy_url))
        elif nc_bytes:
            result.append((name, pre_map.get(idx)))
        else:
            result.append((name, ""))
    return result


# ------------------------------------------------------------------ #
#  结果上报                                                           #
# ------------------------------------------------------------------ #

def _report_result(
    sku: str, local_path: str, level: str, message: str,
    image_url: str | None = None,
) -> None:
    """上报执行结果到 ImageUpload 记录。

    对应 template.py 的 report_execution_result()。

    Args:
        sku (str): 商品 SKU。
        local_path (str): NC 相对路径。
        level (str): INFO / WARNING / ERROR。
        message (str): 详细结果信息。
        image_url (str | None): 预览图片 URL。
    """
    now_str = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{now_str}] [{level}] {message}"
    status_map = {"INFO": ImageUploadStatus.NORMAL, "WARNING": ImageUploadStatus.WARNING, "ERROR": ImageUploadStatus.ERROR}
    status_val = status_map.get(level, ImageUploadStatus.NORMAL)
    record = ImageUpload.objects.filter(image_group=sku).first()
    data: dict[str, Any] = {"image_group": sku, "cloud_path": local_path, "status": status_val}
    if image_url:
        data["image_url"] = image_url
    if record:
        current_log = record.log or ""
        data["log"] = f"{current_log}\n{log_line}".strip()
        ImageUpload.objects.filter(id=record.id).update(**data)
    else:
        data["log"] = log_line
        ImageUpload.objects.create(**data)


def _update_queue_status(
    item: ImageSyncQueue, status: str, error_msg: str = "",
) -> None:
    """更新 ImageSyncQueue 记录状态。

    Args:
        item (ImageSyncQueue): 队列记录。
        status (str): 新状态值。
        error_msg (str): 错误信息。
    """
    item.status = status
    item.error_msg = error_msg
    item.save(update_fields=["status", "error_msg"])


# ------------------------------------------------------------------ #
#  单条处理                                                           #
# ------------------------------------------------------------------ #

def _process_sync_item(
    item: ImageSyncQueue,
    headers: dict[str, str],
    nc_client: NcApiClient,
    admin_user: str,
    mount_point: str,
) -> dict:
    """处理单条同步队列记录。

    对应 template.py 的 process_missing_item()。

    Args:
        item (ImageSyncQueue): 队列记录。
        headers (dict[str, str]): 领星请求头。
        nc_client (NcApiClient): NC 客户端。
        admin_user (str): NC 管理员用户名。
        mount_point (str): NC 挂载点名称。

    Returns:
        dict: 处理结果摘要。
    """
    sku = item.sku.strip()
    local_path = (item.local_path or "").strip()
    logger.info("[ImageSync][process_item] 开始处理 sku=%s path=%s", sku, local_path)

    # 1. 构造 NC 路径并下载图片
    dav_path = _build_product_image_dav_path(admin_user, mount_point, local_path)
    pre_uploaded, local_map = _download_nc_numbered_images(nc_client, dav_path)
    if not pre_uploaded or not local_map:
        msg = f"NC 主图 1.jpg 不存在: {dav_path}"
        _report_result(sku, local_path, "ERROR", msg)
        _update_queue_status(item, ImageSyncStatus.FAILED, msg)
        return {"sku": sku, "success": False, "msg": msg}

    # 2. 内部搜索 listing（在售 + 停售，排除已删除）
    from api_v1.models import LxListingData, LxShops
    records = list(LxListingData.objects.filter(
        seller_sku=sku, is_delete=0,
    ))
    if not records:
        msg = f"SKU {sku} 未找到匹配的 listing"
        _report_result(sku, local_path, "WARNING", msg)
        _update_queue_status(item, ImageSyncStatus.FAILED, msg)
        return {"sku": sku, "success": False, "msg": msg}

    # 3. 批量获取 shop_id → marketplace_id 映射
    sid_set = {r.sid for r in records}
    shops_map = {
        s.sid: s.marketplace_id or ""
        for s in LxShops.objects.filter(sid__in=sid_set)
    }

    # 4. 统一预上传到 upload-center（只做一次，URL 各国家复用）
    pre_result = _preupload_numbered_images(headers, local_map)
    if pre_result[0] is None:
        msg = "预上传本地图片失败，请检查"
        _report_result(sku, local_path, "ERROR", msg)
        _update_queue_status(item, ImageSyncStatus.FAILED, msg)
        return {"sku": sku, "success": False, "msg": msg}
    pre_uploaded, local_map = pre_result

    # 5. 串行遍历每条 listing 记录
    err_list: list[dict] = []
    for record in records:
        marketplace_id = shops_map.get(record.sid, "")
        if not marketplace_id:
            err_list.append({"sku": sku, "shop": record.sid, "code": 0, "msg": "no marketplace_id"})
            continue
        try:
            err = _process_listing_record(
                headers, record, sku, marketplace_id, local_map, pre_uploaded,
            )
            if err:
                err_list.append(err)
        except Exception:
            logger.error("[ImageSync][process_item] 处理 listing 异常", exc_info=True)
        time.sleep(1)
    # 6. 结果上报
    main_img_url = pre_uploaded[0][1] if pre_uploaded else None
    if not err_list:
        msg = f"产品图片（{len(records)} 个）上传成功"
        _report_result(sku, local_path, "INFO", msg, image_url=main_img_url)
        _update_queue_status(item, ImageSyncStatus.SUCCESS)
    else:
        detail_parts = []
        for e in err_list[:3]:
            shop = e.get("shop", "?")
            code = e.get("code", "?")
            emsg = e.get("msg", "?")
            detail_parts.append(f"shop={shop} code={code} msg={emsg}")
        detail = "; ".join(detail_parts)
        if len(err_list) > 3:
            detail += f"; ...(共 {len(err_list)} 条错误)"
        msg = f"部分失败: {len(err_list)}/{len(records)} | {detail}"
        _report_result(sku, local_path, "WARNING", msg, image_url=main_img_url)
        _update_queue_status(item, ImageSyncStatus.FAILED, msg)
    return {"sku": sku, "success": not err_list, "errors": err_list}


# ------------------------------------------------------------------ #
#  入口                                                               #
# ------------------------------------------------------------------ #

def execute_image_sync() -> dict:
    """图片同步队列监控入口。

    查询 PENDING 队列，逐条处理同步任务。

    Returns:
        dict: 处理汇总 {processed, success, failed, errors}。
    """
    logger.info("[ImageSync][execute] 开始执行图片同步")

    # 1. 构建领星 headers
    headers = _build_lingxing_headers()
    if not headers:
        logger.warning("[ImageSync][execute] 领星 headers 不可用，跳过本轮")
        return {"processed": 0, "success": 0, "failed": 0, "errors": ["headers unavailable"]}

    # 2. 获取 NC 连接信息
    nc_info = _get_art_dept_nc_info()
    if not nc_info:
        logger.error("[ImageSync][execute] 无法获取美工部 NC 信息")
        return {"processed": 0, "success": 0, "failed": 0, "errors": ["nc info unavailable"]}
    nc_client, admin_user, mount_point = nc_info

    # 3. 查询 PENDING 队列
    pending = list(ImageSyncQueue.objects.filter(status=ImageSyncStatus.PENDING))
    if not pending:
        logger.info("[ImageSync][execute] 无 PENDING 记录")
        return {"processed": 0, "success": 0, "failed": 0, "errors": []}

    # 4. 处理 local_path 为空的条目：批量搜索 NC 路径
    _resolve_missing_paths(pending, nc_client, admin_user, mount_point)

    # 5. 逐条处理
    result = {"processed": 0, "success": 0, "failed": 0, "errors": []}
    for item in pending:
        if not (item.local_path or "").strip():
            msg = f"SKU {item.sku} 路径仍为空"
            _report_result(item.sku, "", "WARNING", msg)
            _update_queue_status(item, ImageSyncStatus.FAILED, msg)
            result["errors"].append(msg)
            result["failed"] += 1
            continue
        try:
            item_result = _process_sync_item(item, headers, nc_client, admin_user, mount_point)
            result["processed"] += 1
            if item_result.get("success"):
                result["success"] += 1
            else:
                result["failed"] += 1
        except Exception:
            logger.error("[ImageSync][execute] 处理异常 sku=%s", item.sku, exc_info=True)
            result["failed"] += 1
        time.sleep(1)
    logger.info("[ImageSync][execute] 完成: %s", result)
    return result


def _resolve_missing_paths(
    items: list[ImageSyncQueue],
    nc_client: NcApiClient,
    admin_user: str,
    mount_point: str,
) -> None:
    """为 local_path 为空的队列条目搜索 NC 路径并回填。

    对应 template.py 的 find_missing_local_paths_and_search()。

    Args:
        items (list[ImageSyncQueue]): 队列记录列表（原地修改）。
        nc_client (NcApiClient): NC 客户端。
        admin_user (str): NC 管理员用户名。
        mount_point (str): NC 挂载点名称。
    """
    missing = [it for it in items if not (it.local_path or "").strip()]
    if not missing:
        return
    skus = list(dict.fromkeys(it.sku.strip() for it in missing))
    scope = f"/remote.php/dav/files/{admin_user}/{mount_point}/【产品图片】"
    logger.info("[ImageSync][resolve_paths] 搜索 %d 个 SKU 路径", len(skus))
    try:
        path_map, debug_info = search_nc_sku_paths(nc_client, admin_user, scope, skus)
    except RuntimeError as exc:
        logger.error("[ImageSync][resolve_paths] NC 搜索失败: %s", exc, exc_info=True)
        for it in missing:
            msg = f"NC 路径搜索失败: {exc}"
            _report_result(it.sku, "", "WARNING", msg)
            _update_queue_status(it, ImageSyncStatus.FAILED, msg)
        return
    for it in missing:
        paths = path_map.get(it.sku.strip(), [])
        if len(paths) == 1:
            it.local_path = paths[0]
            it.save(update_fields=["local_path"])
            logger.info("[ImageSync][resolve_paths] SKU %s → %s", it.sku, paths[0])
        else:
            msg = f"匹配到 {len(paths)} 个路径，无法唯一确定 | {debug_info}"
            _report_result(it.sku, "", "WARNING", msg)
            _update_queue_status(it, ImageSyncStatus.FAILED, msg)
            logger.warning("[ImageSync][resolve_paths] SKU %s: %s", it.sku, msg)
