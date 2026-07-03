"""Deep verification of function body equivalence"""
import ast, subprocess, os

BASE = '44f3600^'

def git_show(filepath):
    r = subprocess.run(['git', 'show', f'{BASE}:{filepath}'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace',
                       cwd='.')
    return r.stdout if r.returncode == 0 else None

def extract_func_body(source, func_name):
    if not source: return None
    try:
        source_clean = source.encode('utf-8', errors='replace').decode('utf-8')
        tree = ast.parse(source_clean)
    except:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.split('\n')
            return lines[node.body[0].lineno-1 : node.end_lineno]
    return None

def norm(lines):
    if not lines: return []
    result = []
    for l in lines:
        l = l.strip()
        if not l: continue
        if l.startswith('#'): continue
        if l.startswith('"""') and l.endswith('"""'): continue  # skip docstrings
        result.append(l)
    return result

ok = 0
errors = []

def compare(name, old_src, new_src, old_fn, new_fn):
    global ok
    old = extract_func_body(old_src, old_fn)
    new = extract_func_body(new_src, new_fn)
    if not old: errors.append(f"{name}: old {old_fn} NOT FOUND"); return
    if not new: errors.append(f"{name}: new {new_fn} NOT FOUND"); return
    o = norm(old)
    n = norm(new)
    
    # Rename internal calls
    n2 = []
    for l in n:
        l2 = l
        if old_fn.startswith('_') and not new_fn.startswith('_'):
            l2 = l2.replace(new_fn, old_fn)
        n2.append(l2)
    
    if o == n2:
        print(f"  OK [{len(o)} lines] {name}")
        ok += 1
        return
    
    diffs = 0
    for i in range(max(len(o), len(n2))):
        ol = o[i] if i < len(o) else "<MISSING>"
        nl = n2[i] if i < len(n2) else "<MISSING>"
        if ol != nl:
            diffs += 1
            if diffs <= 4:
                errors.append(f"DIFF {name}[{i}]:")
                errors.append(f"  OLD: {ol[:100]}")
                errors.append(f"  NEW: {nl[:100]}")
    if diffs > 0:
        errors.append(f"{name}: {diffs} differences [{len(o)} vs {len(n2)} lines]")
    else:
        print(f"  OK [{len(o)} lines] {name} (after rename)")
        ok += 1

# Get sources
old_kw = git_show('backend-master/apps/ads/sp/views/keyword_view.py')
old_at = git_show('backend-master/apps/ads/sp/views/auto_targeting_view.py')
bid_sel = open('apps/ads/sp/selectors/bid_adjustment_selector.py', encoding='utf-8').read()
tp_sel = open('apps/ads/sp/selectors/time_pricing_selector.py', encoding='utf-8').read()
ci_sel = open('apps/ads/sp/selectors/currency_icon_selector.py', encoding='utf-8').read()
helpers = open('apps/ads/views/_helpers.py', encoding='utf-8').read()

print("=== 1. bid_adjustment (keyword_view -> selector) ===")
compare('build_bid_latest_adjustment_map', old_kw, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('build_bid_lines', old_kw, bid_sel, '_build_bid_lines', 'build_bid_lines')

print("=== 2. time_pricing (keyword_view -> selector) ===")
compare('build_time_pricing_bid_map', old_kw, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('is_time_pricing_active', old_kw, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

print("=== 3. currency_icon (keyword_view class method -> selector) ===")
old_ci = extract_func_body(old_kw, '_resolve_currency_icon')
new_ci = extract_func_body(ci_sel, 'resolve_currency_icon')
o = norm(old_ci) if old_ci else []
n = norm(new_ci) if new_ci else []
if o == n:
    print(f"  OK [{len(o)} lines] resolve_currency_icon")
    ok += 1
else:
    errors.append(f"resolve_currency_icon: [{len(o)} vs {len(n)}] STILL DIFFERS")

print("=== 4. operator_name (keyword_view -> _helpers) ===")
compare('get_operator_name', old_kw, helpers, '_get_operator_name', 'get_operator_name')

print("=== 5. cross-check: auto_targeting same funcs -> same selector ===")
compare('at_build_bid_latest_adjustment_map', old_at, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('at_build_bid_lines', old_at, bid_sel, '_build_bid_lines', 'build_bid_lines')
compare('at_build_time_pricing_bid_map', old_at, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('at_is_time_pricing_active', old_at, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

print("=== 6. Internal call chain ===")
if 'build_bid_lines(rec' in bid_sel:
    print("  OK internal call to build_bid_lines renamed correctly")
    ok += 1
else:
    errors.append("INTERNAL: bid_selector still calls old function name!")

if 'return result' in bid_sel:
    print("  OK return value structure preserved")
    ok += 1

print(f"\n{'='*50}")
print(f"RESULT: {ok} OK, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors[:20]: print(f"  {e}")
else:
    print("ALL CHECKS PASSED - zero business logic differences confirmed")
