"""
api_v1 序列化器包

按业务板块拆分的 DRF 序列化器集合。本 `__init__` 文件统一对外重导出，
保证旧的 `from api_v1.serializers import XxxSerializer` 调用方式继续生效，
同时让新代码可以按板块路径精准导入。
"""

# system 板块
from api_v1.serializers.system.position_serializer import PositionSerializer, PositionWriteSerializer, PositionOptionSerializer
from api_v1.serializers.system.dept_serializer import DeptSerializer
from api_v1.serializers.system.menu_serializer import MenuSerializer
from api_v1.serializers.system.oper_log_serializer import OperLogSerializer
from api_v1.serializers.system.user_serializer import UserSerializer
from api_v1.serializers.system.dict_type_serializer import DictTypeSerializer
from api_v1.serializers.system.dict_item_serializer import DictItemSerializer
from api_v1.serializers.system.config_serializer import ConfigSerializer
from api_v1.serializers.system.mobile_code_send_serializer import MobileCodeSendSerializer
from api_v1.serializers.system.mobile_bind_serializer import MobileBindSerializer
from api_v1.serializers.system.email_code_send_serializer import EmailCodeSendSerializer
from api_v1.serializers.system.email_bind_serializer import EmailBindSerializer

# notice 板块
from api_v1.serializers.notice.notice_brief_serializer import NoticeBriefSerializer
from api_v1.serializers.notice.notice_detail_serializer import NoticeDetailSerializer
from api_v1.serializers.notice.notice_serializer import NoticeSerializer

# crawler 板块
from api_v1.serializers.crawler.crawler_log_serializer import CrawlerLogSerializer
from api_v1.serializers.crawler.crawler_conf_serializer import CrawlerConfSerializer
from api_v1.serializers.crawler.crawler_seller_serializer import CrawlerSellerSerializer
from api_v1.serializers.crawler.crawler_category_serializer import CrawlerCategorySerializer

# file 板块
from api_v1.serializers.file import ImageUploadSerializer

# finance 板块
from api_v1.serializers.finance.monthly_loss_serializer import MonthlyLossSerializer
from api_v1.serializers.finance.monthly_loss_first20_serializer import MonthlyLossFirst20Serializer

# work 板块
from api_v1.serializers.work import WorkReportSerializer

# ads 板块
from api_v1.serializers.ads import LxCampaignInfoSerializer

__all__ = [
    "PositionSerializer", "PositionWriteSerializer", "PositionOptionSerializer",
    "DeptSerializer", "MenuSerializer",
    "OperLogSerializer", "UserSerializer", "DictTypeSerializer", "DictItemSerializer",
    "ConfigSerializer", "MobileCodeSendSerializer", "MobileBindSerializer",
    "EmailCodeSendSerializer", "EmailBindSerializer",
    "NoticeBriefSerializer", "NoticeDetailSerializer", "NoticeSerializer",
    "CrawlerLogSerializer", "CrawlerConfSerializer", "CrawlerSellerSerializer",
    "CrawlerCategorySerializer",
    "ImageUploadSerializer",
    "MonthlyLossSerializer", "MonthlyLossFirst20Serializer",
    "WorkReportSerializer",
    "LxCampaignInfoSerializer",
]
