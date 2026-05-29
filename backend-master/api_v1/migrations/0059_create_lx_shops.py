"""手动迁移：创建 lx_shops 店铺基础数据表（managed=False，使用 RunSQL）。"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0058_userprofile_nc_app_password"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
CREATE TABLE IF NOT EXISTS lx_shops (
    sid            INT          NOT NULL PRIMARY KEY COMMENT '店铺 ID',
    mid            INT          NULL     COMMENT 'Marketplace 序号',
    name           VARCHAR(255) NULL     COMMENT '店铺名称',
    seller_id      VARCHAR(100) NULL     COMMENT 'Seller ID',
    account_name   VARCHAR(255) NULL     COMMENT '账号名称',
    seller_account_id INT       NULL     COMMENT '卖家账号 ID',
    region         VARCHAR(20)  NULL     COMMENT '大区（如 EU / NA）',
    country        VARCHAR(50)  NULL     COMMENT '国家',
    has_ads_setting TINYINT     NOT NULL DEFAULT 0 COMMENT '是否配置广告设置（0未配置/1已配置）',
    marketplace_id VARCHAR(64)  NULL     COMMENT 'Marketplace ID',
    status         TINYINT      NOT NULL DEFAULT 1 COMMENT '店铺状态（0禁用/1启用）'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='店铺基础数据表';
""",
            reverse_sql="DROP TABLE IF EXISTS lx_shops;",
        ),
    ]
