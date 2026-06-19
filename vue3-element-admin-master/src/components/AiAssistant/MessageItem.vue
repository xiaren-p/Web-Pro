<template>
  <div class="message-item" :class="messageClass">
    <!-- AI 助手：左侧头像 + 左对齐内容 -->
    <template v-if="isAssistant">
      <div class="message-item__avatar message-item__avatar--ai">
        <el-icon><MagicStick /></el-icon>
      </div>

      <div class="message-item__body">
        <PlanCard
          v-if="isPlan && message.raw_plan_json"
          :plan="message.raw_plan_json"
          :readonly="planReadonly"
          @confirm="handlePlanConfirm"
          @cancel="handlePlanCancel"
        />

        <template v-else>
          <!-- 深度思考折叠块 -->
          <div v-if="parsedContent.thinking" class="message-item__thinking">
            <button
              type="button"
              class="message-item__thinking-toggle"
              @click="thinkingExpanded = !thinkingExpanded"
            >
              <el-icon class="message-item__thinking-icon"><MagicStick /></el-icon>
              <span>{{ thinkingTitle }}</span>
              <el-icon
                class="message-item__thinking-arrow"
                :class="{ 'is-expanded': thinkingExpanded }"
              >
                <ArrowDown />
              </el-icon>
            </button>
            <div v-show="thinkingExpanded" class="message-item__thinking-body">
              <div
                class="message-item__thinking-markdown"
                v-html="renderAiMarkdown(parsedContent.thinking)"
              />
            </div>
          </div>

          <!-- 正式答案 -->
          <div
            v-if="parsedContent.answer"
            class="message-item__markdown"
            v-html="renderAiMarkdown(parsedContent.answer)"
          />
        </template>

        <div v-if="isStreaming" class="message-item__indicator">
          <span class="message-item__dot" />
          <span class="message-item__dot" />
          <span class="message-item__dot" />
        </div>

        <div v-if="message.status === 'failed'" class="message-item__error">
          生成失败：{{ message.error_msg || "未知错误" }}
        </div>

        <div v-else-if="message.status === 'cancelled'" class="message-item__cancelled">已取消</div>
      </div>
    </template>

    <!-- 用户消息：右对齐气泡 + 真实头像 -->
    <template v-else>
      <div class="message-item__body message-item__body--user">
        <div class="message-item__bubble">
          <div
            v-if="userBubbleHtml"
            class="message-item__bubble-markdown"
            v-html="userBubbleHtml"
          />
          <span v-else class="message-item__bubble-empty">…</span>
        </div>
      </div>
      <div class="message-item__avatar message-item__avatar--user">
        <img
          v-if="userAvatarSrc"
          class="message-item__avatar-img"
          :src="userAvatarSrc"
          :alt="userStore.userInfo.username"
        />
        <el-icon v-else><User /></el-icon>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
/**
 * 单条对话消息渲染。
 *
 * 视觉规则：
 *   - 用户消息：右对齐气泡，浅蓝背景，头像在最右
 *   - AI 消息：左对齐文档流，AI 品牌渐变魔法棒头像在最左
 *   - Plan 提案：用 PlanCard 卡片渲染（替换文本）
 *
 * 内容解析：
 *   - 自动识别 ``<think>...</think>`` 标签，渲染为可折叠"深度思考"块
 *   - 标签外的剩余文本作为正式答案，走 markdown + DOMPurify
 *
 * 所属板块：aiAssistant。
 */

import { computed, ref } from "vue";
import { ArrowDown, MagicStick, User } from "@element-plus/icons-vue";
import { renderAiMarkdown } from "@/utils/markdown";
import { resolveAvatarSrc } from "@/utils/avatarPresets";
import { useUserStore } from "@/store";
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

const userStore = useUserStore();

/** 用户头像 URL（已规范化）；为空时显示默认 User 图标 */
const userAvatarSrc = computed<string>(
  () => resolveAvatarSrc(userStore.userInfo.avatar ?? "") || ""
);

/** 用户消息渲染为 Markdown HTML（同样经 DOMPurify 清洗） */
const userBubbleHtml = computed<string>(() => renderAiMarkdown(props.message.content || ""));

/** 思考块默认折叠；用户主动展开后保持当前展开状态 */
const thinkingExpanded = ref<boolean>(false);

/**
 * 把内容拆分为 ``thinking``（思考过程）与 ``answer``（最终答案）两部分。
 *
 * 解析规则：
 *   - 提取首个 ``<think>...</think>`` 标签内的文本作为 thinking
 *   - 剩余部分作为 answer
 *   - 流式输出过程中可能只看到 ``<think>`` 没看到 ``</think>``：
 *     此时把 ``<think>`` 之后的所有文本暂时归到 thinking，answer 为空
 *
 * @returns thinking 与 answer 字符串对象
 */
const parsedContent = computed<{ thinking: string; answer: string }>(() => {
  const raw = props.message.content || "";
  const startTag = "<think>";
  const endTag = "</think>";

  const startIdx = raw.indexOf(startTag);
  if (startIdx === -1) {
    return { thinking: "", answer: raw };
  }

  const endIdx = raw.indexOf(endTag, startIdx + startTag.length);
  // 流式中：<think> 已到、</think> 未到
  if (endIdx === -1) {
    const before = raw.slice(0, startIdx).trim();
    const thinking = raw.slice(startIdx + startTag.length).trim();
    return {
      thinking,
      answer: before,
    };
  }

  // 完整闭合：把 think 之外的部分拼成 answer
  const before = raw.slice(0, startIdx);
  const thinking = raw.slice(startIdx + startTag.length, endIdx).trim();
  const after = raw.slice(endIdx + endTag.length);
  const answer = (before + after).trim();
  return { thinking, answer };
});

/**
 * 思考块标题：流式中显示"思考中"，结束后显示"已深度思考"。
 */
const thinkingTitle = computed<string>(() => {
  if (!parsedContent.value.answer && isStreaming.value) return "思考中…";
  return "已深度思考";
});

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
  align-items: flex-start;
  padding: 14px 24px;

  /* AI 头像：品牌渐变 */
  &__avatar {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    overflow: hidden;
    font-size: 16px;
    color: #fff;
    border-radius: 10px;

    &--ai {
      background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);
    }

    &--user {
      color: var(--el-text-color-regular);
      background: var(--el-fill-color-darker);
      border-radius: 50%;
      box-shadow:
        0 0 0 2px var(--el-bg-color),
        0 2px 6px rgba(0, 0, 0, 0.08);
    }
  }

  &__avatar-img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  /* 用户消息：整体反向布局，头像在右 */
  &--user {
    flex-direction: row-reverse;
  }

  &__body {
    flex: 1;
    min-width: 0;
    line-height: 1.7;

    &--user {
      display: flex;
      flex: 0 1 auto;
      justify-content: flex-end;
      max-width: 76%;
    }
  }

  /* 用户气泡（主流风格：渐变背景 + 大圆角 + 软阴影） */
  &__bubble {
    position: relative;
    padding: 10px 14px;
    font-size: 14.5px;
    line-height: 1.65;
    color: #fff;
    overflow-wrap: break-word;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-radius: 18px 18px 4px 18px;
    box-shadow:
      0 4px 12px rgba(15, 23, 42, 0.16),
      0 1px 2px rgba(15, 23, 42, 0.1);
  }

  &__bubble-empty {
    opacity: 0.6;
  }

  /* 气泡内 markdown 渲染（白底字色，链接 / 代码块加白色友好版） */
  &__bubble-markdown {
    :deep(p) {
      margin: 4px 0;
    }

    :deep(p:first-child) {
      margin-top: 0;
    }

    :deep(p:last-child) {
      margin-bottom: 0;
    }

    :deep(strong) {
      font-weight: 600;
      color: #fff;
    }

    :deep(em) {
      color: rgba(255, 255, 255, 0.95);
    }

    :deep(a) {
      color: #fff;
      text-decoration: underline;
      text-decoration-color: rgba(255, 255, 255, 0.5);
      text-underline-offset: 2px;

      &:hover {
        text-decoration-color: #fff;
      }
    }

    :deep(code) {
      padding: 1px 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.9em;
      color: #fff;
      background: rgba(255, 255, 255, 0.18);
      border-radius: 4px;
    }

    :deep(pre) {
      padding: 10px 12px;
      margin: 6px 0;
      overflow-x: auto;
      font-size: 12.5px;
      background: rgba(0, 0, 0, 0.22);
      border-radius: 8px;

      code {
        padding: 0;
        color: #fff;
        background: transparent;
      }
    }

    :deep(ul),
    :deep(ol) {
      padding-left: 20px;
      margin: 4px 0;
    }

    :deep(li) {
      margin: 2px 0;
    }

    :deep(blockquote) {
      padding: 4px 12px;
      margin: 6px 0;
      color: rgba(255, 255, 255, 0.92);
      background: rgba(255, 255, 255, 0.08);
      border-left: 3px solid rgba(255, 255, 255, 0.45);
      border-radius: 4px;
    }

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin: 8px 0 4px;
      font-weight: 600;
      color: #fff;
    }

    :deep(h1) {
      font-size: 1.2em;
    }

    :deep(h2) {
      font-size: 1.1em;
    }

    :deep(h3) {
      font-size: 1.05em;
    }

    :deep(table) {
      margin: 6px 0;
      font-size: 13px;
      border-collapse: collapse;

      th,
      td {
        padding: 4px 8px;
        border: 1px solid rgba(255, 255, 255, 0.25);
      }

      th {
        font-weight: 600;
        background: rgba(255, 255, 255, 0.12);
      }
    }

    :deep(hr) {
      margin: 8px 0;
      border: none;
      border-top: 1px solid rgba(255, 255, 255, 0.2);
    }
  }

  /* 思考折叠块 */
  &__thinking {
    margin-bottom: 10px;
    overflow: hidden;
    background: rgba(15, 23, 42, 0.03);
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 12px;
  }

  &__thinking-toggle {
    display: flex;
    gap: 6px;
    align-items: center;
    width: 100%;
    padding: 8px 12px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--el-text-color-secondary);
    cursor: pointer;
    background: transparent;
    border: none;
    transition: background 0.15s;

    &:hover {
      background: rgba(15, 23, 42, 0.04);
    }
  }

  &__thinking-icon {
    font-size: 14px;
    color: #475569;
  }

  &__thinking-arrow {
    margin-left: auto;
    font-size: 14px;
    transition: transform 0.2s;

    &.is-expanded {
      transform: rotate(180deg);
    }
  }

  &__thinking-body {
    padding: 4px 14px 12px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    border-top: 1px dashed var(--el-border-color-lighter);
  }

  &__thinking-markdown {
    line-height: 1.7;

    :deep(p) {
      margin: 4px 0;
    }

    :deep(pre) {
      padding: 10px 12px;
      overflow-x: auto;
      font-size: 12.5px;
      background: rgba(0, 0, 0, 0.04);
      border-radius: 6px;
    }
  }

  /* 正式答案 markdown */
  &__markdown {
    font-size: 14.5px;
    color: var(--el-text-color-primary);
    overflow-wrap: break-word;

    :deep(pre) {
      padding: 12px;
      overflow-x: auto;
      font-size: 13px;
      background: var(--el-fill-color);
      border-radius: 6px;
    }

    :deep(code) {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }

    :deep(p) {
      margin: 6px 0;
    }

    :deep(p:first-child) {
      margin-top: 0;
    }

    :deep(p:last-child) {
      margin-bottom: 0;
    }

    :deep(h1),
    :deep(h2),
    :deep(h3) {
      margin: 14px 0 8px;
      font-weight: 600;
    }

    :deep(ul),
    :deep(ol) {
      padding-left: 20px;
      margin: 6px 0;
    }
  }

  &__indicator {
    display: flex;
    gap: 4px;
    align-items: center;
    height: 16px;
    margin-top: 8px;
  }

  &__dot {
    width: 6px;
    height: 6px;
    background: linear-gradient(135deg, #1e293b, #475569);
    border-radius: 50%;
    animation: ai-pulse 1.2s infinite ease-in-out;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }

    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }

  &__error {
    margin-top: 6px;
    font-size: 13px;
    color: var(--el-color-danger);
  }

  &__cancelled {
    margin-top: 6px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
}

@keyframes ai-pulse {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}
</style>
