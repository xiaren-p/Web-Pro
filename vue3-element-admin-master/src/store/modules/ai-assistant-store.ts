/**
 * AI 助手 Pinia store。
 *
 * 设计要点：
 *   - 仅缓存"会话元数据"（id / title / 最近活跃时间），消息正文不进 localStorage，避免 ERP 敏感数据明文落盘
 *   - 当前激活会话 ID 用 useStorage 持久化，刷新页面自动恢复
 *   - 侧栏开关状态独立持久化，不影响其它布局 store
 */

import { useStorage } from "@vueuse/core";
import { store } from "@/store";
import type { AiConversation } from "@/types/aiAssistant/planSchema";

const STORAGE_KEY_ACTIVE_CONVERSATION = "ai-assistant:active-conversation-id";
const STORAGE_KEY_PANEL_OPEN = "ai-assistant:panel-open";

export const useAiAssistantStore = defineStore("aiAssistant", () => {
  /** 侧栏抽屉是否展开 */
  const panelOpen = useStorage<boolean>(STORAGE_KEY_PANEL_OPEN, false);

  /** 当前激活的会话 ID；为 null 表示尚未选择 */
  const activeConversationId = useStorage<number | null>(STORAGE_KEY_ACTIVE_CONVERSATION, null);

  /** 会话列表（仅元数据，正文按需向后端拉） */
  const conversations = ref<AiConversation[]>([]);

  /** 是否正在向 Dify 发送（防止重复点击） */
  const sending = ref<boolean>(false);

  /**
   * 切换侧栏抽屉显隐。
   */
  function togglePanel(): void {
    panelOpen.value = !panelOpen.value;
  }

  /**
   * 设置侧栏抽屉显隐状态。
   *
   * @param open - 期望状态
   */
  function setPanelOpen(open: boolean): void {
    panelOpen.value = open;
  }

  /**
   * 选择激活会话。传 null 表示进入"新建会话"占位状态。
   *
   * @param id - 会话 ID 或 null
   */
  function setActiveConversation(id: number | null): void {
    activeConversationId.value = id;
  }

  /**
   * 用后端返回的最新列表覆盖本地缓存。
   *
   * @param items - 会话列表
   */
  function setConversations(items: AiConversation[]): void {
    conversations.value = items;
  }

  /**
   * 在列表头部插入一条新会话（首次发起对话后调用）。
   *
   * @param item - 新会话
   */
  function prependConversation(item: AiConversation): void {
    if (conversations.value.some((c) => c.id === item.id)) return;
    conversations.value = [item, ...conversations.value];
  }

  /**
   * 从列表中移除某条会话。
   *
   * @param id - 会话 ID
   */
  function removeConversation(id: number): void {
    conversations.value = conversations.value.filter((c) => c.id !== id);
    if (activeConversationId.value === id) {
      activeConversationId.value = null;
    }
  }

  /**
   * 设置发送锁定状态。
   *
   * @param value - 是否正在发送
   */
  function setSending(value: boolean): void {
    sending.value = value;
  }

  return {
    panelOpen,
    activeConversationId,
    conversations,
    sending,
    togglePanel,
    setPanelOpen,
    setActiveConversation,
    setConversations,
    prependConversation,
    removeConversation,
    setSending,
  };
});

/**
 * 在非组件 setup 上下文（如路由守卫）中获取 store 实例。
 */
export function useAiAssistantStoreHook() {
  return useAiAssistantStore(store);
}
