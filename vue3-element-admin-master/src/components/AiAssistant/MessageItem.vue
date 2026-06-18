<template>
  <div class="message-item" :class="messageClass">
    <div class="message-item__avatar">
      <el-icon v-if="isAssistant"><MagicStick /></el-icon>
      <el-icon v-else><User /></el-icon>
    </div>

    <div class="message-item__body">
      <PlanCard
        v-if="isPlan && message.raw_plan_json"
        :plan="message.raw_plan_json"
        :readonly="planReadonly"
        @confirm="handlePlanConfirm"
        @cancel="handlePlanCancel"
      />

      <div
        v-else-if="message.content"
        class="message-item__markdown"
        v-html="renderedHtml"
      />

      <div v-if="isStreaming" class="message-item__indicator">
        <span class="message-item__dot" />
        <span class="message-item__dot" />
        <span class="message-item__dot" />
      </div>

      <div v-if="message.status === 'failed'" class="message-item__error">
        生成失败：{{ message.error_msg || "未知错误" }}
      </div>

      <div v-else-if="message.status === 'cancelled'" class="message-item__cancelled">
        已取消
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单条对话消息渲染。
 *
 * 根据 message.message_type 自动切换：
 *   - text → markdown 渲染（经 DOMPurify 清洗后 v-html）
 *   - plan → PlanCard 卡片
 * 流式生成中（status=streaming）追加跳动指示器；失败 / 取消时显示状态行。
 *
 * 所属板块：aiAssistant。
 */

import { computed } from "vue";
import { MagicStick, User } from "@element-plus/icons-vue";
import { renderAiMarkdown } from "@/utils/markdown";
import PlanCard from "@/components/AiAssistant/PlanCard.vue";
import type { AiMessage, PlanConfirmPayload } from "@/types/aiAssistant/planSchema";

const props = defineProps<{
  message: AiMessage;
  /** 当 plan 已被确认或会话已结束时禁止再交互 */
  planReadonly?: boolean;
}>();

const emit = defineEmits<{
  (e: "plan-confirm", message: AiMessage, payload: PlanConfirmPayload): void;
  (e: "plan-cancel", message: AiMessage): void;
}>();

const isAssistant = computed<boolean>(() => props.message.role === "assistant");
const isStreaming = computed<boolean>(() => props.message.status === "streaming");
const isPlan = computed<boolean>(() => props.message.message_type === "plan");

const messageClass = computed<string>(() => `message-item--${props.message.role}`);

const renderedHtml = computed<string>(() => renderAiMarkdown(props.message.content));

function handlePlanConfirm(payload: PlanConfirmPayload): void {
  emit("plan-confirm", props.message, payload);
}

function handlePlanCancel(): void {
  emit("plan-cancel", props.message);
}
</script>

<style scoped lang="scss">
.message-item {
  display: flex;
  gap: 12px;
  padding: 12px 16px;

  &--user {
    background: var(--el-fill-color-light);
  }

  &__avatar {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    font-size: 16px;
  }

  &__body {
    flex: 1;
    min-width: 0;
    line-height: 1.6;
  }

  &__markdown {
    word-break: break-word;

    :deep(pre) {
      background: var(--el-fill-color);
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      font-size: 13px;
    }

    :deep(code) {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    :deep(p) {
      margin: 4px 0;
    }
  }

  &__indicator {
    display: flex;
    gap: 4px;
    margin-top: 8px;
    align-items: center;
    height: 16px;
  }

  &__dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--el-color-primary);
    animation: ai-pulse 1.2s infinite ease-in-out;

    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }

  &__error {
    color: var(--el-color-danger);
    font-size: 13px;
    margin-top: 6px;
  }

  &__cancelled {
    color: var(--el-text-color-secondary);
    font-size: 13px;
    margin-top: 6px;
  }
}

@keyframes ai-pulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}
</style>
