"""批量替换废话 docstring 为 Google 风格"""
import pathlib, re

base = pathlib.Path('.')
fixed = 0

# (file_path, old_substring, new_substring)
replacements = [
    # system/views/dept_view.py
    ('apps/system/views/dept_view.py', '"""build。"""', '"""递归构建部门子树节点列表。\n\nArgs:\n    pid (int | None): 父部门 ID，None 表示从根层级开始。\n    path (set[int] | None): 已访问部门 ID 集合，用于循环引用检测。\n\nReturns:\n    list[dict[str, Any]]: 部门树节点列表（含 children）。\n"""'),
    # system/views/user_view.py
    ('apps/system/views/user_view.py', '"""collect。"""', '"""递归收集部门及其所有子部门 ID 到外层集合。\n\nArgs:\n    did (int): 起始部门 ID。\n\nReturns:\n    None: 结果累积到外层 target_ids 集合。\n"""'),
    ('apps/system/views/user_view.py', '"""generic_get。"""', '"""兼容 GET /users 直接返回全部用户列表。\n\nArgs:\n    request: DRF Request 对象。\n\nReturns:\n    Response: 全部用户序列化数据响应。\n"""'),
    # system/views/menu_view.py
    ('apps/system/views/menu_view.py', '"""compute_route_name。"""', '"""计算菜单的路由名称。\n\n仅对菜单类型（type=2）生效；优先取 route_name，\n其次用 component 末段首字母大写，兜底返回 ``Menu{id}``。\n\nReturns:\n    str: 路由名称。\n"""'),
    # system/views/work_report_view.py
    ('apps/system/views/work_report_view.py', '"""_collect 内部辅助方法。"""', '"""递归收集部门及其所有子部门 ID。\n\nArgs:\n    did (int): 起始部门 ID。\n\nReturns:\n    None: 结果累积到外层 dept_ids 集合。\n"""'),
    # system/utils/dept_scope.py
    ('apps/system/utils/dept_scope.py', '"""_collect 内部辅助方法。"""', '"""递归收集部门及其所有子部门 ID。\n\nArgs:\n    did (int): 起始部门 ID。\n\nReturns:\n    None: 结果累积到外层 dept_ids 集合。\n"""'),
    # system/serializers
    ('apps/system/serializers/mobile_code_send_serializer.py', '"""validate_mobile。"""', '"""校验手机号格式是否合法。\n\nArgs:\n    value (str): 待校验手机号。\n\nReturns:\n    str: 校验通过的手机号。\n\nRaises:\n    serializers.ValidationError: 手机号格式不正确时抛出。\n"""'),
    ('apps/system/serializers/mobile_bind_serializer.py', '"""validate_mobile。"""', '"""校验手机号格式是否合法。\n\nArgs:\n    value (str): 待校验手机号。\n\nReturns:\n    str: 校验通过的手机号。\n\nRaises:\n    serializers.ValidationError: 手机号格式不正确时抛出。\n"""'),
    # system/management
    ('apps/system/management/commands/sync_system_menus.py', '"""collect_ids。"""', '"""递归收集菜单节点及其所有子菜单 ID。\n\nArgs:\n    node (Menu): 起始菜单节点。\n\nReturns:\n    list[int]: 该节点及所有子孙菜单 ID 列表。\n"""'),
    ('apps/system/management/commands/purge_file_module_artifacts.py', '"""add_arguments。"""', '"""注册命令行参数。\n\nArgs:\n    parser: Django 命令行参数解析器。\n"""'),
    ('apps/system/management/commands/purge_file_module_artifacts.py', '"""collect。"""', '"""递归收集菜单及其所有子菜单 ID。\n\nArgs:\n    menu (Menu): 起始菜单节点。\n\nReturns:\n    None: 结果累积到外层 target_ids 集合。\n"""'),
    ('apps/system/management/commands/print_recent_logs.py', '"""add_arguments。"""', '"""注册命令行参数。\n\nArgs:\n    parser: Django 命令行参数解析器。\n"""'),
    ('apps/system/management/commands/find_menu_perms.py', '"""add_arguments。"""', '"""注册命令行参数。\n\nArgs:\n    parser: Django 命令行参数解析器。\n"""'),
    # crawler
    ('apps/crawler/serializers/crawler_log_serializer.py', '"""validate_level。"""', '"""归一化日志级别字段。\n\n将 warning/err 等常见别名映射为内部统一集合。\n\nArgs:\n    value (str): 原始日志级别。\n\nReturns:\n    str: 归一化后的日志级别，空值返回 "info"。\n"""'),
    ('apps/crawler/serializers/crawler_log_serializer.py', '"""validate_elapsed_ms。"""', '"""校验并转换耗时字段为整数。\n\nArgs:\n    value: 原始耗时值。\n\nReturns:\n    int: 耗时毫秒数，空值返回 0。\n\nRaises:\n    serializers.ValidationError: 无法转为整数时抛出。\n"""'),
    ('apps/crawler/views/crawler_category_view.py', '"""sites。"""', '"""返回去重后的爬取站点列表。\n\nArgs:\n    request: DRF Request 对象。\n\nReturns:\n    Response: 站点名称列表响应。\n"""'),
    # finance/views/statistics_view.py
    ('apps/finance/views/statistics_view.py', '"""match_owners。"""', '"""判断数据项的负责人是否匹配给定列表。\n\n从 price_list 提取 principal_uids（兼容单值/列表/分隔字符串），\n无命中时回退到扁平化结构的 owner/principal_names。\n\nArgs:\n    item (dict): 单条数据项。\n    owners_list: 待匹配的负责人列表。\n\nReturns:\n    bool: 命中返回 True；owners_list 为空也返回 True。\n"""'),
    ('apps/finance/views/statistics_view.py', '"""match_msku。"""', '"""判断数据项的 MSKU 是否匹配给定列表。\n\n从 price_list/local_infos 提取候选 MSKU，\n无命中时回退到扁平化结构的 msku 字段。\n\nArgs:\n    item (dict): 单条数据项。\n    msku_list: 待匹配的 MSKU 列表。\n\nReturns:\n    bool: 命中返回 True；msku_list 为空也返回 True。\n"""'),
    ('apps/finance/views/statistics_view.py', '"""match_sids。"""', '"""判断数据项的店铺 ID 是否匹配给定列表。\n\nArgs:\n    item (dict): 单条数据项。\n    sids_list: 待匹配的店铺 ID 列表。\n\nReturns:\n    bool: 命中返回 True；sids_list 为空也返回 True。\n"""'),
    # finance/views/monthly_loss_view.py
    ('apps/finance/views/monthly_loss_view.py', '"""_month_variants 内部辅助方法。"""', '"""生成月份字符串的等价格式变体。\n\n支持 YYYYMM 与 YYYY-MM 互转。\n\nArgs:\n    m: 原始月份字符串。\n\nReturns:\n    list[str]: 月份变体列表；空输入返回空列表。\n"""'),
    ('apps/finance/views/monthly_loss_view.py', '"""download。"""', '"""导出月度亏损订单为 xlsx 文件（按产品键聚合）。\n\n支持 owner/time/store 过滤、缓存复用与强制刷新。\n\nArgs:\n    request: DRF Request 对象。\n\nReturns:\n    Response: xlsx 文件流响应；失败时返回错误响应。\n"""'),
    ('apps/finance/views/monthly_loss_view.py', '"""chunked_iter。"""', '"""将序列按固定大小分块的生成器。\n\nArgs:\n    seq: 可迭代序列。\n    size (int): 每块大小，默认 500。\n\nYields:\n    list[tuple]: 每个分块的产品键列表。\n"""'),
    ('apps/finance/views/monthly_loss_view.py', '"""_cleanup_file 内部辅助方法。"""', '"""延迟删除临时文件的后台清理函数。\n\nArgs:\n    path_file (str): 临时文件路径。\n    delay (int): 删除前等待秒数，默认 30。\n"""'),
    # finance/views/monthly_loss_first20_view.py
    ('apps/finance/views/monthly_loss_first20_view.py', '"""_month_variants 内部辅助方法。"""', '"""生成月份字符串的等价格式变体。\n\n支持 YYYYMM 与 YYYY-MM 互转。\n\nArgs:\n    m: 原始月份字符串。\n\nReturns:\n    list[str]: 月份变体列表；空输入返回空列表。\n"""'),
    ('apps/finance/views/monthly_loss_first20_view.py', '"""download。"""', '"""导出本月前 20 天与上月整月数据对比为 xlsx 文件。\n\n仅支持单月对比；支持 owner/store 过滤与缓存复用。\n\nArgs:\n    request: DRF Request 对象。\n\nReturns:\n    Response: xlsx 文件流响应；失败时返回错误响应。\n"""'),
    ('apps/finance/views/monthly_loss_first20_view.py', '"""make_variant_set。"""', '"""生成本月与其去横杠变体的集合。\n\nArgs:\n    m (str): 月份字符串。\n\nReturns:\n    set[str]: 月份及其去横杠格式组成的集合。\n"""'),
    ('apps/finance/views/monthly_loss_first20_view.py', '"""aggregate_rows。"""', '"""用 pandas 按产品与月份聚合行数据为字典。\n\nArgs:\n    rows (list[dict]): 原始数据行。\n    months_list (list[str]): 月份列表。\n\nReturns:\n    dict: 聚合后的数据字典。\n"""'),
    ('apps/finance/views/monthly_loss_first20_view.py', '"""_cleanup 内部辅助方法。"""', '"""延迟删除临时文件的后台清理函数。\n\nArgs:\n    path_file (str): 临时文件路径。\n    delay (int): 删除前等待秒数，默认 30。\n"""'),
    # finance/serializers
    ('apps/finance/serializers/monthly_loss_serializer.py', '"""to_internal_value。"""', '"""反序列化入参为内部值。\n\n强制要求英文字段名，不再兼容中文 key。\n\nArgs:\n    data: 原始输入数据。\n\nReturns:\n    dict: 反序列化后的内部值。\n"""'),
    ('apps/finance/serializers/monthly_loss_serializer.py', '"""to_representation。"""', '"""序列化实例为前端输出结构。\n\n输出英文字段名，并补全元数据字段。\n\nArgs:\n    instance: MonthlyLossOrder 模型实例。\n\nReturns:\n    dict: 序列化后的输出字典。\n"""'),
    # common/utils/captcha.py
    ('apps/common/utils/captcha.py', '"""generate_captcha。"""', '"""生成图形验证码并存入缓存。\n\n无 PIL 环境下回退为透明 1x1 PNG。\n\nArgs:\n    width (int): 图片宽度，默认 120。\n    height (int): 图片高度，默认 40。\n    length (int): 验证码字符数，默认 4。\n    expire (int): 缓存过期秒数，默认 300。\n\nReturns:\n    tuple[str, str, str]: (缓存 key, base64 图片 data URI, 验证码明文)。\n"""'),
    ('apps/common/utils/captcha.py', '"""_norm 内部辅助方法。"""', '"""归一化验证码字符串以便比对。\n\n执行 NFKC 全角转半角、去除首尾空白并转小写。\n\nArgs:\n    s (str): 原始字符串。\n\nReturns:\n    str: 归一化后的字符串；None 返回空串。\n"""'),
    # nc
    ('apps/nc/services/nc_sync_service.py', '"""_run 内部辅助方法。"""', '"""后台线程执行体：运行指定 NcSyncTask 并管理 DB 连接生命周期。\n\n关闭旧连接后逐条执行任务，异常记录日志，\n最终释放线程独占连接。\n\nReturns:\n    None: 结果通过任务表回写。\n"""'),
    ('apps/nc/views/nc_folder_tree_view.py', '"""_collect 内部辅助方法。"""', '"""递归收集部门及其所有子部门 ID。\n\nArgs:\n    did (int): 起始部门 ID。\n\nReturns:\n    None: 结果累积到外层 dept_ids 集合。\n"""'),
    # ads/sp/views/auto_targeting_view.py
    ('apps/ads/sp/views/auto_targeting_view.py', '"""_build_bid_lines 内部辅助方法。"""', '"""构建定位组最近一次竞价调整的可读说明行。\n\n根据记录来源（规则/人工）生成首行说明，转换时区格式化时间，\n并按规则条件组追加明细。\n\nArgs:\n    rec: 竞价调整记录。\n    rule_map (dict): 规则 ID → 规则对象映射。\n    country_name (str): 国家名称。\n    tz_name (str): 时区名称。\n\nReturns:\n    list[str]: 可读说明行列表。\n"""'),
    # ads/sp/rules/services
    ('apps/ads/sp/rules/services/campaign_adjustment_executor.py', '"""_execute 内部辅助方法。"""', '"""执行广告活动调整核心逻辑。\n\n读取 PENDING 记录按 profile 分组，请求 API 并回写状态。\n四种类型（规则预算调整/手动预算调整/暂停/启用）统一执行。\n\nReturns:\n    dict[str, Any]: 执行统计。\n"""'),
    ('apps/ads/sp/rules/services/bid_adjustment_executor.py', '"""_execute 内部辅助方法。"""', '"""执行竞价调整与暂停核心逻辑。\n\n读取 PENDING 记录按 profile 分组，分关键词/定位组请求 API\n并回写状态。BID_ADJUSTMENT 与 BID_PAUSE 在同一请求中执行。\n\nReturns:\n    dict[str, Any]: 执行统计。\n"""'),
    # sales/listing/views/image_view.py
    ('apps/sales/listing/views/image_view.py', '"""delete_ids。"""', '"""按逗号分隔的 ID 列表批量删除图片上传记录。\n\nArgs:\n    request: DRF Request 对象。\n    pk (str): 逗号分隔的 ID 字符串。\n\nReturns:\n    Response: 空数据成功响应。\n"""'),
    ('apps/sales/listing/views/image_view.py', '"""import_csv。"""', '"""通过 CSV 文件批量导入图片组记录。\n\n支持中英文表头，按 imageGroup 做 upsert 并自动提交同步队列。\n\nArgs:\n    request: DRF Request 对象，需包含 file 字段。\n\nReturns:\n    Response: 导入统计。\n"""'),
]

# Also handle all "内部辅助方法" patterns generically for executor files
exec_files = [
    'apps/ads/sp/rules/services/ad_optimization/optimization_executor/executor_targeting.py',
    'apps/ads/sp/rules/services/ad_optimization/optimization_executor/executor_product_targeting.py',
    'apps/ads/sp/rules/services/ad_optimization/optimization_executor/executor_keyword.py',
]

for fpath in exec_files:
    f = base / fpath
    if not f.exists():
        continue
    content = f.read_text(encoding='utf-8')
    # Replace all remaining "内部辅助方法" docstrings with generic Google-style
    import ast
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            ds = ast.get_docstring(node)
            if ds and '内部辅助方法' in ds:
                name = node.name
                # Determine entity type from filename
                entity = '定位组' if 'targeting' in fpath and 'product' not in fpath else ('商品投放' if 'product' in fpath else '关键词')
                new_ds = f'"""{name}（{entity}维度包装）。\n\n委托共享函数执行，附加本维度日志标签。\n\nArgs:\n    *args: 透传给共享函数的位置参数。\n    **kwargs: 透传给共享函数的关键字参数。\n\nReturns:\n    透传共享函数的返回值。\n"""'
                old_ds = f'"""{ds}"""'
                if old_ds in content:
                    content = content.replace(old_ds, new_ds, 1)
                    fixed += 1
    f.write_text(content, encoding='utf-8')

# Apply targeted replacements
for fpath, old, new in replacements:
    f = base / fpath
    if not f.exists():
        continue
    content = f.read_text(encoding='utf-8')
    if old in content:
        content = content.replace(old, new, 1)
        f.write_text(content, encoding='utf-8')
        fixed += 1
    else:
        print(f'NOT FOUND: {fpath} -> {old[:40]}...')

# Handle menu_view.py three "build。" - need context
f = base / 'apps/system/views/menu_view.py'
content = f.read_text(encoding='utf-8')
# All three are nested build() functions
build_ds_options = [
    '递归构建动态路由树。',
    '递归构建菜单树形结构。',
    '递归构建菜单下拉选项树。',
]
idx = 0
while '"""build。"""' in content and idx < 3:
    desc = build_ds_options[idx]
    new_ds = f'"""{desc}\n\nArgs:\n    pid (int | None): 父菜单 ID，None 表示从根层级开始。\n\nReturns:\n    list[dict[str, Any]]: 节点列表（含 children）。\n"""'
    content = content.replace('"""build。"""', new_ds, 1)
    idx += 1
    fixed += 1
f.write_text(content, encoding='utf-8')

# Handle statistics_view.py two "sort_key。"
f = base / 'apps/finance/views/statistics_view.py'
content = f.read_text(encoding='utf-8')
content = content.replace(
    '"""sort_key。"""',
    '"""降序排序键，None 值排末尾。\n\nArgs:\n    it (dict): 单条数据项。\n\nReturns:\n    tuple[int, float]: 有效值返回 (0, -数值)，None 返回 (1, 0)。\n"""',
    1
)
content = content.replace(
    '"""sort_key。"""',
    '"""升序排序键，None 值排末尾。\n\nArgs:\n    it (dict): 单条数据项。\n\nReturns:\n    tuple[int, float]: 有效值返回 (0, 数值)，None 返回 (1, 0)。\n"""',
    1
)
f.write_text(content, encoding='utf-8')
fixed += 2

print(f'Total fixed: {fixed}')
