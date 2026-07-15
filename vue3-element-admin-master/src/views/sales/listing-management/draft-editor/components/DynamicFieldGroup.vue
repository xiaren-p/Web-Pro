/** * 对象组字段组件。 * * @description 匹配领星 DynamicFormGroup。 * 渲染组标题（中文+英文）+
子字段垂直堆叠。 * 子字段使用 DynamicFieldItem 渲染，每个子字段带双语标签。 * 容器背景
#fafbfc，padding 20px，与灵星 CSS 一致。 */
<template>
  <div class="dynamic-group">
    <div class="dynamic-group__title-wrap">
      <span class="dynamic-group__title-zh">{{ fieldConfig.label[0] }}</span>
      <span class="dynamic-group__title-en">{{ fieldConfig.label[1] }}</span>
    </div>
    <div class="dynamic-group__body">
      <div
        v-for="(subConfig, subKey) in fieldConfig.fields"
        :key="subKey"
        class="dynamic-group__field"
      >
        <div class="dynamic-group__label">
          <p class="dynamic-group__label-zh">
            <span
              v-if="requiredFields.includes(subKey) || subConfig.required"
              class="dynamic-group__star"
            >
              *
            </span>
            {{ subConfig.label[0] }}
          </p>
          <p class="dynamic-group__label-en">{{ subConfig.label[1] }}</p>
        </div>
        <div class="dynamic-group__control">
          <DynamicFieldItem
            :field-config="subConfig"
            :model-value="
              ((modelValue[subKey] as Record<string, unknown>)?.value as string | undefined) ?? ''
            "
            @update:model-value="(v) => onSubInput(subKey, v)"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
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

function onSubInput(subKey: string, val: string | number | boolean | undefined) {
  emit("update:modelValue", {
    ...props.modelValue,
    [subKey]: { value: val, marketplace_id: props.marketplaceId },
  });
}
</script>

<style scoped lang="scss">
.dynamic-group {
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

  &__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-bottom: 19px;
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
