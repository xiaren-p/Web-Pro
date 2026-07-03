"""Fix duplicate imports in ad views"""
import pathlib, re

files = [
    'apps/ads/views/shop_profile_view.py',
    'apps/ads/views/ad_portfolio_view.py',
    'apps/ads/sp/views/ad_campaign_view.py',
    'apps/ads/sp/views/ad_group_view.py',
    'apps/ads/sp/views/ad_view.py',
    'apps/ads/sp/views/auto_targeting_view.py',
    'apps/ads/sp/views/auto_negative_targeting_view.py',
    'apps/ads/sp/views/keyword_view.py',
    'apps/ads/sp/views/negative_keyword_view.py',
    'apps/ads/sp/views/ad_campaign_view.py',
    'apps/sales/listing/views/listing_view.py',
    'apps/sales/listing/views/listing_tag_view.py',
    'apps/crawler/views/crawler_log_view.py',
    'apps/system/views/profile_view.py',
]

for fpath in files:
    f = pathlib.Path(fpath)
    c = f.read_text(encoding='utf-8')
    lines = c.split('\n')
    
    # Fix duplicate IsAuthenticated imports - keep first, remove subsequent duplicates
    seen_isa = False
    seen_currency = False
    seen_operator = False
    seen_selectors = set()
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # Deduplicate IsAuthenticated
        if stripped == 'from rest_framework.permissions import IsAuthenticated':
            if not seen_isa:
                seen_isa = True
                new_lines.append(line)
            # else skip duplicate
            continue
        
        # Deduplicate resolve_currency_icon
        if 'from apps.ads.sp.selectors.currency_icon_selector import' in stripped:
            if not seen_currency:
                seen_currency = True
                new_lines.append(line)
            continue
        
        # Deduplicate get_operator_name  
        if 'from apps.ads.views._helpers import get_operator_name' in stripped:
            if not seen_operator:
                seen_operator = True
                new_lines.append(line)
            continue
        
        # Deduplicate campaign_ref_selectors multiple imports
        if 'from apps.ads.sp.selectors.campaign_ref_selectors import' in stripped:
            if stripped not in seen_selectors:
                seen_selectors.add(stripped)
                new_lines.append(line)
            continue
        
        # Deduplicate other selector imports
        if 'from apps.ads.sp.selectors.bid_adjustment_selector import' in stripped:
            if stripped not in seen_selectors:
                seen_selectors.add(stripped)
                new_lines.append(line)
            continue
        
        if 'from apps.ads.sp.selectors.time_pricing_selector import' in stripped:
            if stripped not in seen_selectors:
                seen_selectors.add(stripped)
                new_lines.append(line)
            continue
        
        new_lines.append(line)
    
    f.write_text('\n'.join(new_lines), encoding='utf-8')
    print(f'Dedup: {fpath}')

print('Done')
