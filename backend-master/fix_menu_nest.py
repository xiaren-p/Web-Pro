"""Fix indentation: move data-collect block out of for loop"""
import pathlib

f = pathlib.Path('apps/system/management/commands/sync_system_menus.py')
lines = f.read_text(encoding='utf-8').split('\n')

# Lines 196-253 (0-indexed: 195-252) are at 12-space indent inside the for loop
# They should be at 8-space indent (same level as the for loop)
for i in range(195, min(253, len(lines))):
    line = lines[i]
    if line.startswith('            '):  # 12 spaces
        lines[i] = line[4:]  # Remove 4 spaces
    elif line.strip() == '':
        lines[i] = ''  # Keep blank lines

f.write_text('\n'.join(lines), encoding='utf-8')
print('Fixed sync_system_menus.py indentation')
