"""扫描所有 Python 文件的 docstring 覆盖率"""
import ast, pathlib, collections

base = pathlib.Path('.')
stats = collections.defaultdict(lambda: {'total': 0, 'missing': 0, 'examples': []})

files = list(base.rglob('*.py'))
files = [f for f in files if '__pycache__' not in str(f) and 'migrations' not in str(f) and 'fix_models' not in str(f)]

for f in files:
    try:
        tree = ast.parse(f.read_text(encoding='utf-8'))
    except:
        continue
    rel = str(f).replace('\\', '/')
    if '/apps/' in rel:
        app = rel.split('/apps/')[1].split('/')[0]
    elif 'backend_master' in rel:
        app = 'config'
    else:
        app = 'other'

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stats[app]['total'] += 1
            docstring = ast.get_docstring(node)
            if not docstring:
                stats[app]['missing'] += 1
                if len(stats[app]['examples']) < 5:
                    stats[app]['examples'].append(f'{rel}:{node.lineno} {type(node).__name__} {node.name}')

print('App       | Total | Missing | Pct')
print('-' * 55)
for app in sorted(stats.keys()):
    s = stats[app]
    pct = (s['missing'] / s['total'] * 100) if s['total'] else 0
    print(f'{app:10s} | {s["total"]:5d} | {s["missing"]:7d} | {pct:5.1f}%')
    for ex in s['examples']:
        print(f'  -> {ex}')
print()
total_all = sum(s['total'] for s in stats.values())
missing_all = sum(s['missing'] for s in stats.values())
pct_all = missing_all / total_all * 100 if total_all else 0
print(f'TOTAL: {missing_all}/{total_all} missing ({pct_all:.1f}%)')
