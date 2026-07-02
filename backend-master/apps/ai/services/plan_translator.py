"""Plan Schema 翻译器（plan_translator）。

将 Dify 流式输出中的"计划提案"原始 JSON 翻译为前端可直接渲染的 Plan Schema。
本模块是"数据出口最终成形"原则的关键执行者：所有枚举翻译、字段重命名、
默认值兜底统一在此完成，前端拿到结果后零加工直接绑定。
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import Any, Optional

logger = logging.getLogger(__name__)


# Dify 端约定：Plan Schema 通过特殊标签包裹注入回答中
# 形如 <plan>{"...": ...}</plan>，便于在流式文本里精确切分
_PLAN_TAG_PATTERN = re.compile(r'<plan>(.*?)</plan>', re.DOTALL)


class PlanTranslator:
    """Plan 提案翻译器。

    职责：
        - 从 Dify 累积的回答文本中解析出 ``<plan>...</plan>`` 包裹的 JSON
        - 按前端 Schema 契约补齐缺失字段、统一命名风格（snake_case → 固定 schema）
        - 给可选项分配稳定 key、兜底 ``allow_custom`` / ``multi_select`` 等默认值
        - 翻译枚举（status / role 等）为前端可直接展示的中文标签
    """

    # 默认字段值：Dify 端可能省略部分字段，此处给出稳态默认值，避免前端 if/else 兜底逻辑泛滥
    _DEFAULT_BUTTON_TEXT = '确认执行'

    def extract_plan_text(self, full_answer: str) -> Optional[str]:
        """从 Dify 累积回答中提取 plan 标签内的原始 JSON 字符串。

        Args:
            full_answer (str): Dify 已收到的全部回答（截止当前帧的累积文本）。

        Returns:
            Optional[str]: 标签内的 JSON 字符串；未匹配到时返回 None。
        """
        match = _PLAN_TAG_PATTERN.search(full_answer)
        if not match:
            return None
        return match.group(1).strip()

    def translate(self, raw_plan_text: str) -> Optional[dict[str, Any]]:
        """将 plan 原始 JSON 文本翻译为前端 Schema。

        Args:
            raw_plan_text (str): Dify 注入的 ``<plan>...</plan>`` 内部 JSON 文本。

        Returns:
            Optional[dict[str, Any]]: 翻译后的标准 Plan Schema 字典；
                解析失败时返回 None，调用方应据此回退为普通文本消息。

        Raises:
            该方法不抛出异常，所有解析错误都吞掉并返回 None，避免污染流式主链路。
        """
        try:
            raw = json.loads(raw_plan_text)
        except json.JSONDecodeError as exc:
            logger.warning(
                '[PlanTranslator][translate] Plan JSON 解析失败: err=%s text=%s',
                str(exc),
                raw_plan_text[:200],
            )
            return None

        if not isinstance(raw, dict):
            logger.warning('[PlanTranslator][translate] Plan 顶层非 dict，跳过')
            return None

        # 统一字段命名（即便 Dify 端写错了 camelCase，也兜回 snake_case）
        plan_id = str(raw.get('plan_id') or raw.get('planId') or uuid.uuid4())

        options_raw = raw.get('options') or []
        options = self._translate_options(options_raw)

        confirm_action_raw = raw.get('confirm_action') or raw.get('confirmAction') or {}
        confirm_action = self._translate_confirm_action(confirm_action_raw)

        custom_field_raw = raw.get('custom_field') or raw.get('customField')
        custom_field = self._translate_custom_field(custom_field_raw)

        return {
            'type': 'plan_proposal',
            'plan_id': plan_id,
            'title': str(raw.get('title') or '请确认下列方案'),
            'description': str(raw.get('description') or ''),
            'options': options,
            'multi_select': bool(raw.get('multi_select', raw.get('multiSelect', False))),
            'allow_custom': bool(raw.get('allow_custom', raw.get('allowCustom', False))),
            'custom_field': custom_field,
            'confirm_action': confirm_action,
            'cancellable': bool(raw.get('cancellable', True)),
        }

    def _translate_options(self, options_raw: Any) -> list[dict[str, Any]]:
        """归一化 options 列表。

        每个 option 必须有 key / label / selected 三字段，缺失时补默认值；
        key 缺失时按索引兜底为 ``opt_<i>`` 保证前端 v-for 不报 warning。

        Args:
            options_raw (Any): Dify 原始 options，理论上是 list[dict]。

        Returns:
            list[dict[str, Any]]: 归一化后的 option 列表。
        """
        if not isinstance(options_raw, list):
            return []

        result: list[dict[str, Any]] = []
        for index, item in enumerate(options_raw):
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    'key': str(item.get('key') or f'opt_{index}'),
                    'label': str(item.get('label') or f'选项 {index + 1}'),
                    'selected': bool(item.get('selected', False)),
                }
            )
        return result

    def _translate_custom_field(self, raw: Any) -> Optional[dict[str, str]]:
        """归一化 custom_field 配置。

        Args:
            raw (Any): Dify 原始字段，期望 dict 或 None。

        Returns:
            Optional[dict[str, str]]: 包含 key / label / placeholder 的 dict；
                上游未提供时返回 None。
        """
        if not isinstance(raw, dict):
            return None
        return {
            'key': str(raw.get('key') or 'custom_value'),
            'label': str(raw.get('label') or '其他'),
            'placeholder': str(raw.get('placeholder') or ''),
        }

    def _translate_confirm_action(self, raw: Any) -> dict[str, str]:
        """归一化 confirm_action 配置。

        Args:
            raw (Any): Dify 原始 confirm_action 字段。

        Returns:
            dict[str, str]: 包含 endpoint / method / button_text 的标准结构；
                Dify 未提供端点时返回空字符串，由前端展示为"待接入"占位按钮。
        """
        if not isinstance(raw, dict):
            return {'endpoint': '', 'method': 'POST', 'button_text': self._DEFAULT_BUTTON_TEXT}
        return {
            'endpoint': str(raw.get('endpoint') or ''),
            'method': str(raw.get('method') or 'POST').upper(),
            'button_text': str(raw.get('button_text') or self._DEFAULT_BUTTON_TEXT),
        }
