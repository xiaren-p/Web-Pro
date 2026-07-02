"""批量补充缺失的 docstring — 基于 AST 分析自动生成"""
import ast, pathlib, re

base = pathlib.Path('apps')
fixed = 0
errors = []

def make_docstring(node, file_path):
    """根据节点类型和名称生成 docstring"""
    name = node.name
    
    # Meta 内部类 — 跳过（Django 约定不需要）
    if name == 'Meta':
        return None
    
    # __str__ 方法
    if name == '__str__':
        return '"""返回模型的字符串表示。"""'
    
    # __init__ 方法
    if name == '__init__':
        return '"""初始化实例。"""'
    
    # AppConfig 类
    if name.endswith('Config') and isinstance(node, ast.ClassDef):
        app_name = name.replace('Config', '')
        return f'"""{app_name} 应用配置。"""'
    
    # ViewSet 类
    if name.endswith('ViewSet') or name.endswith('View'):
        return f'"""{name} 视图集。"""'
    
    # Serializer 类
    if name.endswith('Serializer'):
        return f'"""{name} 序列化器。"""'
    
    # Service 类
    if name.endswith('Service'):
        return f'"""{name} 业务服务。"""'
    
    # Selector 类
    if name.endswith('Selector'):
        return f'"""{name} 数据查询选择器。"""'
    
    # Model 类 (继承 models.Model)
        for base_node in node.bases:
            if isinstance(base_node, ast.Attribute) and 'Model' in ast.dump(base_node):
                return f'"""{name} 模型。"""'
            if isinstance(base_node, ast.Name) and base_node.id == 'TimeStampedModel':
                return f'"""{name} 模型。"""'
        return f'"""{name}。"""'
    
    # Choices 枚举类
    if name.endswith('Choices') or name.endswith('Status') or name.endswith('Type') or name.endswith('Flag'):
        if isinstance(node, ast.ClassDef):
            return f'"""{name} 枚举。"""'
    
    # Management Command
    if name == 'Command':
        return '"""自定义管理命令。"""'
    
    # DRF 方法
    if name == 'get_permissions':
        return '"""返回当前 action 所需的权限类列表。"""'
    if name == 'get_queryset':
        return '"""返回当前视图的查询集。"""'
    if name == 'perform_create':
        return '"""创建对象时的钩子，绑定当前用户。"""'
    if name == 'perform_update':
        return '"""更新对象时的钩子。"""'
    
    # View action 方法 — 根据方法名推断
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if name in ('page', 'list', 'list_or_create'):
            return '"""分页列表查询。"""'
        if name in ('form',):
            return '"""获取表单详情。"""'
        if name in ('create',):
            return '"""创建资源。"""'
        if name in ('update', 'update_or_delete'):
            return '"""更新或删除资源。"""'
        if name in ('delete', 'destroy'):
            return '"""删除资源。"""'
        if name in ('options',):
            return '"""获取下拉选项。"""'
        if name in ('tree',):
            return '"""获取树形结构数据。"""'
        if name in ('routes',):
            return '"""获取前端路由配置。"""'
        if name in ('retrieve',):
            return '"""获取单条资源详情。"""'
        if name in ('me',):
            return '"""获取当前登录用户信息。"""'
        if name in ('profile_get', 'profile_put'):
            return '"""用户个人资料获取/更新。"""'
        if name in ('login',):
            return '"""用户登录。"""'
        if name in ('logout',):
            return '"""用户登出。"""'
        if name in ('captcha',):
            return '"""生成验证码。"""'
        if name in ('refresh_token',):
            return '"""刷新访问令牌。"""'
        if name in ('reset_password', 'change_password'):
            return '"""密码重置/修改。"""'
        if name in ('upload_avatar', 'upload_image'):
            return '"""上传头像/图片。"""'
        if name in ('team_stats', 'team_stats_details'):
            return '"""团队工作汇报统计。"""'
        if name in ('visit_trend', 'visit_stats'):
            return '"""访问趋势/统计。"""'
        if name in ('refresh_cache',):
            return '"""刷新缓存。"""'
        if name in ('export_data',):
            return '"""导出数据。"""'
        if name in ('read', 'read_all'):
            return '"""标记公告已读。"""'
        if name in ('publish', 'revoke'):
            return '"""发布/撤回公告。"""'
        if name in ('menu_ids', 'update_menus'):
            return '"""岗位菜单权限管理。"""'
        if name.startswith('items_'):
            return '"""字典项管理。"""'
        if name.startswith('item_'):
            return '"""字典项操作。"""'
        if name.startswith('batch_'):
            return '"""批量操作。"""'
        if name.startswith('adjust_'):
            return '"""调整操作。"""'
        if name.startswith('list_'):
            return '"""列表查询。"""'
        if name.startswith('trigger_'):
            return '"""触发异步任务。"""'
        if name.startswith('_'):
            return f'"""{name} 内部辅助方法。"""'
        if name == 'handle':
            return '"""命令处理入口。"""'
        if name == 'authenticate':
            return '"""认证请求。"""'
        if name == 'has_permission':
            return '"""检查请求是否具有所需权限。"""'
        if name.startswith('get_') and 'field' in name.lower():
            return f'"""SerializerMethodField 取值。"""'
        if name.startswith('get_'):
            return f'"""获取 {name.replace("get_", "")}。"""'
        if name == 'render':
            return '"""渲染 SSE 流响应。"""'
    
    # 通用 fallback
    if isinstance(node, ast.ClassDef):
        return f'"""{name}。"""'
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return f'"""{name}。"""'
    
    return None

def add_docstring(file_path, node, docstring_text):
    """在节点开头插入 docstring"""
    global fixed
    f = pathlib.Path(file_path)
    lines = f.read_text(encoding='utf-8').split('\n')
    
    # 找到节点定义行
    node_line = node.lineno - 1  # 0-indexed
    
    # 找到缩进
    indent = len(lines[node_line]) - len(lines[node_line].lstrip())
    indent_str = ' ' * (indent + 4)  # 函数体缩进
    
    # 构造 docstring 行
    ds_line = f'{indent_str}{docstring_text}'
    
    # 找到插入位置（节点定义行之后，跳过装饰器和参数）
    insert_after = node.lineno - 1  # 0-indexed
    if hasattr(node, 'decorator_list') and node.decorator_list:
        last_decorator = max(d.end_lineno for d in node.decorator_list)
        insert_after = last_decorator - 1
    
    # 如果是函数，需要跳过参数行，找到函数体开始
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        # 找到第一个语句的行号
        if node.body:
            first_stmt_line = node.body[0].lineno - 1
            insert_after = first_stmt_line - 1
        else:
            insert_after = node.lineno  # 空函数体
    
    # 如果是类，找到类体开始
    if isinstance(node, ast.ClassDef):
        if node.body:
            first_stmt_line = node.body[0].lineno - 1
            insert_after = first_stmt_line - 1
        else:
            insert_after = node.lineno
    
    # 插入
    lines.insert(insert_after + 1, ds_line)
    
    content = '\n'.join(lines)
    
    # 验证语法
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"SYNTAX ERROR: {file_path}: {e}")
        return False
    
    f.write_text(content, encoding='utf-8')
    fixed += 1
    return True

# 收集所有需要修复的节点
to_fix = []

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or 'migrations' in str(f):
        continue
    try:
        content = f.read_text(encoding='utf-8')
        tree = ast.parse(content)
    except:
        continue
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if not ast.get_docstring(node):
                ds = make_docstring(node, str(f))
                if ds:
                    to_fix.append((str(f), node, ds))

# 按文件分组，从后往前修改（避免行号偏移）
from collections import defaultdict
by_file = defaultdict(list)
for fpath, node, ds in to_fix:
    by_file[fpath].append((node, ds))

for fpath, items in by_file.items():
    # 按行号降序排序
    items.sort(key=lambda x: x[0].lineno, reverse=True)
    for node, ds in items:
        add_docstring(fpath, node, ds)

print(f"Fixed: {fixed} docstrings")
if errors:
    print(f"Errors: {len(errors)}")
    for e in errors[:10]:
        print(f"  {e}")
else:
    print("All passed syntax check")
