"""Doris MySQL 协议数据库后端，跳过 Django 的 MySQL 8.0+ 版本检查。

Doris 通过 MySQL 协议通信，但其 server_version 报告为 5.7.99，
而 Django mysql 后端要求 MySQL 8.0.11+，直接使用会抛 NotSupportedError。
本后端继承 Django 原生 mysql 后端，仅覆盖版本检查方法。
"""
from django.db.backends.mysql import base as mysql_base


class DatabaseWrapper(mysql_base.DatabaseWrapper):
    """Doris MySQL 协议后端：跳过 MySQL 版本检查。"""

    def check_database_version_supported(self):
        """Doris 不报 MySQL 真实版本号，跳过版本最低要求检查。

        Django 原生实现会检查 self.mysql_version >= (8, 0, 11)，
        此处直接跳过以保证 analytics 只读查询正常执行。
        """
        pass
