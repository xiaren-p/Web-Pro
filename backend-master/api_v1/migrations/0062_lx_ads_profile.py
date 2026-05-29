"""创建广告账号基础表 lx_ads_profile（managed=True）。"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api_v1", "0061_add_qinglong_config"),
    ]

    operations = [
        migrations.CreateModel(
            name="LxAdsProfile",
            fields=[
                (
                    "profile_id",
                    models.BigIntegerField(
                        primary_key=True,
                        serialize=False,
                        verbose_name="广告 Profile ID",
                    ),
                ),
                (
                    "sid",
                    models.CharField(
                        default="",
                        max_length=100,
                        verbose_name="店铺 ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        default="",
                        max_length=255,
                        verbose_name="账号名称",
                    ),
                ),
                (
                    "country_code",
                    models.CharField(
                        default="",
                        max_length=10,
                        verbose_name="国家代码",
                    ),
                ),
                (
                    "currency_code",
                    models.CharField(
                        default="",
                        max_length=10,
                        verbose_name="货币代码",
                    ),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("sp", "Sponsored Products"),
                            ("sb", "Sponsored Brands"),
                            ("sd", "Sponsored Display"),
                            ("dsp", "Demand-Side Platform"),
                        ],
                        default="",
                        max_length=20,
                        verbose_name="账号类型",
                    ),
                ),
                (
                    "status",
                    models.IntegerField(
                        choices=[(0, "禁用"), (1, "启用")],
                        default=1,
                        verbose_name="启用状态",
                    ),
                ),
            ],
            options={
                "verbose_name": "广告账号",
                "verbose_name_plural": "广告账号列表",
                "db_table": "lx_ads_profile",
                "ordering": ["profile_id"],
            },
        ),
    ]
