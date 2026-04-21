"""
api_v1 数据模型定义

说明：
- 为系统管理提供最小可用的数据结构：角色、部门、菜单、字典、配置、公告、日志、文件、用户扩展。
- 字段命名贴近前端需求；必要时增加唯一索引与排序字段。
- 后续可根据业务增加约束、索引与级联策略。
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class TimeStampedModel(models.Model):
    """时间戳抽象基类：自动维护创建/更新时间"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

class CurrencyIcon(TimeStampedModel):
    """货币图标配置"""
    id = models.AutoField(primary_key=True)
    country = models.CharField(max_length=50, unique=True, verbose_name="国家")
    code = models.CharField(max_length=50, verbose_name="货币代码")
    icon = models.CharField(max_length=50, verbose_name="货币标识")
    name = models.CharField(max_length=100, verbose_name="名字")

    class Meta:
        db_table = "currency_icon"
        verbose_name = "货币图标配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.country} - {self.code}"


class Role(TimeStampedModel):
    """角色表

    code: 角色编码，唯一
    name: 角色名称
    status: 是否启用
    remark: 备注
    order_num: 排序
    data_scope: 数据权限范围
        1 = 全部数据
        2 = 部门及子部门数据
        3 = 本部门数据
        4 = 本人数据
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50)
    status = models.BooleanField(default=True)
    remark = models.CharField(max_length=255, blank=True, default="")
    order_num = models.IntegerField(default=0)
    data_scope = models.IntegerField(default=1, help_text="1=全部数据 2=部门及子部门 3=本部门 4=本人")
    menus = models.ManyToManyField('Menu', blank=True, related_name='roles')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "角色"
        verbose_name_plural = "角色"
        ordering = ("order_num", "id")


class Department(TimeStampedModel):
    """部门表：父子树结构"""
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=100, blank=True, default="", help_text="部门编号")
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)
    order_num = models.IntegerField(default=0)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "部门"
        verbose_name_plural = "部门"
        ordering = ("order_num", "id")


class Menu(TimeStampedModel):
    MENU_TYPES = (
        (1, 'Directory'),
        (2, 'Menu'),
        (3, 'Button'),
        (4, 'External'),
    )
    name = models.CharField(max_length=100, help_text="菜单名称")
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)
    type = models.IntegerField(choices=MENU_TYPES, default=2)
    route_name = models.CharField(max_length=100, blank=True, default="", help_text="路由名称 name")
    path = models.CharField(max_length=200, blank=True, default="", help_text="路由路径")
    component = models.CharField(max_length=200, blank=True, default="", help_text="前端组件路径")
    perms = models.CharField(max_length=200, blank=True, default="", help_text="权限标识")
    icon = models.CharField(max_length=100, blank=True, default="", help_text="图标标识")
    order_num = models.IntegerField(default=0)
    visible = models.BooleanField(default=True)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "菜单"
        verbose_name_plural = "菜单"
        ordering = ("order_num", "id")


class DictType(TimeStampedModel):
    """字典类型表"""
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "字典类型"
        verbose_name_plural = "字典类型"


class DictItem(TimeStampedModel):
    """字典项表：同一字典下 value 唯一"""
    dict_type = models.ForeignKey(DictType, related_name='items', on_delete=models.CASCADE)
    label = models.CharField(max_length=100)
    value = models.CharField(max_length=100)
    sort = models.IntegerField(default=0)
    status = models.BooleanField(default=True)
    # 标签类型（Element Plus Tag type），用于前端渲染样式，可为空
    tag_type = models.CharField(max_length=20, blank=True, default="")

    class Meta:
        unique_together = (('dict_type', 'value'),)

    def __str__(self):
        return f"{self.dict_type.code}:{self.label}"

    class Meta:
        verbose_name = "字典项"
        verbose_name_plural = "字典项"
        ordering = ("sort", "id")


class Config(TimeStampedModel):
    """系统参数配置"""
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField(blank=True, default="")
    remark = models.CharField(max_length=255, blank=True, default="")
    status = models.BooleanField(default=True)

    def __str__(self):
        return self.key

    class Meta:
        verbose_name = "系统参数"
        verbose_name_plural = "系统参数"


class Notice(TimeStampedModel):
    """通知公告"""
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True, default="")
    type = models.CharField(max_length=50, blank=True, default="general")
    level = models.CharField(max_length=20, default='L')  # L/M/H
    target_type = models.IntegerField(default=1)  # 1: 全体, 2: 指定
    status = models.CharField(max_length=20, default='draft')  # draft/published/revoked
    publish_time = models.DateTimeField(null=True, blank=True)
    revoke_time = models.DateTimeField(null=True, blank=True)
    creator = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "通知公告"
        verbose_name_plural = "通知公告"


class NoticeTarget(TimeStampedModel):
    """通知指定目标用户"""
    notice = models.ForeignKey(Notice, on_delete=models.CASCADE, related_name='targets')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notice_targets')

    class Meta:
        unique_together = (('notice', 'user'),)
        verbose_name = "通知目标"
        verbose_name_plural = "通知目标"


class OperLog(TimeStampedModel):
    """操作日志"""
    module = models.CharField(max_length=100)
    action = models.TextField()
    operator = models.CharField(max_length=100, blank=True, default="")
    ip = models.CharField(max_length=45, blank=True, default="")
    user_agent = models.CharField(max_length=255, blank=True, default="")
    result = models.CharField(max_length=20, default='success')
    elapsed_ms = models.IntegerField(default=0)

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ("-id",)


class CrawlerLog(TimeStampedModel):
    """爬虫专用日志表（与系统操作日志分离）

    字段说明：
    - module: 日志来源模块
    - content: 日志内容/消息
    - level: 日志级别（debug/info/warn/error）
    - elapsed_ms: 模块耗时（毫秒）
    - operator/ip/user_agent: 可选上下文信息
    """
    LEVEL_CHOICES = (
        ("debug", "debug"),
        ("info", "info"),
        ("warn", "warn"),
        ("error", "error"),
    )

    module = models.CharField(max_length=100, blank=True, default="")
    content = models.TextField(blank=True, default="")
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default="info")
    elapsed_ms = models.IntegerField(default=0)
    operator = models.CharField(max_length=100, blank=True, default="")
    ip = models.CharField(max_length=45, blank=True, default="")
    user_agent = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        verbose_name = "爬虫日志"
        verbose_name_plural = "爬虫日志"
        ordering = ("-id",)




class UserProfile(TimeStampedModel):
    """用户扩展信息（不替换内置 User，避免迁移复杂度）"""
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    nickname = models.CharField(max_length=100, blank=True, default="")
    mobile = models.CharField(max_length=20, blank=True, default="")
    avatar = models.CharField(max_length=255, blank=True, default="")
    # cloud_id: 存储第三方 Seafile 返回的标识（例如 account email/ID），用于后续同步删除
    cloud_id = models.CharField(max_length=255, blank=True, default="")
    dept = models.ForeignKey('Department', null=True, blank=True, on_delete=models.SET_NULL)
    gender = models.IntegerField(default=0, help_text="0=保密,1=男,2=女")

    roles = models.ManyToManyField(Role, blank=True, related_name='users')

    class Meta:
        verbose_name = "用户扩展"
        verbose_name_plural = "用户扩展"


class AuthToken(TimeStampedModel):
    """简单的访问/刷新令牌"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    access_token = models.CharField(max_length=200, unique=True)
    refresh_token = models.CharField(max_length=200, unique=True)
    access_expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    revoked = models.BooleanField(default=False)

    def is_access_valid(self):
        return (not self.revoked) and timezone.now() < self.access_expires_at

    def is_refresh_valid(self):
        return (not self.revoked) and timezone.now() < self.refresh_expires_at

    class Meta:
        verbose_name = "认证令牌"
        verbose_name_plural = "认证令牌"
        indexes = [
            models.Index(fields=["access_token"]),
            models.Index(fields=["refresh_token"]),
        ]


class CloudAuthToken(TimeStampedModel):
    """缓存 Seafile cloud token（临时）

    说明：用于在用户登录后，后端使用该用户凭据向 Seafile 获取 token 并缓存，
    仅用于后端对 Seafile 的短期代理请求。前端**不**直接使用此 token。
    """
    user = models.OneToOneField(User, related_name='cloud_token', on_delete=models.CASCADE)
    site = models.CharField(max_length=255, blank=True, default="")
    token = models.CharField(max_length=255, blank=True, default="")
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "云认证令牌"
        verbose_name_plural = "云认证令牌"


class NoticeRead(TimeStampedModel):
    """用户-公告已读记录

    用于记录某用户已读的公告，前端展示“我的公告/未读”时可以排除已读项。
    """
    user = models.ForeignKey(User, related_name='notice_reads', on_delete=models.CASCADE)
    notice = models.ForeignKey(Notice, related_name='reads', on_delete=models.CASCADE)
    read_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "公告已读"
        verbose_name_plural = "公告已读"
        unique_together = (('user', 'notice'),)


class CrawlerConf(TimeStampedModel):
    """数据采集节点配置

    前端使用字段名：server_name, node, ip, status, order_num
    该模型用于记录可公开访问的爬取节点配置（开放接口，无需认证）
    """
    server_name = models.CharField(max_length=200)
    node = models.CharField(max_length=200)
    ip = models.CharField(max_length=100, blank=True, default="")
    status = models.IntegerField(default=1)
    order_num = models.IntegerField(default=0)

    class Meta:
        verbose_name = "数据采集节点"
        verbose_name_plural = "数据采集节点"
        ordering = ("order_num", "id")


class CrawlerSellerAccount(TimeStampedModel):
    """卖家精灵账号配置（供爬虫/任务使用）

    字段：username, password, status, order_num
    注意：密码以明文保存用于对外系统认证（如需加密请在后续迭代改造）
    """
    username = models.CharField(max_length=200)
    password = models.CharField(max_length=255, blank=True, default="")
    status = models.IntegerField(default=1)
    order_num = models.IntegerField(default=0)

    class Meta:
        verbose_name = "卖家精灵账号"
        verbose_name_plural = "卖家精灵账号"
        ordering = ("order_num", "id")


class CrawlerCategory(TimeStampedModel):
    """爬取类目表

    前端字段名映射：name, category_id, site, category_type, status
    """
    name = models.CharField(max_length=200)
    category_id = models.CharField(max_length=200, blank=True, default="")
    site = models.CharField(max_length=100, blank=True, default="")
    category_type = models.CharField(max_length=100, blank=True, default="")
    status = models.IntegerField(default=1)

    class Meta:
        verbose_name = "爬取类目"
        verbose_name_plural = "爬取类目"
        ordering = ("-created_at", "id")


class OrderProfitCache(TimeStampedModel):
    """缓存从 LingXing /basicOpen/finance/mreport/OrderProfit 拉取的原始数据

    - key: 基于请求参数的唯一 key（例如 sids,startDate,endDate,currency,searchValue 列表的哈希）
    - params: 原始参数 JSON，用于诊断
    - data: 原始响应 data 列表的 JSON 序列化字符串
    - created_at 来自 TimeStampedModel，可用于判断是否超过缓存有效期
    """
    key = models.CharField(max_length=128, db_index=True, unique=True)
    params = models.TextField(blank=True, default="")
    data = models.TextField(blank=True, default="")

    class Meta:
        verbose_name = "OrderProfit 缓存"
        verbose_name_plural = "OrderProfit 缓存"
        indexes = [
            models.Index(fields=["created_at"]),
        ]


class MonthlyLossOrder(TimeStampedModel):
    """月度亏损订单统计

    前端与 API 使用中文字段名（接口接受和返回中文键）。用于记录每个月的亏损条目统计。
    """
    image_url = models.CharField("图片URL", max_length=512, blank=True, default="")
    msku = models.CharField("MSKU", max_length=200, blank=True, default="")
    asin = models.CharField("ASIN", max_length=50, blank=True, default="")
    parent_asin = models.CharField("父ASIN", max_length=50, blank=True, default="")
    store_country = models.CharField("店铺/国家", max_length=200, blank=True, default="")
    product_name_sku = models.CharField("品名/SKU", max_length=512, blank=True, default="")
    gross_profit = models.DecimalField("毛利润", max_digits=18, decimal_places=4, null=True, blank=True)
    gross_margin = models.DecimalField("毛利率", max_digits=8, decimal_places=4, null=True, blank=True)
    net_gross_margin = models.DecimalField("净毛利率", max_digits=8, decimal_places=4, null=True, blank=True)
    return_rate = models.DecimalField("退货率", max_digits=8, decimal_places=6, null=True, blank=True)
    refund_amount_rate = models.DecimalField("退款率", max_digits=8, decimal_places=6, null=True, blank=True)
    total_stock_fee = models.DecimalField("仓储费", max_digits=18, decimal_places=4, null=True, blank=True)
    spend = models.DecimalField("广告费", max_digits=18, decimal_places=4, null=True, blank=True)
    spend_rate = models.DecimalField("广告率费", max_digits=8, decimal_places=6, null=True, blank=True)
    # 销量（整数），默认 0，允许为空以兼容历史数据
    sales = models.IntegerField("销量", null=True, blank=True, default=0)
    owner = models.CharField("负责人", max_length=100, blank=True, default="")
    month = models.CharField("月份", max_length=7, db_index=True, help_text="YYYY-MM")

    class Meta:
        verbose_name = "月度亏损订单统计"
        verbose_name_plural = "月度亏损订单统计"
        ordering = ("-month","-id")

    def __str__(self):
        return f"{self.msku} {self.asin} {self.month}"


class MonthlyLossOrderFirst20(TimeStampedModel):
    """月度前20天亏损订单统计

    与 MonthlyLossOrder 字段一致，但语义上仅记录当月前 20 天的统计数据。
    """
    image_url = models.CharField("图片URL", max_length=512, blank=True, default="")
    msku = models.CharField("MSKU", max_length=200, blank=True, default="")
    asin = models.CharField("ASIN", max_length=50, blank=True, default="")
    parent_asin = models.CharField("父ASIN", max_length=50, blank=True, default="")
    store_country = models.CharField("店铺/国家", max_length=200, blank=True, default="")
    product_name_sku = models.CharField("品名/SKU", max_length=512, blank=True, default="")
    gross_profit = models.DecimalField("毛利润", max_digits=18, decimal_places=4, null=True, blank=True)
    gross_margin = models.DecimalField("毛利率", max_digits=8, decimal_places=4, null=True, blank=True)
    net_gross_margin = models.DecimalField("净毛利率", max_digits=8, decimal_places=4, null=True, blank=True)
    return_rate = models.DecimalField("退货率", max_digits=8, decimal_places=6, null=True, blank=True)
    refund_amount_rate = models.DecimalField("退款率", max_digits=8, decimal_places=6, null=True, blank=True)
    total_stock_fee = models.DecimalField("仓储费", max_digits=18, decimal_places=4, null=True, blank=True)
    spend = models.DecimalField("广告费", max_digits=18, decimal_places=4, null=True, blank=True)
    spend_rate = models.DecimalField("广告率费", max_digits=8, decimal_places=6, null=True, blank=True)
    # 销量（整数），默认 0，允许为空以兼容历史数据
    sales = models.IntegerField("销量", null=True, blank=True, default=0)
    owner = models.CharField("负责人", max_length=100, blank=True, default="")
    month = models.CharField("月份", max_length=7, db_index=True, help_text="YYYY-MM")

    class Meta:
        verbose_name = "月度前20天亏损订单统计"
        verbose_name_plural = "月度前20天亏损订单统计"
        ordering = ("-month","-id")

    def __str__(self):
        return f"{self.msku} {self.asin} {self.month}"


# ---------------- 文件管理微模块模型（最小可用） -----------------
class FileFolder(TimeStampedModel):
    """文件夹

    使用 external_id 与前端传入的 fileId/hash 保持对应，避免与内部主键耦合。
    根目录以 parent=None 表示；逻辑删除采用 is_deleted + deleted_at。
    """
    external_id = models.CharField(max_length=64, unique=True, help_text="前端生成的文件夹ID")
    name = models.CharField(max_length=255)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children', on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "文件夹"
        verbose_name_plural = "文件夹"
        indexes = [
            models.Index(fields=["external_id"]),
            models.Index(fields=["is_deleted"]),
        ]

    def __str__(self):
        return self.name


class FileAsset(TimeStampedModel):
    """合并后的文件（逻辑文件）

    file_id: 前端生成的文件ID（区分于数据库主键）
    merge_file_id: 分片阶段生成的临时合并ID (pid) — 便于前端把每个分片与目标文件关联。
    file_hash: 整体文件哈希（用于秒传/断点续传判断）
    total_chunks / uploaded_chunks: 分片计数与进度
    is_completed: 是否已全部分片上传合并
    storage_path: 完整文件或合并后文件的实际存储路径（当前阶段占位，可为最后一个分片路径）
    """
    file_id = models.CharField(max_length=64, unique=True, help_text="前端生成的文件ID")
    merge_file_id = models.CharField(max_length=64, unique=True, help_text="分片阶段合并文件ID")
    name = models.CharField(max_length=255)
    size = models.BigIntegerField(default=0)
    file_hash = models.CharField(max_length=128, db_index=True)
    ext = models.CharField(max_length=50, blank=True, default="")
    mime_type = models.CharField(max_length=100, blank=True, default="")
    folder = models.ForeignKey(FileFolder, null=True, blank=True, related_name='assets', on_delete=models.SET_NULL)
    owner = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    total_chunks = models.IntegerField(default=0)
    uploaded_chunks = models.IntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    storage_path = models.CharField(max_length=255, blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "文件"
        verbose_name_plural = "文件"
        indexes = [
            models.Index(fields=["file_hash"]),
            models.Index(fields=["is_deleted", "is_completed"]),
        ]

    def __str__(self):
        return self.name


class FileChunk(TimeStampedModel):
    """文件分片记录

    chunk_hash: 单个分片哈希，用于断点续传去重。
    num: 分片序号（从0开始）
    storage_path: 分片物理存储相对路径
    """
    asset = models.ForeignKey(FileAsset, related_name='chunks', on_delete=models.CASCADE)
    chunk_hash = models.CharField(max_length=128, db_index=True)
    num = models.IntegerField()
    size = models.BigIntegerField(default=0)
    storage_path = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "文件分片"
        verbose_name_plural = "文件分片"
        unique_together = ("asset", "num")
        indexes = [
            models.Index(fields=["chunk_hash"]),
        ]

    def __str__(self):
        return f"{self.asset_id}:{self.num}"


class ImageUpload(TimeStampedModel):
    """图片上传记录"""
    image_group = models.CharField(max_length=255, verbose_name="图片组")
    # Allow cloud_path to be empty so frontend can omit it
    cloud_path = models.CharField(max_length=500, verbose_name="Cloud 路径", blank=True, null=True)
    status = models.CharField(max_length=50, blank=True, null=True, verbose_name="状态") # normal, warning, error
    log = models.TextField(blank=True, null=True, verbose_name="日志")
    image_url = models.CharField(max_length=500, blank=True, null=True, verbose_name="图片URL")

    class Meta:
        db_table = 'sys_image_upload'
        ordering = ['-created_at']


class WorkReport(TimeStampedModel):
    """
    工作汇报 (日报/周报)
    """
    REPORT_TYPES = (
        ('daily', '日报'),
        ('weekly', '周报'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    type = models.CharField(max_length=20, choices=REPORT_TYPES, default='daily')
    content = models.TextField(blank=True, default='', help_text='今日工作内容')
    plan = models.TextField(blank=True, default='', help_text='明日计划')
    issues = models.TextField(blank=True, default='', help_text='遇到问题/需要协助')
    work_hours = models.DecimalField(max_digits=4, decimal_places=1, default=8.0, help_text='工时')
    progress = models.IntegerField(default=0, help_text='进度百分比')
    report_date = models.DateField(default=timezone.now, help_text='汇报日期')

    class Meta:
        verbose_name = '工作汇报'
        verbose_name_plural = '工作汇报'
        ordering = ('-report_date', '-created_at')

    def __str__(self):
        return f'{self.user.username} {self.report_date} {self.type}'

class AdCampaign(TimeStampedModel):
    """广告活动基础数据表"""
    campaign_id = models.CharField(max_length=100, unique=True, help_text="活动ID")
    profile_id = models.CharField(max_length=100, help_text="Profile ID")
    store_id = models.CharField(max_length=100, help_text="Store ID")
    portfolio_id = models.CharField(max_length=100, null=True, blank=True, help_text="Portfolio ID")
    
    state = models.CharField(max_length=20, help_text="状态")
    sponsored_type = models.CharField(max_length=50, help_text="赞助类型 (sponsored_type)")
    targeting_type = models.CharField(max_length=50, help_text="投放类型 (targeting_type)")
    store_name = models.CharField(max_length=100, null=True, blank=True, help_text="店铺")
    
    name = models.CharField(max_length=255, help_text="广告活动名称")
    service_status = models.CharField(max_length=50, help_text="服务状态")
    portfolio_name = models.CharField(max_length=255, null=True, blank=True, help_text="广告组合")
    bidding_type = models.CharField(max_length=50, help_text="竞价策略")
    start_date = models.DateField(null=True, blank=True, help_text="开始日期")
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="预算")
    last_over_budget_at = models.DateTimeField(null=True, blank=True, help_text="超预算时间")

    class Meta:
        db_table = "v1_ad_campaign"
        verbose_name = "广告活动"


class AdMetricData(TimeStampedModel):
    """广告指标数据表"""
    campaign_id = models.CharField(max_length=100, unique=True, help_text="活动ID主键")
    impressions = models.IntegerField(null=True, blank=True, help_text="曝光量")
    impressions_percent = models.CharField(max_length=50, null=True, blank=True, help_text="曝光%")
    clicks = models.IntegerField(null=True, blank=True, help_text="点击")
    clicks_percent = models.CharField(max_length=50, null=True, blank=True, help_text="点击%")
    ctr = models.CharField(max_length=50, null=True, blank=True, help_text="CTR")
    cpc = models.CharField(max_length=50, null=True, blank=True, help_text="CPC")
    spends = models.CharField(max_length=50, null=True, blank=True, help_text="花费")
    spends_percent = models.CharField(max_length=50, null=True, blank=True, help_text="花费%")
    cpa = models.CharField(max_length=50, null=True, blank=True, help_text="CPA")
    sales = models.CharField(max_length=50, null=True, blank=True, help_text="广告销售额")
    sales_percent = models.CharField(max_length=50, null=True, blank=True, help_text="广告销售额%")
    direct_sales = models.CharField(max_length=50, null=True, blank=True, help_text="直接销售额")
    acos = models.CharField(max_length=50, null=True, blank=True, help_text="ACoS")
    roas = models.CharField(max_length=50, null=True, blank=True, help_text="ROAS")
    orders = models.IntegerField(null=True, blank=True, help_text="广告订单")
    direct_orders = models.IntegerField(null=True, blank=True, help_text="直接订单")
    cvr = models.CharField(max_length=50, null=True, blank=True, help_text="CVR")
    unit_price = models.CharField(max_length=50, null=True, blank=True, help_text="广告笔单价")
    ad_units = models.IntegerField(null=True, blank=True, help_text="广告销量")
    top_of_search_impression_share = models.CharField(max_length=50, null=True, blank=True, help_text="IS")

    class Meta:
        db_table = "v1_ad_metric_data"
        verbose_name = "广告指标数据"

class LxSellers(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='id')
    name = models.CharField(max_length=255, null=True, blank=True)
    seller_id = models.CharField(max_length=100, null=True, blank=True)
    country_code = models.CharField(max_length=10, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    is_concept = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'lx_sellers'

class LxListingInfo(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name="listing 产品ID")
    msku = models.CharField(max_length=100, blank=True, default="")
    fnsku = models.CharField(max_length=100, blank=True, default="")
    status = models.IntegerField(default=0, verbose_name="状态")
    product_link = models.ForeignKey('LxProductInfo', null=True, blank=True, on_delete=models.DO_NOTHING, db_column='asin', to_field='asin', related_name='listings')
    item_name = models.TextField(blank=True, null=True, verbose_name="标题")
    shop_link = models.ForeignKey('LxSellers', null=True, blank=True, on_delete=models.DO_NOTHING, db_column='store_id', to_field='id', related_name='listings')
    fulfillment_channel_type = models.CharField(max_length=50, blank=True, default="", verbose_name="配送方式")
    # ... rest is the same
    amz_product_id = models.CharField(max_length=100, blank=True, default="", verbose_name="商品编码")
    amz_product_id_type = models.CharField(max_length=50, blank=True, default="")
    parent_asin = models.CharField(max_length=100, blank=True, default="", verbose_name="父体ASIN")
    variant_text = models.JSONField(blank=True, null=True, verbose_name="变体属性")
    seller_category = models.TextField(blank=True, null=True, verbose_name="大类类目")
    seller_rank = models.IntegerField(default=0, verbose_name="大类排名")
    small_rank = models.IntegerField(default=0, verbose_name="小类排名")
    small_category = models.CharField(max_length=255, blank=True, default="", verbose_name="小类类目")
    stars = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="评分")
    reviews_num = models.IntegerField(default=0, verbose_name="Rating总数")
    pair_type = models.CharField(max_length=200, blank=True, default="", verbose_name="配对方式")
    open_date_time = models.CharField(max_length=100, blank=True, default="", verbose_name="创建时间")
    on_sale_time = models.CharField(max_length=100, blank=True, default="", verbose_name="开售时间")
    first_order_time = models.CharField(max_length=100, blank=True, default="", verbose_name="首单时间")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'lx_listing_info'
        verbose_name = 'Listing 基础表'


class LxProductInfo(models.Model):
    asin = models.CharField(max_length=100, primary_key=True, verbose_name="ASIN")
    product_id = models.BigIntegerField(default=0, verbose_name="产品ID")
    local_sku = models.CharField(max_length=100, blank=True, default="", verbose_name="本地SKU")
    local_name = models.CharField(max_length=255, blank=True, default="", verbose_name="品名")
    image = models.TextField(blank=True, null=True, verbose_name="图片")
    brand = models.CharField(max_length=100, blank=True, default="", verbose_name="亚马逊品牌")
    local_brand = models.CharField(max_length=100, blank=True, default="", verbose_name="本地品牌")
    principal_list = models.JSONField(blank=True, null=True, verbose_name="负责人信息")
    assort = models.CharField(max_length=100, blank=True, default="", verbose_name="分类")
    label = models.CharField(max_length=100, blank=True, default="", verbose_name="标签")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'lx_product_info'
        verbose_name = '产品基础表'


class LxListingRemark(models.Model):
    id = models.BigAutoField(primary_key=True)
    listing = models.OneToOneField(LxListingInfo, on_delete=models.CASCADE, db_column='listing_id', related_name='remark', db_constraint=False)
    remark_text = models.TextField(blank=True, null=True, verbose_name="备注")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'lx_listing_remark'
        verbose_name = 'Listing备注'
        verbose_name_plural = verbose_name

class LxOrderProfit(models.Model):
    listing_id = models.BigAutoField(primary_key=True, verbose_name='listing 产品ID')
    report_date = models.DateField(verbose_name='报表时间')
    asin = models.CharField(max_length=100, blank=True, default='', verbose_name='ASIN')
    gross_profit = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='毛利润')
    gross_margin = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, verbose_name='毛利率')
    net_gross_margin = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, verbose_name='净毛利率')
    volume = models.IntegerField(default=0, verbose_name='销量')
    return_rate = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, verbose_name='退货率')
    refund_amount_rate = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, verbose_name='退款率')
    total_stock_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='仓储费')
    spend = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name='广告费')
    spend_rate = models.DecimalField(max_digits=10, decimal_places=4, default=0.0000, verbose_name='广告费率')
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        managed = False
        db_table = 'lx_order_profit'
        verbose_name = '产品利润报表'
        verbose_name_plural = verbose_name


class LxListingMetrics(models.Model):
    listing = models.OneToOneField(LxListingInfo, on_delete=models.DO_NOTHING, primary_key=True, db_column='listing_id', related_name='metrics')
    regular_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="售价")
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="价格")
    landed_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="优惠价")
    b2b_price = models.CharField(max_length=255, blank=True, default="", verbose_name="B2B价格")
    listing_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Listing价格")
    afn_fulfillable_quantity = models.IntegerField(default=0, verbose_name="FBA可售")
    fba_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="预估FBA费")
    referral_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="平台费")
    yesterday_volume = models.IntegerField(default=0, verbose_name="昨日销量")
    total_volume = models.IntegerField(default=0, verbose_name="7天销量")
    fourteen_volume = models.IntegerField(default=0, verbose_name="14天销量")
    thirty_volume = models.IntegerField(default=0, verbose_name="30天销量")
    average_seven_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="7天日均销量")
    average_fourteen_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="14天日均销量")
    average_thirty_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="30天日均销量")
    yesterday_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="昨日销售额")
    seven_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="7天销售额")
    fourteen_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="14天销售额")
    thirty_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="30天销售额")
    yesterday_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="昨日广告费")
    seven_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="7天广告费")
    fourteen_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="14天广告费")
    thirty_spend = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="30天广告费")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'lx_listing_metrics'
        verbose_name = 'Listing业务指标表'


class LxUserList(models.Model):
    """用户列表数据表"""
    uid = models.BigIntegerField(primary_key=True, help_text="主键")
    name = models.CharField(max_length=255, null=True, blank=True, help_text="名字")
    name_zh = models.CharField(max_length=255, null=True, blank=True, help_text="中文名字")
    has_rule = models.BooleanField(null=True, blank=True, help_text="是否有规则")
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True, help_text="系统更新时间")

    class Meta:
        managed = False
        db_table = "lx_user_list"
        verbose_name = "用户列表"
        verbose_name_plural = "用户列表"


