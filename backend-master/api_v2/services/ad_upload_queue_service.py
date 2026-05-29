"""广告上传队列业务服务（ad_upload_queue_service）。

职责：
  1. 解析上传的 xlsx 文件，按（广告活动 × 国家）粒度拆分并批量创建队列记录。
  2. 批量删除队列记录。

解析逻辑与 processor.py 保持对齐：
  - 读取主表 Sheet1（店铺名、广告活动名称、SKU）
  - 读取各国家站点 sheet（DE/IT/FR/ES/UK），提取关键词
  - 按（店铺 × 广告活动 × 国家）三维展开，每个组合落一条队列记录
"""

import logging
import os
import re
import tempfile
from typing import Any

import pandas as pd
from django.contrib.auth.models import User
from django.db import transaction

from api_v2.models.ad_upload_queue import AdParseStatus, AdUploadQueue

logger = logging.getLogger(__name__)

# ── 常量（与 processor.py 对齐）────────────────────────────────────────────────
_MAIN_SHEET: str = "Sheet1"
_COL_SHOP: str = "店铺名"
_COL_AD_NAME: str = "广告活动名称"
_COL_SKU: str = "SKU"
_REQUIRED_COLS: tuple[str, ...] = (_COL_SHOP, _COL_AD_NAME, _COL_SKU)
_KEYWORD_HEADER: str = "关键词"
_START_PREFIX: str = "START "
_END_TOKEN: str = "END"
_TARGET_SITES: tuple[str, ...] = ("DE", "IT", "FR", "ES", "UK")

_SHOP_RE = re.compile(r"^[a-zA-Z0-9]+$")
_AD_NAME_RE = re.compile(
    r"^[a-zA-Z0-9+]+(?:-[a-zA-Z0-9+]+)*(?:\s+[a-zA-Z0-9+]+(?:-[a-zA-Z0-9+]+)*)*$"
)
_SKU_RE = re.compile(r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$")


# ── 内部解析辅助函数 ────────────────────────────────────────────────────────────

def _find_keyword_col_index(row: pd.Series) -> int:
    """在候选表头行中查找"关键词"列的索引。

    Args:
        row (pd.Series): 当前候选表头行。

    Returns:
        int: 命中时返回 0-based 列索引；未命中返回 -1。
    """
    for col_idx, val in enumerate(row):
        if str(val).strip() == _KEYWORD_HEADER:
            return col_idx
    return -1


def _parse_site_sheet(df: pd.DataFrame) -> dict[str, list[str]]:
    """解析单个站点 sheet，提取"广告活动名 → 关键词列表"映射。

    使用状态机识别 START <广告名> → 表头 → 数据行 → END 块结构。

    Args:
        df (pd.DataFrame): 已用 header=None 读出的整张站点 sheet。

    Returns:
        dict[str, list[str]]: {"广告活动名": ["关键词1", ...]}。
    """
    keywords_map: dict[str, list[str]] = {}
    current_ad_name: str = ""
    keyword_col_index: int = -1
    state: str = "searching"

    for _, row in df.iterrows():
        first_col = str(row[0]).strip() if pd.notna(row[0]) else ""

        if state == "searching":
            if first_col.startswith(_START_PREFIX):
                current_ad_name = first_col[len(_START_PREFIX):].strip()
                keywords_map.setdefault(current_ad_name, [])
                state = "reading_header"
            continue

        if state == "reading_header":
            keyword_col_index = _find_keyword_col_index(row)
            state = "reading_data" if keyword_col_index >= 0 else "searching"
            continue

        # state == "reading_data"
        if first_col == _END_TOKEN:
            state = "searching"
            current_ad_name = ""
            keyword_col_index = -1
            continue

        if 0 <= keyword_col_index < len(row):
            kw = row[keyword_col_index]
            if pd.notna(kw):
                keywords_map[current_ad_name].append(str(kw).strip())

    return keywords_map


def _read_site_keywords(file_path: str) -> dict[str, dict[str, list[str]]]:
    """读取文件中所有可用站点 sheet 的关键词映射。

    Args:
        file_path (str): xlsx 文件绝对路径。

    Returns:
        dict[str, dict[str, list[str]]]: {"DE": {"广告活动名": ["kw1", ...]}, ...}
    """
    result: dict[str, dict[str, list[str]]] = {}
    try:
        xls = pd.ExcelFile(file_path, engine="openpyxl")
        sheet_names = xls.sheet_names
    except Exception as exc:
        logger.warning(
            "[AdUploadQueueService][_read_site_keywords] 打开 Excel 失败: %s", exc
        )
        return result

    for site in _TARGET_SITES:
        if site not in sheet_names:
            continue
        try:
            site_df = pd.read_excel(file_path, sheet_name=site, header=None, engine="openpyxl")
            result[site] = _parse_site_sheet(site_df)
            logger.info(
                "[AdUploadQueueService][_read_site_keywords] 站点 %s 解析完成: ad_count=%s",
                site, len(result[site]),
            )
        except Exception as exc:
            logger.warning(
                "[AdUploadQueueService][_read_site_keywords] 站点 %s 读取失败: %s", site, exc
            )

    return result


def _get_group_error(shop: str, ad_name: str, group: pd.DataFrame) -> str | None:
    """校验一个（店铺 × 广告活动）分组的合规性。

    依次检查店铺名、广告活动名称、组内每条 SKU，遇到第一处问题即返回错误描述。
    全部合规返回 None。

    Args:
        shop (str): 店铺名（已 ffill 归一化）。
        ad_name (str): 广告活动名称（已 ffill 归一化）。
        group (pd.DataFrame): 该分组的所有数据行。

    Returns:
        str | None: 错误描述字符串；无错误返回 None。
    """
    if not _SHOP_RE.match(shop):
        return f"{_COL_SHOP}='{shop}' 格式不合规（仅允许英文字母和数字）"

    if not _AD_NAME_RE.match(ad_name):
        return f"{_COL_AD_NAME}='{ad_name}' 格式不合规"

    for _, row in group.iterrows():
        if pd.notna(row[_COL_SKU]):
            sku = str(row[_COL_SKU])
            if not _SKU_RE.match(sku):
                return f"{_COL_SKU}='{sku}' 格式不合规（仅允许字母/数字/横杠）"

    return None


# ── 内部核心解析实现 ────────────────────────────────────────────────────────────

def _do_parse_and_create(
    tmp_path: str,
    user: User | None,
) -> tuple[list[AdUploadQueue], str | None]:
    """执行 xlsx 解析并批量落库。

    Args:
        tmp_path (str): 已落盘的 xlsx 临时文件绝对路径。
        user (User | None): 当前操作用户。

    Returns:
        tuple[list[AdUploadQueue], str | None]:
            - 已创建的记录列表（成功时非空）。
            - error_msg：文件级错误时非 None，此时列表为空。
    """
    # 1. 读主表
    try:
        df = pd.read_excel(tmp_path, sheet_name=_MAIN_SHEET, engine="openpyxl")
    except ValueError as exc:
        if "Worksheet named" in str(exc):
            return [], f"文件中未找到 '{_MAIN_SHEET}' 工作表"
        return [], f"读取主表失败：{exc}"
    except Exception as exc:
        return [], f"读取文件失败：{exc}"

    # 2. 校验必需列
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        return [], f"主表缺少必需列：{', '.join(missing)}"

    # 3. 读站点关键词
    site_keywords = _read_site_keywords(tmp_path)

    # 4. 归一化主表（向下填充店铺名/广告活动名）
    df[_COL_SHOP] = df[_COL_SHOP].ffill()
    shop_group_id = (df[_COL_SHOP] != df[_COL_SHOP].shift()).cumsum()
    df[_COL_AD_NAME] = df.groupby(shop_group_id)[_COL_AD_NAME].ffill()
    df = df.dropna(subset=[_COL_SHOP, _COL_AD_NAME])

    # 5. 按（店铺 × 广告活动 × 国家）三维展开，内联校验并构造队列记录。
    #    格式不合规的分组不阻断整体上传，改为以 FAILED 状态落库并在 msg 中注明原因，
    #    其余合规分组正常以 SUCCESS 状态写入。
    records_to_create: list[AdUploadQueue] = []
    for shop, shop_group in df.groupby(_COL_SHOP, sort=False):
        for ad_name, ad_group in shop_group.groupby(_COL_AD_NAME, sort=False):
            error_msg = _get_group_error(str(shop), str(ad_name), ad_group)

            if error_msg:
                # 校验失败：5 个站点全部以 FAILED 状态落库，SKU/关键词留空
                for site in _TARGET_SITES:
                    records_to_create.append(
                        AdUploadQueue(
                            campaign_name=str(ad_name),
                            shop=str(shop),
                            country=site,
                            ad_type="sp",
                            skus=[],
                            keywords=[],
                            parse_status=AdParseStatus.FAILED,
                            msg=error_msg,
                            created_by=user,
                        )
                    )
            else:
                # 校验通过：正常展开 5 个站点
                skus: list[str] = ad_group[_COL_SKU].dropna().astype(str).tolist()
                if not skus:
                    continue
                for site in _TARGET_SITES:
                    keywords: list[str] = site_keywords.get(site, {}).get(str(ad_name), [])
                    records_to_create.append(
                        AdUploadQueue(
                            campaign_name=str(ad_name),
                            shop=str(shop),
                            country=site,
                            ad_type="sp",
                            skus=skus,
                            keywords=keywords,
                            parse_status=AdParseStatus.SUCCESS,
                            msg="成功",
                            created_by=user,
                        )
                    )

    if not records_to_create:
        return [], "文件中未解析出有效广告数据，请检查主表内容"

    # 7. 批量落库（原子操作）
    with transaction.atomic():
        created = AdUploadQueue.objects.bulk_create(records_to_create)

    logger.info(
        "[AdUploadQueueService][parse_and_create_queue] 队列记录创建完成: count=%s user=%s",
        len(created), user,
    )
    return created, None


# ── 对外公共入口 ────────────────────────────────────────────────────────────────

def parse_and_create_queue(
    file_obj: Any,
    user: User | None,
) -> tuple[list[AdUploadQueue], str | None]:
    """解析上传的 xlsx 文件并批量创建广告上传队列记录。

    整体流程：写临时文件 → 解析主表 → 读站点关键词 → 合规校验 → 批量落库。
    任何文件级错误均以 error_msg 返回，不抛出异常。

    Args:
        file_obj: Django InMemoryUploadedFile 或实现了 chunks() 方法的类文件对象。
        user (User | None): 当前操作用户，用于记录创建者。

    Returns:
        tuple[list[AdUploadQueue], str | None]:
            - 已创建的 AdUploadQueue 记录列表（文件级错误时为空列表）。
            - error_msg：文件级错误时非 None，成功时为 None。
    """
    try:
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
            for chunk in file_obj.chunks():
                tmp.write(chunk)
    except Exception as exc:
        logger.error(
            "[AdUploadQueueService][parse_and_create_queue] 临时文件写入失败: %s",
            exc, exc_info=True,
        )
        return [], f"文件读取失败：{exc}"

    try:
        return _do_parse_and_create(tmp_path, user)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def bulk_delete_queue(ids: list[int], user: User | None) -> int:
    """按 ID 列表批量删除队列记录。

    Args:
        ids (list[int]): 要删除的记录 ID 列表。
        user (User | None): 当前操作用户（仅用于日志）。

    Returns:
        int: 实际删除的记录数。
    """
    deleted_count, _ = AdUploadQueue.objects.filter(id__in=ids).delete()
    logger.info(
        "[AdUploadQueueService][bulk_delete_queue] 批量删除完成: count=%s user=%s",
        deleted_count, user,
    )
    return deleted_count
