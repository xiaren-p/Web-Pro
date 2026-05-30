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

from api_v1.models.lingxing.basic.lx_shops import LxShops
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
# 子表名合规性校验：仅接受标准两位大写国家代码（如 DE / UK / US），超出范围的子表直接跳过。
_SITE_NAME_RE = re.compile(r"^[A-Z]{2}$")

# 广告类型推断：广告活动名末尾 token 决定投放类型（AUTO → 自动投放，MANU → 手动投放）
_AD_TYPE_MAP: dict[str, str] = {"AUTO": "auto", "MANU": "manual"}

# 竞价参数各字段默认値（与 AdUploadQueue.params 结构对齐）
_BIDDING_DEFAULTS: dict[str, float] = {
    "daily_budget": 1.00,
    "default_bid": 0.12,
    "close_match_bid": 0.12,
    "loose_match_bid": 0.10,
    "substitutes_bid": 0.10,
    "complements_bid": 0.10,
}

_SHOP_RE = re.compile(r"^[a-zA-Z0-9]+$")
_AD_NAME_RE = re.compile(
    r"^[a-zA-Z0-9+]+(?:-[a-zA-Z0-9+]+)*(?:\s+[a-zA-Z0-9+]+(?:-[a-zA-Z0-9+]+)*)*$"
)
_SKU_RE = re.compile(r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$")


# ── 内部解析辅助函数 ────────────────────────────────────────────────────────────

def _build_params(skus: list[str], keywords: list[str], bp: dict[str, float]) -> dict:
    """构造广告队列记录的 params 字段完整内容。

    将 skus、keywords 与各竞价字段封装为单一字典，bp 缺键时取各字段默认値。

    Args:
        skus (list[str]): SKU 列表。
        keywords (list[str]): 关键词列表。
        bp (dict[str, float]): 竞价参数，键名与 _BIDDING_DEFAULTS 一致。

    Returns:
        dict: params 字段的完整内容。
    """
    return {
        "skus": skus,
        "keywords": keywords,
        **{k: bp.get(k, default) for k, default in _BIDDING_DEFAULTS.items()},
    }


def _infer_ad_type(ad_name: str) -> str:
    """根据广告活动名称末尾 token 推断广告类型。

    末尾 token 为 "AUTO" 时为自动投放，为 "MANU" 时为手动投放，其他默认 "auto"。

    Args:
        ad_name (str): 广告活动名称，如 "X-HLS-LQ-SR AUTO" 或 "X-HLS-LQ-SR MANU"。

    Returns:
        str: "auto" 或 "manual"。
    """
    last_token = ad_name.strip().rsplit(" ", 1)[-1].upper()
    return _AD_TYPE_MAP.get(last_token, "auto")


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
    """读取文件中所有合规子表的关键词映射。

    合规子表：表名匹配 `_SITE_NAME_RE`（两位大写字母）且不为主表 Sheet1。
    返回 dict 的 key 即为实际发现的有效站点列表，展开时以此为准。

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

    for sheet in sheet_names:
        # 子表名合规性过滤：必须为两位大写字母（标准国家代码）
        if not _SITE_NAME_RE.match(sheet):
            continue
        try:
            site_df = pd.read_excel(file_path, sheet_name=sheet, header=None, engine="openpyxl")
            result[sheet] = _parse_site_sheet(site_df)
            logger.info(
                "[AdUploadQueueService][_read_site_keywords] 站点 %s 解析完成: ad_count=%s",
                sheet, len(result[sheet]),
            )
        except Exception as exc:
            logger.warning(
                "[AdUploadQueueService][_read_site_keywords] 站点 %s 读取失败: %s", sheet, exc
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
    ad_type_filter: str,
    country_filter: list[str] | None,
    bidding_params: dict[str, float] | None = None,
) -> tuple[list[AdUploadQueue], str | None, list[str]]:
    """执行 xlsx 解析并批量落库。

    Args:
        tmp_path (str): 已落盘的 xlsx 临时文件绝对路径。
        user (User | None): 当前操作用户。
        ad_type_filter (str): 广告类型筛选，取値 "all" / "auto" / "manual"。
        country_filter (list[str] | None): 手动指定的国家代码列表；None 表示按表需求自动发现。
        bidding_params (dict[str, float] | None): 竞价配置字典，键名与模型字段一致；
            None 时全部使用字段默认值。

    Returns:
        tuple[list[AdUploadQueue], str | None, list[str]]:
            - 已创建的记录列表（成功时非空）。
            - error_msg：文件级错误时非 None，此时列表为空。
            - skipped_warnings：手动广告无关键词被跳过的提示信息列表。
    """
    bp = bidding_params or {}  # 竞价参数快捷引用，缺键时使用模型字段默认值
    # 1. 读主表
    try:
        df = pd.read_excel(tmp_path, sheet_name=_MAIN_SHEET, engine="openpyxl")
    except ValueError as exc:
        if "Worksheet named" in str(exc):
            return [], f"文件中未找到 '{_MAIN_SHEET}' 工作表", []
        return [], f"读取主表失败：{exc}", []
    except Exception as exc:
        return [], f"读取文件失败：{exc}", []

    # 2. 校验必需列
    missing = [c for c in _REQUIRED_COLS if c not in df.columns]
    if missing:
        return [], f"主表缺少必需列：{', '.join(missing)}", []

    # 3. 读站点关键词（同时动态发现合规站点：子表名 = 两位大写国家代码）
    site_keywords = _read_site_keywords(tmp_path)
    discovered_sites: list[str] = list(site_keywords.keys())

    if not discovered_sites:
        return [], "文件中未发现合规站点子表（子表名应为两位大写国家代码，如 DE、UK）", []

    # 3c. 根据前端传入的 country_filter 过滤有效站点：
    #     None = 按表需求，使用文件中全部发现站点；传入列表则求交，文件没有的巻默忽略。
    if country_filter:
        effective_sites: list[str] = [s for s in discovered_sites if s in set(country_filter)]
        if not effective_sites:
            return [], (
                f"选中的国家（{', '.join(country_filter)}）在文件中均不存在对应站点子表"
            ), []
    else:
        effective_sites = discovered_sites

    # 3b. 预加载 lx_shops 所有已知店铺名称（用于后续店铺-国家存在性校验）
    #     格式："{shop_name}-{site}"，例如 "MF-DE"。
    valid_shop_sites: frozenset[str] = frozenset(
        LxShops.objects.values_list("name", flat=True)
    )

    # 4. 归一化主表（向下填充店铺名/广告活动名）
    df[_COL_SHOP] = df[_COL_SHOP].ffill()
    shop_group_id = (df[_COL_SHOP] != df[_COL_SHOP].shift()).cumsum()
    df[_COL_AD_NAME] = df.groupby(shop_group_id)[_COL_AD_NAME].ffill()
    df = df.dropna(subset=[_COL_SHOP, _COL_AD_NAME])

    # 5. 按（店铺 × 广告活动 × 国家）三维展开，内联校验并构造队列记录。
    #
    #    核心拼接规则：
    #      Excel 主表中的广告活动名（如 X-HLS-LQ-HJ）不含类型后缀。
    #      服务层在落库时自动拼接，产出：
    #        - "X-HLS-LQ-HJ AUTO"  ad_type="auto"   关键词可为空
    #        - "X-HLS-LQ-HJ MANU"  ad_type="manual" 无关键词时跳过
    #      关键词从站点子表中按原始广告活动名（不含后缀）查找。
    #
    #    前端 ad_type_filter 控制创建范围：
    #      "all"    → 同时创建 auto 和 manual 两种记录
    #      "auto"   → 仅创建 AUTO 记录
    #      "manual" → 仅创建 MANU 记录
    #
    #    格式不合规的分组不阻断整体上传，以 FAILED 状态落库并在 msg 中注明原因。
    records_to_create: list[AdUploadQueue] = []
    skipped_warnings: list[str] = []

    # 根据前端筛选参数确定本次需要创建的广告类型列表
    if ad_type_filter == "all":
        types_to_create: list[str] = ["auto", "manual"]
    else:
        types_to_create = [ad_type_filter]

    for shop, shop_group in df.groupby(_COL_SHOP, sort=False):
        for ad_name, ad_group in shop_group.groupby(_COL_AD_NAME, sort=False):
            # 先做组级合规校验（店铺/广告名/sku）
            error_msg = _get_group_error(str(shop), str(ad_name), ad_group)
            if error_msg:
                # 校验失败：对所有类型和站点以 FAILED 状态落库，campaign_name 含对应后缀
                for ad_type in types_to_create:
                    suffix = "AUTO" if ad_type == "auto" else "MANU"
                    for site in effective_sites:
                        records_to_create.append(
                            AdUploadQueue(
                                campaign_name=f"{ad_name} {suffix}",
                                shop=str(shop),
                                country=site,
                                ad_type=ad_type,
                                params=_build_params([], [], bp),
                                parse_status=AdParseStatus.FAILED,
                                msg=error_msg,
                                created_by=user,
                            )
                        )
                continue

            skus: list[str] = ad_group[_COL_SKU].dropna().astype(str).tolist()
            if not skus:
                continue

            for ad_type in types_to_create:
                suffix = "AUTO" if ad_type == "auto" else "MANU"
                campaign_name_with_suffix = f"{ad_name} {suffix}"
                for site in effective_sites:
                    shop_site_key = f"{shop}-{site}"
                    if shop_site_key not in valid_shop_sites:
                        # 店铺-国家组合在 lx_shops 中不存在，以 FAILED 状态落库
                        records_to_create.append(
                            AdUploadQueue(
                                campaign_name=campaign_name_with_suffix,
                                shop=str(shop),
                                country=site,
                                ad_type=ad_type,
                                params=_build_params([], [], bp),
                                parse_status=AdParseStatus.FAILED,
                                msg=f"店铺不存在（{shop_site_key}）",
                                created_by=user,
                            )
                        )
                        continue

                    # 关键词按原始广告活动名（不含后缀）在站点子表中查找
                    keywords: list[str] = site_keywords.get(site, {}).get(str(ad_name), [])
                    # 手动广告无关键词：跳过且记录提示
                    if ad_type == "manual" and not keywords:
                        skipped_warnings.append(
                            f"{campaign_name_with_suffix}（{site}）没有关键词，不予创建"
                        )
                        continue

                    # 自动广告允许关键词为空
                    records_to_create.append(
                        AdUploadQueue(
                            campaign_name=campaign_name_with_suffix,
                            shop=str(shop),
                            country=site,
                            ad_type=ad_type,
                            params=_build_params(skus, keywords, bp),
                            parse_status=AdParseStatus.PENDING,
                            msg="队列中",
                            created_by=user,
                        )
                    )

    if not records_to_create:
        return [], "文件中未解析出有效广告数据，请检查主表内容", skipped_warnings

    # 7. 批量落库（原子操作）
    with transaction.atomic():
        created = AdUploadQueue.objects.bulk_create(records_to_create)

    logger.info(
        "[AdUploadQueueService][parse_and_create_queue] 队列记录创建完成: count=%s skipped=%s user=%s",
        len(created), len(skipped_warnings), user,
    )
    return created, None, skipped_warnings


# ── 对外公共入口 ────────────────────────────────────────────────────────────────

def parse_and_create_queue(
    file_obj: Any,
    user: User | None,
    ad_type_filter: str = "all",
    country_filter: list[str] | None = None,
    bidding_params: dict[str, float] | None = None,
) -> tuple[list[AdUploadQueue], str | None, list[str]]:
    """解析上传的 xlsx 文件并批量创建广告上传队列记录。

    整体流程：写临时文件 → 解析主表 → 读站点关键词 → 合规校验 → 批量落库。
    任何文件级错误均以 error_msg 返回，不抛出异常。

    Args:
        file_obj: Django InMemoryUploadedFile 或实现了 chunks() 方法的类文件对象。
        user (User | None): 当前操作用户，用于记录创建者。
        ad_type_filter (str): "all"（默认，都创建）/ "auto"（仅自动）/ "manual"（仅手动）。
        country_filter (list[str] | None): 手动指定国家代码列表；None 表示按表需求。
        bidding_params (dict[str, float] | None): 竞价配置，键名与 AdUploadQueue 竞价字段一致；
            None 时全部使用字段默认值（每日预算 1，各竞价 0.10 / 0.12）。

    Returns:
        tuple[list[AdUploadQueue], str | None, list[str]]:
            - 已创建的 AdUploadQueue 记录列表（文件级错误时为空列表）。
            - error_msg：文件级错误时非 None，成功时为 None。
            - skipped_warnings：被跳过的手动广告提示信息列表。
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
        return [], f"文件读取失败：{exc}", []

    try:
        return _do_parse_and_create(tmp_path, user, ad_type_filter, country_filter, bidding_params)
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
