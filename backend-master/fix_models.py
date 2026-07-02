"""批量修复模型: managed=False + ordering + __str__ + __init__.py + FK引用
每次修改后用 ast.parse 验证语法正确性"""
import re, pathlib, ast

base = pathlib.Path('.')
fixed = 0
errors = []

def safe_write(fpath, content):
    global fixed
    f = base / fpath
    # Verify syntax before writing
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"SYNTAX ERROR in {fpath}: {e}")
        return False
    f.write_text(content, encoding='utf-8')
    fixed += 1
    return True

# ── 1. managed=False for external data tables ──
managed_false = [
    'apps/ads/models/lx_ads_portfolio.py',
    'apps/ads/models/lx_ads_profile.py',
    'apps/ads/sp/models/lx_sp_campaign.py',
    'apps/ads/sp/models/lx_sp_ad_group.py',
    'apps/ads/sp/models/lx_sp_ad.py',
    'apps/ads/sp/models/lx_sp_keyword.py',
    'apps/ads/sp/models/lx_sp_target.py',
    'apps/ads/sp/models/lx_sp_negative_target.py',
    'apps/ads/sp/models/lx_sp_campaign_report.py',
    'apps/ads/sp/models/lx_sp_ad_group_report.py',
    'apps/ads/sp/models/lx_sp_ad_report.py',
    'apps/ads/sp/models/lx_sp_keyword_report.py',
    'apps/ads/sp/models/lx_sp_target_report.py',
    'apps/ads/sp/models/lx_sp_search_term_report.py',
    'apps/ads/sp/timing/models/lx_time_pricing_strategy.py',
    'apps/ads/sp/rules/models/sp_campaign_adjustment.py',
    'apps/ads/sp/rules/models/sp_bid_adjustment.py',
    'apps/ads/sp/rules/models/sp_ad_optimization_strategy.py',
    'apps/ads/sp/rules/models/lx_api_err.py',
    'apps/ads/sp/rules/models/lx_ad_rule_group.py',
    'apps/ads/sp/rules/models/lx_ad_rule.py',
    'apps/common/models/image_upload.py',
    'apps/finance/models/lx_profit_report_msku.py',
    'apps/product/models/lx_local_product.py',
    'apps/product/models/lx_product_custom_field.py',
    'apps/product/models/lx_product_tag.py',
    'apps/product/models/lx_supplier_quote.py',
    'apps/sales/listing/models/lx_listing_data.py',
    'apps/sales/listing/models/lx_listing_meta.py',
    'apps/sales/listing/models/lx_listing_remark.py',
]
for fpath in managed_false:
    f = base / fpath
    content = f.read_text(encoding='utf-8')
    if 'managed = False' in content:
        continue
    # Add managed = False right after 'class Meta:'
    content = re.sub(
        r'(class Meta:\n)',
        r'\1        managed = False  # 外部数据表，Django 不管理 schema\n',
        content,
        count=1
    )
    safe_write(fpath, content)

print(f'managed=False: {fixed} files')
fixed = 0

# ── 2. ordering + __str__ additions ──
# Map: (file, ordering_value, __str__expr)
model_fixes = [
    # system
    ('apps/system/models/auth_token.py', '["-created_at"]', '        return f"AuthToken<user={self.user_id}>"'),
    ('apps/system/models/config.py', '["key"]', '        return f"Config<{self.key}>"'),
    ('apps/system/models/dict_type.py', '["code"]', '        return f"DictType<{self.code}>"'),
    ('apps/system/models/user_profile.py', '["user__username"]', '        return f"UserProfile<{self.user.username}>"'),
    ('apps/system/models/oper_log.py', None, '        return f"OperLog<{self.module}@{self.id}>"'),
    # common
    ('apps/common/models/image_upload.py', '["-created_at"]', '        return f"ImageUpload<{self.pk}> {self.image_group}"'),
    ('apps/common/models/file_folder.py', '["name"]', '        return f"FileFolder<{self.name}>"'),
    ('apps/common/models/file_asset.py', '["-created_at"]', '        return f"FileAsset<{self.file_name}>"'),
    ('apps/common/models/file_chunk.py', '["index"]', '        return f"FileChunk<{self.index}>"'),
    # notice
    ('apps/notice/models/notice.py', '["-publish_time", "-id"]', '        return f"Notice<{self.title}>"'),
    ('apps/notice/models/notice_target.py', '["-id"]', '        return f"NoticeTarget<notice={self.notice_id}>"'),
    ('apps/notice/models/notice_read.py', '["-id"]', '        return f"NoticeRead<user={self.user_id}>"'),
    # finance
    ('apps/finance/models/order_profit_cache.py', '["key"]', '        return f"OrderProfitCache<{self.key}>"'),
    # sales listing
    ('apps/sales/listing/models/lx_listing_info.py', '["id"]', '        return f"LxListingInfo<{self.id} {self.msku}>"'),
    ('apps/sales/listing/models/lx_listing_remark.py', '["id"]', '        return f"LxListingRemark<listing={self.listing_id}>"'),
    ('apps/sales/listing/models/lx_product_info.py', '["asin"]', '        return f"LxProductInfo<{self.asin}>"'),
    ('apps/sales/listing/models/lx_listing_metrics.py', None, '        return f"LxListingMetrics<listing={self.listing_id}>"'),
    # crawler
    ('apps/crawler/models/crawler_category.py', None, '        return f"{self.name} ({self.category_id})"'),
    ('apps/crawler/models/crawler_conf.py', None, '        return f"{self.server_name} ({self.node})"'),
    ('apps/crawler/models/crawler_seller_account.py', None, '        return f"{self.username}"'),
    ('apps/crawler/models/crawler_log.py', None, '        return f"CrawlerLog<{self.id}>"'),
]

for fpath, ordering, str_expr in model_fixes:
    f = base / fpath
    content = f.read_text(encoding='utf-8')
    changed = False

    # Add ordering if missing and provided
    if ordering and 'ordering' not in content:
        content = re.sub(
            r'(class Meta:\n)',
            rf'\1        ordering = {ordering}\n',
            content,
            count=1
        )
        changed = True

    # Add __str__ if missing
    if 'def __str__' not in content:
        # Insert after the Meta class block ends (before the next def or end of class)
        # Find the last line of Meta (a line starting with 8+ spaces that's inside Meta)
        # Strategy: insert before the first 'def ' at class level (4 spaces indent)
        str_block = f'\n    def __str__(self) -> str:\n{str_expr}\n'
        # Find end of Meta class - look for the pattern: closing bracket of indexes or last Meta attr
        # Insert after Meta block, before next method
        content = re.sub(
            r'(\n    def )',
            str_block + r'\1',
            content,
            count=1
        )
        changed = True

    if changed:
        safe_write(fpath, content)

print(f'ordering+__str__: {fixed} files')
fixed = 0

# ── 3. models/__init__.py for sales, timing, rules ──
init_files = {
    'apps/sales/models/__init__.py': '''from apps.sales.models.lx_user import LxUser
from apps.sales.models.lx_shops import LxShops
from apps.sales.models.lx_exchange_rate import LxExchangeRate

__all__ = ["LxUser", "LxShops", "LxExchangeRate"]
''',
    'apps/ads/sp/timing/models/__init__.py': '''from apps.ads.sp.timing.models.lx_time_pricing_strategy import LxTimePricingStrategy
from apps.ads.sp.timing.models.ad_time_pricing_hit import AdTimePricingHit

__all__ = ["LxTimePricingStrategy", "AdTimePricingHit"]
''',
    'apps/ads/sp/rules/models/__init__.py': '''from apps.ads.sp.rules.models.lx_ad_rule import LxAdRule
from apps.ads.sp.rules.models.lx_ad_rule_group import LxAdRuleGroup
from apps.ads.sp.rules.models.sp_bid_adjustment import SpBidAdjustment
from apps.ads.sp.rules.models.sp_campaign_adjustment import SpCampaignAdjustment
from apps.ads.sp.rules.models.sp_ad_optimization_strategy import SpAdOptimizationStrategy
from apps.ads.sp.rules.models.ad_upload_queue import AdUploadQueue
from apps.ads.sp.rules.models.lx_api_err import LxApiErr

__all__ = ["LxAdRule", "LxAdRuleGroup", "SpBidAdjustment", "SpCampaignAdjustment", "SpAdOptimizationStrategy", "AdUploadQueue", "LxApiErr"]
''',
}
for fpath, content in init_files.items():
    safe_write(fpath, content)

print(f'__init__.py: {fixed} files')

if errors:
    print(f'\nERRORS ({len(errors)}):')
    for e in errors:
        print(f'  {e}')
else:
    print('\nAll files passed syntax check')
