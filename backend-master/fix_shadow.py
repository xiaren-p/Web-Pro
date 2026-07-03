"""Remove local cache function defs that shadow selector imports"""
import pathlib, ast

fpath = pathlib.Path('apps/ads/sp/views/ad_campaign_view.py')
source = fpath.read_text(encoding='utf-8')
tree = ast.parse(source)

funcs_to_remove = {
    'get_profile_map', 'get_sid_country_map', 'get_rate_map', 'load_all_listing_caches',
    'get_tag_asin_map', 'get_owner_asin_map', 'get_asin_info_map',
    'get_asin_cp_map', 'get_sku_cp_map', 'get_cp_asin_map'
}

# Find all FunctionDef nodes at module level (not nested)
ranges_to_remove = []
for node in ast.iter_child_nodes(tree):
    if isinstance(node, ast.FunctionDef) and node.name in funcs_to_remove:
        ranges_to_remove.append((node.lineno - 1, node.end_lineno))

# Sort by start line descending (so we can remove from bottom up)
ranges_to_remove.sort(reverse=True)

lines = source.split('\n')
for start, end in ranges_to_remove:
    # Remove the function definition and its body
    del lines[start:end]
    # If there's a blank line before it, remove one extra blank
    if start > 0 and lines[start-1].strip() == '':
        del lines[start-1]

# Also remove the _REF_TTL and _cache import if no local cache funcs remain
# Check if any remaining definition uses _cache
remaining = '\n'.join(lines)
if '_cache.get(' not in remaining and '_cache.set(' not in remaining:
    lines = [l for l in lines if 'from django.core.cache import cache as _cache' not in l]
    lines = [l for l in lines if '_REF_TTL = 600' not in l]

# Clean up triple+ blank lines
result = []
blank_count = 0
for line in lines:
    if line.strip() == '':
        blank_count += 1
        if blank_count <= 2:
            result.append(line)
    else:
        blank_count = 0
        result.append(line)

fpath.write_text('\n'.join(result), encoding='utf-8')
print('Done')
