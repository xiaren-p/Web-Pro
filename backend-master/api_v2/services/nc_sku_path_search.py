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

# 编号图片文件名前缀（不含扩展名）
_NUMBERED_PREFIXES: set[str] = {str(i) for i in range(1, 8)}


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
    """判断文件名列表中是否包含编号图片（1-7 开头 + 图片扩展名）。

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
) -> bool:
    """判断一条 NC 路径是否匹配指定 SKU。

    移植自 search_sku_paths.py 的 matches_sku_for_dir()，
    保留完整的三段匹配逻辑以覆盖各种 SKU 命名模式。

    Args:
        path_components (list[str]): URL 解码后的目录名序列
                                      （从挂载点根到叶子目录）。
        sku (str): 待匹配的 SKU 字符串。
        filenames (list[str]): 叶子目录中的文件名列表。

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
    # 去除 scope 前缀得到相对路径
    relative = href
    if href.startswith(scope_prefix):
        relative = href[len(scope_prefix):]
    relative = unquote(relative).strip("/")
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


def search_nc_sku_paths(
    client: "NcApiClient",
    admin_user: str,
    scope_dav: str,
    skus: list[str],
) -> tuple[dict[str, list[str]], str]:
    """在 NC 中搜索与给定 SKU 列表匹配的图片目录。

    利用 WebDAV SEARCH 一次请求获取所有编号图片文件，
    然后按父目录分组并应用 SKU 段匹配算法。

    Args:
        client (NcApiClient): 已初始化的 NC API 客户端。
        admin_user (str): NC 管理员用户名。
        scope_dav (str): 搜索范围 WebDAV 路径，
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

    # 1. 搜索所有 jpg 图片（一次 SEARCH 请求）
    # scope_dav 可能是 /remote.php/dav/files/... 或 /files/... 格式
    # SEARCH XML 需要 /files/{user}/... 格式
    if scope_dav.startswith("/remote.php/dav"):
        scope_for_search = scope_dav[len("/remote.php/dav"):]
    else:
        scope_for_search = scope_dav
    files = client.search_dav_files(scope_for_search, "%.jpg", "image/%")
    if not files:
        # 尝试 jpeg/png/webp
        for ext in ("%.jpeg", "%.png", "%.webp"):
            extra = client.search_dav_files(scope_for_search, ext, "image/%")
            files.extend(extra)
    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 搜索到图片文件数=%d",
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

    # 4. 对每个编号图片目录匹配每个 SKU
    scope_prefix = scope_dav.rstrip("/")

    results: dict[str, list[str]] = {sku: [] for sku in skus}
    for href, fnames in numbered_dirs.items():
        components = _href_to_path_components(href, scope_prefix)
        for sku in skus:
            if _matches_sku_for_path(components, sku, fnames):
                # 存储相对于 scope 的路径
                relative = href.rstrip("/").lstrip("/")
                if relative.startswith(scope_prefix.lstrip("/")):
                    relative = relative[len(scope_prefix.lstrip("/")):]
                relative = relative.strip("/")
                results[sku].append(relative)

    # 5. 按深度去重剪枝
    for sku in results:
        results[sku] = _prune_by_depth(results[sku])

    matched_count = sum(1 for v in results.values() if v)
    # 构建调试摘要
    sample_dirs: list[str] = []
    for debug_href, debug_fnames in list(numbered_dirs.items())[:8]:
        comps = _href_to_path_components(debug_href, scope_prefix)
        sample_dirs.append("/".join(comps) if comps else "(empty)")
    debug_info = (
        f"图片文件数={len(files)}, "
        f"编号目录数={len(numbered_dirs)}, "
        f"scope={scope_for_search}, "
        f"示例目录: {'; '.join(sample_dirs) or '(无)'}"
    )
    logger.info(
        "[nc_sku_path_search][search_nc_sku_paths] 匹配 SKU=%d/%d | %s",
        matched_count, len(skus), debug_info,
    )
    return results, debug_info
