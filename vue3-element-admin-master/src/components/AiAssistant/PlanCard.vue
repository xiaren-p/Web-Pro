<template>
  <div class="plan-card">
    <div class="plan-card__header">
      <el-icon class="plan-card__icon"><MagicStick /></el-icon>
      <span class="plan-card__title">{{ plan.title }}</span>
    </div>

    <div v-if="plan.description" class="plan-card__desc">
      {{ plan.description }}
    </div>

    <div class="plan-card__options">
      <el-checkbox-group v-if="plan.multi_select" v-model="selectedKeys" :disabled="readonly">
        <el-checkbox
          v-for="opt in plan.options"
          :key="opt.key"
          :label="opt.key"
          class="plan-card__option"
        >
          {{ opt.label }}
        </el-checkbox>
      </el-checkbox-group>

      <el-radio-group v-else v-model="singleKey" :disabled="readonly">
        <el-radio
          v-for="opt in plan.options"
          :key="opt.key"
          :label="opt.key"
          class="plan-card__option"
        >
          {{ opt.label }}
        </el-radio>
      </el-radio-group>
    </div>

    <div v-if="plan.allow_custom && plan.custom_field" class="plan-card__custom">
      <el-input
        v-model="customValue"
        :placeholder="plan.custom_field.placeholder"
        :disabled="readonly"
        clearable
      >
        <template #prepend>{{ plan.custom_field.label }}</template>
      </el-input>
    </div>

    <div class="plan-card__actions">
      <el-button v-if="plan.cancellable" size="default" :disabled="readonly" @click="handleCancel">
        取消
      </el-button>
      <el-button
        type="primary"
        size="default"
        :disabled="readonly || !canConfirm"
        @click="handleConfirm"
      >
        {{ plan.confirm_action.button_text }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Plan 提案交互卡片。
 *
 * 完全由后端下发的 Plan Schema 驱动渲染：
 *   - multi_select 决定走 checkbox 还是 radio
 *   - allow_custom + custom_field 决定是否渲染"其他"输入框
 *   - cancellable 决定是否显示取消按钮
 *   - 任何 UI 行为都不在组件内硬编码，便于后端按业务调整 Schema
 *
 * 所属板块：aiAssistant。
 */

import { computed, ref, watch } from "vue";
import { MagicStick } from "@element-plus/icons-vue";
import type { PlanConfirmPayload, PlanProposal } from "@/types/aiAssistant/planSchema";

const props = defineProps<{
  plan: PlanProposal;
  /** 只读模式：消息已确认或已取消时禁用全部交互 */
  readonly?: boolean;
}>();

const emit = defineEmits<{
  (e: "confirm", payload: PlanConfirmPayload): void;
  (e: "cancel"): void;
}>();

/** 多选模式下的已选 key 数组 */
const selectedKeys = ref<string[]>(props.plan.options.filter((o) => o.selected).map((o) => o.key));

/** 单选模式下的已选 key */
const singleKey = ref<string>(props.plan.options.find((o) => o.selected)?.key ?? "");

/** 自定义输入值 */
const customValue = ref<string>("");

/** 切换 plan 时重置内部状态（同一个组件被多个 plan 复用时） */
watch(
  () => props.plan.plan_id,
  () => {
    selectedKeys.value = props.plan.options.filter((o) => o.selected).map((o) => o.key);
    singleKey.value = props.plan.options.find((o) => o.selected)?.key ?? "";
    customValue.value = "";
  }
);

const canConfirm = computed<boolean>(() => {
  if (props.plan.multi_select) {
    return selectedKeys.value.length > 0 || customValue.value.trim().length > 0;
  }
  return singleKey.value.length > 0 || customValue.value.trim().length > 0;
});

/**
 * 整理用户选择，向上抛出 confirm 事件。
 */
function handleConfirm(): void {
  const keys = props.plan.multi_select
    ? selectedKeys.value
    : singleKey.value
      ? [singleKey.value]
      : [];

  emit("confirm", {
    plan_id: props.plan.plan_id,
    selected_keys: keys,
    custom_value: customValue.value.trim(),
  });
}

/**
 * 用户点击"取消"按钮：向上抛出 cancel 事件，由父组件决定是否标记消息已驳回。
 */
function handleCancel(): void {
  emit("cancel");
}
</script>

<style scoped lang="scss">
.plan-card {
  padding: 16px;
  margin: 8px 0;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 8px;

  &__header {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
    color: var(--el-color-primary);
  }

  &__icon {
    font-size: 18px;
  }

  &__title {
    font-size: 15px;
    font-weight: 600;
  }

  &__desc {
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.5;
    color: var(--el-text-color-regular);
  }

  &__options {
    display: flex;
    flex-direction: column;
    margin-bottom: 12px;
  }

  &__option {
    margin: 4px 0;
  }

  &__custom {
    margin-bottom: 12px;
  }

  &__actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
  }
}
</style>
