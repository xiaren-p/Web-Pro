"""广告活动调整执行器（campaign_adjustment_executor）。

读取 SpCampaignAdjustment 待执行记录，
调用 middle.hanlis.cn API 执行预算调整 / 广告活动暂停 / 广告活动启用并回写结果。
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
from django.core.cache import cache
from django.utils import timezone

from api_v1.models.lingxing.ads.basic.lx_ads_profile import LxAdsProfile
from api_v2.models.lx_api_err import LxApiErr
from api_v2.models.sp_campaign_adjustment import (
    CampaignExecutionTypeChoices,
    SpCampaignAdjustment,
)
from api_v2.models.sp_bid_adjustment import AdjustmentStatusChoices, ExecutionStatusChoices
from api_v2.services.qinglong_env_service import get_cached_env, refresh_with_task_trigger

logger = logging.getLogger(__name__)

_CAMPAIGN_API = "https://middle.hanlis.cn/basicOpen/adReport/manage/putSpCampaign"
_API_BATCH_SIZE = 500
_API_TIMEOUT = 60
_LOCK_KEY = "campaign_adjustment_lock"
_LOCK_TIMEOUT = 1800  # API 调用锁 TTL（仅异常兜底，正常路径 finally 中主动释放）


# ============================================================
# 辅助函数
# ============================================================

def _get_middle_headers() -> dict[str, str]:
    """从缓存获取 MIDDLE_API_HEADERS 并解析为请求头字典。"""
    raw = get_cached_env("MIDDLE_API_HEADERS") or ""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if not raw:
        logger.error("[campaign_adjustment] MIDDLE_API_HEADERS 缓存为空")
        return headers
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            headers.update(parsed)
    except json.JSONDecodeError:
        logger.exception("[campaign_adjustment] MIDDLE_API_HEADERS JSON 解析失败")
    return headers


def _log_api_err(url: str, request_body: str, code: str = "", message: str = "") -> None:
    """写入 API 错误日志到 LxApiErr 表。"""
    try:
        LxApiErr.objects.create(
            task="campaign_adjustment",
            task_name="广告活动调整",
            url=url,
            method="POST",
            parameter=request_body or "",
            code=str(code),
            message=str(message),
        )
    except Exception:
        logger.exception("[campaign_adjustment] 写入 LxApiErr 失败")


def _get_profile_sid(profile_id: int) -> int:
    """查询店铺 sid，失败返回 0。"""
    try:
        sid_raw = LxAdsProfile.objects.filter(profile_id=profile_id).values_list("sid", flat=True).first() or "0"
        return int(sid_raw) if str(sid_raw).isdigit() else 0
    except Exception:
        logger.warning("[campaign_adjustment] 查询 sid 失败 profile=%d", profile_id, exc_info=True)
        return 0


def _build_payload(record: SpCampaignAdjustment) -> dict:
    """单条记录构建 API 参数字典。

    CAMPAIGN_PAUSE 类型：传 state=paused + isBaseValue=0。
    CAMPAIGN_ENABLE 类型：传 state=enabled + isBaseValue=0。
    预算调整类型：传 budget={"budgetType":"DAILY","budget":X.XX} + isBaseValue=0。

    Returns:
        {"campaignId": int, ...}
    """
    base: dict[str, Any] = {"campaignId": record.campaign_id, "isBaseValue": 0}

    if record.execution_type == CampaignExecutionTypeChoices.CAMPAIGN_PAUSE:
        base["state"] = "paused"
        return base

    if record.execution_type == CampaignExecutionTypeChoices.CAMPAIGN_ENABLE:
        base["state"] = "enabled"
        return base

    # 预算调整类型：RULE_BUDGET_ADJUSTMENT / MANUAL_BUDGET_ADJUSTMENT
    budget = round(float(record.budget_after or 0), 2)
    base["budget"] = {"budgetType": "DAILY", "budget": budget}
    return base


# ============================================================
# API 调用（含重试）
# ============================================================

def _call_api(
    url: str, profile_id: int, sid: int, payload: list[dict],
) -> list[dict]:
    """调用 middle API 并返回 apiResult 列表。

    最多重试 3 次；首次 401 时自动刷新认证头；最终失败时写入 LxApiErr。
    """
    body: dict[str, Any] = {"sid": sid, "profile_id": profile_id, "campaigns": payload}
    body_str = json.dumps(body, ensure_ascii=False)
    headers = _get_middle_headers()
    last_code, last_error = "ERR", ""

    for attempt in range(3):
        try:
            resp = requests.post(url, json=body, headers=headers, timeout=_API_TIMEOUT)

            if resp.status_code == 401 and attempt == 0:
                logger.warning("[campaign_adjustment] 401，刷新 MIDDLE_API_HEADERS")
                try:
                    refresh_with_task_trigger()
                    headers = _get_middle_headers()
                except Exception:
                    logger.exception("[campaign_adjustment] 刷新失败")
                continue

            resp.raise_for_status()
            data = resp.json()

            if data.get("code") in (0, 1):
                return (data.get("data") or {}).get("apiResult", [])

            if attempt < 2:
                logger.warning("[campaign_adjustment] code=%s 第%d次重试", data.get("code"), attempt + 1)
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
    logger.error("[campaign_adjustment] API 最终失败 %s profile=%d: %s", url, profile_id, last_error)
    return []


# ============================================================
# 结果匹配
# ============================================================

def _apply_results(
    results: list[dict],
    records: list[SpCampaignAdjustment],
    now_utc: datetime,
) -> None:
    """将 API 返回结果按 campaignId 匹配并写入对应记录。

    成功时写 msg，四种类型各写不同描述。

    Args:
        results: API 返回的 apiResult 列表
        records: 本批次对应的 SpCampaignAdjustment 记录列表
        now_utc: 调整时间
    """
    id_to_record: dict[int, SpCampaignAdjustment] = {
        rec.campaign_id: rec for rec in records
    }

    for result in results:
        result_id = result.get("campaignId")
        if result_id is None:
            continue
        record = id_to_record.get(int(result_id))
        if record is None:
            continue

        is_pause = record.execution_type == CampaignExecutionTypeChoices.CAMPAIGN_PAUSE
        is_enable = record.execution_type == CampaignExecutionTypeChoices.CAMPAIGN_ENABLE
        is_budget_rule = record.execution_type == CampaignExecutionTypeChoices.RULE_BUDGET_ADJUSTMENT
        is_budget_manual = record.execution_type == CampaignExecutionTypeChoices.MANUAL_BUDGET_ADJUSTMENT

        if result.get("code") == "SUCCESS":
            record.execution_status = ExecutionStatusChoices.SUCCESS
            if is_pause:
                record.msg = "广告活动暂停成功"
            elif is_enable:
                record.msg = "广告活动启用成功"
            elif is_budget_rule:
                before = round(float(record.budget_before or 0), 4)
                after = round(float(record.budget_after or 0), 4)
                record.msg = f"规则预算调整成功 {before} → {after}"
            elif is_budget_manual:
                before = round(float(record.budget_before or 0), 4)
                after = round(float(record.budget_after or 0), 4)
                record.msg = f"手动预算调整成功 {before} → {after}"
        else:
            record.execution_status = ExecutionStatusChoices.FAILED
            error_desc = result.get("description", "unknown")
            if is_pause:
                record.msg = f"广告活动暂停失败，error: {error_desc}"
            elif is_enable:
                record.msg = f"广告活动启用失败，error: {error_desc}"
            elif is_budget_rule:
                record.msg = f"规则预算调整失败，error: {error_desc}"
            elif is_budget_manual:
                record.msg = f"手动预算调整失败，error: {error_desc}"

        record.adjustment_status = AdjustmentStatusChoices.SUCCESS
        record.adjustment_time = now_utc


# ============================================================
# 主流程
# ============================================================

def execute_campaign_adjustment() -> dict[str, Any]:
    """执行广告活动调整：读 PENDING 记录，按 profile 分组，请求 API 并回写。

    TaskExecutionLock 已在任务体层做并发控制，此处不重复加锁。

    四种类型（规则预算调整 / 手动预算调整 / 广告活动暂停 / 广告活动启用）统一执行。

    Returns:
        {"processed": int, "success": int, "failed": int, "errors": [str]}
    """
    return _execute()


def _execute() -> dict[str, Any]:
    records = list(SpCampaignAdjustment.objects.filter(
        adjustment_status=AdjustmentStatusChoices.PENDING,
        created_at__gte=timezone.now() - timezone.timedelta(hours=2),
    ).order_by("profile_id"))
    if not records:
        logger.info("[campaign_adjustment] 无待执行记录")
        return {"processed": 0, "success": 0, "failed": 0, "errors": []}

    logger.info("[campaign_adjustment] 待执行记录数=%d", len(records))

    # 按 profile_id 分组
    profile_groups: dict[int, list[SpCampaignAdjustment]] = defaultdict(list)
    for rec in records:
        profile_groups[rec.profile_id].append(rec)

    now_utc = timezone.now()
    all_updates: list[SpCampaignAdjustment] = []
    processed = 0
    success = 0
    failed = 0
    errors: list[str] = []

    for profile_id, group in profile_groups.items():
        try:
            sid = _get_profile_sid(profile_id)

            campaign_pairs: list[tuple[SpCampaignAdjustment, dict]] = []
            for rec in group:
                campaign_pairs.append((rec, _build_payload(rec)))
                all_updates.append(rec)
                processed += 1

            # 分批调 API
            for i in range(0, len(campaign_pairs), _API_BATCH_SIZE):
                batch = campaign_pairs[i:i + _API_BATCH_SIZE]
                batch_records = [r for r, _ in batch]
                payload = [p for _, p in batch]
                results = _call_api(_CAMPAIGN_API, profile_id, sid, payload)
                _apply_results(results, batch_records, now_utc)

            logger.info("[campaign_adjustment] profile=%d done: total=%d", profile_id, len(group))

        except Exception:
            logger.exception("[campaign_adjustment] profile=%d 异常", profile_id)
            errors.append(f"profile={profile_id}")

    # 一次 bulk_update 回写所有记录
    if all_updates:
        SpCampaignAdjustment.objects.bulk_update(
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

    logger.info("[campaign_adjustment] 完成 processed=%d success=%d failed=%d errors=%d",
                processed, success, failed, len(errors))
    return {"processed": processed, "success": success, "failed": failed, "errors": errors}
