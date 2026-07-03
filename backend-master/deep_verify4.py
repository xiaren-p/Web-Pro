"""Final verification: compare pure logic, skip ALL docstrings/imports/comments"""
import ast, subprocess

BASE = '44f3600^'

def git_show(fp):
    r = subprocess.run(['git','show',f'{BASE}:{fp}'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', cwd='.')
    return r.stdout if r.returncode == 0 else None

def get_logic_lines(source, func_name):
    """Get ONLY the logic lines of a function - no docstrings, no imports, no comments"""
    if not source: return []
    try:
        tree = ast.parse(source.encode('utf-8','replace').decode('utf-8'))
    except: return []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            lines = source.split('\n')
            result = []
            # Get docstring node if present
            doc_node = ast.get_docstring(node, clean=False)
            # Find first statement that is NOT the docstring
            first_body = node.body[0]
            if (isinstance(first_body, ast.Expr) and 
                isinstance(first_body.value, ast.Constant) and 
                isinstance(first_body.value.value, str)):
                start_idx = first_body.end_lineno  # skip docstring line
            else:
                start_idx = first_body.lineno - 1
            
            for i in range(start_idx, node.end_lineno):
                stripped = lines[i].strip()
                if not stripped: continue
                if stripped.startswith('#'): continue
                if stripped.startswith('from ') or stripped.startswith('import '): continue
                result.append(stripped)
            return result
    return []

def compare(name, old_src, new_src, old_fn, new_fn):
    global ok
    o = get_logic_lines(old_src, old_fn)
    n = get_logic_lines(new_src, new_fn)
    if not o: errors.append(f"NOT FOUND: old {old_fn}"); return
    if not n: errors.append(f"NOT FOUND: new {new_fn}"); return
    
    # Rename internal calls
    if old_fn.startswith('_') and not new_fn.startswith('_'):
        n = [l.replace(new_fn, old_fn) for l in n]
    
    if o == n:
        print(f"  PASS [{len(o)} logic lines] {name}")
        ok[0] += 1; return
    
    diffs = 0
    for i in range(max(len(o), len(n))):
        ol = o[i] if i < len(o) else ""
        nl = n[i] if i < len(n) else ""
        if ol != nl: diffs += 1
    if diffs:
        errors.append(f"  FAIL {name}: {diffs} logic differences in {len(o)}/{len(n)} lines")
        for i in range(min(len(o), len(n))):
            if o[i] != n[i]:
                errors.append(f"    L{i}: OLD>{o[i][:80]}")
                errors.append(f"    L{i}: NEW>{n[i][:80]}")
                break
    else:
        print(f"  PASS [{len(o)} lines] {name} (renames only)")
        ok[0] += 1

ok = [0]
errors = []

print("=== DEEP LOGIC VERIFICATION ===")
print("(comparing pure logic - no docstrings, imports, or comments)")
print()

old_kw = git_show('backend-master/apps/ads/sp/views/keyword_view.py')
old_at = git_show('backend-master/apps/ads/sp/views/auto_targeting_view.py')
bid_sel = open('apps/ads/sp/selectors/bid_adjustment_selector.py', encoding='utf-8').read()
tp_sel = open('apps/ads/sp/selectors/time_pricing_selector.py', encoding='utf-8').read()
ci_sel = open('apps/ads/sp/selectors/currency_icon_selector.py', encoding='utf-8').read()
helpers = open('apps/ads/views/_helpers.py', encoding='utf-8').read()

compare('build_bid_latest_adjustment_map', old_kw, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('build_bid_lines', old_kw, bid_sel, '_build_bid_lines', 'build_bid_lines')
compare('build_time_pricing_bid_map', old_kw, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('is_time_pricing_active', old_kw, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')
compare('resolve_currency_icon', old_kw, ci_sel, '_resolve_currency_icon', 'resolve_currency_icon')
compare('get_operator_name', old_kw, helpers, '_get_operator_name', 'get_operator_name')

# Cross-check with auto_targeting
compare('at_build_bid_latest_adjustment', old_at, bid_sel, '_build_bid_latest_adjustment_map', 'build_bid_latest_adjustment_map')
compare('at_build_bid_lines', old_at, bid_sel, '_build_bid_lines', 'build_bid_lines')
compare('at_build_time_pricing_bid_map', old_at, tp_sel, '_build_time_pricing_bid_map', 'build_time_pricing_bid_map')
compare('at_is_time_pricing_active', old_at, tp_sel, '_is_time_pricing_active', 'is_time_pricing_active')

# Internal call check
if 'build_bid_lines(rec' in bid_sel:
    print("  PASS internal call: build_bid_lines renamed correctly")

print(f"\n{'='*50}")
if errors:
    print(f"RESULT: {ok[0]} PASSED, {len(errors)} FAILURES")
    for e in errors: print(e)
else:
    print(f"RESULT: {ok[0]}/{ok[0]} ALL PASSED")
    print("CONFIRMED: ZERO business logic differences in any extracted function")
