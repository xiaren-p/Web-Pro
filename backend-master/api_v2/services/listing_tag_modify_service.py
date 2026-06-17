"""Listing 商品标签修改执行器（listing_tag_modify_service）。

读取 ListingTagModifyQueue 表中待处理的记录，
按修改类型分批，调用 middle.hanlis.cn API 完成标签绑定的新增与移除操作。
处理成功后删除对应的队列记录。
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import Any

import requests

from api_v2.models.listing_tag_modify_queue import (
    ListingTagModifyQueue,
    ModifyActionChoices,
)
from api_v2.models.lx_api_err import LxApiErr
from api_v2.services.qinglong_env_service import get_cached_env, refresh_with_task_trigger

logger = logging.getLogger(__name__)

_BIND_URL = "https://middle.hanlis.cn/basicOpen/listingManage/bindListingAndTag"
_UNBIND_URL = "https://middle.hanlis.cn/basicOpen/listingManage/removeListingAndTag"
_API_TIMEOUT = 60
_MAX_RETRIES = 3


# ============================================================
# 辅助函数（复刻 listing_tag_service.py 模式）
# ============================================================

def _get_middle_headers() -> dict[str, str]:
    """从缓存获取 MIDDLE_API_HEADERS 并解析为请求头字典。"""
    raw = get_cached_env("MIDDLE_API_HEADERS") or ""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if not raw:
        logger.error("[ListingTagModifyService] MIDDLE_API_HEADERS 缓存为空")
        return headers
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            headers.update(parsed)
    except json.JSONDecodeError:
        logger.exception("[ListingTagModifyService] MIDDLE_API_HEADERS JSON 解析失败")
    return headers


def _log_api_err(url: str, request_body: str, code: str = "", message: str = "") -> None:
    """写入 API 错误日志到 LxApiErr 表。"""
    try:
        LxApiErr.objects.create(
            task="listing_tag_modify",
            task_name="Listing商品标签修改",
            url=url,
            method="POST",
            parameter=request_body or "",
            code=str(code),
            message=str(message),
        )
    except Exception:
        logger.exception("[ListingTagModifyService] 写入 LxApiErr 失败")


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
                logger.warning("[ListingTagModifyService] 401，刷新 MIDDLE_API_HEADERS")
                try:
                    refresh_with_task_trigger()
                    headers = _get_middle_headers()
                except Exception:
                    logger.exception("[ListingTagModifyService] 刷新失败")
                continue

            resp.raise_for_status()
            data = resp.json()

            if data.get("code") == 0:
                return data

            if attempt < _MAX_RETRIES - 1:
                logger.warning(
                    "[ListingTagModifyService] code=%s 第%d次重试 url=%s",
                    data.get("code"), attempt + 1, url,
                )
                time.sleep((attempt + 1) * 2)
                continue

            _log_api_err(
                url=url, request_body=body_str,
                code=str(data.get("code", "")), message=data.get("message", ""),
            )
            logger.error(
                "[ListingTagModifyService] API 最终失败 url=%s code=%s msg=%s",
                url, data.get("code"), data.get("message"),
            )
            return data

        except requests.Timeout:
            if attempt < _MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 3)
                continue
            _log_api_err(url=url, request_body=body_str, code="TIMEOUT", message="超时")
            logger.error("[ListingTagModifyService] 请求超时 url=%s", url)
            return {"code": -1, "message": "TIMEOUT"}

        except requests.ConnectionError:
            if attempt < _MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 3)
                continue
            _log_api_err(url=url, request_body=body_str, code="CONN_ERR", message="连接失败")
            logger.error("[ListingTagModifyService] 连接失败 url=%s", url)
            return {"code": -1, "message": "CONN_ERR"}

        except requests.RequestException as e:
            if attempt < _MAX_RETRIES - 1 and getattr(e, "response", None) is not None and e.response.status_code >= 500:
                time.sleep((attempt + 1) * 2)
                continue
            err_code = str(getattr(e, "response", None) and e.response.status_code or "ERR")
            _log_api_err(url=url, request_body=body_str, code=err_code, message=str(e))
            logger.error("[ListingTagModifyService] 请求异常 url=%s err=%s", url, e, exc_info=True)
            return {"code": -1, "message": str(e)}

    return {"code": -1, "message": "UNKNOWN"}


# ============================================================
# 分组合并规则
# ============================================================

def _build_tag_key(tag_ids: list[str]) -> str:
    """将 tag_ids 数组生成稳定的分组键（排序后以逗号拼接）。"""
    return ",".join(sorted(tag_ids))


def _group_by_tag_ids(
    records: list[ListingTagModifyQueue],
) -> dict[str, list[ListingTagModifyQueue]]:
    """
    按 tag_ids 内容分组：相同 tag_ids 的队列记录可以合并到一次 API 请求中。

    Returns:
        dict: {tag_key: [record, ...]}
    """
    groups: dict[str, list[ListingTagModifyQueue]] = defaultdict(list)
    for rec in records:
        key = _build_tag_key(rec.tag_ids or [])
        groups[key].append(rec)
    return dict(groups)


# ============================================================
# 新增
# ============================================================

def _process_add_entries() -> dict[str, int]:
    """
    处理修改类型为 add 的队列记录。

    按 tag_ids 分组，相同 tag_ids 的 MSKU 合并到一个 bindDetail 请求中。
    成功后删除对应的队列记录。

    Returns:
        dict: {"processed": int, "success": int, "failed": int}
    """
    records = list(
        ListingTagModifyQueue.objects.filter(action=ModifyActionChoices.ADD).order_by("id")
    )
    if not records:
        logger.info("[ListingTagModifyService] 无新增标签的队列记录")
        return {"processed": 0, "success": 0, "failed": 0}

    logger.info("[ListingTagModifyService] 新增队列记录数=%d", len(records))
    success = 0
    failed = 0

    grouped = _group_by_tag_ids(records)
    for tag_key, group in grouped.items():
        tag_ids = tag_key.split(",") if tag_key else []
        bind_detail = [
            {"sid": rec.sid, "relationId": rec.msku}
            for rec in group
        ]

        try:
            body = {"bindDetail": bind_detail, "tagIds": tag_ids}
            resp = _post_api(_BIND_URL, body)

            if resp.get("code") == 0:
                record_ids = [rec.id for rec in group]
                ListingTagModifyQueue.objects.filter(id__in=record_ids).delete()
                success += len(group)
                logger.info(
                    "[ListingTagModifyService] 新增绑定成功 count=%d tag_ids=%s",
                    len(group), tag_ids,
                )
            else:
                failed += len(group)
                logger.error(
                    "[ListingTagModifyService] 新增绑定失败 tag_ids=%s code=%s msg=%s",
                    tag_ids, resp.get("code"), resp.get("message"),
                )

        except Exception:
            logger.exception(
                "[ListingTagModifyService] 新增绑定异常 tag_ids=%s", tag_ids,
            )
            failed += len(group)

    logger.info(
        "[ListingTagModifyService] 新增处理完成 processed=%d success=%d failed=%d",
        len(records), success, failed,
    )
    return {"processed": len(records), "success": success, "failed": failed}


# ============================================================
# 移除
# ============================================================

def _process_remove_entries() -> dict[str, int]:
    """
    处理修改类型为 remove 的队列记录。

    按 tag_ids 分组，相同 tag_ids 的 MSKU 合并到一个 bindDetail 请求中。
    成功后删除对应的队列记录。

    Returns:
        dict: {"processed": int, "success": int, "failed": int}
    """
    records = list(
        ListingTagModifyQueue.objects.filter(action=ModifyActionChoices.REMOVE).order_by("id")
    )
    if not records:
        logger.info("[ListingTagModifyService] 无移除标签的队列记录")
        return {"processed": 0, "success": 0, "failed": 0}

    logger.info("[ListingTagModifyService] 移除队列记录数=%d", len(records))
    success = 0
    failed = 0

    grouped = _group_by_tag_ids(records)
    for tag_key, group in grouped.items():
        tag_ids = tag_key.split(",") if tag_key else []
        bind_detail = [
            {"sid": rec.sid, "relationId": rec.msku}
            for rec in group
        ]

        try:
            body = {"bindDetail": bind_detail, "globalTagIds": tag_ids}
            resp = _post_api(_UNBIND_URL, body)

            if resp.get("code") == 0:
                record_ids = [rec.id for rec in group]
                ListingTagModifyQueue.objects.filter(id__in=record_ids).delete()
                success += len(group)
                logger.info(
                    "[ListingTagModifyService] 移除绑定成功 count=%d tag_ids=%s",
                    len(group), tag_ids,
                )
            else:
                failed += len(group)
                logger.error(
                    "[ListingTagModifyService] 移除绑定失败 tag_ids=%s code=%s msg=%s",
                    tag_ids, resp.get("code"), resp.get("message"),
                )

        except Exception:
            logger.exception(
                "[ListingTagModifyService] 移除绑定异常 tag_ids=%s", tag_ids,
            )
            failed += len(group)

    logger.info(
        "[ListingTagModifyService] 移除处理完成 processed=%d success=%d failed=%d",
        len(records), success, failed,
    )
    return {"processed": len(records), "success": success, "failed": failed}


# ============================================================
# 主流程
# ============================================================

def execute_listing_tag_modify() -> dict[str, Any]:
    """
    执行 Listing 商品标签修改任务：按修改类型分批处理新增和移除的队列记录。

    Returns:
        dict:
            {
                "add": {"processed": int, "success": int, "failed": int},
                "remove": {"processed": int, "success": int, "failed": int},
            }
    """
    logger.info("[ListingTagModifyService] 开始执行 Listing 商品标签修改同步")

    add_result = _process_add_entries()
    remove_result = _process_remove_entries()

    logger.info(
        "[ListingTagModifyService] 同步完成 add=%s remove=%s",
        add_result, remove_result,
    )
    return {
        "add": add_result,
        "remove": remove_result,
    }
