"""Listing 标签同步执行器（listing_tag_service）。

读取 LxListingTag 表中创建中 / 删除中的记录，
调用 middle.hanlis.cn API 完成标签的创建与删除操作，并回写数据库。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from apps.sales.listing.models.lx_listing_tag import LxListingTag
from apps.ads.models.lx_api_err import LxApiErr
from api_v2.services.qinglong_env_service import get_cached_env, refresh_with_task_trigger

logger = logging.getLogger(__name__)

_ADD_TAG_URL = "https://middle.hanlis.cn/basicOpen/globalTag/listing/addTag"
_LIST_TAG_URL = "https://middle.hanlis.cn/basicOpen/globalTag/listing/page/list"
_REMOVE_TAG_URL = "https://middle.hanlis.cn/basicOpen/globalTag/listing/removeTag"
_API_TIMEOUT = 60
_DELETE_BATCH_SIZE = 10
_MAX_RETRIES = 3


# ============================================================
# 辅助函数
# ============================================================

def _get_middle_headers() -> dict[str, str]:
    """从缓存获取 MIDDLE_API_HEADERS 并解析为请求头字典。"""
    raw = get_cached_env("MIDDLE_API_HEADERS") or ""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if not raw:
        logger.error("[ListingTagService] MIDDLE_API_HEADERS 缓存为空")
        return headers
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            headers.update(parsed)
    except json.JSONDecodeError:
        logger.exception("[ListingTagService] MIDDLE_API_HEADERS JSON 解析失败")
    return headers


def _log_api_err(url: str, request_body: str, code: str = "", message: str = "") -> None:
    """写入 API 错误日志到 LxApiErr 表。"""
    try:
        LxApiErr.objects.create(
            task="listing_tag_sync",
            task_name="Listing标签同步",
            url=url,
            method="POST",
            parameter=request_body or "",
            code=str(code),
            message=str(message),
        )
    except Exception:
        logger.exception("[ListingTagService] 写入 LxApiErr 失败")


def _post_api(url: str, body: dict) -> dict[str, Any]:
    """
    调用 middle API，返回响应 JSON。

    最多重试 3 次；首次 401 时自动刷新认证头；最终失败时写入 LxApiErr。

    Args:
        url: API 地址。
        body: 请求体字典。

    Returns:
        dict: API 响应 JSON，失败时 code 非 0。
    """
    body_str = json.dumps(body, ensure_ascii=False)
    headers = _get_middle_headers()

    for attempt in range(_MAX_RETRIES):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=_API_TIMEOUT)

            if resp.status_code == 401 and attempt == 0:
                logger.warning("[ListingTagService] 401，刷新 MIDDLE_API_HEADERS")
                try:
                    refresh_with_task_trigger()
                    headers = _get_middle_headers()
                except Exception:
                    logger.exception("[ListingTagService] 刷新失败")
                continue

            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0:
                return data

            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    "[ListingTagService] code=%s 第%d次重试 url=%s",
                    data.get("code"), attempt + 1, url,
                )
                time.sleep((attempt + 1) * 2)
                continue

            _log_api_err(
                url=url, request_body=body_str,
                code=str(data.get("code", "")), message=data.get("message", ""),
            )
            logger.error(
                "[ListingTagService] API 最终失败 url=%s code=%s msg=%s",
                url, data.get("code"), data.get("message"),
            )
            return data

        except requests.Timeout:
            if attempt < _MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 3)
                continue
            _log_api_err(url=url, request_body=body_str, code="TIMEOUT", message="超时")
            logger.error("[ListingTagService] 请求超时 url=%s", url)
            return {"code": -1, "message": "TIMEOUT"}

        except requests.ConnectionError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 3)
                continue
            _log_api_err(url=url, request_body=body_str, code="CONN_ERR", message="连接失败")
            logger.error("[ListingTagService] 连接失败 url=%s", url)
            return {"code": -1, "message": "CONN_ERR"}

        except requests.RequestException as e:
            if attempt < _MAX_RETRIES - 1 and getattr(e, "response", None) is not None and e.response.status_code >= 500:
                time.sleep((attempt + 1) * 2)
                continue
            err_code = str(getattr(e, "response", None) and e.response.status_code or "ERR")
            _log_api_err(url=url, request_body=body_str, code=err_code, message=str(e))
            logger.error("[ListingTagService] 请求异常 url=%s err=%s", url, e, exc_info=True)
            return {"code": -1, "message": str(e)}

    return {"code": -1, "message": "UNKNOWN"}


# ============================================================
# 创建中 → 正常
# ============================================================

def _process_creating_tags() -> dict[str, int]:
    """
    处理创建中的标签：调 addTag → 查询 global_tag_id 和 type → 回写并改状态为 normal。

    Returns:
        dict: {"processed": int, "success": int, "failed": int}
    """
    records = list(LxListingTag.objects.filter(status="creating"))
    if not records:
        logger.info("[ListingTagService] 无创建中的标签记录")
        return {"processed": 0, "success": 0, "failed": 0}

    logger.info("[ListingTagService] 创建中记录数=%d", len(records))
    success = 0
    failed = 0

    for record in records:
        try:
            add_body = {"tag_name": record.tag_name}
            add_resp = _post_api(_ADD_TAG_URL, add_body)

            if add_resp.get("code") != 0:
                logger.error(
                    "[ListingTagService] addTag 失败 tag_name=%s code=%s msg=%s",
                    record.tag_name, add_resp.get("code"), add_resp.get("message"),
                )
                failed += 1
                continue

            # 查询标签信息，获取 global_tag_id 和 type
            search_body = {"search_field": "tag_name", "search_value": record.tag_name}
            search_resp = _post_api(_LIST_TAG_URL, search_body)

            if search_resp.get("code") != 0:
                logger.error(
                    "[ListingTagService] page/list 查询失败 tag_name=%s code=%s msg=%s",
                    record.tag_name, search_resp.get("code"), search_resp.get("message"),
                )
                failed += 1
                continue

            data_list = search_resp.get("data", [])
            if not data_list:
                logger.warning(
                    "[ListingTagService] page/list 无匹配结果 tag_name=%s", record.tag_name,
                )
                failed += 1
                continue

            tag_data = data_list[0]
            record.global_tag_id = tag_data.get("global_tag_id", "")
            record.type = tag_data.get("type", "")
            record.status = "normal"
            record.save(update_fields=["global_tag_id", "type", "status", "updated_at"])

            logger.info(
                "[ListingTagService] 标签创建成功 tag_name=%s global_tag_id=%s type=%s",
                record.tag_name, record.global_tag_id, record.type,
            )
            success += 1

        except Exception:
            logger.exception(
                "[ListingTagService] 处理创建标签异常 tag_name=%s", record.tag_name,
            )
            failed += 1

    logger.info(
        "[ListingTagService] 创建处理完成 processed=%d success=%d failed=%d",
        len(records), success, failed,
    )
    return {"processed": len(records), "success": success, "failed": failed}


# ============================================================
# 删除中 → 删除记录
# ============================================================

def _process_deleting_tags() -> dict[str, int]:
    """
    处理删除中的标签：批量调 removeTag（每批最多 10 个），成功后删除数据库记录。

    Returns:
        dict: {"processed": int, "deleted": int, "failed": int}
    """
    records = list(
        LxListingTag.objects.filter(status="deleting").exclude(global_tag_id="")
    )
    if not records:
        logger.info("[ListingTagService] 无删除中的标签记录")
        return {"processed": 0, "deleted": 0, "failed": 0}

    logger.info("[ListingTagService] 删除中记录数=%d", len(records))
    deleted = 0
    failed = 0

    # 按每批 10 个分组
    for i in range(0, len(records), _DELETE_BATCH_SIZE):
        batch = records[i:i + _DELETE_BATCH_SIZE]
        tag_ids = [r.global_tag_id for r in batch]

        try:
            remove_body = {"tag_ids": tag_ids}
            resp = _post_api(_REMOVE_TAG_URL, remove_body)

            if resp.get("code") == 0:
                record_ids = [r.id for r in batch]
                LxListingTag.objects.filter(id__in=record_ids).delete()
                deleted += len(batch)
                logger.info(
                    "[ListingTagService] 批量删除成功 batch=%d-%d tag_ids=%s",
                    i, i + len(batch), tag_ids,
                )
            else:
                failed += len(batch)
                logger.error(
                    "[ListingTagService] 批量删除失败 tag_ids=%s code=%s msg=%s",
                    tag_ids, resp.get("code"), resp.get("message"),
                )

        except Exception:
            logger.exception(
                "[ListingTagService] 批量删除异常 tag_ids=%s", tag_ids,
            )
            failed += len(batch)

    logger.info(
        "[ListingTagService] 删除处理完成 processed=%d deleted=%d failed=%d",
        len(records), deleted, failed,
    )
    return {"processed": len(records), "deleted": deleted, "failed": failed}


# ============================================================
# 主流程
# ============================================================

def execute_listing_tag_sync() -> dict[str, Any]:
    """
    执行 Listing 标签同步任务：按状态分批处理创建中和删除中的标签。

    Returns:
        dict:
            {
                "creating": {"processed": int, "success": int, "failed": int},
                "deleting": {"processed": int, "deleted": int, "failed": int},
            }
    """
    logger.info("[ListingTagService] 开始执行 Listing 标签同步")

    creating_result = _process_creating_tags()
    deleting_result = _process_deleting_tags()

    logger.info(
        "[ListingTagService] 同步完成 creating=%s deleting=%s",
        creating_result, deleting_result,
    )
    return {
        "creating": creating_result,
        "deleting": deleting_result,
    }
