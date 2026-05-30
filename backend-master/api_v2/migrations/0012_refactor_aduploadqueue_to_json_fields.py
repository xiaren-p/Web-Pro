"""将 AdUploadQueue 中分散的竞价/SKU/关键词/步骤 ID 字段合并为 params 和 step_ids 两个 JSONField。

迁移步骤：
  1. 新增 params（JSONField）和 step_ids（JSONField）两列。
  2. RunPython：将现有行的旧字段值搬迁至新 JSON 列。
  3. 删除所有被替换的旧列。
"""

from django.db import migrations, models


def _migrate_to_json(apps, schema_editor):
    """将每行旧字段的值写入 params 和 step_ids JSON 列。"""
    AdUploadQueue = apps.get_model("api_v2", "AdUploadQueue")

    for record in AdUploadQueue.objects.all().iterator(chunk_size=200):
        record.params = {
            "skus": record.skus or [],
            "keywords": record.keywords or [],
            "daily_budget": float(record.daily_budget or 1.00),
            "default_bid": float(record.default_bid or 0.12),
            "close_match_bid": float(record.close_match_bid or 0.12),
            "loose_match_bid": float(record.loose_match_bid or 0.10),
            "substitutes_bid": float(record.substitutes_bid or 0.10),
            "complements_bid": float(record.complements_bid or 0.10),
        }
        record.step_ids = {
            "campaign_id": record.campaign_id or "",
            "ad_group_id": record.ad_group_id or "",
            "product_ad_ids": record.product_ad_ids or [],
            "keyword_ids": record.keyword_ids or [],
        }
        record.save(update_fields=["params", "step_ids"])


class Migration(migrations.Migration):

    dependencies = [
        ("api_v2", "0011_aduploadqueue_keyword_ids"),
    ]

    operations = [
        # ── Step 1: 新增 JSON 列 ─────────────────────────────────────────────────
        migrations.AddField(
            model_name="aduploadqueue",
            name="params",
            field=models.JSONField(default=dict, verbose_name="广告参数"),
        ),
        migrations.AddField(
            model_name="aduploadqueue",
            name="step_ids",
            field=models.JSONField(default=dict, verbose_name="步骤产出 ID"),
        ),
        # ── Step 2: 数据搬迁 ─────────────────────────────────────────────────────
        migrations.RunPython(_migrate_to_json, migrations.RunPython.noop),
        # ── Step 3: 删除旧列 ─────────────────────────────────────────────────────
        migrations.RemoveField(model_name="aduploadqueue", name="skus"),
        migrations.RemoveField(model_name="aduploadqueue", name="keywords"),
        migrations.RemoveField(model_name="aduploadqueue", name="daily_budget"),
        migrations.RemoveField(model_name="aduploadqueue", name="default_bid"),
        migrations.RemoveField(model_name="aduploadqueue", name="close_match_bid"),
        migrations.RemoveField(model_name="aduploadqueue", name="loose_match_bid"),
        migrations.RemoveField(model_name="aduploadqueue", name="substitutes_bid"),
        migrations.RemoveField(model_name="aduploadqueue", name="complements_bid"),
        migrations.RemoveField(model_name="aduploadqueue", name="campaign_id"),
        migrations.RemoveField(model_name="aduploadqueue", name="ad_group_id"),
        migrations.RemoveField(model_name="aduploadqueue", name="product_ad_ids"),
        migrations.RemoveField(model_name="aduploadqueue", name="keyword_ids"),
    ]
