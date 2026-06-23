import json
import csv
import io
import os
import uuid
import traceback
from datetime import datetime
from PIL import Image

from django.conf import settings
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated

from api_v1.models import ImageUpload
from api_v1.serializers import ImageUploadSerializer
from api_v1.serializers.image_sync_queue import ImageSyncQueueSerializer
from api_v1.services.lingxing.image_sync_queue_service import (
    batch_upsert_sync_tasks,
    get_queue_queryset,
    upsert_sync_task,
)
from api_v1.utils.responses import drf_ok, drf_error

class ImageUploadViewSet(viewsets.ModelViewSet):
    queryset = ImageUpload.objects.all()
    serializer_class = ImageUploadSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        image_group = self.request.query_params.get('imageGroup')
        status = self.request.query_params.get('status')
        if image_group:
            qs = qs.filter(image_group__icontains=image_group)
        if status:
            qs = qs.filter(status=status)
        return qs

    def page(self, request):
        qs = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return drf_ok({'list': serializer.data, 'total': qs.count()})

    def form(self, request, pk=None):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return drf_ok(serializer.data)

    def create(self, request, *args, **kwargs):
        # 检查图片组是否已存在
        image_group = request.data.get('imageGroup')
        if image_group:
            existing = ImageUpload.objects.filter(image_group=image_group).first()
            if existing:
                # 如果已存在，则执行更新逻辑
                serializer = self.get_serializer(existing, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return drf_ok(serializer.data)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # 新建后自动提交同步队列
        upsert_sync_task(serializer.instance)

        return drf_ok(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # 检查图片组唯一性 (排除自身)
        new_image_group = request.data.get('imageGroup')
        if new_image_group and new_image_group != instance.image_group:
            if ImageUpload.objects.filter(image_group=new_image_group).exclude(id=instance.id).exists():
                return drf_error(f"图片组 '{new_image_group}' 已存在")

        # 处理日志追加逻辑
        data = request.data
        if isinstance(data, dict) or hasattr(data, 'copy'):
             data = data.copy()
             
        new_log = data.get('log')
        if new_log:
            current_log = instance.log or ""
            # 如果已有日志，则追加换行
            if current_log:
                combined_log = f"{current_log}\n{new_log}"
            else:
                combined_log = new_log
            data['log'] = combined_log

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return drf_ok(serializer.data)

    def delete_ids(self, request, pk=None):
        id_list = pk.split(',')
        self.queryset.filter(id__in=id_list).delete()
        return drf_ok()

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """同步单个图片组到内部同步队列。"""
        instance = self.get_object()
        success, log_line = upsert_sync_task(instance)

        if success:
            return drf_ok({"msg": "Sync success", "log": log_line})
        return drf_error(f"Sync failed: {log_line}")

    @action(detail=False, methods=['post'])
    def import_csv(self, request):
        file = request.FILES.get('file')
        if not file:
            return drf_error("请上传文件")
        
        if not file.name.lower().endswith('.csv'):
            return drf_error("请上传 CSV 文件")

        try:
            # 尝试读取文件内容，处理编码
            content = file.read()
            try:
                decoded_content = content.decode('utf-8-sig')
            except UnicodeDecodeError:
                try:
                    decoded_content = content.decode('gbk')
                except UnicodeDecodeError:
                    return drf_error("文件编码格式不支持，请使用 UTF-8 或 GBK")

            io_string = io.StringIO(decoded_content)
            reader = csv.DictReader(io_string)
            
            # 检查表头
            fieldnames = reader.fieldnames
            if not fieldnames:
                return drf_error("CSV 文件为空或格式错误")

            # 映射表头（支持中文和英文表头）
            # imageGroup: 图片组, imageGroup
            # cloudPath: Cloud 路径, cloudPath （可选）

            header_map = {}
            for h in fieldnames:
                h_clean = h.strip()
                if h_clean in ['图片组', 'imageGroup']:
                    header_map['imageGroup'] = h
                elif h_clean in ['Cloud 路径', 'cloudPath']:
                    header_map['cloudPath'] = h

            # 图片组为必需列，Cloud 路径为可选列（若缺失，将以空字符串处理）
            if 'imageGroup' not in header_map:
                return drf_error("CSV 文件必须包含“图片组”列")

            created_count = 0
            updated_count = 0
            failed_count = 0
            failed_items = []
            success_ids = []
            
            for row in reader:
                image_group = row.get(header_map['imageGroup'], '').strip()
                if 'cloudPath' in header_map:
                    cloud_path = row.get(header_map['cloudPath'], '').strip()
                else:
                    cloud_path = ''
                
                if not image_group:
                    continue
                
                try:
                    # Upsert Logic
                    existing = ImageUpload.objects.filter(image_group=image_group).first()
                    if existing:
                        existing.cloud_path = cloud_path
                        existing.save()
                        upsert_sync_task(existing)
                        updated_count += 1
                        success_ids.append(existing.id)
                    else:
                        obj = ImageUpload.objects.create(image_group=image_group, cloud_path=cloud_path)
                        upsert_sync_task(obj)
                        created_count += 1
                        success_ids.append(obj.id)
                except Exception as e:
                    failed_count += 1
                    failed_items.append(f"{image_group}")
            
            return drf_ok({
                'created': created_count,
                'updated': updated_count,
                'failed': failed_count,
                'failed_items': failed_items,
                'success_ids': success_ids
            })

        except Exception as e:
            return drf_error(f"导入失败: {str(e)}")

    @action(detail=False, methods=['post'])
    def batch_sync(self, request):
        """批量同步到内部同步队列。

        Args:
            ids (list[str] | str): ID 列表或逗号分隔的 ID 字符串。
        """
        ids = request.data.get('ids', [])
        if isinstance(ids, str):
            ids = ids.split(',')

        if not ids:
            return drf_error("No ids provided")

        queryset = self.get_queryset().filter(id__in=ids)
        results = batch_upsert_sync_tasks(list(queryset))

        return drf_ok(results)

    @action(detail=False, methods=['get'])
    def queue(self, request):
        """查询内部图片同步队列（手动分页 + imageGroup 过滤）。

        DRF 未配置全局分页类，paginate_queryset 返回 None，
        因此在此手动切片实现分页，返回 {list, total} 格式。
        """
        qs = get_queue_queryset(request.query_params.dict())
        total = qs.count()

        page_num = int(request.query_params.get('pageNum', 1))
        page_size = int(request.query_params.get('pageSize', 10))
        start = (page_num - 1) * page_size
        page_qs = qs[start:start + page_size]

        serializer = ImageSyncQueueSerializer(page_qs, many=True)
        return drf_ok({'list': serializer.data, 'total': total})

    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        """
        图片上传接口
        - 接收 file 参数
        - 压缩为 60x60
        - 存入 media/uploads
        - 返回 URL
        """
        file_obj = request.FILES.get('file')
        if not file_obj:
            return drf_error("No file uploaded")

        try:
            # 1. Open image with Pillow
            img = Image.open(file_obj)
            
            # 2. Resize to 60x60
            img = img.resize((60, 60), Image.LANCZOS)
            
            # 3. Generate filename
            ext = os.path.splitext(file_obj.name)[1] or '.jpg'
            filename = f"{uuid.uuid4().hex}{ext}"
            
            # 4. Save to media/uploads
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            img.save(file_path)
            
            # 5. Construct URL
            # Assuming MEDIA_URL is /media/
            file_url = f"{settings.MEDIA_URL}uploads/{filename}"
            
            # If request has host info, make it absolute (optional, but user asked for access link)
            full_url = request.build_absolute_uri(file_url)
            
            return drf_ok({"url": full_url, "path": f"uploads/{filename}"})
            
        except Exception as e:
            return drf_error(f"Image upload failed: {str(e)}")
