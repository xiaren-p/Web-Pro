/** * 单嵌套对象字段组件。 * * @description 匹配领星 DynamicFormSingleGroup。 * 用于 value
内只有一个子键且该子键值为对象（如外层的单层嵌套）的场景。 * 渲染子对象内的字段属性，支持 isAsChild
模式（嵌入在其他组内时不重复显示标题）。 */
<template>
  <div class="dynamic-single-group" :class="{ 'dynamic-single-group--child': isAsChild }">
    <div v-if="!isAsChild" class="dynamic-single-group__title-wrap">
      <span class="dynamic-single-group__title-zh">{{ fieldConfig.label[0] }}</span>
      <span class="dynamic-single-group__title-en">{{ fieldConfig.label[1] }}</span>
    </div>
    <div v-for="entry in fieldEntries" :key="entry.key" class="dynamic-single-group__field">
      <div class="dynamic-single-group__label">
        <p class="dynamic-single-group__label-zh">
          <span
            v-if="requiredFields.includes(entry.key) || entry.config.required"
            class="dynamic-single-group__star"
          >
            *
          </span>
          {{ entry.config.label[0] }}
        </p>
        <p class="dynamic-single-group__label-en">{{ entry.config.label[1] }}</p>
      </div>
      <div class="dynamic-single-group__control">
        <DynamicFieldItem
          :field-config="entry.config"
          :model-value="getSubValue(entry.key)"
          @update:model-value="(v) => onSubInput(entry.key, v)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import { computed } from "vue";
import DynamicFieldItem from "./DynamicFieldItem.vue";

interface Props {
  fieldConfig: ParsedFieldConfig;
  modelValue: Record<string, unknown>;
  subKey: string;
  requiredFields?: string[];
  marketplaceId?: string;
  isAsChild?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  requiredFields: () => [],
  marketplaceId: "",
  isAsChild: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>];
}>();

interface FieldEntry {
  key: string;
  config: ParsedFieldConfig;
  isObject: boolean;
}

const fieldEntries = computed<FieldEntry[]>(() => {
  if (!props.fieldConfig.fields) return [];
  return Object.entries(props.fieldConfig.fields).map(([key, config]) => ({
    key,
    config,
    isObject: false,
  }));
});

function getSubValue(fieldKey: string): string {
  const sub = props.modelValue[props.subKey];
  if (!sub || typeof sub !== "object") return "";
  return String((sub as Record<string, any>)[fieldKey]?.value ?? "");
}

function onSubInput(fieldKey: string, val: string | number | boolean | undefined) {
  const next = { ...props.modelValue };
  if (!next[props.subKey] || typeof next[props.subKey] !== "object") {
    next[props.subKey] = {};
  }
  (next[props.subKey] as Record<string, unknown>)[fieldKey] = {
    value: val,
    marketplace_id: props.marketplaceId,
  };
  emit("update:modelValue", next);
}
</script>

<style scoped lang="scss">
.dynamic-single-group {
  padding: 20px 20px 1px;
  margin-bottom: 20px;
  background: rgb(250 251 252);

  &--child {
    padding: 0;
    margin-bottom: 0;
    background: transparent;
  }

  &__title-wrap {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
  }

  &__title-zh {
    margin-right: 10px;
    font-size: 14px;
    font-weight: 700;
    color: #000;
  }

  &__title-en {
    font-weight: 700;
    color: #999;
  }

  &__field {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  &__label {
    flex-shrink: 0;
    width: 160px;
    padding-top: 5px;
    text-align: right;
  }

  &__label-zh {
    margin: 0;
    font-size: 12px;
    line-height: 16px;
    color: #33363c;
  }

  &__label-en {
    margin: 0;
    font-size: 12px;
    line-height: 16px;
    color: #888c94;
  }

  &__star {
    margin-right: 4px;
    font-size: 10px;
    color: #f5222d;
  }

  &__control {
    flex: 1;
    min-width: 0;
  }
}
</style>
