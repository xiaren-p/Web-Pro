/** * 多值列表字段组件。 * * @description 匹配领星 DynamicFormList。 * 用于 maxUniqueItems > 1
且仅含单个子字段的数组字段。 * 支持添加项（不超过 maxUniqueItems）和删除项（保留至少 1 项）。 *
每行渲染 DynamicFieldItem 绑定到 items[index].value。 */
<template>
  <div class="dynamic-list">
    <div v-for="(item, index) in modelValue" :key="index" class="dynamic-list__row">
      <DynamicFieldItem
        :field-config="fieldConfig"
        :model-value="String(item.value ?? '')"
        class="dynamic-list__control"
        @update:model-value="(v) => onItemInput(index, v)"
      />
      <div class="dynamic-list__actions">
        <el-button
          v-if="modelValue.length > 1"
          text
          size="small"
          type="danger"
          @click="removeItem(index)"
        >
          删除
        </el-button>
      </div>
    </div>
    <el-button
      v-if="modelValue.length < (fieldConfig.maxUniqueItems ?? Infinity)"
      size="small"
      @click="addItem"
    >
      添加
    </el-button>
  </div>
</template>

<script setup lang="ts">
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import DynamicFieldItem from "./DynamicFieldItem.vue";

interface Props {
  fieldConfig: ParsedFieldConfig;
  modelValue: Record<string, unknown>[];
  required?: boolean;
  marketplaceId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  required: false,
  marketplaceId: "",
});

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>[]];
}>();

function onItemInput(index: number, val: string | number | boolean | undefined) {
  const next = [...props.modelValue];
  next[index] = { ...next[index], value: val };
  emit("update:modelValue", next);
}

function addItem() {
  const next = [...props.modelValue];
  next.push({ value: "", marketplace_id: props.marketplaceId });
  emit("update:modelValue", next);
}

function removeItem(index: number) {
  const next = props.modelValue.filter((_, i) => i !== index);
  emit("update:modelValue", next);
}
</script>

<style scoped lang="scss">
.dynamic-list {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__row {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__control {
    flex: 1;
  }

  &__actions {
    flex-shrink: 0;
  }
}
</style>
