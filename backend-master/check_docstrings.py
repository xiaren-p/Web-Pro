"""检查每个 apps/ 子目录的 docstring 覆盖率"""
import ast, pathlib, collections

base = pathlib.Path('apps')
stats = collections.defaultdict(lambda: {'total': 0, 'missing': 0, 'examples': []})

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or 'migrations' in str(f):
        continue
    try:
        tree = ast.parse(f.read_text(encoding='utf-8'))
    except:
        continue
    
    rel = str(f).replace('\\', '/')
    parts = rel.split('/')
    if len(parts) >= 3:
        app = parts[1]
        if len(parts) >= 4:
            subdir = parts[2]
        else:
            subdir = '_root'
    else:
        app = parts[0]
        subdir = '_root'
    
    key = f"{app}/{subdir}"
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stats[key]['total'] += 1
            docstring = ast.get_docstring(node)
            if not docstring:
                stats[key]['missing'] += 1
                if len(stats[key]['examples']) < 2:
                    short = rel.replace('apps/', '')
                    stats[key]['examples'].append(f'  {short}:{node.lineno} {node.name}')

print(f"{'Domain':<30s} | {'Total':>5s} | {'Missing':>7s} | {'%':>5s}")
print("-" * 60)
for key in sorted(stats.keys()):
    s = stats[key]
    if s['total'] == 0:
        continue
    pct = s['missing'] / s['total'] * 100
    print(f"{key:<30s} | {s['total']:5d} | {s['missing']:7d} | {pct:5.1f}%")
    for ex in s['examples']:
        print(f"  {ex}")

total_all = sum(s['total'] for s in stats.values())
missing_all = sum(s['missing'] for s in stats.values())
print(f"\nTOTAL: {missing_all}/{total_all} missing ({missing_all/total_all*100:.1f}%)")
