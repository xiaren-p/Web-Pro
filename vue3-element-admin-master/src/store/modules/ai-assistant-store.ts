/**
 * AI 助手 Pinia store。
 *
 * 设计要点：
 *   - 仅缓存"会话元数据"（id / title / 最近活跃时间），消息正文不进 localStorage，避免 ERP 敏感数据明文落盘
 *   - 当前激活会话 ID 用 useStorage 持久化，刷新页面自动恢复
 *   - 侧栏开关状态独立持久化，不影响其它布局 store
 */

import { useStorage } from "@vueuse/core";
import { computed } from "vue";
import { store } from "@/store";
import type { AiApp, AiConversation, AiConversationGroup } from "@/types/aiAssistant/planSchema";

const STORAGE_KEY_ACTIVE_CONVERSATION = "ai-assistant:active-conversation-id";
const STORAGE_KEY_PANEL_OPEN = "ai-assistant:panel-open";
const STORAGE_KEY_ACTIVE_APP_CODE = "ai-assistant:active-app-code";

export const useAiAssistantStore = defineStore("aiAssistant", () => {
  /** 侧栏抽屉是否展开 */
  const panelOpen = useStorage<boolean>(STORAGE_KEY_PANEL_OPEN, false);

  /** 当前激活的会话 UUID；为 null 表示尚未选择 */
  const activeConversationId = useStorage<string | null>(STORAGE_KEY_ACTIVE_CONVERSATION, null);

  /** 用户选定的 Dify 应用 code；null 表示走系统默认应用 */
  const activeAppCode = useStorage<string | null>(STORAGE_KEY_ACTIVE_APP_CODE, null);

  /** 后端拉的全部启用 Dify 应用列表（按 sort_order 升序） */
  const availableApps = ref<AiApp[]>([]);

  /** 会话列表（仅元数据，正文按需向后端拉） */
  const conversations = ref<AiConversation[]>([]);

  /** 用户自定义分组列表（按 order 升序） */
  const groups = ref<AiConversationGroup[]>([]);

  /** 是否正在向 Dify 发送（防止重复点击） */
  const sending = ref<boolean>(false);

  /**
   * 当前选中的 Dify 应用对象。
   *
   * 计算规则：
   *   1. 优先按 ``activeAppCode`` 匹配
   *   2. 若 activeAppCode 为 null 或匹配不到（应用已停用）→ 回退到 ``is_default=true``
   *   3. 仍找不到 → 取列表第一条
   *   4. 列表为空 → null
   */
  const currentApp = computed<AiApp | null>(() => {
    if (availableApps.value.length === 0) return null;
    if (activeAppCode.value) {
      const matched = availableApps.value.find((a) => a.code === activeAppCode.value);
      if (matched) return matched;
    }
    const fallback = availableApps.value.find((a) => a.is_default);
    return fallback ?? availableApps.value[0];
  });

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
   * @param id - 会话 UUID 或 null
   */
  function setActiveConversation(id: string | null): void {
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
   * @param id - 会话 UUID
   */
  function removeConversation(id: string): void {
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

  /**
   * 用后端返回的最新分组列表覆盖本地缓存。
   *
   * @param items - 分组列表
   */
  function setGroups(items: AiConversationGroup[]): void {
    groups.value = items;
  }

  /**
   * 更新本地分组（重命名 / 移序后调用）。
   *
   * @param updated - 已更新的分组实例
   */
  function patchGroup(updated: AiConversationGroup): void {
    const idx = groups.value.findIndex((g) => g.id === updated.id);
    if (idx >= 0) groups.value[idx] = updated;
  }

  /**
   * 把新建的分组加到本地缓存末尾。
   *
   * @param group - 新建分组
   */
  function appendGroup(group: AiConversationGroup): void {
    if (groups.value.some((g) => g.id === group.id)) return;
    groups.value = [...groups.value, group];
  }

  /**
   * 从本地缓存移除分组（不影响其下会话本地缓存的 group_id 字段）。
   *
   * @param groupId - 分组 UUID
   */
  function removeGroup(groupId: string): void {
    groups.value = groups.value.filter((g) => g.id !== groupId);
    // 关联会话本地标记为未分组（与后端 SET_NULL 行为一致）
    conversations.value = conversations.value.map((c) =>
      c.group_id === groupId ? { ...c, group_id: null } : c
    );
  }

  /**
   * 用后端返回的 Dify 应用列表覆盖本地缓存。
   *
   * @param items - 后端 list_apps 返回的应用数组
   */
  function setApps(items: AiApp[]): void {
    availableApps.value = items;
  }

  /**
   * 切换当前激活的 Dify 应用。
   *
   * @param code - 目标应用 code；传 null 表示恢复到 currentApp 计算的默认值
   */
  function setActiveApp(code: string | null): void {
    activeAppCode.value = code;
  }

  return {
    panelOpen,
    activeConversationId,
    activeAppCode,
    availableApps,
    currentApp,
    conversations,
    groups,
    sending,
    togglePanel,
    setPanelOpen,
    setActiveConversation,
    setConversations,
    prependConversation,
    removeConversation,
    setSending,
    setGroups,
    patchGroup,
    appendGroup,
    removeGroup,
    setApps,
    setActiveApp,
  };
});

/**
 * 在非组件 setup 上下文（如路由守卫）中获取 store 实例。
 */
export function useAiAssistantStoreHook() {
  return useAiAssistantStore(store);
}
