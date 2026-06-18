<template>
  <el-drawer
    v-model="drawerVisible"
    :size="480"
    :with-header="false"
    direction="rtl"
    :close-on-click-modal="false"
    class="ai-chat-panel"
  >
    <div class="ai-chat-panel__layout">
      <header class="ai-chat-panel__header">
        <div class="ai-chat-panel__title">
          <el-icon><MagicStick /></el-icon>
          <span>AI 助手</span>
        </div>
        <div class="ai-chat-panel__header-actions">
          <el-tooltip content="新建对话" placement="bottom">
            <el-button :icon="Plus" circle text @click="handleNewConversation" />
          </el-tooltip>
          <el-tooltip content="历史会话" placement="bottom">
            <el-button :icon="ChatLineRound" circle text @click="historyVisible = true" />
          </el-tooltip>
          <el-tooltip content="关闭" placement="bottom">
            <el-button :icon="Close" circle text @click="store.setPanelOpen(false)" />
          </el-tooltip>
        </div>
      </header>

      <section ref="messageListRef" class="ai-chat-panel__messages">
        <div v-if="messages.length === 0" class="ai-chat-panel__empty">
          <el-icon class="ai-chat-panel__empty-icon"><MagicStick /></el-icon>
          <p>开始对话，让 AI 帮你处理 ERP 任务</p>
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
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          :autosize="{ minRows: 2, maxRows: 6 }"
          placeholder="输入你的问题（Enter 发送，Shift+Enter 换行）"
          resize="none"
          :disabled="store.sending"
          @keydown.enter.exact.prevent="handleSend"
        />
        <div class="ai-chat-panel__footer-actions">
          <span class="ai-chat-panel__hint">{{ footerHint }}</span>
          <el-button
            v-if="canCancelStreaming"
            size="default"
            @click="handleCancelStreaming"
          >
            停止生成
          </el-button>
          <el-button
            type="primary"
            size="default"
            :disabled="!canSend"
            :loading="store.sending"
            @click="handleSend"
          >
            发送
          </el-button>
        </div>
      </footer>
    </div>

    <el-drawer
      v-model="historyVisible"
      title="历史会话"
      :size="320"
      direction="ltr"
      append-to-body
    >
      <div class="ai-chat-panel__history">
        <div
          v-for="conv in store.conversations"
          :key="conv.id"
          class="ai-chat-panel__history-item"
          :class="{ 'is-active': conv.id === store.activeConversationId }"
          @click="handleSelectConversation(conv.id)"
        >
          <div class="ai-chat-panel__history-title">{{ conv.title || "(无标题)" }}</div>
          <div class="ai-chat-panel__history-time">{{ conv.updated_at }}</div>
          <el-button
            class="ai-chat-panel__history-delete"
            :icon="Delete"
            size="small"
            text
            @click.stop="handleDeleteConversation(conv.id)"
          />
        </div>
        <el-empty v-if="store.conversations.length === 0" description="暂无历史会话" />
      </div>
    </el-drawer>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * AI 助手主侧栏。
 *
 * 核心交互模型：
 *   1. 侧栏打开 → 加载会话列表 + 自动选中最近活跃会话 + 拉历史消息
 *   2. 用户发送 → POST /chat/ 拿 assistant_message_id → 立即占位本地消息 → 订阅 SSE
 *   3. SSE 收到 token / plan / done → 累积到本地消息字段，UI 实时刷新
 *   4. 离开页面 / 刷新 → Celery 任务继续跑，回来后基于 message_id 重新订阅可补播
 *
 * 所属板块：aiAssistant。
 */

import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  ChatLineRound,
  Close,
  Delete,
  MagicStick,
  Plus,
} from "@element-plus/icons-vue";

import {
  cancelMessage,
  deleteConversation,
  listConversations,
  listMessages,
  startChat,
} from "@/api/aiAssistant/aiChat";
import {
  useAiChatStream,
  type SubscribeHandle,
} from "@/composables/aiAssistant/useAiChatStream";
import { useAiAssistantStore } from "@/store/modules/ai-assistant-store";
import MessageItem from "@/components/AiAssistant/MessageItem.vue";
import type {
  AiMessage,
  PlanConfirmPayload,
  PlanProposal,
} from "@/types/aiAssistant/planSchema";

const store = useAiAssistantStore();

const drawerVisible = computed<boolean>({
  get: () => store.panelOpen,
  set: (val) => store.setPanelOpen(val),
});

const historyVisible = ref<boolean>(false);
const inputText = ref<string>("");
const messages = ref<AiMessage[]>([]);
const messageListRef = ref<HTMLElement | null>(null);

/** 当前激活的 SSE 订阅句柄；切换会话 / 新发送 / 卸载时主动 abort */
let activeSubscription: SubscribeHandle | null = null;
/** 当前正在订阅的 assistant message id */
const subscribingMessageId = ref<number | null>(null);

const canSend = computed<boolean>(
  () => inputText.value.trim().length > 0 && !store.sending,
);

const canCancelStreaming = computed<boolean>(
  () => subscribingMessageId.value !== null,
);

const footerHint = computed<string>(() => {
  if (store.sending) return "AI 正在思考…";
  if (subscribingMessageId.value !== null) return "AI 正在生成…";
  return "";
});

/**
 * 找到当前消息列表中"最新一条 plan 消息"的 ID，仅它允许交互，历史 plan 一律只读。
 */
const latestPlanMessageId = computed<number | null>(() => {
  for (let i = messages.value.length - 1; i >= 0; i -= 1) {
    if (messages.value[i].message_type === "plan") return messages.value[i].id;
  }
  return null;
});

watch(
  () => store.panelOpen,
  async (open) => {
    if (open) {
      await loadConversations();
      await loadActiveMessages();
    }
  },
  { immediate: true },
);

watch(
  () => store.activeConversationId,
  async () => {
    abortSubscription();
    await loadActiveMessages();
  },
);

onMounted(async () => {
  if (store.panelOpen) {
    await loadConversations();
    await loadActiveMessages();
  }
});

onBeforeUnmount(() => {
  abortSubscription();
});

/**
 * 拉取会话列表。
 */
async function loadConversations(): Promise<void> {
  try {
    const resp = await listConversations();
    store.setConversations(resp.items);
    if (store.activeConversationId === null && resp.items.length > 0) {
      store.setActiveConversation(resp.items[0].id);
    }
  } catch (err) {
    ElMessage.error("加载会话列表失败");
  }
}

/**
 * 拉取当前激活会话的全部历史消息，并对仍在生成中的最后一条自动续订 SSE。
 */
async function loadActiveMessages(): Promise<void> {
  if (store.activeConversationId === null) {
    messages.value = [];
    return;
  }
  try {
    const resp = await listMessages(store.activeConversationId);
    messages.value = resp.items;
    scrollToBottom();

    // 续订：如果最后一条是 assistant 消息且仍在 pending/streaming，重新订阅 SSE
    const last = messages.value[messages.value.length - 1];
    if (last && last.role === "assistant" && (last.status === "pending" || last.status === "streaming")) {
      subscribeMessage(last.id);
    }
  } catch (err) {
    ElMessage.error("加载消息失败");
  }
}

/**
 * 处理用户发送：入队 → 占位本地消息 → 订阅 SSE。
 */
async function handleSend(): Promise<void> {
  if (!canSend.value) return;
  const query = inputText.value.trim();
  inputText.value = "";
  store.setSending(true);

  try {
    const resp = await startChat({
      query,
      conversation_id: store.activeConversationId ?? undefined,
    });

    const isNewConversation = store.activeConversationId === null;
    store.setActiveConversation(resp.conversation_id);

    // 本地占位消息（避免等历史接口刷新）
    const now = new Date().toISOString();
    messages.value.push(buildLocalUserMessage(resp.user_message_id, resp.conversation_id, query, now));
    messages.value.push(buildLocalAssistantPlaceholder(resp.assistant_message_id, resp.conversation_id, now));

    if (isNewConversation) {
      await loadConversations();
    }

    scrollToBottom();
    subscribeMessage(resp.assistant_message_id);
  } catch (err) {
    ElMessage.error("发送失败，请稍后重试");
  } finally {
    store.setSending(false);
  }
}

/**
 * 启动 SSE 订阅。
 *
 * @param messageId - 要订阅的 assistant 消息 ID
 */
function subscribeMessage(messageId: number): void {
  abortSubscription();
  subscribingMessageId.value = messageId;

  activeSubscription = useAiChatStream(messageId, {
    onToken: ({ text, replay }) => {
      const target = findMessage(messageId);
      if (!target) return;
      // 历史回放：用 replay 文本替换占位 content
      if (replay) {
        target.content = text;
      } else {
        target.content = (target.content || "") + text;
      }
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
    onMessageMeta: () => {
      // 当前未使用，保留以便日后扩展（如显示 conversation_id 等）
    },
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

/**
 * 中止当前订阅（不向后端发取消，仅断开本地连接）。
 */
function abortSubscription(): void {
  if (activeSubscription) {
    activeSubscription.abort();
    activeSubscription = null;
  }
  subscribingMessageId.value = null;
}

/**
 * 用户主动停止生成：调后端 cancel 接口（中止 Celery 任务）。
 */
async function handleCancelStreaming(): Promise<void> {
  if (subscribingMessageId.value === null) return;
  const id = subscribingMessageId.value;
  try {
    await cancelMessage(id);
  } catch {
    // 后端取消失败也无所谓，订阅会因 done 帧自然关闭
  }
}

/**
 * 切换激活会话。
 *
 * @param id - 目标会话 ID
 */
function handleSelectConversation(id: number): void {
  store.setActiveConversation(id);
  historyVisible.value = false;
}

/**
 * 删除会话（带二次确认）。
 *
 * @param id - 目标会话 ID
 */
async function handleDeleteConversation(id: number): Promise<void> {
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

/**
 * 新建会话：清空激活会话 ID 即可，发送时会自动新建。
 */
function handleNewConversation(): void {
  abortSubscription();
  store.setActiveConversation(null);
  messages.value = [];
}

/**
 * 用户在 Plan 卡片点击确认（本期不接业务端点，仅本地反馈 + 提示）。
 *
 * @param message - 源消息
 * @param payload - PlanCard 抛出的载荷
 */
function handlePlanConfirm(message: AiMessage, payload: PlanConfirmPayload): void {
  // TODO(后续接入业务端点): 根据 message.raw_plan_json.confirm_action.endpoint 调真实业务接口
  console.info("[AiAssistant] Plan confirmed", {
    message_id: message.id,
    payload,
    target: message.raw_plan_json?.confirm_action,
  });
  ElMessage.success("已记录确认动作（业务端点接入后将触发真实执行）");
}

/**
 * 用户在 Plan 卡片点击取消。
 *
 * @param message - 源消息
 */
function handlePlanCancel(message: AiMessage): void {
  console.info("[AiAssistant] Plan cancelled", { message_id: message.id });
  ElMessage.info("已取消该方案");
}

/**
 * 滚动消息列表到底部。
 */
function scrollToBottom(): void {
  void nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight;
    }
  });
}

/**
 * 在本地消息数组中查找指定 ID 的消息。
 *
 * @param id - 消息 ID
 * @returns 找到的引用或 null
 */
function findMessage(id: number): AiMessage | null {
  return messages.value.find((m) => m.id === id) ?? null;
}

/**
 * 构造本地占位的用户消息（在后端 listMessages 刷新前用）。
 *
 * @param id - 消息 ID
 * @param conversationId - 会话 ID
 * @param content - 文本内容
 * @param createdAt - 创建时间字符串
 * @returns 占位消息
 */
function buildLocalUserMessage(
  id: number,
  conversationId: number,
  content: string,
  createdAt: string,
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

/**
 * 构造本地占位的 AI 待生成消息。
 *
 * @param id - 消息 ID
 * @param conversationId - 会话 ID
 * @param createdAt - 创建时间字符串
 * @returns 占位消息
 */
function buildLocalAssistantPlaceholder(
  id: number,
  conversationId: number,
  createdAt: string,
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
    flex-direction: column;
    height: 100%;
  }

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-light);
    flex-shrink: 0;
  }

  &__title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 16px;
    font-weight: 600;
  }

  &__header-actions {
    display: flex;
    gap: 4px;
  }

  &__messages {
    flex: 1;
    overflow-y: auto;
    padding: 8px 0;
  }

  &__empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--el-text-color-secondary);
    font-size: 14px;

    p {
      margin-top: 12px;
    }
  }

  &__empty-icon {
    font-size: 48px;
    color: var(--el-color-primary-light-5);
  }

  &__footer {
    border-top: 1px solid var(--el-border-color-light);
    padding: 12px 16px;
    flex-shrink: 0;
  }

  &__footer-actions {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 8px;
    margin-top: 8px;
  }

  &__hint {
    color: var(--el-text-color-secondary);
    font-size: 12px;
    margin-right: auto;
  }

  &__history {
    padding: 8px;
  }

  &__history-item {
    position: relative;
    padding: 10px 36px 10px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: background 0.15s;
    margin-bottom: 4px;

    &:hover {
      background: var(--el-fill-color-light);
    }

    &.is-active {
      background: var(--el-color-primary-light-9);
    }
  }

  &__history-title {
    font-size: 14px;
    color: var(--el-text-color-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  &__history-time {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 2px;
  }

  &__history-delete {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
  }
}
</style>
