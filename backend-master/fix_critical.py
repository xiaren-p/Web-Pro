"""Fix critical issues across the codebase"""
import pathlib, re

# 1. Fix traceback exposure in finance views
for fpath in ['apps/finance/views/statistics_view.py', 'apps/finance/views/monthly_loss_view.py', 'apps/finance/views/monthly_loss_first20_view.py']:
    f = pathlib.Path(fpath)
    c = f.read_text(encoding='utf-8')
    # Remove "'trace': tb" patterns
    c = re.sub(r"'trace':\s*tb\s*[,]?(?:\s*\n\s*)?", '', c)
    c = re.sub(r'["]trace["]:\s*tb\s*[,]?(?:\s*\n\s*)?', '', c)
    f.write_text(c, encoding='utf-8')
    print(f'Fixed traces: {fpath}')

# 2. Fix settings.py REDIS_URL + celery docstring
f = pathlib.Path('backend_master/settings.py')
c = f.read_text(encoding='utf-8')
c = c.replace('REDIS_URL if False else env("REDIS_URL")', 'env("REDIS_URL")')
f.write_text(c, encoding='utf-8')

# 3. Fix celery.py docstring
f = pathlib.Path('backend_master/celery.py')
c = f.read_text(encoding='utf-8')
c = c.replace('-Q default -c 2', '-Q celery,parallel_queue,single_thread_queue')
f.write_text(c, encoding='utf-8')

# 4. Fix _helpers.py duplicate get_operator_name
f = pathlib.Path('apps/ads/views/_helpers.py')
c = f.read_text(encoding='utf-8')
# Remove the 2nd copy (the one after line 215)
lines = c.split('\n')
# Find the second definition
first_def = None
second_def = None
for i, line in enumerate(lines):
    if 'def get_operator_name' in line:
        if first_def is None:
            first_def = i
        else:
            second_def = i
if second_def and first_def:
    # Remove from second_def to end of function (blank line after)
    end = second_def
    for j in range(second_def + 1, len(lines)):
        if lines[j].strip() == '' and j > second_def + 10:
            end = j
            break
    del lines[second_def:end+1]
    f.write_text('\n'.join(lines), encoding='utf-8')
    print('Fixed: _helpers.py duplicate get_operator_name')

print('All critical fixes applied')
