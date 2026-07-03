"""Frontend deep scan: dead code, stale refs, deprecated APIs, architecture"""
import pathlib, re

base = pathlib.Path('vue3-element-admin-master/src')
results = {
    'todo_fixme': [],
    'any_type': [],
    'deprecated_route': [],
    'empty_component': [],
    'no_types_file': [],
}
deleted_routes = ['/statistics/', 'lossmakingorders_sync', 'lossmakingorders_data']

for f in sorted(base.rglob('*.ts')) + sorted(base.rglob('*.vue')):
    if '.d.ts' in str(f): continue
    try:
        c = f.read_text(encoding='utf-8')
    except:
        continue
    rel = str(f).replace('\\', '/').replace('vue3-element-admin-master/', '')
    
    # TODO/FIXME
    for m in re.finditer(r'//\s*(TODO|FIXME|XXX|HACK)', c):
        line = c[:m.start()].count('\n') + 1
        text = c[m.start():m.start()+80].replace('\n', ' ').strip()
        results['todo_fixme'].append(f'{rel}:{line}: {text}')
    
    # any type overuse
    any_count = len(re.findall(r':\s*any\b', c))
    if any_count > 5:
        results['any_type'].append(f'{rel}: {any_count}x any')
    
    # Deleted backend routes
    for route in deleted_routes:
        if route in c and 'api/' in rel:
            results['deprecated_route'].append(f'{rel}: references {route}')
    
    # Empty component script
    if f.suffix == '.vue' and '<script' not in c:
        results['empty_component'].append(rel)

for cat, items in results.items():
    if items:
        print(f'\n=== {cat.upper()} ({len(items)}) ===')
        for item in items[:20]:
            print(f'  {item}')
        if len(items) > 20:
            print(f'  ... {len(items)-20} more')

print(f'\nTotal issues: {sum(len(v) for v in results.values())}')
