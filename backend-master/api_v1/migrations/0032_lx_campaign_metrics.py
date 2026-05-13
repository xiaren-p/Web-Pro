# Generated manually — 创建广告活动指标表（非托管，managed=False）
from django.db import migrations


# SQLite 建表 SQL（updated_at 用 SQLite 的 datetime('now') 函数默认值）
CREATE_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS lx_campaign_metrics (
    id          INTEGER PRIMARY KEY,
    campaign_id TEXT    NOT NULL,
    top_of_search_impression_share TEXT DEFAULT '',
    sales       REAL    DEFAULT 0.0,
    direct_sales REAL   DEFAULT 0.0,
    orders      INTEGER DEFAULT 0,
    direct_orders INTEGER DEFAULT 0,
    unit_price  REAL    DEFAULT 0.0,
    ad_units    INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    clicks      INTEGER DEFAULT 0,
    cpc         REAL    DEFAULT 0.0,
    spends      REAL    DEFAULT 0.0,
    timestamp   TEXT    NOT NULL,
    updated_at  TEXT    DEFAULT (datetime('now'))
)
"""

# MySQL 建表 SQL（updated_at 改为 DATETIME DEFAULT CURRENT_TIMESTAMP）
CREATE_SQL_MYSQL = """
CREATE TABLE IF NOT EXISTS lx_campaign_metrics (
    id          INT PRIMARY KEY,
    campaign_id VARCHAR(255) NOT NULL,
    top_of_search_impression_share VARCHAR(255) DEFAULT '',
    sales       DOUBLE   DEFAULT 0.0,
    direct_sales DOUBLE  DEFAULT 0.0,
    orders      INT      DEFAULT 0,
    direct_orders INT    DEFAULT 0,
    unit_price  DOUBLE   DEFAULT 0.0,
    ad_units    INT      DEFAULT 0,
    impressions INT      DEFAULT 0,
    clicks      INT      DEFAULT 0,
    cpc         DOUBLE   DEFAULT 0.0,
    spends      DOUBLE   DEFAULT 0.0,
    timestamp   VARCHAR(64) NOT NULL,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

DROP_SQL = "DROP TABLE IF EXISTS lx_campaign_metrics"


def create_table(apps, schema_editor):
    """
    根据当前数据库引擎选择对应的建表 SQL 并执行。

    Args:
        apps: Django 应用注册表（RunPython 标准参数）
        schema_editor: 数据库 Schema 操作器，通过 vendor 属性判断引擎类型
    """
    vendor = schema_editor.connection.vendor  # 'sqlite' | 'mysql' | 'postgresql'
    if vendor == "sqlite":
        sql = CREATE_SQL_SQLITE
    else:
        sql = CREATE_SQL_MYSQL
    schema_editor.execute(sql)


def drop_table(apps, schema_editor):
    """
    回滚时删除 lx_campaign_metrics 表。

    Args:
        apps: Django 应用注册表
        schema_editor: 数据库 Schema 操作器
    """
    schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):
    """
    创建广告活动指标表（lx_campaign_metrics），用于存储按天汇总的广告数据。

    使用 RunPython 使建表 SQL 兼容 SQLite 与 MySQL 两种引擎。
    注意：MySQL DDL 语句会触发隐式提交，因此 atomic=False 以跳过事务包裹。
    """

    atomic = False  # MySQL DDL（CREATE TABLE）不支持事务回滚，必须关闭自动事务

    dependencies = [
        ("api_v1", "0042_merge_20260421_1509"),
    ]

    operations = [
        migrations.RunPython(
            code=create_table,
            reverse_code=drop_table,
        ),
    ]
