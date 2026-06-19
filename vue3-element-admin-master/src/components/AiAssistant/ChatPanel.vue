<template>
  <el-drawer
    v-model="drawerVisible"
    :size="1080"
    :with-header="false"
    direction="rtl"
    :close-on-click-modal="false"
    class="ai-chat-panel"
  >
    <div class="ai-chat-panel__layout">
      <!-- 左侧栏 -->
      <aside class="ai-chat-panel__sidebar">
        <div class="ai-chat-panel__sidebar-header">
          <div class="ai-chat-panel__brand">
            <el-icon class="ai-chat-panel__brand-icon"><MagicStick /></el-icon>
            <span class="ai-chat-panel__brand-text">AI 助手</span>
          </div>
        </div>

        <div class="ai-chat-panel__sidebar-body">
          <el-button
            type="primary"
            :icon="EditPen"
            class="ai-chat-panel__new-btn"
            @click="handleNewConversation"
          >
            新建对话
            <span class="ai-chat-panel__shortcut-hint">{{ modKeyLabel }}+/</span>
          </el-button>

          <el-input
            ref="searchInputRef"
            v-model="searchKeyword"
            :prefix-icon="Search"
            :placeholder="`搜索对话（${modKeyLabel}+K）`"
            clearable
            class="ai-chat-panel__search"
          />

          <!-- 分组管理头部 -->
          <div class="ai-chat-panel__groups-header">
            <span class="ai-chat-panel__groups-title">对话分组</span>
            <el-tooltip content="新建分组" placement="top">
              <el-button :icon="Plus" circle text size="small" @click="handleCreateGroup" />
            </el-tooltip>
          </div>

          <div class="ai-chat-panel__history">
            <!-- 搜索模式：展示搜索命中 -->
            <template v-if="isSearching">
              <div v-if="searchLoading" class="ai-chat-panel__search-loading">
                <el-icon class="is-loading"><Loading /></el-icon>
                搜索中…
              </div>
              <div v-else-if="searchHits.length === 0" class="ai-chat-panel__empty-hint">
                未找到匹配的对话
              </div>
              <div v-else class="ai-chat-panel__group">
                <div class="ai-chat-panel__group-label">搜索结果（{{ searchHits.length }}）</div>
                <div
                  v-for="hit in searchHits"
                  :key="`${hit.conversation_id}-${hit.message_id ?? 'title'}`"
                  class="ai-chat-panel__history-item is-search-hit"
                  :class="{ 'is-active': hit.conversation_id === store.activeConversationId }"
                  @click="handleSelectConversation(hit.conversation_id)"
                >
                  <div class="ai-chat-panel__hit">
                    <div class="ai-chat-panel__hit-title">
                      {{ hit.conversation_title }}
                    </div>
                    <div v-if="hit.message_id" class="ai-chat-panel__hit-snippet">
                      <el-tag size="small" :type="hit.role === 'user' ? 'info' : 'primary'">
                        {{ hit.role === "user" ? "你" : "AI" }}
                      </el-tag>
                      <span v-html="highlightKeyword(hit.snippet, searchKeyword)" />
                    </div>
                  </div>
                </div>
              </div>
            </template>

            <!-- 正常模式：置顶 + 分组 + 未分组（按时间） -->
            <template v-else>
              <!-- 置顶区 -->
              <div v-if="pinnedConversations.length > 0" class="ai-chat-panel__group">
                <div class="ai-chat-panel__group-label">
                  <el-icon><Top /></el-icon>
                  <span>置顶</span>
                </div>
                <ConversationItem
                  v-for="conv in pinnedConversations"
                  :key="conv.id"
                  :conversation="conv"
                  :groups="store.groups"
                  :active="conv.id === store.activeConversationId"
                  @select="handleSelectConversation"
                  @rename="handleRenameConversation"
                  @delete="handleDeleteConversation"
                  @pin="handlePinConversation"
                  @move="handleMoveConversation"
                  @export="handleExportConversation"
                />
              </div>

              <!-- 用户自定义分组 -->
              <div v-for="group in store.groups" :key="group.id" class="ai-chat-panel__group">
                <div class="ai-chat-panel__group-label is-clickable">
                  <el-icon><Folder /></el-icon>
                  <span class="ai-chat-panel__group-name">{{ group.name }}</span>
                  <el-dropdown
                    trigger="click"
                    placement="bottom-end"
                    class="ai-chat-panel__group-menu"
                    @click.stop
                    @command="(cmd: string) => handleGroupCommand(cmd, group)"
                  >
                    <el-button :icon="More" circle text size="small" @click.stop />
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="rename" :icon="EditPen">重命名</el-dropdown-item>
                        <el-dropdown-item command="delete" :icon="Delete" divided>
                          <span style="color: var(--el-color-danger)">删除分组</span>
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
                <ConversationItem
                  v-for="conv in conversationsByGroup[group.id] || []"
                  :key="conv.id"
                  :conversation="conv"
                  :groups="store.groups"
                  :active="conv.id === store.activeConversationId"
                  @select="handleSelectConversation"
                  @rename="handleRenameConversation"
                  @delete="handleDeleteConversation"
                  @pin="handlePinConversation"
                  @move="handleMoveConversation"
                  @export="handleExportConversation"
                />
                <div
                  v-if="(conversationsByGroup[group.id] || []).length === 0"
                  class="ai-chat-panel__group-empty"
                >
                  暂无对话
                </div>
              </div>

              <!-- 未分组：按时间分组 -->
              <div
                v-for="dateGroup in dateGroupsForUngrouped"
                :key="dateGroup.label"
                class="ai-chat-panel__group"
              >
                <div class="ai-chat-panel__group-label">{{ dateGroup.label }}</div>
                <ConversationItem
                  v-for="conv in dateGroup.items"
                  :key="conv.id"
                  :conversation="conv"
                  :groups="store.groups"
                  :active="conv.id === store.activeConversationId"
                  @select="handleSelectConversation"
                  @rename="handleRenameConversation"
                  @delete="handleDeleteConversation"
                  @pin="handlePinConversation"
                  @move="handleMoveConversation"
                  @export="handleExportConversation"
                />
              </div>

              <div
                v-if="
                  pinnedConversations.length === 0 &&
                  dateGroupsForUngrouped.length === 0 &&
                  store.groups.length === 0
                "
                class="ai-chat-panel__empty-hint"
              >
                暂无对话
              </div>
            </template>
          </div>
        </div>
      </aside>

      <!-- 右侧主区 -->
      <main class="ai-chat-panel__main">
        <header class="ai-chat-panel__main-header">
          <span class="ai-chat-panel__main-title">{{ currentConversationTitle }}</span>
          <div class="ai-chat-panel__main-actions">
            <el-tooltip
              v-if="store.activeConversationId && messages.length > 0"
              content="导出对话为 Markdown"
              placement="bottom"
            >
              <el-button :icon="Download" circle text @click="handleExportCurrentConversation" />
            </el-tooltip>
            <el-tooltip content="关闭（Esc）" placement="bottom">
              <el-button :icon="Close" circle text @click="store.setPanelOpen(false)" />
            </el-tooltip>
          </div>
        </header>

        <section ref="messageListRef" class="ai-chat-panel__messages">
          <div v-if="messages.length === 0" class="ai-chat-panel__empty">
            <div class="ai-chat-panel__empty-logo">
              <el-icon><MagicStick /></el-icon>
            </div>
            <h3 class="ai-chat-panel__empty-title">你好，我是 AI 助手</h3>
            <p class="ai-chat-panel__empty-desc">可以帮你处理 ERP 任务、生成方案、回答问题</p>
            <p class="ai-chat-panel__empty-shortcut">
              快捷键：
              <kbd>{{ modKeyLabel }}</kbd>
              +
              <kbd>K</kbd>
              搜索 ·
              <kbd>{{ modKeyLabel }}</kbd>
              +
              <kbd>/</kbd>
              新建对话
            </p>
          </div>

          <MessageItem
            v-for="msg in messages"
            :key="msg.id"
            :message="msg"
            :plan-readonly="msg.id !== latestPlanMessageId"
            @plan-confirm="handlePlanConfirm"
            @plan-cancel="handlePlanCancel"
          />
        </section>

        <footer class="ai-chat-panel__footer">
          <div class="ai-chat-panel__composer">
            <el-input
              v-model="inputText"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 8 }"
              placeholder="向 AI 提问"
              resize="none"
              :disabled="store.sending"
              class="ai-chat-panel__composer-input"
              @keydown.enter.exact.prevent="handleSend"
            />
            <div class="ai-chat-panel__composer-toolbar">
              <div class="ai-chat-panel__composer-tools">
                <el-tooltip
                  :content="thinkingEnabled ? '关闭深度思考' : '开启深度思考（让 AI 推理更深入）'"
                  placement="top"
                >
                  <button
                    type="button"
                    class="ai-chat-panel__chip"
                    :class="{ 'is-active': thinkingEnabled }"
                    :disabled="store.sending"
                    @click="thinkingEnabled = !thinkingEnabled"
                  >
                    <el-icon class="ai-chat-panel__chip-icon"><MagicStick /></el-icon>
                    <span>思考</span>
                  </button>
                </el-tooltip>
              </div>
              <div class="ai-chat-panel__composer-status">
                <span v-if="footerHint" class="ai-chat-panel__hint">{{ footerHint }}</span>
                <el-button
                  v-if="canCancelStreaming"
                  size="small"
                  round
                  @click="handleCancelStreaming"
                >
                  停止生成
                </el-button>
                <el-tooltip content="发送（Enter）" placement="top">
                  <button
                    type="button"
                    class="ai-chat-panel__send-btn"
                    :class="{ 'is-disabled': !canSend, 'is-loading': store.sending }"
                    :disabled="!canSend"
                    @click="handleSend"
                  >
                    <el-icon v-if="store.sending" class="is-spinning"><Loading /></el-icon>
                    <el-icon v-else><Top /></el-icon>
                  </button>
                </el-tooltip>
              </div>
            </div>
          </div>
          <div class="ai-chat-panel__footer-tip">
            内容由 AI 生成，关键操作请人工确认 ·
            <kbd>Enter</kbd>
            发送 ·
            <kbd>Shift</kbd>
            +
            <kbd>Enter</kbd>
            换行
          </div>
        </footer>
      </main>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * AI 助手主侧栏（千问风格双栏 + 分组 / 置顶 / 全文搜索 / 导出 / 快捷键）。
 *
 * 所属板块：aiAssistant。
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Close,
  Delete,
  Download,
  EditPen,
  Folder,
  Loading,
  MagicStick,
  More,
  Plus,
  Search,
  Top,
} from "@element-plus/icons-vue";

import {
  cancelMessage,
  createGroup,
  deleteConversation,
  deleteGroup,
  listConversations,
  listGroups,
  listMessages,
  moveConversationToGroup,
  pinConversation,
  renameConversation,
  renameGroup,
  searchConversations,
  startChat,
} from "@/api/aiAssistant/aiChat";
import { useAiChatStream, type SubscribeHandle } from "@/composables/aiAssistant/useAiChatStream";
import { groupConversationsByDate } from "@/composables/aiAssistant/useConversationGroups";
import { exportConversationAsMarkdown } from "@/composables/aiAssistant/useExportConversation";
import { useKeyboardShortcuts } from "@/composables/aiAssistant/useKeyboardShortcuts";
import { useAiAssistantStore } from "@/store/modules/ai-assistant-store";
import ConversationItem from "@/components/AiAssistant/ConversationItem.vue";
import MessageItem from "@/components/AiAssistant/MessageItem.vue";
import type {
  AiConversation,
  AiConversationGroup,
  AiMessage,
  AiSearchHit,
  PlanConfirmPayload,
  PlanProposal,
} from "@/types/aiAssistant/planSchema";

const store = useAiAssistantStore();

const drawerVisible = computed<boolean>({
  get: () => store.panelOpen,
  set: (val) => store.setPanelOpen(val),
});

const searchKeyword = ref<string>("");
const searchHits = ref<AiSearchHit[]>([]);
const searchLoading = ref<boolean>(false);
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

const inputText = ref<string>("");
/** 是否启用"深度思考"模式（透传给 Dify 工作流变量 ``thinking_mode``） */
const thinkingEnabled = ref<boolean>(false);
const messages = ref<AiMessage[]>([]);
const messageListRef = ref<HTMLElement | null>(null);
const searchInputRef = ref<{ focus?: () => void } | null>(null);

let activeSubscription: SubscribeHandle | null = null;
const subscribingMessageId = ref<string | null>(null);

const isSearching = computed<boolean>(() => searchKeyword.value.trim().length > 0);

const modKeyLabel = computed<string>(() => {
  if (typeof navigator === "undefined") return "Ctrl";
  return /mac/i.test(navigator.platform) ? "⌘" : "Ctrl";
});

const canSend = computed<boolean>(() => inputText.value.trim().length > 0 && !store.sending);
const canCancelStreaming = computed<boolean>(() => subscribingMessageId.value !== null);

const footerHint = computed<string>(() => {
  if (store.sending) return "AI 正在思考…";
  if (subscribingMessageId.value !== null) return "AI 正在生成…";
  return "";
});

const currentConversationTitle = computed<string>(() => {
  if (store.activeConversationId === null) return "新对话";
  const conv = store.conversations.find((c) => c.id === store.activeConversationId);
  return conv?.title || "新对话";
});

/** 已置顶会话（跨分组聚合到顶部，按 pinned_at 倒序） */
const pinnedConversations = computed<AiConversation[]>(() =>
  store.conversations
    .filter((c) => c.is_pinned)
    .slice()
    .sort((a, b) => (b.pinned_at || "").localeCompare(a.pinned_at || ""))
);

/** 按 group_id 索引会话（仅未置顶会话进入分组桶） */
const conversationsByGroup = computed<Record<string, AiConversation[]>>(() => {
  const map: Record<string, AiConversation[]> = {};
  for (const conv of store.conversations) {
    if (conv.is_pinned) continue;
    if (!conv.group_id) continue;
    (map[conv.group_id] = map[conv.group_id] || []).push(conv);
  }
  return map;
});

/** 未分组且未置顶的会话，按日期分组 */
const dateGroupsForUngrouped = computed(() => {
  const ungrouped = store.conversations.filter((c) => !c.is_pinned && !c.group_id);
  return groupConversationsByDate(ungrouped);
});

/** 当前消息列表中"最新一条 plan 消息"的 ID，仅它允许交互 */
const latestPlanMessageId = computed<string | null>(() => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    if (messages.value[i].message_type === "plan") return messages.value[i].id;
  }
  return null;
});

watch(
  () => store.panelOpen,
  async (open) => {
    if (open) {
      await Promise.all([loadGroups(), loadConversations()]);
      await loadActiveMessages();
    }
  },
  { immediate: true }
);

watch(
  () => store.activeConversationId,
  async () => {
    abortSubscription();
    await loadActiveMessages();
  }
);

/** 搜索关键词变化时防抖 300ms 调后端搜索 */
watch(searchKeyword, (val) => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
  const trimmed = val.trim();
  if (!trimmed) {
    searchHits.value = [];
    searchLoading.value = false;
    return;
  }
  searchLoading.value = true;
  searchDebounceTimer = setTimeout(async () => {
    try {
      const resp = await searchConversations(trimmed);
      searchHits.value = resp.items;
    } catch {
      searchHits.value = [];
    } finally {
      searchLoading.value = false;
    }
  }, 300);
});

useKeyboardShortcuts(
  {
    onFocusSearch: () => {
      searchInputRef.value?.focus?.();
    },
    onNewConversation: () => {
      handleNewConversation();
    },
    onEscape: () => {
      store.setPanelOpen(false);
    },
  },
  () => store.panelOpen
);

onMounted(async () => {
  if (store.panelOpen) {
    await Promise.all([loadGroups(), loadConversations()]);
    await loadActiveMessages();
  }
});

onBeforeUnmount(() => {
  abortSubscription();
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer);
});

/* ── 加载逻辑 ─────────────────────────────────────────── */

async function loadConversations(): Promise<void> {
  try {
    const resp = await listConversations();
    store.setConversations(resp.items);
    if (store.activeConversationId === null && resp.items.length > 0) {
      store.setActiveConversation(resp.items[0].id);
    }
  } catch {
    ElMessage.error("加载会话列表失败");
  }
}

async function loadGroups(): Promise<void> {
  try {
    const resp = await listGroups();
    store.setGroups(resp.items);
  } catch {
    // 分组失败不影响对话核心功能，静默
  }
}

async function loadActiveMessages(): Promise<void> {
  if (store.activeConversationId === null) {
    messages.value = [];
    return;
  }
  try {
    const resp = await listMessages(store.activeConversationId);
    messages.value = resp.items;
    scrollToBottom();
    const last = messages.value[messages.value.length - 1];
    if (
      last &&
      last.role === "assistant" &&
      (last.status === "pending" || last.status === "streaming")
    ) {
      subscribeMessage(last.id);
    }
  } catch {
    ElMessage.error("加载消息失败");
  }
}

/* ── 发送 / 订阅 ──────────────────────────────────────── */

async function handleSend(): Promise<void> {
  if (!canSend.value) return;
  const query = inputText.value.trim();
  inputText.value = "";
  store.setSending(true);

  try {
    const resp = await startChat({
      query,
      conversation_id: store.activeConversationId ?? undefined,
      inputs: { thinking_mode: thinkingEnabled.value ? "on" : "off" },
    });

    const isNewConversation = store.activeConversationId === null;
    store.setActiveConversation(resp.conversation_id);

    const now = new Date().toISOString();
    messages.value.push(
      buildLocalUserMessage(resp.user_message_id, resp.conversation_id, query, now)
    );
    messages.value.push(
      buildLocalAssistantPlaceholder(resp.assistant_message_id, resp.conversation_id, now)
    );

    if (isNewConversation) {
      await loadConversations();
    }

    scrollToBottom();
    subscribeMessage(resp.assistant_message_id);
  } catch {
    ElMessage.error("发送失败，请稍后重试");
  } finally {
    store.setSending(false);
  }
}

function subscribeMessage(messageId: string): void {
  abortSubscription();
  subscribingMessageId.value = messageId;

  activeSubscription = useAiChatStream(messageId, {
    onToken: ({ text, replay }) => {
      const target = findMessage(messageId);
      if (!target) return;
      if (replay) target.content = text;
      else target.content = (target.content || "") + text;
      target.status = "streaming";
      scrollToBottom();
    },
    onPlan: (plan: PlanProposal) => {
      const target = findMessage(messageId);
      if (!target) return;
      target.message_type = "plan";
      target.message_type_label = "计划提案";
      target.raw_plan_json = plan;
    },
    onMessageMeta: () => {},
    onError: (err) => {
      const target = findMessage(messageId);
      if (target) {
        target.status = "failed";
        target.error_msg = err.message;
      }
      ElMessage.error(`AI 出错：${err.message}`);
    },
    onDone: ({ cancelled, final_status }) => {
      const target = findMessage(messageId);
      if (target && target.status !== "failed") {
        target.status = cancelled ? "cancelled" : final_status === "failed" ? "failed" : "done";
      }
      subscribingMessageId.value = null;
      activeSubscription = null;
    },
    onNetworkError: (err) => {
      ElMessage.warning(`连接中断，刷新页面可重新订阅：${err.message}`);
      subscribingMessageId.value = null;
      activeSubscription = null;
    },
  });
}

function abortSubscription(): void {
  if (activeSubscription) {
    activeSubscription.abort();
    activeSubscription = null;
  }
  subscribingMessageId.value = null;
}

async function handleCancelStreaming(): Promise<void> {
  if (subscribingMessageId.value === null) return;
  const id = subscribingMessageId.value;
  try {
    await cancelMessage(id);
  } catch {
    /* 静默 */
  }
}

/* ── 会话操作 ─────────────────────────────────────────── */

function handleSelectConversation(id: string): void {
  store.setActiveConversation(id);
}

function handleNewConversation(): void {
  abortSubscription();
  store.setActiveConversation(null);
  messages.value = [];
  searchKeyword.value = "";
}

async function handleRenameConversation(conv: AiConversation): Promise<void> {
  let newTitle: string;
  try {
    const result = await ElMessageBox.prompt("请输入新的对话名称", "重命名", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      inputValue: conv.title || "",
      inputValidator: (val) => {
        if (!val || !val.trim()) return "标题不能为空";
        if (val.length > 200) return "标题不能超过 200 字";
        return true;
      },
    });
    newTitle = result.value.trim();
  } catch {
    return;
  }

  try {
    await renameConversation(conv.id, newTitle);
    const target = store.conversations.find((c) => c.id === conv.id);
    if (target) target.title = newTitle;
    ElMessage.success("已重命名");
  } catch {
    ElMessage.error("重命名失败");
  }
}

async function handleDeleteConversation(id: string): Promise<void> {
  try {
    await ElMessageBox.confirm("确认删除该会话？所有消息将被清空。", "提示", {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteConversation(id);
    store.removeConversation(id);
    if (store.activeConversationId === id) {
      store.setActiveConversation(null);
      messages.value = [];
    }
    ElMessage.success("已删除");
  } catch {
    ElMessage.error("删除失败");
  }
}

async function handlePinConversation(conv: AiConversation): Promise<void> {
  const targetState = !conv.is_pinned;
  try {
    await pinConversation(conv.id, targetState);
    const local = store.conversations.find((c) => c.id === conv.id);
    if (local) {
      local.is_pinned = targetState;
      local.pinned_at = targetState ? new Date().toISOString() : null;
    }
    ElMessage.success(targetState ? "已置顶" : "已取消置顶");
  } catch {
    ElMessage.error("操作失败");
  }
}

async function handleMoveConversation(conv: AiConversation, groupId: string | null): Promise<void> {
  try {
    await moveConversationToGroup(conv.id, groupId);
    const local = store.conversations.find((c) => c.id === conv.id);
    if (local) local.group_id = groupId;
    ElMessage.success(groupId ? "已移到分组" : "已移出分组");
  } catch {
    ElMessage.error("移动失败");
  }
}

async function handleExportConversation(conv: AiConversation): Promise<void> {
  try {
    const resp = await listMessages(conv.id);
    exportConversationAsMarkdown(conv, resp.items);
    ElMessage.success("已导出");
  } catch {
    ElMessage.error("导出失败");
  }
}

function handleExportCurrentConversation(): void {
  if (store.activeConversationId === null) return;
  const conv = store.conversations.find((c) => c.id === store.activeConversationId);
  if (!conv) return;
  exportConversationAsMarkdown(conv, messages.value);
  ElMessage.success("已导出");
}

/* ── 分组操作 ─────────────────────────────────────────── */

async function handleCreateGroup(): Promise<void> {
  let name: string;
  try {
    const result = await ElMessageBox.prompt("请输入分组名称", "新建分组", {
      confirmButtonText: "创建",
      cancelButtonText: "取消",
      inputValidator: (val) => {
        if (!val || !val.trim()) return "名称不能为空";
        if (val.length > 80) return "名称不能超过 80 字";
        return true;
      },
    });
    name = result.value.trim();
  } catch {
    return;
  }

  try {
    const group = await createGroup(name);
    store.appendGroup(group);
    ElMessage.success("已创建分组");
  } catch (err: unknown) {
    const msg = (err as { message?: string })?.message || "创建失败";
    ElMessage.error(msg);
  }
}

async function handleGroupCommand(command: string, group: AiConversationGroup): Promise<void> {
  if (command === "rename") {
    await handleRenameGroup(group);
  } else if (command === "delete") {
    await handleDeleteGroup(group);
  }
}

async function handleRenameGroup(group: AiConversationGroup): Promise<void> {
  let newName: string;
  try {
    const result = await ElMessageBox.prompt("请输入新的分组名称", "重命名分组", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      inputValue: group.name,
      inputValidator: (val) => {
        if (!val || !val.trim()) return "名称不能为空";
        if (val.length > 80) return "名称不能超过 80 字";
        return true;
      },
    });
    newName = result.value.trim();
  } catch {
    return;
  }

  try {
    const updated = await renameGroup(group.id, newName);
    store.patchGroup(updated);
    ElMessage.success("已重命名");
  } catch {
    ElMessage.error("重命名失败");
  }
}

async function handleDeleteGroup(group: AiConversationGroup): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除分组「${group.name}」？分组内的对话会变成未分组。`,
      "提示",
      {
        type: "warning",
      }
    );
  } catch {
    return;
  }
  try {
    await deleteGroup(group.id);
    store.removeGroup(group.id);
    ElMessage.success("已删除分组");
  } catch {
    ElMessage.error("删除失败");
  }
}

/* ── Plan 卡片 ────────────────────────────────────────── */

function handlePlanConfirm(message: AiMessage, payload: PlanConfirmPayload): void {
  console.info("[AiAssistant] Plan confirmed", {
    message_id: message.id,
    payload,
    target: message.raw_plan_json?.confirm_action,
  });
  ElMessage.success("已记录确认动作（业务端点接入后将触发真实执行）");
}

function handlePlanCancel(message: AiMessage): void {
  console.info("[AiAssistant] Plan cancelled", { message_id: message.id });
  ElMessage.info("已取消该方案");
}

/* ── 工具函数 ─────────────────────────────────────────── */

function scrollToBottom(): void {
  void nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

function findMessage(id: string): AiMessage | null {
  return messages.value.find((m) => m.id === id) ?? null;
}

/**
 * 把搜索关键词在文本中高亮（< mark > 标签）。
 * 已经过 DOMPurify 风格的简单转义防 XSS。
 */
function highlightKeyword(text: string, keyword: string): string {
  if (!text) return "";
  const escapeHtml = (s: string): string =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const safeText = escapeHtml(text);
  const trimmed = keyword.trim();
  if (!trimmed) return safeText;
  const safeKeyword = escapeHtml(trimmed).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return safeText.replace(new RegExp(safeKeyword, "gi"), (m) => `<mark>${m}</mark>`);
}

function buildLocalUserMessage(
  id: string,
  conversationId: string,
  content: string,
  createdAt: string
): AiMessage {
  return {
    id,
    conversation_id: conversationId,
    role: "user",
    role_label: "用户",
    message_type: "text",
    message_type_label: "文本",
    status: "done",
    status_label: "已完成",
    content,
    raw_plan_json: null,
    error_msg: "",
    created_at: createdAt,
    updated_at: createdAt,
  };
}

function buildLocalAssistantPlaceholder(
  id: string,
  conversationId: string,
  createdAt: string
): AiMessage {
  return {
    id,
    conversation_id: conversationId,
    role: "assistant",
    role_label: "AI 助手",
    message_type: "text",
    message_type_label: "文本",
    status: "pending",
    status_label: "待处理",
    content: "",
    raw_plan_json: null,
    error_msg: "",
    created_at: createdAt,
    updated_at: createdAt,
  };
}
</script>

<style scoped lang="scss">
.ai-chat-panel {
  &__layout {
    display: flex;
    height: 100%;
    background: var(--el-bg-color);
  }

  /* ── 左侧栏 ─────────────────────────────────────────── */
  &__sidebar {
    display: flex;
    flex-shrink: 0;
    flex-direction: column;
    width: 280px;
    background: var(--el-fill-color-extra-light, #fafafa);
    border-right: 1px solid var(--el-border-color-light);
  }

  &__sidebar-header {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    height: 52px;
    padding: 0 16px;
    border-bottom: 1px solid var(--el-border-color-lighter);
  }

  &__brand {
    display: flex;
    gap: 8px;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
  }

  &__brand-icon {
    font-size: 20px;
    color: #1e293b;
  }

  &__sidebar-body {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    padding: 12px;
  }

  &__new-btn {
    position: relative;
    width: 100%;
    height: 36px;
    margin-bottom: 12px;
    font-weight: 500;
  }

  &__shortcut-hint {
    padding: 1px 6px;
    margin-left: 8px;
    font-size: 11px;
    font-weight: 400;
    line-height: 1.4;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 4px;
  }

  &__search {
    margin-bottom: 12px;

    :deep(.el-input__wrapper) {
      border-radius: 8px;
    }
  }

  &__groups-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 4px;
    margin: 4px 0 6px;
  }

  &__groups-title {
    font-size: 12px;
    font-weight: 500;
    color: var(--el-text-color-secondary);
  }

  &__history {
    flex: 1;
    padding: 0 8px;
    margin: 0 -8px;
    overflow-y: auto;

    &::-webkit-scrollbar {
      width: 6px;
    }
    &::-webkit-scrollbar-thumb {
      background: var(--el-border-color);
      border-radius: 3px;
    }
    &::-webkit-scrollbar-thumb:hover {
      background: var(--el-border-color-darker);
    }
  }

  &__group {
    margin-bottom: 12px;
  }

  &__group-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__group-menu {
    visibility: hidden;
  }

  &__group-label {
    display: flex;
    gap: 6px;
    align-items: center;
    padding: 4px 8px;
    margin-bottom: 4px;
    font-size: 12px;
    font-weight: 500;
    color: var(--el-text-color-secondary);

    &.is-clickable:hover {
      cursor: default;
      background: var(--el-fill-color);
      border-radius: 6px;

      .ai-chat-panel__group-menu {
        visibility: visible;
      }
    }
  }

  &__group-empty {
    padding: 4px 12px;
    font-size: 12px;
    font-style: italic;
    color: var(--el-text-color-placeholder);
  }

  &__empty-hint {
    padding: 24px 0;
    font-size: 13px;
    color: var(--el-text-color-placeholder);
    text-align: center;
  }

  &__search-loading {
    display: flex;
    gap: 6px;
    align-items: center;
    justify-content: center;
    padding: 16px 0;
    font-size: 13px;
    color: var(--el-text-color-secondary);

    .is-loading {
      animation: rotating 1.5s linear infinite;
    }
  }

  /* 搜索命中项 */
  &__history-item.is-search-hit {
    align-items: flex-start;
    padding: 8px 10px;
  }

  &__hit {
    flex: 1;
    min-width: 0;
  }

  &__hit-title {
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 13.5px;
    font-weight: 500;
    color: var(--el-text-color-primary);
    white-space: nowrap;
  }

  &__hit-snippet {
    display: flex;
    gap: 6px;
    align-items: center;
    margin-top: 4px;
    font-size: 12px;
    color: var(--el-text-color-secondary);

    span {
      display: -webkit-box;
      overflow: hidden;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      -webkit-box-orient: vertical;
      line-height: 1.5;
    }

    :deep(mark) {
      padding: 0 2px;
      color: #1e293b;
      background: rgba(15, 23, 42, 0.12);
      border-radius: 2px;
    }
  }

  /* ── 右侧主区 ───────────────────────────────────────── */
  &__main {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
  }

  &__main-header {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: space-between;
    height: 60px;
    padding: 0 24px;
    border-bottom: 1px solid var(--el-border-color-light);
  }

  &__main-title {
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 17px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    letter-spacing: 0.2px;
    white-space: nowrap;
  }

  &__main-actions {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  &__messages {
    flex: 1;
    padding: 12px 0;
    overflow-y: auto;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 0 24px;
    text-align: center;
  }

  &__empty-logo {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    font-size: 32px;
    color: #fff;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
  }

  &__empty-title {
    margin: 0 0 4px;
    font-size: 18px;
    font-weight: 600;
  }

  &__empty-desc {
    margin: 0 0 16px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  &__empty-shortcut {
    margin: 0;
    font-size: 12px;
    color: var(--el-text-color-placeholder);

    kbd {
      display: inline-block;
      padding: 1px 6px;
      margin: 0 2px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 11px;
      background: var(--el-fill-color);
      border: 1px solid var(--el-border-color);
      border-radius: 4px;
    }
  }

  &__footer {
    flex-shrink: 0;
    padding: 12px 24px 18px;
  }

  &__composer {
    padding: 14px 16px 10px;
    background: var(--el-bg-color);
    border: 1px solid var(--el-border-color);
    border-radius: 16px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition:
      border-color 0.18s,
      box-shadow 0.18s;

    &:focus-within {
      border-color: var(--el-text-color-primary);
      box-shadow:
        0 0 0 3px rgba(15, 23, 42, 0.06),
        0 2px 8px rgba(15, 23, 42, 0.06);
    }
  }

  &__composer-input {
    /* 干掉 el-input/textarea 内部所有边框、shadow，让外层 composer 唯一显示边框 */
    :deep(.el-textarea) {
      background: transparent;
    }

    :deep(.el-textarea__inner) {
      padding: 0;
      font-size: 14.5px;
      line-height: 1.65;
      color: var(--el-text-color-primary);
      resize: none;
      background: transparent;
      border: none;
      border-radius: 0;
      box-shadow: none !important;
      transition: none;

      &::placeholder {
        color: var(--el-text-color-placeholder);
      }

      &:hover,
      &:focus {
        background: transparent;
        border: none;
        box-shadow: none !important;
      }
    }
  }

  &__composer-toolbar {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
  }

  &__composer-tools {
    display: flex;
    gap: 6px;
    align-items: center;
  }

  &__composer-status {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__chip-icon {
    font-size: 13px;
  }

  /* 思考 / 后续工具按钮（chip 风格）*/
  &__chip {
    display: inline-flex;
    gap: 4px;
    align-items: center;
    height: 28px;
    padding: 0 12px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--el-text-color-regular);
    cursor: pointer;
    user-select: none;
    background: var(--el-bg-color);
    border: 1px solid var(--el-border-color);
    border-radius: 14px;
    transition: all 0.18s;

    &:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }

    &:hover:not(:disabled) {
      color: var(--el-text-color-primary);
      background: var(--el-fill-color);
      border-color: var(--el-border-color-darker);
    }

    &.is-active {
      color: #fff;
      background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
      border-color: transparent;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);

      .ai-chat-panel__chip-icon {
        color: #fff;
      }
    }
  }

  /* 圆形发送按钮 */
  &__send-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    padding: 0;
    font-size: 16px;
    color: #fff;
    cursor: pointer;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border: none;
    border-radius: 50%;
    box-shadow: 0 4px 14px rgba(15, 23, 42, 0.22);
    transition:
      transform 0.15s,
      box-shadow 0.15s,
      opacity 0.15s;

    &:active:not(.is-disabled) {
      transform: translateY(0) scale(0.96);
    }

    &:hover:not(.is-disabled):not(.is-loading) {
      box-shadow: 0 6px 18px rgba(15, 23, 42, 0.3);
      transform: translateY(-1px) scale(1.04);
    }

    &.is-disabled {
      color: var(--el-text-color-placeholder);
      cursor: not-allowed;
      background: var(--el-fill-color-darker);
      box-shadow: none;
    }

    &.is-loading {
      cursor: wait;
    }

    .is-spinning {
      animation: rotating 1s linear infinite;
    }
  }

  &__hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }

  &__footer-tip {
    margin-top: 10px;
    font-size: 11px;
    color: var(--el-text-color-placeholder);
    text-align: center;

    kbd {
      display: inline-block;
      padding: 1px 5px;
      margin: 0 2px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 10.5px;
      background: var(--el-fill-color);
      border: 1px solid var(--el-border-color);
      border-radius: 3px;
    }
  }
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
