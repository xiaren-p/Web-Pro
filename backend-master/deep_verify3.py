"""Deep verification - skip imports, docstrings; compare pure logic"""
import ast, subprocess

BASE = '44f3600^'

def git_show(fp):
    r = subprocess.run(['git','show',f'{BASE}:{fp}'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd='.')
    return r.stdout if r.returncode == 0 else None

def extract_func_body(source, func_name):
    if not source: return None
    try:
        tree = ast.parse(source.encode('utf-8','replace').decode('utf-8'))
    except: return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.split('\n')
            return lines[node.body[0].lineno-1:node.end_lineno]
    return None

def norm(lines):
    """Normalize: remove imports, docstrings, comments, empty lines"""
    if not lines: return []
    result = []
    in_docstring = False
    for l in lines:
        stripped = l.strip()
        if not stripped: continue
        if stripped.startswith('#'): continue
        if stripped.startswith('from ') or stripped.startswith('import '): continue
        if stripped.startswith('"""') and stripped.endswith('"""') and len(stripped) > 6: continue
        if stripped == '"""': in_docstring = not in_docstring; continue
        if in_docstring: continue
        result.append(stripped)
    return result

ok = 0
errors = []

def compare(name, old_src, new_src, old_fn, new_fn):
    global ok
    old = extract_func_body(old_src, old_fn)
    new = extract_func_body(new_src, new_fn)
    if not old: errors.append(f"NOT FOUND old: {old_fn} in {name}"); return
    if not new: errors.append(f"NOT FOUND new: {new_fn} in {name}"); return
    
    o = norm(old)
    n = norm(new)
    # Rename internal function calls
    if old_fn.startswith('_') and not new_fn.startswith('_'):
        n = [l.replace(new_fn, old_fn) for l in n]
    
    if o == n:
        print(f"  PASS [{len(o)} logic lines] {name}")
        ok += 1
        return
    
    diffs = 0
    for i in range(max(len(o), len(n))):
        ol = o[i] if i < len(o) else ""
        nl = n[i] if i < len(n) else ""
        if ol != nl:
            diffs += 1
            if diffs <= 3:
                errors.append(f"  {name}[L{i}]: OLD>{ol[:90]}")
                errors.append(f"  {name}[L{i}]: NEW>{nl[:90]}")
    if diffs:
        errors.append(f"  FAIL {name}: {diffs} logic differences [{len(o)} vs {len(n)} lines]")
    else:
        print(f"  PASS [{len(o)} lines] {name} (reorder only)")
        ok += 1

# Get sources
old_kw = git_show('backend-master/apps/ads/sp/views/keyword_view.py')
old_at = git_show('backend-master/apps/ads/sp/views/auto_targeting_view.py')
bid_sel = open('apps/ads/sp/selectors/bid_adjustment_selector.py', encoding='utf-8').read()
tp_sel = open('apps/ads/sp/selectors/time_pricing_selector.py', encoding='utf-8').read()
ci_sel = open('apps/ads/sp/selectors/currency_icon_selector.py', encoding='utf-8').read()
helpers = open('apps/ads/views/_helpers.py', encoding='utf-8').read()

print("1. bid_adjustment (keyword_view -> selector)")
compare('map', old_kw, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('lines', old_kw, bid_sel, '_build_bid_lines', 'build_bid_lines')

print("2. time_pricing (keyword_view -> selector)")
compare('tp_map', old_kw, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('tp_active', old_kw, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

print("3. currency_icon")
old_ci = extract_func_body(old_kw, '_resolve_currency_icon')
new_ci = extract_func_body(ci_sel, 'resolve_currency_icon')
o = norm(old_ci) if old_ci else []
n = norm(new_ci) if new_ci else []
if o == n: print(f"  PASS [{len(o)} lines]"); ok += 1
else: errors.append(f"currency_icon: {len(o)} vs {len(n)} differs")

print("4. operator_name")
compare('op', old_kw, helpers, '_get_operator_name', 'get_operator_name')

print("5. cross-check auto_targeting")
compare('at_map', old_at, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('at_lines', old_at, bid_sel, '_build_bid_lines', 'build_bid_lines')
compare('at_tp_map', old_at, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('at_tp_active', old_at, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

print(f"\n{'='*50}")
if errors:
    print(f"RESULT: {ok} PASSED, {len(errors)//2} failures:")
    for e in errors: print(e)
else:
    print(f"RESULT: {ok}/{ok} ALL PASSED - zero logic differences")
