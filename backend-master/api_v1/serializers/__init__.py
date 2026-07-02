"""
api_v1 序列化器包

按业务板块拆分的 DRF 序列化器集合。本 `__init__` 文件统一对外重导出，
保证旧的 `from api_v1.serializers import XxxSerializer` 调用方式继续生效，
同时让新代码可以按板块路径精准导入。
"""

# system 板块
from apps.system.serializers.position_serializer import PositionSerializer, PositionWriteSerializer, PositionOptionSerializer
from apps.system.serializers.dept_serializer import DeptSerializer
from apps.system.serializers.menu_serializer import MenuSerializer
from apps.system.serializers.oper_log_serializer import OperLogSerializer
from apps.system.serializers.user_serializer import UserSerializer
from apps.system.serializers.dict_type_serializer import DictTypeSerializer
from apps.system.serializers.dict_item_serializer import DictItemSerializer
from apps.system.serializers.config_serializer import ConfigSerializer
from apps.system.serializers.mobile_code_send_serializer import MobileCodeSendSerializer
from apps.system.serializers.mobile_bind_serializer import MobileBindSerializer
from apps.system.serializers.email_code_send_serializer import EmailCodeSendSerializer
from apps.system.serializers.email_bind_serializer import EmailBindSerializer

# file 板块
from apps.common.serializers.image_upload_serializer import ImageUploadSerializer
from apps.sales.listing.serializers.image_sync_queue_serializer import ImageSyncQueueSerializer

# work 板块
from apps.system.serializers.work_serializer import WorkReportSerializer

# migrated to apps/*
# notice -> apps.notice.serializers
# crawler -> apps.crawler.serializers
# finance -> apps.finance.serializers
# ads -> apps.ads.sp.timing.serializers / apps.ads.sp.rules.serializers

__all__ = [
    "PositionSerializer", "PositionWriteSerializer", "PositionOptionSerializer",
    "DeptSerializer", "MenuSerializer",
    "OperLogSerializer", "UserSerializer", "DictTypeSerializer", "DictItemSerializer",
    "ConfigSerializer", "MobileCodeSendSerializer", "MobileBindSerializer",
    "EmailCodeSendSerializer", "EmailBindSerializer",
    "ImageUploadSerializer",
    "ImageSyncQueueSerializer",
    "WorkReportSerializer",
]

