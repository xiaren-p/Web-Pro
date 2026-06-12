"""SP 广告规则策略视图（LxAdRule / LxAdRuleGroup）。"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from api_v1.models.lingxing.ads.lx_ad_rule import LxAdRule
from api_v1.models.lingxing.ads.lx_ad_rule_group import LxAdRuleGroup
from api_v1.serializers.lingxing.rule_strategy_serializer import (
    LxAdRuleSerializer,
    LxAdRuleGroupSerializer,
)
from api_v1.utils.pagination import paginate_queryset
from api_v1.utils.responses import drf_error, drf_ok


class RuleStrategyViewSet(viewsets.ViewSet):
    """广告规则 CRUD（需要登录）。

    路由：
    - GET  /ads/rule-strategy/rules           → 分页列表
    - POST /ads/rule-strategy/rules           → 新增规则
    - GET  /ads/rule-strategy/rules/<id>       → 获取单条规则
    - PUT  /ads/rule-strategy/rules/<id>       → 更新规则
    - DELETE /ads/rule-strategy/rules/<id>     → 删除规则
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        """列表查询 / 新增规则。"""
        if request.method.lower() == "get":
            qs = LxAdRule.objects.all()
            total, items, page_num, page_size = paginate_queryset(request, qs)
            data = LxAdRuleSerializer(items, many=True).data
            return drf_ok({
                "total": total,
                "list": data,
                "pageNum": page_num,
                "pageSize": page_size,
            })

        # 新增
        rule_name = request.data.get("name", "").strip()
        if rule_name and LxAdRule.objects.filter(name=rule_name).exists():
            return drf_error(f"规则名称「{rule_name}」已存在，请使用其他名称", status=409)
        ser = LxAdRuleSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return drf_error("参数错误", status=400, data={"errors": ser.errors})
        obj = ser.save()
        return drf_ok(LxAdRuleSerializer(obj).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)")
    def retrieve(self, request, id: str):
        """获取单条规则。"""
        try:
            obj = LxAdRule.objects.get(pk=id)
            return drf_ok(LxAdRuleSerializer(obj).data)
        except LxAdRule.DoesNotExist:
            return drf_error("未找到该规则", status=404)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)/update")
    def update(self, request, id: str):
        """更新规则。"""
        try:
            obj = LxAdRule.objects.get(pk=id)
        except LxAdRule.DoesNotExist:
            return drf_error("未找到该规则", status=404)

        ser = LxAdRuleSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return drf_error("参数错误", status=400, data={"errors": ser.errors})
        # 更新时检查名称唯一性（排除自身）
        new_name = request.data.get("name", "").strip()
        if new_name and LxAdRule.objects.filter(name=new_name).exclude(pk=obj.pk).exists():
            return drf_error(f"规则名称「{new_name}」已存在，请使用其他名称", status=409)
        obj = ser.save()
        return drf_ok(LxAdRuleSerializer(obj).data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<id>[^/]+)/delete")
    def destroy(self, request, id: str):
        """删除规则，同时清理所有规则组中对该规则的引用。"""
        try:
            rule_id = int(id)
            rule = LxAdRule.objects.get(pk=rule_id)
        except (ValueError, LxAdRule.DoesNotExist):
            return drf_error("未找到该规则", status=404)

        # 清理所有规则组 rule_order 中对该规则的引用
        groups = LxAdRuleGroup.objects.all()
        for group in groups:
            if rule_id in (group.rule_order or []):
                group.rule_order = [rid for rid in group.rule_order if rid != rule_id]
                group.save(update_fields=["rule_order"])

        rule.delete()
        return drf_ok(status=204)


class RuleStrategyGroupViewSet(viewsets.ViewSet):
    """规则组 CRUD（需要登录）。

    路由：
    - GET  /ads/rule-strategy/groups               → 规则组列表（含规则详情）
    - POST /ads/rule-strategy/groups               → 新增规则组
    - GET  /ads/rule-strategy/groups/<id>           → 获取单个规则组
    - PUT  /ads/rule-strategy/groups/<id>           → 更新规则组
    - DELETE /ads/rule-strategy/groups/<id>         → 删除规则组
    - POST /ads/rule-strategy/groups/<id>/add-rules    → 添加规则到组
    - POST /ads/rule-strategy/groups/<id>/remove-rule  → 从组移除规则
    """

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get", "post"], url_path="")
    def list_or_create(self, request):
        """列表查询 / 新增规则组。"""
        if request.method.lower() == "get":
            qs = LxAdRuleGroup.objects.all()
            total, items, page_num, page_size = paginate_queryset(request, qs)
            data = LxAdRuleGroupSerializer(items, many=True).data
            return drf_ok({
                "total": total,
                "list": data,
                "pageNum": page_num,
                "pageSize": page_size,
            })

        # 新增
        ser = LxAdRuleGroupSerializer(data=request.data, context={"request": request})
        if not ser.is_valid():
            return drf_error("参数错误", status=400, data={"errors": ser.errors})
        obj = ser.save()
        return drf_ok(LxAdRuleGroupSerializer(obj).data, status=201)

    @action(detail=False, methods=["get"], url_path=r"(?P<id>[^/]+)")
    def retrieve(self, request, id: str):
        """获取单个规则组。"""
        try:
            obj = LxAdRuleGroup.objects.get(pk=id)
            return drf_ok(LxAdRuleGroupSerializer(obj).data)
        except LxAdRuleGroup.DoesNotExist:
            return drf_error("未找到该规则组", status=404)

    @action(detail=False, methods=["put"], url_path=r"(?P<id>[^/]+)/update")
    def update(self, request, id: str):
        """更新规则组。"""
        try:
            obj = LxAdRuleGroup.objects.get(pk=id)
        except LxAdRuleGroup.DoesNotExist:
            return drf_error("未找到该规则组", status=404)

        ser = LxAdRuleGroupSerializer(obj, data=request.data, partial=True)
        if not ser.is_valid():
            return drf_error("参数错误", status=400, data={"errors": ser.errors})
        obj = ser.save()
        return drf_ok(LxAdRuleGroupSerializer(obj).data)

    @action(detail=False, methods=["delete"], url_path=r"(?P<id>[^/]+)/delete")
    def destroy(self, request, id: str):
        """删除规则组。"""
        try:
            obj = LxAdRuleGroup.objects.get(pk=id)
        except LxAdRuleGroup.DoesNotExist:
            return drf_error("未找到该规则组", status=404)
        obj.delete()
        return drf_ok(status=204)

    @action(detail=False, methods=["post"], url_path=r"(?P<id>[^/]+)/add-rules")
    def add_rules(self, request, id: str):
        """添加规则到规则组。

        Body: {"ruleIds": [1, 2, 3]}
        规则 ID 会被追加到 rule_order 末尾。
        """
        try:
            group = LxAdRuleGroup.objects.get(pk=id)
        except LxAdRuleGroup.DoesNotExist:
            return drf_error("未找到该规则组", status=404)

        rule_ids = request.data.get("ruleIds", [])
        if not isinstance(rule_ids, list) or not rule_ids:
            return drf_error("ruleIds 必须是非空数组", status=400)

        current_order = group.rule_order or []
        for rid in rule_ids:
            if rid not in current_order:
                current_order.append(rid)
        group.rule_order = current_order
        group.save(update_fields=["rule_order"])
        return drf_ok(LxAdRuleGroupSerializer(group).data)

    @action(detail=False, methods=["post"], url_path=r"(?P<id>[^/]+)/remove-rule")
    def remove_rule(self, request, id: str):
        """从规则组移除规则。

        Body: {"ruleId": 1}
        """
        try:
            group = LxAdRuleGroup.objects.get(pk=id)
        except LxAdRuleGroup.DoesNotExist:
            return drf_error("未找到该规则组", status=404)

        rule_id = request.data.get("ruleId")
        if rule_id is None:
            return drf_error("ruleId 不能为空", status=400)

        current_order = group.rule_order or []
        if rule_id in current_order:
            current_order.remove(rule_id)
            group.rule_order = current_order
            group.save(update_fields=["rule_order"])

        return drf_ok(LxAdRuleGroupSerializer(group).data)
