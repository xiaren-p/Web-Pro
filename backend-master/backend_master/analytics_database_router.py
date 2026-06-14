"""Doris 分析库路由器（analytics）。"""


class AnalyticsDatabaseRouter:
    """Doris 分析库路由器，阻止 Django 在分析库执行迁移。

    该路由器不主动接管任何模型的读写库选择，避免业务代码被隐式路由到 Doris。
    报表查询必须在调用处显式使用 `.using("analytics")`，这样能保证 MySQL 主库
    继续承担业务写入和迁移职责，Doris 只作为只读分析库参与聚合查询。
    """

    def db_for_read(self, model, **hints) -> None:
        """不改变模型读取数据库。

        Args:
            model: Django 模型类。
            **hints: Django 数据库路由提示信息。

        Returns:
            None: 返回 None 表示交回 Django 默认路由处理。
        """
        return None

    def db_for_write(self, model, **hints) -> None:
        """不改变模型写入数据库。

        Args:
            model: Django 模型类。
            **hints: Django 数据库路由提示信息。

        Returns:
            None: 返回 None 表示交回 Django 默认路由处理。
        """
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints) -> bool | None:
        """阻止 Django 对 Doris 分析库执行迁移。

        Args:
            db (str): 当前迁移目标数据库别名。
            app_label (str): Django App 标签。
            model_name (str | None): 当前迁移模型名。
            **hints: Django 数据库路由提示信息。

        Returns:
            bool | None: analytics 返回 False 阻止迁移，其余数据库返回 None 交给默认逻辑。
        """
        if db == "analytics":
            return False
        return None
