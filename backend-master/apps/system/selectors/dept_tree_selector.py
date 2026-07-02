"""部门树形结构查询选择器。

提供部门树构建（含循环引用检测）与部门列表查询的只读逻辑。
"""
from typing import Any

from apps.system.models import Department


def build_dept_tree(nodes: list[Department]) -> list[dict[str, Any]]:
    """构建部门树形结构（带循环检测保护）。

    将扁平部门列表转为树形嵌套结构，同时维护已访问节点集合
    以防止数据中的异常循环引用造成无限递归。

    Args:
        nodes (list[Department]): 部门查询集或列表。

    Returns:
        list[dict[str, Any]]: 根层级部门树节点列表（含 children）。
    """
    by_parent: dict[int, list[Department]] = {}
    for d in nodes:
        pid = d.parent_id or 0
        by_parent.setdefault(pid, []).append(d)

    def build(pid: int | None = None, path: set[int] | None = None) -> list[dict[str, Any]]:
        """递归构建部门子树节点列表。

        Args:
            pid (int | None): 父部门 ID，None 表示从根层级开始。
            path (set[int] | None): 已访问部门 ID 集合，用于循环引用检测。

        Returns:
            list[dict[str, Any]]: 部门树节点列表（含 children）。
        """
        if path is None:
            path = set()
        res: list[dict[str, Any]] = []
        for d in by_parent.get(pid or 0, []):
            if d.id in path:
                continue
            new_path = set(path)
            new_path.add(d.id)
            res.append({
                "id": d.id,
                "parentId": d.parent_id,
                "name": d.name,
                "code": getattr(d, "code", ""),
                "status": 1 if d.status else 0,
                "sort": d.order_num,
                "children": build(d.id, new_path),
            })
        return res

    return build(None)
