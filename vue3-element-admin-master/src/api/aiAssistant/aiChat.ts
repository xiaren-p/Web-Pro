/**
 * AI 助手对话 API 模块。
 *
 * 仅做请求封装，不做业务加工：
 *   - 普通 REST 接口走项目共享 axios 实例（自动注入 Authorization）
 *   - SSE 订阅由 useAiChatStream 直接调用，避免 axios 的 timeout 干扰流式
 */

import request from "@/utils/request";
import type { AiConversation, AiMessage, ChatStartResponse } from "@/types/aiAssistant/planSchema";

/**
 * 启动一轮对话。立即返回消息 ID，真实生成在后端 Celery 异步执行。
 *
 * @param payload - 入参
 * @param payload.query - 用户提问原文
 * @param payload.conversation_id - 续接会话的 ID；新建对话时省略
 * @param payload.inputs - Dify 工作流变量
 * @returns 后端返回的会话 / 消息 ID 三元组
 */
export function startChat(payload: {
  query: string;
  conversation_id?: number | null;
  inputs?: Record<string, unknown>;
}): Promise<ChatStartResponse> {
  return request.post("/api/v2/ai/chat/", payload);
}

/**
 * 拉取当前用户的会话列表（最近活跃倒序）。
 */
export function listConversations(): Promise<{ items: AiConversation[] }> {
  return request.get("/api/v2/ai/conversations/");
}

/**
 * 拉取某会话的全部消息（用于刷新页面后的历史回放）。
 *
 * @param conversationId - 会话 ID
 */
export function listMessages(conversationId: number): Promise<{ items: AiMessage[] }> {
  return request.get(`/api/v2/ai/conversations/${conversationId}/messages/`);
}

/**
 * 删除会话及其全部消息。
 *
 * @param conversationId - 会话 ID
 */
export function deleteConversation(conversationId: number): Promise<{ success: boolean }> {
  return request.delete(`/api/v2/ai/conversations/${conversationId}/`);
}

/**
 * 取消正在生成的 AI 消息。后端会向 Celery 发取消信号并广播 done 事件。
 *
 * @param messageId - 消息 ID
 */
export function cancelMessage(messageId: number): Promise<{ success: boolean }> {
  return request.post(`/api/v2/ai/messages/${messageId}/cancel/`);
}
