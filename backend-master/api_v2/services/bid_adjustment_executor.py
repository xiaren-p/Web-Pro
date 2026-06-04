"""竞价调整执行器（bid_adjustment_executor）。

按 profile_id 分组获取 SpBidAdjustment 待执行记录，
构建 middle.hanlis.cn API 参数并调用，回写执行结果。

API 令牌桶容量为 1，必须串行执行，不可并行。
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone as dt_timezone
from typing import Any

import requests

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v2.models.lx_api_err import LxApiErr
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, ExecutionTypeChoices, SpBidAdjustment,
)
from api_v2.services.qinglong_env_service import get_cached_env, refresh_with_task_trigger

logger = logging.getLogger(__name__)

# middle.hanlis.cn API 端点
_TARGET_API = "https://middle.hanlis.cn/basicOpen/adReport/manage/putSpTarget"
_KEYWORD_API = "https://middle.hanlis.cn/basicOpen/adReport/manage/putSpKeyword"
_API_BATCH_SIZE = 500
_API_TIMEOUT = 60


# ============================================================
# 获取 API 鉴权头
# ============================================================

def _get_middle_headers() -> dict[str, str]:
    """从缓存获取 MIDDLE_API_HEADERS，JSON 解析为请求头字典。

    Returns:
        {"Content-Type": "application/json", ...}
    """
    raw = get_cached_env("MIDDLE_API_HEADERS") or ""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if not raw:
        logger.error("[bid_adjustment] MIDDLE_API_HEADERS 缓存为空")
        return headers
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            headers.update(parsed)
    except json.JSONDecodeError:
        logger.exception("[bid_adjustment] MIDDLE_API_HEADERS JSON 解析失败")
    return headers


# ============================================================
# API 日志
# ============================================================

def _log_api_err(
    url: str, request_body: str,
    code: str = "", message: str = "",
) -> None:
    """写入 API 错误日志。

    Args:
        url: 请求的完整 URL
        request_body: 请求体（截断）
        code: HTTP 状态码或 API 错误码
        message: 错误信息
    """
    try:
        LxApiErr.objects.create(
            task="bid_adjustment",
            task_name="竞价调整",
            url=url,
            method="POST",
            parameter=request_body or "",
            code=str(code),
            message=str(message),
        )
    except Exception:
        logger.exception("[bid_adjustment] 写入 LxApiErr 失败")


# ============================================================
# API 调用
# ============================================================

def _call_api(
    url: str, profile_id: int, items_key: str, payload: list[dict],
) -> list[dict]:
    """调用 middle API，返回 apiResult 列表。最多重试 3 次。"""
    sid = ""
    try:
        sid_raw = LxAdsProfile.objects.filter(profile_id=profile_id).values_list("sid", flat=True).first() or "0"
        sid = int(sid_raw) if str(sid_raw).isdigit() else 0
    except Exception:
        logger.warning("[bid_adjustment] 查询 sid 失败 profile=%d", profile_id, exc_info=True)

    body = {"sid": sid, "profile_id": profile_id, items_key: payload}
    return _call_api_with_retry(url, body, profile_id)


def _handle_response(resp: requests.Response) -> tuple[list[dict] | None, dict | None]:
    """处理 middle API HTTP 响应。

    Returns:
        (apiResult, None) 成功时；(None, error_dict) 需要重试时；
        (None, None) 不可重试的失败。
        error_dict = {"code": str, "message": str, "retry": bool}
    """
    data = resp.json()
    if data.get("code") in (0, 1):
        return (data.get("data") or {}).get("apiResult", []), None
    # 应用层错误（100、500等）
    retry = data.get("code") not in (0, 1, "0", "1")
    return None, {"code": str(data.get("code", "")), "message": data.get("message", ""), "retry": retry}


def _call_api_with_retry(url: str, body: dict, profile_id: int) -> list[dict]:
    """带重试机制的 HTTP POST 调用，最多 3 次。"""
    body_str = json.dumps(body, ensure_ascii=False)
    headers = _get_middle_headers()
    last_code, last_error = "ERR", ""

    for attempt in range(3):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=_API_TIMEOUT)

            if resp.status_code == 401 and attempt == 0:
                logger.warning("[bid_adjustment] 401，刷新 MIDDLE_API_HEADERS")
                try:
                    refresh_with_task_trigger()
                    headers = _get_middle_headers()
                except Exception:
                    logger.exception("[bid_adjustment] 刷新失败")
                continue

            resp.raise_for_status()
            result, err = _handle_response(resp)
            if result is not None:
                return result
            if err and err.get("retry") and attempt < 2:
                logger.warning("[bid_adjustment] code=%s 第%d次重试", err["code"], attempt + 1)
                last_code, last_error = err["code"], err["message"]
                time.sleep((attempt + 1) * 2)
                continue
            last_code, last_error = err["code"] if err else "", err["message"] if err else ""
            break

        except requests.Timeout:
            if attempt < 2:
                time.sleep((attempt + 1) * 3); continue
            last_code, last_error = "TIMEOUT", "超时"
        except requests.ConnectionError:
            if attempt < 2:
                time.sleep((attempt + 1) * 3); continue
            last_code, last_error = "CONN_ERR", "连接失败"
        except requests.RequestException as e:
            if attempt < 2 and getattr(e, "response", None) is not None and e.response.status_code >= 500:
                time.sleep((attempt + 1) * 2); continue
            last_code = str(getattr(e, "response", None) and e.response.status_code or "ERR")
            last_error = str(e)
            break

    _log_api_err(url=url, request_body=body_str, code=last_code, message=last_error)
    logger.error("[bid_adjustment] API 最终失败 %s profile=%d: %s", url, profile_id, last_error)
    return []


# ============================================================
# 比较竞价 + 构建 payload
# ============================================================

def _bid_changed(record: SpBidAdjustment) -> bool:
    """判断调整前后竞价是否不同。"""
    before = float(record.bid_before or 0)
    after = float(record.bid_after or 0)
    return before != after


def _build_item_payload(record: SpBidAdjustment) -> dict:
    """单条记录构建 API 参数，所有字段必须存在（空字符串占位）。

    Returns:
        {"keywordId"/"targetId": ..., "state": "", "bid": ..., "isBaseValue": 0, "baseType": "", "baseValue": ""}
    """
    bid = round(float(record.bid_after or 0), 2)
    if record.keyword_id:
        return {"keywordId": record.keyword_id, "bid": bid, "isBaseValue": 0}
    return {"targetId": record.target_id, "bid": bid, "isBaseValue": 0}


# ============================================================
# 主流程
# ============================================================

def _process_profile_group(
    profile_id: int, group: list[SpBidAdjustment], now_utc: datetime,
) -> dict[str, int]:
    """处理单个 profile 的竞价调整记录。

    Args:
        profile_id: 店铺 Profile ID
        group: 该 profile 的待处理记录列表
        now_utc: 当前 UTC 时间

    Returns:
        {"total": int, "success": int, "failed": int}
    """
    keywords: list[dict] = []
    targets: list[dict] = []
    group_updates: list[SpBidAdjustment] = []
    success = 0

    for rec in group:
        if not _bid_changed(rec):
            rec.execution_status = ExecutionStatusChoices.SUCCESS
            rec.adjustment_status = AdjustmentStatusChoices.SUCCESS
            rec.adjustment_time = now_utc
            rec.msg = "竞价调整值不变，无需调整"
            group_updates.append(rec)
            success += 1
            continue
        if rec.keyword_id:
            keywords.append(_build_item_payload(rec))
        else:
            targets.append(_build_item_payload(rec))
        group_updates.append(rec)

    # 先批量更新未变化的记录
    unchanged = [r for r in group_updates if r.execution_status == ExecutionStatusChoices.SUCCESS]
    if unchanged:
        SpBidAdjustment.objects.bulk_update(
            unchanged,
            ["execution_status", "adjustment_status", "adjustment_time", "msg", "updated_at"],
        )

    # 调用 API
    _call_api_batch(_KEYWORD_API, profile_id, "keywords", keywords, group_updates, now_utc)
    _call_api_batch(_TARGET_API, profile_id, "targetingClauses", targets, group_updates, now_utc)

    # 批量更新 API 调用后的所有记录
    api_processed = [r for r in group_updates if r.adjustment_status == AdjustmentStatusChoices.SUCCESS and r.msg != "竞价调整值不变，无需调整"]
    if api_processed:
        SpBidAdjustment.objects.bulk_update(
            api_processed,
            ["execution_status", "adjustment_status", "adjustment_time", "msg", "updated_at"],
            batch_size=500,
        )
    sc = sum(1 for r in api_processed if r.execution_status == ExecutionStatusChoices.SUCCESS)
    return {"total": len(group), "success": success + sc, "failed": len(api_processed) - sc}


def _call_api_batch(
    api_url: str, profile_id: int, items_key: str,
    items: list[dict], group_updates: list[SpBidAdjustment], now_utc: datetime,
) -> None:
    """分批调用 middle API 并应用结果。

    Args:
        api_url: API 端点 URL
        profile_id: 店铺 Profile ID
        items_key: 列表字段名
        items: 待发送的投放项列表
        group_updates: 当前 profile 的待更新记录列表
        now_utc: 当前 UTC 时间
    """
    for i in range(0, len(items), _API_BATCH_SIZE):
        batch = items[i:i + _API_BATCH_SIZE]
        results = _call_api(api_url, profile_id, items_key, batch)
        _apply_api_results(batch, results, group_updates, now_utc, items_key)


def execute_bid_adjustment() -> dict[str, Any]:
    """执行竞价调整：按 profile_id 分批处理 PENDING 记录，调用 middle API。

    Returns:
        {"processed": int, "success": int, "failed": int, "errors": [str]}
    """
    records = list(SpBidAdjustment.objects.filter(
        adjustment_status=AdjustmentStatusChoices.PENDING,
    ).order_by("profile_id"))
    if not records:
        logger.info("[bid_adjustment] 无待执行记录")
        return {"processed": 0, "success": 0, "failed": 0, "errors": []}

    logger.info("[bid_adjustment] 待执行记录数=%d", len(records))
    profile_groups: dict[int, list[SpBidAdjustment]] = defaultdict(list)
    for rec in records:
        profile_groups[rec.profile_id].append(rec)

    now_utc = datetime.now(dt_timezone.utc)
    processed = 0
    success = 0
    failed = 0
    errors: list[str] = []

    for profile_id, group in profile_groups.items():
        try:
            result = _process_profile_group(profile_id, group, now_utc)
            processed += result["total"]
            success += result["success"]
            failed += result["failed"]
            logger.info("[bid_adjustment] profile=%d done: total=%d success=%d failed=%d",
                        profile_id, result["total"], result["success"], result["failed"])
        except Exception:
            logger.exception("[bid_adjustment] profile=%d 异常", profile_id)
            errors.append(f"profile={profile_id}")

    logger.info("[bid_adjustment] 完成 processed=%d success=%d failed=%d errors=%d",
                processed, success, failed, len(errors))
    return {"processed": processed, "success": success, "failed": failed, "errors": errors}


def _apply_api_results(
    batch: list[dict], results: list[dict],
    group_updates: list[SpBidAdjustment], now_utc: datetime,
    item_type: str,
) -> None:
    """将 API 返回结果写入对应 SpBidAdjustment 记录。

    匹配策略：
      1. 优先按 result 中的 targetId/keywordId 匹配
      2. 失败记录的 ID 可能为 null → 按 batch 索引匹配为备选
    """
    id_field = "keywordId" if item_type == "keyword" else "targetId"

    # 构建 batch 索引的反向映射（仅用于 ID 为 null 的失败匹配）
    idx_to_record: dict[int, SpBidAdjustment] = {}
    for idx, item in enumerate(batch):
        item_id = int(item.get(id_field, 0))
        for rec in group_updates:
            rec_id = rec.keyword_id if item_type == "keyword" else rec.target_id
            if rec_id == item_id:
                idx_to_record[idx] = rec
                break

    for idx, result in enumerate(results):
        # 先按 ID 匹配
        result_id = result.get(id_field)
        record = None
        if result_id is not None:
            for rec in group_updates:
                rec_id = rec.keyword_id if item_type == "keyword" else rec.target_id
                if rec_id == int(result_id):
                    record = rec
                    break

        # ID 为 null 或匹配不到 → 按索引匹配
        if record is None and idx < len(batch):
            record = idx_to_record.get(idx)

        if record is None:
            continue

        if result.get("code") == "SUCCESS":
            record.execution_status = ExecutionStatusChoices.SUCCESS
            before = round(float(record.bid_before or 0), 4)
            after = round(float(record.bid_after or 0), 4)
            record.msg = f"竞价调整成功 {before} → {after}"
        else:
            record.execution_status = ExecutionStatusChoices.FAILED
            record.msg = f"竞价调整失败，error: {result.get('description', 'unknown')}"

        record.adjustment_status = AdjustmentStatusChoices.SUCCESS
        record.adjustment_time = now_utc
