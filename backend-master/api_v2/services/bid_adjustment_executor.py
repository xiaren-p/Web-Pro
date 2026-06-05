"""竞价调整执行器（bid_adjustment_executor）。

读取 SpBidAdjustment 待执行记录，按关键词 / 定位组分两组，
调用 middle.hanlis.cn API 执行竞价调整并回写结果。
API 令牌桶容量为 1，必须串行执行，不可并行。
"""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import requests
from django.utils import timezone

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v2.models.lx_api_err import LxApiErr
from api_v2.models.sp_bid_adjustment import (
    AdjustmentStatusChoices, ExecutionStatusChoices, SpBidAdjustment,
)
from api_v2.services.qinglong_env_service import get_cached_env, refresh_with_task_trigger

logger = logging.getLogger(__name__)

_TARGET_API = "https://middle.hanlis.cn/basicOpen/adReport/manage/putSpTarget"
_KEYWORD_API = "https://middle.hanlis.cn/basicOpen/adReport/manage/putSpKeyword"
_API_BATCH_SIZE = 500
_API_TIMEOUT = 60


# ============================================================
# 辅助函数
# ============================================================

def _get_middle_headers() -> dict[str, str]:
    """从缓存获取 MIDDLE_API_HEADERS 并解析为请求头字典。"""
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


def _log_api_err(url: str, request_body: str, code: str = "", message: str = "") -> None:
    """写入 API 错误日志到 LxApiErr 表。"""
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


def _get_profile_sid(profile_id: int) -> int:
    """查询店铺 sid，失败返回 0。"""
    try:
        sid_raw = LxAdsProfile.objects.filter(profile_id=profile_id).values_list("sid", flat=True).first() or "0"
        return int(sid_raw) if str(sid_raw).isdigit() else 0
    except Exception:
        logger.warning("[bid_adjustment] 查询 sid 失败 profile=%d", profile_id, exc_info=True)
        return 0


def _build_payload(record: SpBidAdjustment) -> dict:
    """单条记录构建 API 参数字典。

    Returns:
        {"keywordId"/"targetId": int, "bid": float, "isBaseValue": 0}
    """
    bid = round(float(record.bid_after or 0), 2)
    if record.keyword_id:
        return {"keywordId": record.keyword_id, "bid": bid, "isBaseValue": 0}
    return {"targetId": record.target_id, "bid": bid, "isBaseValue": 0}


# ============================================================
# API 调用（含重试）
# ============================================================

def _call_api(
    url: str, profile_id: int, sid: int, items_key: str, payload: list[dict],
) -> list[dict]:
    """调用 middle API 并返回 apiResult 列表。

    最多重试 3 次；首次 401 时自动刷新认证头；最终失败时写入 LxApiErr。
    """
    body = {"sid": sid, "profile_id": profile_id, items_key: payload}
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
            data = resp.json()

            if data.get("code") in (0, 1):
                return (data.get("data") or {}).get("apiResult", [])

            if attempt < 2:
                logger.warning("[bid_adjustment] code=%s 第%d次重试", data.get("code"), attempt + 1)
                last_code, last_error = str(data.get("code", "")), data.get("message", "")
                time.sleep((attempt + 1) * 2)
                continue

            last_code, last_error = str(data.get("code", "")), data.get("message", "")
            break

        except requests.Timeout:
            if attempt < 2:
                time.sleep((attempt + 1) * 3)
                continue
            last_code, last_error = "TIMEOUT", "超时"
        except requests.ConnectionError:
            if attempt < 2:
                time.sleep((attempt + 1) * 3)
                continue
            last_code, last_error = "CONN_ERR", "连接失败"
        except requests.RequestException as e:
            if attempt < 2 and getattr(e, "response", None) is not None and e.response.status_code >= 500:
                time.sleep((attempt + 1) * 2)
                continue
            last_code = str(getattr(e, "response", None) and e.response.status_code or "ERR")
            last_error = str(e)
            break

    _log_api_err(url=url, request_body=body_str, code=last_code, message=last_error)
    logger.error("[bid_adjustment] API 最终失败 %s profile=%d: %s", url, profile_id, last_error)
    return []


# ============================================================
# 结果匹配
# ============================================================

def _apply_results(
    results: list[dict],
    records: list[SpBidAdjustment],
    now_utc: datetime,
    item_type: str,
) -> None:
    """将 API 返回结果按 keywordId / targetId 匹配并写入对应记录。

    Args:
        results: API 返回的 apiResult 列表
        records: 本批次对应的 SpBidAdjustment 记录列表
        now_utc: 调整时间
        item_type: "keyword" 或 "target"
    """
    id_field = "keywordId" if item_type == "keyword" else "targetId"

    id_to_record: dict[int, SpBidAdjustment] = {}
    for rec in records:
        rec_id = rec.keyword_id if item_type == "keyword" else rec.target_id
        if rec_id is not None:
            id_to_record[rec_id] = rec

    for result in results:
        result_id = result.get(id_field)
        if result_id is None:
            continue
        record = id_to_record.get(int(result_id))
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


# ============================================================
# 主流程
# ============================================================

def execute_bid_adjustment() -> dict[str, Any]:
    """执行竞价调整：读 PENDING 记录，按 profile 分组，分关键词 / 定位组请求 API 并回写。

    Returns:
        {"processed": int, "success": int, "failed": int, "errors": [str]}
    """
    records = list(SpBidAdjustment.objects.filter(
        adjustment_status=AdjustmentStatusChoices.PENDING,
        created_at__gte=timezone.now() - timezone.timedelta(hours=2),
    ).order_by("profile_id"))
    if not records:
        logger.info("[bid_adjustment] 无待执行记录")
        return {"processed": 0, "success": 0, "failed": 0, "errors": []}

    logger.info("[bid_adjustment] 待执行记录数=%d", len(records))

    # 按 profile_id 分组
    profile_groups: dict[int, list[SpBidAdjustment]] = defaultdict(list)
    for rec in records:
        profile_groups[rec.profile_id].append(rec)

    now_utc = timezone.now()
    all_updates: list[SpBidAdjustment] = []
    processed = 0
    success = 0
    failed = 0
    errors: list[str] = []

    for profile_id, group in profile_groups.items():
        try:
            sid = _get_profile_sid(profile_id)
            keywords: list[tuple[SpBidAdjustment, dict]] = []
            targets: list[tuple[SpBidAdjustment, dict]] = []

            for rec in group:
                if rec.keyword_id:
                    keywords.append((rec, _build_payload(rec)))
                else:
                    targets.append((rec, _build_payload(rec)))
                all_updates.append(rec)
                processed += 1

            # 分批调 API：关键词
            for i in range(0, len(keywords), _API_BATCH_SIZE):
                batch = keywords[i:i + _API_BATCH_SIZE]
                batch_records = [r for r, _ in batch]
                payload = [p for _, p in batch]
                results = _call_api(_KEYWORD_API, profile_id, sid, "keywords", payload)
                _apply_results(results, batch_records, now_utc, "keyword")

            # 分批调 API：定位组
            for i in range(0, len(targets), _API_BATCH_SIZE):
                batch = targets[i:i + _API_BATCH_SIZE]
                batch_records = [r for r, _ in batch]
                payload = [p for _, p in batch]
                results = _call_api(_TARGET_API, profile_id, sid, "targetingClauses", payload)
                _apply_results(results, batch_records, now_utc, "target")

            logger.info("[bid_adjustment] profile=%d done: total=%d", profile_id, len(group))

        except Exception:
            logger.exception("[bid_adjustment] profile=%d 异常", profile_id)
            errors.append(f"profile={profile_id}")

    # 一次 bulk_update 回写所有记录
    if all_updates:
        SpBidAdjustment.objects.bulk_update(
            all_updates,
            ["execution_status", "adjustment_status", "adjustment_time", "msg", "updated_at"],
            batch_size=500,
        )

    # 统计 API 实际调用结果
    for rec in all_updates:
        if rec.adjustment_status == AdjustmentStatusChoices.SUCCESS:
            if rec.execution_status == ExecutionStatusChoices.SUCCESS:
                success += 1
            elif rec.execution_status == ExecutionStatusChoices.FAILED:
                failed += 1

    logger.info("[bid_adjustment] 完成 processed=%d success=%d failed=%d errors=%d",
                processed, success, failed, len(errors))
    return {"processed": processed, "success": success, "failed": failed, "errors": errors}
