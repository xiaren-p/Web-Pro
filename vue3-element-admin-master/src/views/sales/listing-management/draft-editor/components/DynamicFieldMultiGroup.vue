/** * 混合类型组字段组件。 * * @description 匹配领星 DynamicFormMultiGroup。 * 用于 value
内含多个子键、其中部分子键值为对象的场景（"multiObj" 类型）。 * 内部根据 useFieldClassification
的分类结果，混合渲染： * - 对象值子键 → DynamicFieldSingleGroup（isAsChild） * - 简单值子键 →
DynamicFieldItem * - 数组值子键 → DynamicFieldList * * 领星对应： * ``` * value: { simpleField:
"value", objectField: { sub: { value: "" } }, ... } * ``` */
<template>
  <div class="dynamic-multi-group">
    <div class="dynamic-multi-group__title-wrap">
      <span class="dynamic-multi-group__title-zh">{{ fieldConfig.label[0] }}</span>
      <span class="dynamic-multi-group__title-en">{{ fieldConfig.label[1] }}</span>
    </div>
    <div v-for="entry in renderEntries" :key="entry.key" class="dynamic-multi-group__field">
      <div class="dynamic-multi-group__label">
        <p class="dynamic-multi-group__label-zh">
          <span
            v-if="requiredFields.includes(entry.key) || entry.config.required"
            class="dynamic-multi-group__star"
          >
            *
          </span>
          {{ entry.config.label[0] }}
        </p>
        <p class="dynamic-multi-group__label-en">{{ entry.config.label[1] }}</p>
      </div>
      <div class="dynamic-multi-group__control">
        <DynamicFieldItem
          :field-config="entry.config"
          :model-value="String((modelValue[entry.key] as Record<string, unknown>)?.value ?? '')"
          @update:model-value="(v) => onSimpleInput(entry.key, v)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import DynamicFieldItem from "./DynamicFieldItem.vue";

interface Props {
  fieldConfig: ParsedFieldConfig;
  modelValue: Record<string, unknown>;
  requiredFields?: string[];
  marketplaceId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  requiredFields: () => [],
  marketplaceId: "",
});

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>];
}>();

interface RenderEntry {
  key: string;
  config: ParsedFieldConfig;
  isObject: boolean;
}

const renderEntries = computed<RenderEntry[]>(() => {
  if (!props.fieldConfig.fields) return [];
  return Object.entries(props.fieldConfig.fields).map(([key, config]) => ({
    key,
    config,
    isObject: false, // 领星思路：fields 内的子字段至少是简单值
  }));
});

function onSimpleInput(fieldKey: string, val: string | number | boolean | undefined) {
  const next = { ...props.modelValue };
  next[fieldKey] = { value: val, marketplace_id: props.marketplaceId };
  emit("update:modelValue", next);
}
</script>

<style scoped lang="scss">
.dynamic-multi-group {
  padding: 20px 20px 1px;
  margin-bottom: 20px;
  background: rgb(250 251 252);

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
