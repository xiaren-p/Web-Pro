"""深度对比验证: git show提取旧代码 vs 当前selector代码"""
import ast, subprocess, os, sys

BASE = '44f3600^'  # commit before all refactoring

def git_show(filepath):
    """Get file content from old commit"""
    r = subprocess.run(['git', 'show', f'{BASE}:{filepath}'], 
                       capture_output=True, text=True, cwd='.')
    return r.stdout if r.returncode == 0 else None

def extract_func_body(source, func_name):
    """Extract the body lines of a function from source"""
    if not source: return None
    try:
        tree = ast.parse(source)
    except:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.split('\n')
            return lines[node.body[0].lineno-1 : node.end_lineno]
    return None

def norm(lines):
    """Normalize: strip, skip empty/comments"""
    if not lines: return []
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith('#')]

ok = 0
errors = []

def compare(name, old_src, new_src, old_fn, new_fn):
    global ok
    old = extract_func_body(old_src, old_fn)
    new = extract_func_body(new_src, new_fn)
    if not old: errors.append(f"{name}: old {old_fn} not found"); return
    if not new: errors.append(f"{name}: new {new_fn} not found"); return
    o = norm(old)
    n = norm(new)
    if o == n:
        print(f"  ✓ {name}: IDENTICAL ({len(o)} stmts)")
        ok += 1
        return
    # Try with function name replacement
    n2 = [l.replace(new_fn, old_fn) for l in n]
    if o == n2:
        print(f"  ✓ {name}: IDENTICAL after name fix ({len(o)} stmts)")
        ok += 1
        return
    diffs = 0
    for i in range(max(len(o), len(n))):
        ol = o[i] if i < len(o) else "<MISSING>"
        nl = n[i] if i < len(n) else "<MISSING>"
        if ol != nl:
            diffs += 1
            if diffs <= 3:
                errors.append(f"{name}[{i}]: OLD={ol[:80]}")
                errors.append(f"{name}[{i}]: NEW={nl[:80]}")
    if diffs > 0:
        errors.append(f"{name}: {diffs} REAL differences!")

# Get old sources
old_kw = git_show('backend-master/apps/ads/sp/views/keyword_view.py')
old_at = git_show('backend-master/apps/ads/sp/views/auto_targeting_view.py')

# Get new selector sources
bid_sel = open('apps/ads/sp/selectors/bid_adjustment_selector.py', encoding='utf-8').read()
tp_sel = open('apps/ads/sp/selectors/time_pricing_selector.py', encoding='utf-8').read()
ci_sel = open('apps/ads/sp/selectors/currency_icon_selector.py', encoding='utf-8').read()
helpers = open('apps/ads/views/_helpers.py', encoding='utf-8').read()

# ── Bid adjustment (from keyword_view) ──
print("=== bid_adjustment (keyword_view → selector) ===")
compare('build_bid_latest_adjustment_map', old_kw, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('build_bid_lines', old_kw, bid_sel, '_build_bid_lines', 'build_bid_lines')

# ── Time pricing (from keyword_view) ──
print("=== time_pricing (keyword_view → selector) ===")
compare('build_time_pricing_bid_map', old_kw, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('is_time_pricing_active', old_kw, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

# ── Currency icon (from keyword_view) ──
print("=== currency_icon (keyword_view method → selector) ===")
old_ci = extract_func_body(old_kw, '_resolve_currency_icon')
new_ci = extract_func_body(ci_sel, 'resolve_currency_icon')
o = norm(old_ci) if old_ci else []
n = norm(new_ci) if new_ci else []
if o == n:
    print(f"  ✓ resolve_currency_icon: IDENTICAL ({len(o)} stmts)")
    ok += 1
else:
    errors.append(f"resolve_currency_icon: {len(o)} vs {len(n)} lines differ")

# ── Operator name (from keyword_view) ──
print("=== operator_name (keyword_view → _helpers) ===")
compare('get_operator_name', old_kw, helpers, '_get_operator_name', 'get_operator_name')

# ── Cross-check: auto_targeting_view versions match too ──
print("=== cross-check: auto_targeting_view same funcs → same selector ===")
compare('at_build_bid_latest_adjustment_map', old_at, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('at_build_bid_lines', old_at, bid_sel, '_build_bid_lines', 'build_bid_lines')
compare('at_build_time_pricing_bid_map', old_at, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('at_is_time_pricing_active', old_at, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

# ── Internal call chain ──
print("=== internal calls ===")
if 'build_bid_lines(rec' in bid_sel:
    print("  ✓ bid_sel internally calls build_bid_lines (renamed)")
    ok += 1
else:
    errors.append("bid_sel does NOT call build_bid_lines internally!")
if 'entity_field__in' in tp_sel:
    print("  ✓ entity_field dynamic query preserved")
    ok += 1

print(f"\n{'='*50}")
print(f"RESULTS: {ok} PASSED, {len(errors)} ISSUES")
for e in errors: print(f"  ❌ {e}")
if not errors and ok >= 9:
    print("ALL CHECKS PASSED — zero business logic differences")
