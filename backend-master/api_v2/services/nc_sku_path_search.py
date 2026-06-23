"""NC SKU 路径搜索工具（nc_sku_path_search）。

通过 NC WebDAV SEARCH（RFC 5323）服务器端搜索编号图片文件，
结合从外部自动化项目移植的 SKU 段匹配算法，在 NC 目录树中
定位与给定 SKU 匹配的图片目录。

核心算法移植自 search_sku_paths.py 的 matches_sku_for_dir()。
"""
import logging
import re
from typing import TYPE_CHECKING
from urllib.parse import unquote

if TYPE_CHECKING:
    from api_v1.services.nc.nc_api_client import NcApiClient

logger = logging.getLogger(__name__)

# 图片文件扩展名集合
_IMAGE_EXTS: set[str] = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}

# 编号图片文件名前缀（1-12，不含扩展名）
_NUMBERED_PREFIXES: set[str] = {str(i) for i in range(1, 13)}


def _extract_hyphen_segs(name: str) -> list[str]:
    """从名称开头提取连字符段序列。

    使用正则匹配名称开头的字母数字-连字符部分，再按 '-' 切分为小写段列表。
    与 search_sku_paths.py 的 extract_hyphen_segs 完全一致。

    Args:
        name (str): 目录名或文件名。

    Returns:
        list[str]: 小写段列表；无法匹配时返回空列表。

    Examples:
        >>> _extract_hyphen_segs("Y-AS-NY01-BK 主图")
        ['y', 'as', 'ny01', 'bk']
    """
    if not name:
        return []
    match = re.match(r"^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)", name)
    if not match:
        return []
    return [seg.lower() for seg in match.group(1).split("-") if seg]


def _has_numbered_image(filenames: list[str]) -> bool:
    """判断文件名列表中是否包含编号图片（1-12 开头 + 图片扩展名）。

    Args:
        filenames (list[str]): 目录中的文件名列表。

    Returns:
        bool: 存在至少一个编号图片时返回 True。
    """
    for name in filenames:
        root, ext = _split_filename(name)
        if ext.lower() in _IMAGE_EXTS and root in _NUMBERED_PREFIXES:
            return True
    return False


def _split_filename(name: str) -> tuple[str, str]:
    """将文件名拆分为根名和扩展名（不依赖 os.path，因为路径来自 URL）。

    Args:
        name (str): 文件名。

    Returns:
        tuple[str, str]: (根名, 扩展名含点号)。
    """
    dot_idx = name.rfind(".")
    if dot_idx <= 0:
        return name, ""
    return name[:dot_idx], name[dot_idx:]


def _matches_sku_for_path(
    path_components: list[str],
    sku: str,
    filenames: list[str],
    has_child_dirs: bool = False,
) -> bool:
    """判断一条 NC 路径是否匹配指定 SKU。

    移植自 search_sku_paths.py 的 matches_sku_for_dir()，
    包含四段匹配策略以覆盖各种 SKU 命名模式（含变体后缀）。

    Args:
        path_components (list[str]): URL 解码后的目录名序列
                                      （从挂载点根到叶子目录）。
        sku (str): 待匹配的 SKU 字符串。
        filenames (list[str]): 叶子目录中的文件名列表。
        has_child_dirs (bool): 该目录是否含有其他编号图片子目录。
            若有则视为分类目录，禁止反向前缀匹配（策略 4）。

    Returns:
        bool: 匹配时返回 True。
    """
    sku = sku.strip()
    if not sku:
        return False
    segs = [s for s in sku.split("-") if s]
    if not segs:
        return False

    sku_segs = [s.lower() for s in segs]
    dir_names_lower = [d.lower() for d in path_components]

    # 策略 1：严格前缀匹配 —— 路径中某目录名的连字符段 >= SKU 段数且前缀相等
    for dname in path_components:
        dh = _extract_hyphen_segs(dname)
        if dh and len(dh) >= len(sku_segs) and dh[:len(sku_segs)] == sku_segs:
            return True

    # 策略 2：文件名匹配 —— 文件名（去扩展名）的连字符段匹配 SKU
    for name in filenames:
        base, _ = _split_filename(name)
        bh = _extract_hyphen_segs(base)
        if bh and len(bh) >= len(sku_segs) and bh[:len(sku_segs)] == sku_segs:
            return True

    # 策略 3：祖先 + 剩余段匹配
    n = len(path_components)
    m = len(segs)
    for i in range(n):
        dir_hy_segs = _extract_hyphen_segs(path_components[i])
        if not dir_hy_segs:
            continue
        for k in range(2, m + 1):
            if len(dir_hy_segs) < k:
                continue
            if dir_hy_segs[:k] != [s.lower() for s in segs[:k]]:
                continue
            # 构造路径中剩余段序列
            remaining_in_path: list[str] = []
            if len(dir_hy_segs) > k:
                remaining_in_path.extend(dir_hy_segs[k:])
            remaining_in_path.extend(dir_names_lower[i + 1:])
            remaining_sku = [s.lower() for s in segs[k:]]
            # 严格相等
            if len(remaining_in_path) == len(remaining_sku):
                if remaining_in_path == remaining_sku:
                    return True
            # 允许缺失子段（如 -M/-F）
            if len(remaining_in_path) == 0:
                return True
            # 保守后备：剩余 SKU 段全部出现在路径中且至少一段在祖先之后
            if set(remaining_sku).issubset(set(dir_names_lower)):
                after_names = dir_names_lower[i + 1:]
                if any(r in after_names for r in remaining_sku):
                    return True

    # 策略 4：反向前缀匹配 —— 目录名的连字符段是 SKU 段的前缀（≥ 3 段）
    # 例：目录 Z-HLS-AQBX-CR 匹配 SKU Z-HLS-AQBX-CR-HK1（SKU 含变体后缀）
    # 禁止对分类目录使用（含有子目录的父目录可能误匹配多个变体）
    # 仅当叶子目录名本身包含 SKU 前缀时启用（排除“厂家图片”等通用目录）
    if not has_child_dirs and path_components:
        leaf_name = path_components[-1]
        leaf_dh = _extract_hyphen_segs(leaf_name)
        if leaf_dh and leaf_dh == sku_segs[:len(leaf_dh)]:
            # 叶子目录名本身包含 SKU 前缀（如 Z-HLS-AQBX-CR 反光...）
            for dname in path_components:
                dh = _extract_hyphen_segs(dname)
                if (
                    dh
                    and 3 <= len(dh) < len(sku_segs)
                    and dh == sku_segs[:len(dh)]
                ):
                    return True
        elif leaf_name.isascii():
            # 叶子目录名为纯 ASCII（如 BLUE、02 等变体目录）
            # 找路径中最长的 SKU 前缀匹配组件
            best_prefix_len = 0
            best_match_idx = -1
            for i, dname in enumerate(path_components):
                dh = _extract_hyphen_segs(dname)
                if (
                    dh
                    and len(dh) >= 3
                    and len(dh) <= len(sku_segs)
                    and dh == sku_segs[:len(dh)]
                    and len(dh) > best_prefix_len
                ):
                    best_prefix_len = len(dh)
                    best_match_idx = i
            if best_match_idx >= 0:
                # 叶子对应的 SKU 段位置 = 前缀长度 + 叶子到匹配组件的偏移量
                leaf_offset = len(path_components) - 1 - best_match_idx
                sku_pos = best_prefix_len + leaf_offset - 1
                if len(leaf_dh) == 1 and sku_pos < len(sku_segs):
                    # 变体冲突检查（如 01 ≠ 02）
                    if leaf_dh[0] != sku_segs[sku_pos]:
                        return False
                return True

    return False


def _href_to_path_components(href: str, scope_prefix: str) -> list[str]:
    """从 WebDAV href 中提取路径组件序列。

    去除 scope 前缀后，URL 解码并按 '/' 分割得到目录名列表。

    Args:
        href (str): WebDAV href，如 /remote.php/dav/files/admin/美工部/【产品图片】/SKU/ 。
        scope_prefix (str): 搜索范围前缀，如 /remote.php/dav/files/admin/美工部/【产品图片】 。

    Returns:
        list[str]: URL 解码后的目录名序列（不含空字符串）。
    """
    # 先 URL 解码，再去除 scope 前缀（NC 返回的 href 含 URL 编码中文）
    decoded_href = unquote(href)
    relative = decoded_href
    decoded_scope = unquote(scope_prefix)
    if decoded_href.startswith(decoded_scope):
        relative = decoded_href[len(decoded_scope):]
    relative = relative.strip("/")
    if not relative:
        return []
    return [part for part in relative.split("/") if part]


def _parent_href(href: str) -> str:
    """从文件 href 中提取父目录 href。

    Args:
        href (str): 文件的完整 WebDAV href。

    Returns:
        str: 父目录 href（以 / 结尾）。
    """
    stripped = href.rstrip("/")
    last_slash = stripped.rfind("/")
    if last_slash <= 0:
        return "/"
    return stripped[:last_slash + 1]


def _prune_by_depth(paths: list[str]) -> list[str]:
    """按深度去重剪枝：保留最浅匹配，子目录被父目录覆盖时去除。

    Args:
        paths (list[str]): 相对路径列表。

    Returns:
        list[str]: 剪枝后的路径列表。
    """
    if not paths:
        return paths
    sorted_paths = sorted(paths, key=lambda p: (p.count("/"), len(p)))
    result: list[str] = []
    for p in sorted_paths:
        norm_p = p.rstrip("/") + "/"
        is_child = False
        for kept in result:
            norm_k = kept.rstrip("/") + "/"
            if norm_p.startswith(norm_k):
                is_child = True
                break
        if not is_child:
            result.append(p)
    return result


def _filter_parent_prefixes(paths: list[str]) -> list[str]:
    """去除父级匹配：如果某路径是另一匹配路径的父目录，则去除该父路径。

    确保只保留最具体的匹配，避免父分类目录被误匹配。
    例：Z-HLS-AQBX 和 Z-HLS-AQBX-CR 都匹配时，去除 Z-HLS-AQBX。

    Args:
        paths (list[str]): 相对路径列表。

    Returns:
        list[str]: 过滤后的路径列表（仅保留最具体匹配）。
    """
    if len(paths) <= 1:
        return paths
    result: list[str] = []
    for p in paths:
        norm_p = p.rstrip("/") + "/"
        # 如果存在其他路径以当前路径为前缀，则当前路径是父目录，跳过
        is_parent = any(
            other.rstrip("/").startswith(norm_p)
            for other in paths
            if other != p
        )
        if not is_parent:
            result.append(p)
    return result


def search_nc_sku_paths(
    client: "NcApiClient",
    admin_user: str,
    scope_dav: str,
    skus: list[str],
) -> tuple[dict[str, list[str]], str]:
    """在 NC 中搜索与给定 SKU 列表匹配的图片目录。

    按编号图片文件名（1.% ~ 7.%）分次 SEARCH，每次结果集很小，
    避免全量搜索的结果截断问题，然后按父目录分组并应用 SKU 段匹配算法。

    Args:
        client (NcApiClient): 已初始化的 NC API 客户端。
        admin_user (str): NC 管理员用户名。
        scope_dav (str): 搜索范围 WebDAV 完整路径，
                         如 /remote.php/dav/files/admin/美工部/【产品图片】 。
        skus (list[str]): 待搜索的 SKU 列表。

    Returns:
        tuple[dict[str, list[str]], str]:
            ({sku: [相对路径, ...]}, 调试摘要字符串)。

    Raises:
        RuntimeError: NC 通信失败时抛出。
    """
    if not skus:
        return {}, "无 SKU"

    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 开始搜索: scope=%s sku_count=%d",
        scope_dav, len(skus),
    )

    # 1. 按编号图片文件名分次 SEARCH（1.% ~ 7.%）
    #    每次只搜一个编号前缀，结果集远小于 nresults 上限，不会被截断
    if scope_dav.startswith("/remote.php/dav"):
        scope_for_search = scope_dav[len("/remote.php/dav"):]
    else:
        scope_for_search = scope_dav
    files: list[dict] = []
    for prefix in range(1, 13):
        batch = client.search_dav_files(
            scope_for_search, f"{prefix}.%", "image/%",
        )
        files.extend(batch)
    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 编号图片文件数=%d",
        len(files),
    )

    # 2. 按父目录分组
    parent_map: dict[str, list[str]] = {}
    for f in files:
        parent = _parent_href(f["href"])
        parent_map.setdefault(parent, []).append(f["name"])

    # 3. 筛选含编号图片的目录
    numbered_dirs: dict[str, list[str]] = {}
    for parent, fnames in parent_map.items():
        if _has_numbered_image(fnames):
            numbered_dirs[parent] = fnames

    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 编号图片目录数=%d",
        len(numbered_dirs),
    )

    # 4. 预计算含有子目录的父目录（用于禁止策略 4 误匹配分类目录）
    parent_hrefs: set[str] = set()
    for href in numbered_dirs:
        parent = _parent_href(href)
        if parent in numbered_dirs:
            parent_hrefs.add(parent)

    # 5. 对每个编号图片目录匹配每个 SKU
    scope_prefix = scope_dav.rstrip("/")

    results: dict[str, list[str]] = {sku: [] for sku in skus}
    for href, fnames in numbered_dirs.items():
        components = _href_to_path_components(href, scope_prefix)
        has_children = href in parent_hrefs
        for sku in skus:
            if _matches_sku_for_path(components, sku, fnames, has_children):
                # 存储相对于 scope 的路径（需先 URL 解码）
                decoded_href = unquote(href).rstrip("/").lstrip("/")
                decoded_scope = unquote(scope_prefix).lstrip("/")
                if decoded_href.startswith(decoded_scope):
                    relative = decoded_href[len(decoded_scope):]
                else:
                    relative = decoded_href
                relative = relative.strip("/")
                results[sku].append(relative)

    # 6. 过滤父级匹配 + 深度剪枝
    for sku in results:
        results[sku] = _filter_parent_prefixes(results[sku])
        results[sku] = _prune_by_depth(results[sku])

    matched_count = sum(1 for v in results.values() if v)
    # 构建调试摘要
    sample_dirs: list[str] = []
    for debug_href, debug_fnames in list(numbered_dirs.items())[:8]:
        comps = _href_to_path_components(debug_href, scope_prefix)
        sample_dirs.append("/".join(comps) if comps else "(empty)")
    debug_info = (
        f"编号图片数={len(files)}, "
        f"编号目录数={len(numbered_dirs)}, "
        f"scope={scope_for_search}, "
        f"示例目录: {'; '.join(sample_dirs) or '(无)'}"
    )
    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 匹配 SKU=%d/%d | %s",
        matched_count, len(skus), debug_info,
    )
    return results, debug_info
