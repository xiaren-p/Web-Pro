/**
 * AI 助手对话 API 模块。
 *
 * 普通 REST 接口走 request 实例（baseURL /dev-api → /api/v1）。
 * SSE 订阅由 useAiChatStream 直接 fetch 调用，避免 axios timeout 干扰流式。
 */
import request from "@/utils/request";
import type {
  AiApp,
  AiConversation,
  AiConversationGroup,
  AiMessage,
  AiSearchHit,
  ChatStartResponse,
} from "@/types/aiAssistant/planSchema";

/**
 * 启动一轮对话。立即返回消息 ID，真实生成在后端 Celery 异步执行。
 *
 * @param payload - 入参
 * @param payload.query - 用户提问原文
 * @param payload.conversation_id - 续接会话的 UUID；新建对话时省略
 * @param payload.inputs - Dify 工作流变量
 * @returns 后端返回的会话 / 消息 UUID 三元组
 */
export function startChat(payload: {
  query: string;
  conversation_id?: string | null;
  app_code?: string | null;
  inputs?: Record<string, unknown>;
}): Promise<ChatStartResponse> {
  return request({ method: "post", url: "/ai/chat/", data: payload });
}

/**
 * 拉取后台维护的全部启用 Dify 应用。
 *
 * @returns 应用列表。
 */
export function listAiApps(): Promise<{ items: AiApp[] }> {
  return request({ method: "get", url: "/ai/apps/" });
}

/**
 * 拉取当前用户的会话列表（最近活跃倒序）。
 *
 * @returns 会话列表。
 */
export function listConversations(): Promise<{ items: AiConversation[] }> {
  return request({ method: "get", url: "/ai/conversations/" });
}

/**
 * 拉取某会话的全部消息（用于刷新页面后的历史回放）。
 *
 * @param conversationId - 会话 UUID
 */
export function listMessages(conversationId: string): Promise<{ items: AiMessage[] }> {
  return request({ method: "get", url: `/ai/conversations/${conversationId}/messages/` });
}

/**
 * 删除会话及其全部消息。
 *
 * @param conversationId - 会话 UUID
 */
export function deleteConversation(conversationId: string): Promise<{ success: boolean }> {
  return request({ method: "delete", url: `/ai/conversations/${conversationId}/` });
}

/**
 * 重命名会话标题。
 *
 * @param conversationId - 会话 UUID
 * @param title - 新标题（≤ 200 字）
 */
export function renameConversation(
  conversationId: string,
  title: string
): Promise<{ success: boolean; title: string }> {
  return request({
    method: "patch",
    url: `/ai/conversations/${conversationId}/rename/`,
    data: { title },
  });
}

/**
 * 取消正在生成的 AI 消息。
 *
 * @param messageId - 消息 UUID。
 * @returns 操作结果。
 */
export function cancelMessage(messageId: string): Promise<{ success: boolean }> {
  return request({ method: "post", url: `/ai/messages/${messageId}/cancel/` });
}

/**
 * 置顶 / 取消置顶会话。
 *
 * @param conversationId - 会话 UUID
 * @param pinned - true 置顶；false 取消置顶
 */
export function pinConversation(
  conversationId: string,
  pinned: boolean
): Promise<{ success: boolean; pinned: boolean }> {
  return request({
    method: "patch",
    url: `/ai/conversations/${conversationId}/pin/`,
    data: { pinned },
  });
}

/**
 * 把会话移到指定分组（或移出所有分组）。
 *
 * @param conversationId - 会话 UUID
 * @param groupId - 目标分组 UUID；传 null 表示移到"未分组"
 */
export function moveConversationToGroup(
  conversationId: string,
  groupId: string | null
): Promise<{ success: boolean }> {
  return request({
    method: "post",
    url: `/ai/conversations/${conversationId}/move/`,
    data: { group_id: groupId },
  });
}

/**
 * 全文搜索会话标题与消息内容。
 *
 * @param keyword - 关键词
 * @param limit - 命中上限（默认 30，上限 100）
 */
export function searchConversations(
  keyword: string,
  limit: number = 30
): Promise<{ items: AiSearchHit[] }> {
  return request({
    method: "get",
    url: "/ai/conversations/search/",
    params: { q: keyword, limit },
  });
}

/* ── 分组管理 ──────────────────────────────────────────── */

/**
 * 获取当前用户的全部分组。
 *
 * @returns 分组列表。
 */
export function listGroups(): Promise<{ items: AiConversationGroup[] }> {
  return request({ method: "get", url: "/ai/groups/" });
}

/**
 * 新建分组。
 *
 * @param name - 分组名称（≤ 80 字，用户内唯一）
 */
export function createGroup(name: string): Promise<AiConversationGroup> {
  return request({ method: "post", url: "/ai/groups/create/", data: { name } });
}

/**
 * 重命名分组。
 *
 * @param groupId - 分组 UUID
 * @param name - 新名称
 */
export function renameGroup(groupId: string, name: string): Promise<AiConversationGroup> {
  return request({ method: "patch", url: `/ai/groups/${groupId}/rename/`, data: { name } });
}

/**
 * 删除分组（关联会话变为未分组，不级联删除）。
 *
 * @param groupId - 分组 UUID
 */
export function deleteGroup(groupId: string): Promise<{ success: boolean }> {
  return request({ method: "delete", url: `/ai/groups/${groupId}/` });
}

/**
 * 按前端给定顺序更新分组排序。
 *
 * @param orderedIds - 期望从上到下的分组 UUID 数组
 */
export function reorderGroups(orderedIds: string[]): Promise<{ success: boolean }> {
  return request({ method: "post", url: "/ai/groups/reorder/", data: { ordered_ids: orderedIds } });
}
