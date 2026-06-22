"""Dify 平台 HTTP 客户端（dify_client）。

封装与 Dify chat-messages 流式接口的交互细节，屏蔽：
    - SSE 协议解析（拆分 ``data: {...}\\n\\n`` 帧）
    - Bearer 认证头注入
    - 网络异常 / 超时分类
对外只暴露同步生成器接口，由上层 Celery 任务消费。

多应用支持：
    每个 ``DifyApp`` 实例携带独立的 ``api_base`` + 加密的 ``api_key``，本客户端在
    实例化时按 app 解析凭据。无参实例化时回退到 ``DifyApp.objects.get_default()``，
    兼容历史调用方式。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Optional

import requests

if TYPE_CHECKING:
    from api_v2.models.dify_app import DifyApp

logger = logging.getLogger(__name__)


# Dify SSE 帧最大空闲超时（秒）：超过此时间未收到任何字节即视为对端断流。
# 给 LLM 预留充足思考时间但又不致永久挂起。
_READ_TIMEOUT = 120

# 建立连接的超时（秒）：Dify 服务可达即应在 10 秒内握手完成，否则视为不可用。
_CONNECT_TIMEOUT = 10


@dataclass
class DifyStreamChunk:
    """Dify 流式响应中的单个事件帧。

    Dify 原生 SSE 的事件类型较多（``message`` / ``message_end`` / ``agent_thought`` 等），
    本类做归一化封装，供上层 PlanTranslator / AiChatService 消费。

    Attributes:
        event (str): 事件类型字符串，原样保留 Dify 字段。
        answer_delta (str): 仅 ``message`` 事件下携带的本帧增量文本，非 message 事件为空字符串。
        conversation_id (str): Dify 会话 ID，首帧返回后即固定。
        message_id (str): Dify 消息 ID，message_end 事件后稳定。
        raw (dict): 原始 chunk 数据，供 Translator 提取自定义字段使用。
    """

    event: str
    answer_delta: str
    conversation_id: str
    message_id: str
    raw: dict


class DifyClient:
    """Dify 流式对话 HTTP 客户端。

    设计：
        实例化时按传入的 ``DifyApp`` 一次性解析凭据（base + 解密后的 api_key），
        避免每次请求重复读 DB / Fernet 解密。``stream_chat`` 返回生成器，调用方
        逐帧消费即可，客户端本身不缓存中间状态，可由 Celery 多 worker 共用。
    """

    def __init__(self, app: Optional['DifyApp'] = None) -> None:
        """初始化客户端，从 DifyApp 实例（或默认应用）解析凭据。

        Args:
            app (Optional[DifyApp]): 显式指定要调用的 Dify 应用。
                为 None 时调用 ``DifyApp.objects.get_default()`` 取系统默认应用，
                兼容历史调用方式。

        Raises:
            RuntimeError: 当解析后的 ``base_url`` 或 ``api_key`` 任一为空时抛出。
        """
        # 延迟导入避免模型层启动期循环依赖
        from api_v2.models.dify_app import DifyApp as _DifyApp

        resolved_app = app if app is not None else _DifyApp.objects.get_default()

        self._app_code: str = resolved_app.code
        self._app_mode: str = resolved_app.mode
        self._base_url: str = resolved_app.resolve_api_base()
        self._api_key: str = resolved_app.decrypt_api_key()

        if not self._base_url or not self._api_key:
            raise RuntimeError(
                f'[DifyClient][__init__] DifyApp<{self._app_code}> 凭据不完整，'
                'base_url 或 api_key 为空。请检查应用配置与 settings.DIFY_API_BASE。'
            )

    def stream_chat(
        self,
        query: str,
        user_identifier: str,
        conversation_id: str = '',
        inputs: Optional[dict] = None,
    ) -> Iterator[DifyStreamChunk]:
        """向 Dify 发起流式对话，逐帧 yield 解析后的 chunk。

        Args:
            query (str): 用户本轮提问的原始文本。
            user_identifier (str): 终端用户标识，Dify 用于跨会话的用户级配额隔离，
                建议传 Django ``user.id`` 字符串化结果。
            conversation_id (str): Dify 会话 ID；首轮对话传空字符串，后续轮次传上轮的返回值。
            inputs (Optional[dict]): Dify 工作流变量；ERP 场景常用字段如 ``shop_id`` / ``module``
                等，由上层业务编排注入。

        Yields:
            DifyStreamChunk: 解析后的归一化事件帧。

        Raises:
            requests.RequestException: 网络层异常（连接失败、超时等）。
            RuntimeError: Dify 返回非 2xx 状态码或 SSE 协议格式异常。
        """
        # Chatflow 与 Agent 在 Dify 端共用 /v1/chat-messages；Workflow 走另一个端点暂不实现
        url = f'{self._base_url}/v1/chat-messages'
        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
        }
        body = {
            'query': query,
            'inputs': inputs or {},
            'response_mode': 'streaming',
            'user': user_identifier,
            'conversation_id': conversation_id,
        }

        logger.info(
            '[DifyClient][stream_chat] 发起请求: app=%s mode=%s user=%s conv=%s query_len=%s',
            self._app_code,
            self._app_mode,
            user_identifier,
            conversation_id or '<new>',
            len(query),
        )

        with requests.post(
            url,
            headers=headers,
            json=body,
            stream=True,
            timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
        ) as response:
            if response.status_code != 200:
                error_text = response.text[:500]
                logger.error(
                    '[DifyClient][stream_chat] Dify 返回非 200: app=%s status=%s body=%s',
                    self._app_code,
                    response.status_code,
                    error_text,
                )
                raise RuntimeError(f'Dify 调用失败 status={response.status_code}: {error_text}')

            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line:
                    continue
                # SSE 帧格式：``data: {...}``。Dify 不发自定义 event 行，全部走 data 包裹的 JSON。
                if not raw_line.startswith('data:'):
                    continue

                data_text = raw_line[5:].strip()
                if data_text in ('', '[DONE]'):
                    continue

                try:
                    payload = json.loads(data_text)
                except json.JSONDecodeError:
                    logger.warning(
                        '[DifyClient][stream_chat] 跳过非法 JSON 帧: %s',
                        data_text[:200],
                    )
                    continue

                yield DifyStreamChunk(
                    event=str(payload.get('event', '')),
                    answer_delta=str(payload.get('answer', '')),
                    conversation_id=str(payload.get('conversation_id', '')),
                    message_id=str(payload.get('message_id', '')),
                    raw=payload,
                )
