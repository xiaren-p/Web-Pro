"""Batch add JSDoc to API method stubs - reads file, adds JSDoc, writes back"""
import re, pathlib

API_DIR = pathlib.Path('vue3-element-admin-master/src/api')

# Map of file -> { method_name: JSDoc }
fixes = {
    'config/index.ts': {
        'getPage': '分页查询系统配置列表。',
        'getFormData': '获取配置编辑表单数据。',
        'create': '创建配置项。',
        'update': '更新配置项。',
        'deleteByIds': '批量删除配置。',
        'deleteById': '删除单个配置（委托 deleteByIds）。',
        'refreshCache': '刷新配置缓存。',
    },
    'notice/index.ts': {
        'getPage': '分页查询通知列表。',
        'getFormData': '获取通知编辑表单数据。',
        'publish': '发布通知。',
        'revoke': '撤回已发布通知。',
        'getDetail': '获取通知详情（含内容）。',
        'read': '标记单条通知已读。',
        'readAll': '标记全部通知已读。',
        'getMyPage': '分页获取我的通知。',
        'exportData': '导出通知数据为 Excel。',
        'create': '创建通知。',
        'update': '更新通知。',
        'deleteByIds': '批量删除通知。',
    },
    'dict/index.ts': {
        'getPage': '分页查询字典类型列表。',
        'getFormData': '获取字典类型编辑表单数据。',
        'create': '创建字典类型。',
        'update': '更新字典类型。',
        'deleteByIds': '批量删除字典类型。',
        'getItemPage': '分页查询字典项列表。',
        'getItemForm': '获取字典项编辑表单数据。',
        'createItem': '创建字典项。',
        'updateItem': '更新字典项。',
        'deleteItems': '批量删除字典项。',
        'getItemOptions': '获取字典项下拉选项。',
    },
    'crawler/category.ts': {
        'getPage': '分页查询爬虫分类列表。',
        'getFormData': '获取分类编辑表单数据。',
        'create': '创建分类。',
        'update': '更新分类。',
        'deleteByIds': '批量删除分类。',
        'getSites': '获取分类下的站点列表。',
    },
    'crawler/conf.ts': {
        'getList': '获取爬虫配置列表。',
        'getFormData': '获取配置编辑表单数据。',
        'create': '创建配置。',
        'update': '更新配置。',
        'deleteByIds': '批量删除配置。',
    },
    'crawler/seller.ts': {
        'getList': '获取爬虫卖家账号列表。',
        'getFormData': '获取账号编辑表单数据。',
        'create': '创建卖家账号。',
        'update': '更新卖家账号。',
        'deleteByIds': '批量删除卖家账号。',
    },
    'position/index.ts': {
        'getPage': '分页查询岗位列表。',
        'getOptions': '获取岗位下拉选项。',
        'getMenuIds': '获取岗位关联的菜单权限 ID 列表。',
        'saveMenus': '保存岗位菜单权限。',
    },
    'shops/index.ts': {
        'getOptions': '获取店铺下拉选项。',
        'getOwners': '获取负责人下拉选项。',
    },
    'upload/index.ts': {
        'uploadImage': '上传图片（multipart/form-data）。',
    },
    'imageUpload/index.ts': {
        'getPage': '分页查询图片上传记录。',
        'getFormData': '获取图片上传编辑表单数据。',
        'create': '创建图片上传记录。',
        'update': '更新图片上传记录。',
        'deleteByIds': '批量删除图片上传记录。',
        'sync': '同步单条图片上传记录。',
        'batchSync': '批量同步图片上传记录。',
        'getQueue': '获取图片同步队列。',
        'importCsv': '通过 CSV 批量导入图片组。',
    },
}

for fpath, methods in fixes.items():
    f = API_DIR / fpath
    if not f.exists(): continue
    content = f.read_text(encoding='utf-8')
    changed = False
    
    for method_name, doc in methods.items():
        # Match: methodName(...) at line start with 2 spaces
        pattern = rf'(\n  {method_name}\()'
        if re.search(pattern, content) and not re.search(rf'/\*\*\s*\n.*\*/\s*\n  {method_name}\(', content) and not re.search(rf'\n\s+/\*\* {re.escape(doc)} \*/\s*\n  {method_name}\(', content):
            replacement = rf'\n  /** {doc} */\n  {method_name}('
            content = re.sub(pattern, replacement, content, count=1)
            changed = True
    
    if changed:
        f.write_text(content, encoding='utf-8')
        print(f'Added JSDoc: {fpath} ({sum(1 for m in methods if f"/** {methods[m]} */" in content)} methods)')

print('Done')
