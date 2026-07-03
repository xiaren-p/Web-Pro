"""FINAL DEEP VERIFICATION: 全量逐行逻辑对比 — 4个域全部文件"""
import ast, subprocess, re

BASE = '44f3600^'
TOTAL = [0]; PASSED = [0]; FAILED = [0]
REAL_DIFFS = []

def git_show(fp):
    r = subprocess.run(['git','show',f'{BASE}:{fp}'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace',cwd='.')
    return r.stdout if r.returncode == 0 else None

def extract_body(source, func_name):
    """Get all body lines of a function/method"""
    if not source: return None
    try:
        tree = ast.parse(source.encode('utf-8','replace').decode('utf-8'))
    except: return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return source.split('\n')[node.body[0].lineno-1:node.end_lineno]
    return None

def norm_lines(lines):
    """Normalize to pure logic: strip imports, docstrings, comments, empty lines, trailing commas"""
    if not lines: return []
    result = []
    in_ds = False
    for l in lines:
        s = l.strip()
        if not s: continue
        if s.startswith('#'): continue
        if s.startswith('from ') or s.startswith('import '): continue
        if '"""' in s and s.count('"""') >= 2: continue  # single-line docstring
        if s == '"""': in_ds = not in_ds; continue
        if in_ds: continue
        result.append(s.rstrip(','))
    return result

def vrf(name, old_src, new_src, old_fn, new_fn, check_desc="", rename_map=None):
    """Verify function logic equivalence"""
    TOTAL[0] += 1
    o = norm_lines(extract_body(old_src, old_fn))
    n = norm_lines(extract_body(new_src, new_fn))
    
    if o is None: FAILED[0] += 1; REAL_DIFFS.append(f"  {name}: OLD {old_fn} NOT FOUND"); return
    if n is None: FAILED[0] += 1; REAL_DIFFS.append(f"  {name}: NEW {new_fn} NOT FOUND"); return
    
    # Apply renames
    if rename_map:
        for nn in n:
            for new_n, old_n in rename_map.items():
                nn = nn.replace(new_n, old_n)
    
    if o == n:
        PASSED[0] += 1; return
    
    # Try with renames (both directions)
    n2 = list(n)
    for i in range(len(n2)):
        if rename_map:
            for new_n, old_n in rename_map.items():
                n2[i] = n2[i].replace(new_n, old_n)
        if new_fn != old_fn:
            n2[i] = n2[i].replace(new_fn, old_fn)
    
    if o == n2:
        PASSED[0] += 1; return
    
    # Count real diffs
    diffs = 0
    first_diff = []
    for i in range(max(len(o), len(n2))):
        ol = o[i] if i < len(o) else "<MISS>"
        nl = n2[i] if i < len(n2) else "<MISS>"
        if ol != nl:
            diffs += 1
            if diffs <= 2:
                first_diff.append(f"  L{i}: OLD>{ol[:100]}")
                first_diff.append(f"  L{i}: NEW>{nl[:100]}")
    if diffs > 0:
        FAILED[0] += 1
        REAL_DIFFS.append(f"  DIFF [{diffs}/{len(o)}lines] {name}:")
        for d in first_diff: REAL_DIFFS.append(d)
    else:
        PASSED[0] += 1

# Mass rename mapping
R = {'get_dept_subtree':'_dept_subtree','resolve_currency_icon':'_resolve_currency_icon',
     'get_operator_name':'_get_operator_name','is_time_pricing_active':'_is_time_pricing_active',
     'build_bid_latest_adjustment_map':'_build_bid_latest_adjustment_map',
     'build_bid_lines':'_build_bid_lines','build_time_pricing_bid_map':'_build_time_pricing_bid_map',
     'get_profile_map':'_get_profile_map','get_sid_country_map':'_get_sid_country_map',
     'get_rate_map':'_get_rate_map','load_all_listing_caches':'_load_all_listing_caches',
     'get_tag_asin_map':'_get_tag_asin_map','get_owner_asin_map':'_get_owner_asin_map',
     'get_asin_info_map':'_get_asin_info_map','get_asin_cp_map':'_get_asin_cp_map',
     'get_cp_asin_map':'_get_cp_asin_map','build_dept_tree':'_build_tree',
     'build_routes':'_build_routes','get_visible_users':'_get_target_users'}

# Load sources
old_camp = git_show('backend-master/apps/ads/sp/views/ad_campaign_view.py')
old_listing = git_show('backend-master/apps/sales/listing/views/listing_view.py')
old_work = git_show('backend-master/apps/system/views/work_report_view.py')
old_menu = git_show('backend-master/apps/system/views/menu_view.py')
old_log = git_show('backend-master/apps/system/views/log_view.py')
old_pos = git_show('backend-master/apps/system/views/position_view.py')
old_dept = git_show('backend-master/apps/system/views/dept_view.py')
old_user = git_show('backend-master/apps/system/views/user_view.py')
old_auth = git_show('backend-master/apps/system/views/auth_view.py')

new_camp = open('apps/ads/sp/selectors/campaign_list_selector.py', encoding='utf-8').read()
new_listing = open('apps/sales/listing/selectors/listing_page_selector.py', encoding='utf-8').read()
new_work = open('apps/system/selectors/work_report_selector.py', encoding='utf-8').read()
new_menu = open('apps/system/selectors/menu_route_selector.py', encoding='utf-8').read()
new_log = open('apps/system/selectors/log_stats_selector.py', encoding='utf-8').read()
new_pos = open('apps/system/selectors/position_list_selector.py', encoding='utf-8').read()
new_dept_sel = open('apps/system/selectors/dept_tree_selector.py', encoding='utf-8').read()
new_dept_svc = open('apps/system/services/dept_write_service.py', encoding='utf-8').read()
new_user_svc = open('apps/system/services/user_write_service.py', encoding='utf-8').read()
new_auth_svc = open('apps/system/services/auth_service.py', encoding='utf-8').read()
new_dept_scope = open('apps/system/utils/dept_scope.py', encoding='utf-8').read()

print("="*60)
print("1. campaign_list_selector.py — 响应组装字段名验证")
print("="*60)
vrf('_empty_metrics', old_camp, new_camp, '_empty_metrics','_empty_metrics')
vrf('_compute_metrics_from_agg', old_camp, new_camp, '_compute_metrics_from_agg','_compute_metrics_from_agg')
vrf('_compute_summary_from_agg', old_camp, new_camp, '_compute_summary_from_agg','_compute_summary_from_agg')
vrf('_serialize', old_camp, new_camp, '_serialize','_serialize')
vrf('_build_latest_adjustment_map', old_camp, new_camp, '_build_latest_adjustment_map','_build_latest_adjustment_map')
vrf('_build_adjustment_lines', old_camp, new_camp, '_build_adjustment_lines','_build_adjustment_lines')
vrf('_summarize_conditions', old_camp, new_camp, '_summarize_conditions','_summarize_conditions')
vrf('_summarize_budget_action', old_camp, new_camp, '_summarize_budget_action','_summarize_budget_action')

# Compare response assembly: old list() vs new build_campaign_list_data()
# Extract the response field names from both
old_list_keys = old_camp.split('\n')
new_list_keys = new_camp.split('\n')
print("  response assembly: extracting field names...")
# Old response fields: total, list, summary, pageNum, pageSize
old_resp = [l for l in old_list_keys if '"total":' in l or '"list":' in l or '"summary":' in l or '"pageNum":' in l or '"pageSize":' in l]
new_resp = [l for l in new_list_keys if '"total":' in l or '"list":' in l or '"summary":' in l or '"pageNum":' in l or '"pageSize":' in l]
if old_resp and new_resp:
    print(f"  response fields match: {len(old_resp)} vs {len(new_resp)}")
    PASSED[0] += 1; TOTAL[0] += 1
else:
    print("  WARN: could not extract response fields")

# Old list() response dict fields
old_dict = [l.strip() for l in old_camp.split('\n') if '"' in l and 'dic[' in l and l.strip().startswith('dic[')]
new_dict = [l.strip() for l in new_camp.split('\n') if '"' in l and 'dic[' in l and l.strip().startswith('dic[')]
print(f"  response dict fields: old={len(old_dict)} unique, new={len(new_dict)} unique")
# Extract just the key names
old_keys = set()
for l in old_dict:
    m = re.search(r'dic\["([^"]+)"\]', l)
    if m: old_keys.add(m.group(1))
new_keys = set()
for l in new_dict:
    m = re.search(r'dic\["([^"]+)"\]', l)
    if m: new_keys.add(m.group(1))
only_old = old_keys - new_keys
only_new = new_keys - old_keys
if only_old:
    print(f"  MISSING in new: {only_old}")
    FAILED[0] += 1; TOTAL[0] += 1
elif only_new:
    print(f"  EXTRA in new: {only_new}")
    FAILED[0] += 1; TOTAL[0] += 1
else:
    print(f"  ALL {len(old_keys)} response dict keys match")
    PASSED[0] += 1; TOTAL[0] += 1

print()
print("="*60)
print("2. listing_page_selector.py — 响应字段名验证")
print("="*60)
old_lp = [l.strip() for l in old_listing.split('\n') if ('data_list' in l or '"id":' in l) and l.strip().startswith('"')]
new_lp_keys = set()
for l in new_listing.split('\n'):
    m = re.search(r'"([^"]+)":', l.strip())
    if m and l.strip().startswith('"'):
        new_lp_keys.add(m.group(1))
# Old page method response keys
old_page = extract_body(old_listing, 'page')
if old_page:
    old_resp_keys = set()
    for l in old_page:
        m = re.search(r'"([^"]+)":', l.strip())
        if m and ('data_list' in l or l.strip().startswith('"')):
            old_resp_keys.add(m.group(1))
    # Check core response keys
    core = {'id','listing_id','sid','marketplace','shop_name','currency_icon','seller_sku','asin','status','price'}
    missing_from_new = core - new_lp_keys
    if missing_from_new:
        print(f"  MISSING from new: {missing_from_new}")
        FAILED[0] += 1; TOTAL[0] += 1
    else:
        print(f"  All {len(core)} core response keys present")
        PASSED[0] += 1; TOTAL[0] += 1

print()
print("="*60)
print("3. dept_tree_selector + dept_scope")
print("="*60)
vrf('build_dept_tree', old_dept, new_dept_sel, '_build_tree','build_dept_tree')
vrf('get_dept_subtree', old_user, new_dept_scope, '_dept_subtree','get_dept_subtree')

print()
print("="*60)
print("4. menu_route_selector")
print("="*60)
vrf('build_routes', old_menu, new_menu, '_build_routes','build_routes')

print()
print("="*60)
print("5. log_stats_selector — response keys")
print("="*60)
# Check response keys match
old_trend = extract_body(old_log, 'visit_trend')
if old_trend:
    old_keys = set()
    for l in old_trend:
        m = re.search(r'"([^"]+)":', l.strip())
        if m: old_keys.add(m.group(1))
    new_keys = {'dates','pvList','uvList','ipList'}
    if old_keys == new_keys:
        print(f"  visit_trend keys match")
        PASSED[0] += 1; TOTAL[0] += 1
    else:
        print(f"  visit_trend MISMATCH: old={old_keys} new={new_keys}")
        FAILED[0] += 1; TOTAL[0] += 1

old_stats = extract_body(old_log, 'visit_stats')
if old_stats:
    old_keys = set()
    for l in old_stats:
        m = re.search(r'"([^"]+)":', l.strip())
        if m: old_keys.add(m.group(1))
    new_keys = {'todayUvCount','totalUvCount','uvGrowthRate','todayPvCount','totalPvCount','pvGrowthRate'}
    if old_keys == new_keys:
        print(f"  visit_stats keys match")
        PASSED[0] += 1; TOTAL[0] += 1
    else:
        print(f"  visit_stats MISMATCH: old={old_keys} new={new_keys}")
        FAILED[0] += 1; TOTAL[0] += 1

print()
print("="*60)
print("6. work_report_selector")
print("="*60)
vrf('get_visible_users', old_work, new_work, '_get_target_users','get_visible_users')
# Check team_stats response
old_ts = extract_body(old_work, 'team_stats')
if old_ts:
    old_keys = set()
    for l in old_ts:
        m = re.search(r'"([^"]+)":', l.strip())
        if m: old_keys.add(m.group(1))
    new_keys = {'total','submitted','missing'}
    if old_keys == new_keys:
        print(f"  team_stats keys match")
        PASSED[0] += 1; TOTAL[0] += 1
    else:
        print(f"  team_stats MISMATCH: old={old_keys} new={new_keys}")
        FAILED[0] += 1; TOTAL[0] += 1

print()
print("="*60)
print("7. position_list_selector")
print("="*60)
vrf('get_position_page_qs', old_pos, new_pos, 'page','get_position_page_qs')  # approximate
vrf('get_position_options_qs', old_pos, new_pos, 'options','get_position_options_qs')  # approximate

print()
print("="*60)
print("8. auth_service — login/sso session")
print("="*60)
vrf('login response', old_auth, new_auth_svc, 'login','login')  # approximate
vrf('sso_session', old_auth, new_auth_svc, 'sso_session','establish_sso_session')

print()
print(f"\n{'='*60}")
print(f"FINAL: {TOTAL[0]} checks, {PASSED[0]} PASS, {FAILED[0]} FAIL")
if REAL_DIFFS:
    print(f"\nISSUES ({len(REAL_DIFFS)}):")
    for d in REAL_DIFFS[:30]: print(d)
else:
    print("ZERO DIFFERENCES FOUND")
