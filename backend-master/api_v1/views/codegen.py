import json
import zipfile
import io
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django.db import connection

from api_v1.utils.responses import drf_ok, drf_error

class CodegenViewSet(viewsets.ViewSet):
    """
    代码生成：基于数据库表结构生成 CRUD 模板代码
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"], url_path="table/list")
    def table_list(self, request):
        """获取当前数据库的所有表名及注释"""
        table_name = request.query_params.get("tableName", "")
        with connection.cursor() as cursor:
            # 兼容 MySQL 和 SQLite (本例主要适配 SQLite/MySQL)
            # 若是 SQLite:
            if connection.vendor == 'sqlite':
                sql = "SELECT name, type FROM sqlite_master WHERE type='table'"
                if table_name:
                    sql += f" AND name LIKE '%%{table_name}%%'"
                cursor.execute(sql)
                rows = cursor.fetchall()
                data = [{"tableName": r[0], "tableComment": r[0], "createTime": ""} for r in rows]
            else:
                # MySQL
                sql = "SELECT table_name, table_comment, create_time FROM information_schema.tables WHERE table_schema = DATABASE()"
                if table_name:
                    sql += f" AND table_name LIKE '%%{table_name}%%'"
                cursor.execute(sql)
                rows = cursor.fetchall()
                data = [{"tableName": r[0], "tableComment": r[1], "createTime": r[2]} for r in rows]

        return drf_ok({"list": data, "total": len(data)})

    @action(detail=False, methods=["get"], url_path="table/info/(?P<tableName>[^/]+)")
    def table_info(self, request, tableName):
        """获取指定表的字段详情"""
        if not tableName:
             return drf_error("未指定表名")
        
        # Django introspection
        # from django.db import connection
        # cursor = connection.cursor()
        # description = connection.introspection.get_table_description(cursor, tableName)
        
        # 为了更详细的信息（类型、键等），我们此处做简易实现
        # 注意：真实生产环境建议使用专用的生成器库
        
        columns = []
        with connection.cursor() as cursor:
            if connection.vendor == 'sqlite':
                # PRAGMA table_info(table_name)
                # cid, name, type, notnull, dflt_value, pk
                cursor.execute(f"PRAGMA table_info({tableName})")
                rows = cursor.fetchall()
                for r in rows:
                    columns.append({
                        "columnName": r[1],
                        "columnType": r[2],
                        "isPk": (r[5] == 1),
                        "isNullable": (r[3] == 0),
                        "columnComment": "" # SQLite 无原生注释
                    })
            else:
                 # MySQL
                 sql = """
                 SELECT column_name, data_type, column_key, is_nullable, column_comment 
                 FROM information_schema.columns 
                 WHERE table_schema = DATABASE() AND table_name = %s
                 ORDER BY ordinal_position
                 """
                 cursor.execute(sql, [tableName])
                 rows = cursor.fetchall()
                 for r in rows:
                     columns.append({
                        "columnName": r[0],
                        "columnType": r[1],
                        "isPk": (r[2] == "PRI"),
                        "isNullable": (r[3] == "YES"),
                        "columnComment": r[4]
                     })
        
        return drf_ok({"tableName": tableName, "columns": columns})

    @action(detail=False, methods=["post"], url_path="preview")
    def preview(self, request):
        """
        预览生成的代码
        接收参数：tableName, packageName, author...
        返回：{"java": "...", "vue": "...", "sql": "..."}
        """
        data = request.data
        table_name = data.get("tableName")
        # 简单模拟生成
        # 实际逻辑应使用模板引擎 jinja2 等
        
        code_map = {}
        code_map["model.py"] = f"# Model for {table_name}\nclass MyModel(models.Model):\n    pass"
        code_map["serializer.py"] = f"# Serializer for {table_name}\nclass MySerializer(serializers.ModelSerializer):\n    pass"
        code_map["views.py"] = f"# ViewSet for {table_name}\nclass MyViewSet(viewsets.ModelViewSet):\n    pass"
        code_map["index.vue"] = f"<!-- Vue for {table_name} -->\n<template></template>"
        
        return drf_ok(code_map)

    @action(detail=False, methods=["post"], url_path="download")
    def download(self, request):
        """下载生成的代码 zip"""
        data = request.data
        table_name = data.get("tableName") or "code"
        
        # 模拟生成文件
        file_map = {
            f"{table_name}_model.py": "# code...",
            f"{table_name}_view.py": "# code...",
        }
        
        # 内存中打包 ZIP
        mem_file = io.BytesIO()
        with zipfile.ZipFile(mem_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            for fname, content in file_map.items():
                zf.writestr(fname, content)
        
        mem_file.seek(0)
        from django.http import HttpResponse
        resp = HttpResponse(mem_file.read(), content_type='application/octet-stream')
        resp['Content-Disposition'] = f'attachment; filename="codegen_{table_name}.zip"'
        return resp
