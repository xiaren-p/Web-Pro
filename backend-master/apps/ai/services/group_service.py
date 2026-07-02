"""AI 对话分组管理服务（ai_group_service）。"""

from __future__ import annotations

import logging
import uuid
from typing import Optional, Union

from django.contrib.auth.models import User
from django.db import IntegrityError

from apps.ai.models.conversation import AiConversation
from apps.ai.models.conversation_group import AiConversationGroup

logger = logging.getLogger(__name__)


class AiGroupService:
    """AI 对话分组的业务编排。

    职责：分组 CRUD、把会话移入 / 移出分组、维护分组排序。
    所有读写均强制 ``user`` 过滤，避免越权操作他人分组。
    """

    def list_groups(self, user: User) -> list[AiConversationGroup]:
        """返回用户的全部分组（按 order 升序）。

        Args:
            user (User): 当前登录用户。

        Returns:
            list[AiConversationGroup]: 分组列表。
        """
        return list(AiConversationGroup.objects.filter(user=user))

    def create_group(self, user: User, name: str) -> AiConversationGroup:
        """新建一个分组。

        Args:
            user (User): 当前登录用户。
            name (str): 分组名称（≤ 80 字，用户内唯一）。

        Returns:
            AiConversationGroup: 新建的分组实例。

        Raises:
            ValueError: 名称为空 / 过长 / 同名分组已存在。
        """
        cleaned = (name or '').strip()
        if not cleaned:
            raise ValueError('分组名称不能为空')
        if len(cleaned) > 80:
            raise ValueError('分组名称不能超过 80 字')

        max_order = (
            AiConversationGroup.objects.filter(user=user)
            .order_by('-order')
            .values_list('order', flat=True)
            .first()
        )
        next_order = (max_order or 0) + 1

        try:
            return AiConversationGroup.objects.create(
                user=user,
                name=cleaned,
                order=next_order,
            )
        except IntegrityError as exc:
            raise ValueError(f'已存在同名分组: {cleaned}') from exc

    def rename_group(
        self,
        user: User,
        public_id: Union[uuid.UUID, str],
        name: str,
    ) -> AiConversationGroup:
        """重命名分组。

        Args:
            user (User): 当前登录用户。
            public_id (uuid.UUID | str): 目标分组 public_id。
            name (str): 新名称。

        Returns:
            AiConversationGroup: 更新后的分组实例。

        Raises:
            ValueError: 新名称非法 / 同名冲突。
            AiConversationGroup.DoesNotExist: 分组不存在或无权访问。
        """
        cleaned = (name or '').strip()
        if not cleaned:
            raise ValueError('分组名称不能为空')
        if len(cleaned) > 80:
            raise ValueError('分组名称不能超过 80 字')

        group = AiConversationGroup.objects.get(public_id=public_id, user=user)
        group.name = cleaned
        try:
            group.save(update_fields=['name', 'updated_at'])
        except IntegrityError as exc:
            raise ValueError(f'已存在同名分组: {cleaned}') from exc
        return group

    def delete_group(self, user: User, public_id: Union[uuid.UUID, str]) -> None:
        """删除分组（不级联删会话，会话变为"未分组"）。

        Args:
            user (User): 当前登录用户。
            public_id (uuid.UUID | str): 目标分组 public_id。

        Raises:
            AiConversationGroup.DoesNotExist: 分组不存在或无权访问。
        """
        group = AiConversationGroup.objects.get(public_id=public_id, user=user)
        # 通过 on_delete=SET_NULL 自动把关联会话置为未分组
        group.delete()

    def move_conversation(
        self,
        user: User,
        conversation_public_id: Union[uuid.UUID, str],
        group_public_id: Optional[Union[uuid.UUID, str]],
    ) -> AiConversation:
        """把会话移到指定分组（或移出所有分组）。

        Args:
            user (User): 当前登录用户。
            conversation_public_id (uuid.UUID | str): 会话 public_id。
            group_public_id (Optional[uuid.UUID | str]): 目标分组 public_id；
                传 None 表示移到"未分组"。

        Returns:
            AiConversation: 更新后的会话实例。

        Raises:
            AiConversation.DoesNotExist: 会话不存在或无权访问。
            AiConversationGroup.DoesNotExist: 分组不存在或无权访问。
        """
        conversation = AiConversation.objects.get(
            public_id=conversation_public_id,
            user=user,
        )

        if group_public_id is None:
            conversation.group = None
        else:
            target_group = AiConversationGroup.objects.get(
                public_id=group_public_id,
                user=user,
            )
            conversation.group = target_group

        conversation.save(update_fields=['group', 'updated_at'])
        return conversation

    def reorder_groups(
        self,
        user: User,
        ordered_public_ids: list[Union[uuid.UUID, str]],
    ) -> None:
        """按前端给定顺序更新分组排序。

        Args:
            user (User): 当前登录用户。
            ordered_public_ids (list): 期望从上到下的分组 public_id 列表。
        """
        for index, pid in enumerate(ordered_public_ids):
            AiConversationGroup.objects.filter(public_id=pid, user=user).update(
                order=index + 1,
            )
