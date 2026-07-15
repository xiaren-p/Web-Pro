<template>
  <!-- 单值简单字段 -->
  <DynamicFieldItem
    v-if="category === 'single'"
    :field-config="fieldConfig"
    :model-value="((modelValue[0] as Record<string, unknown>)?.value as string) ?? ''"
    :disabled="disabled"
    @update:model-value="
      (v) => emit('update:modelValue', [{ ...((modelValue[0] as object) || {}), value: v }])
    "
  />

  <!-- 多值列表（maxUniqueItems > 1，单子键） -->
  <DynamicFieldList
    v-else-if="category === 'singleArray'"
    :field-config="fieldConfig"
    :model-value="modelValue as Record<string, unknown>[]"
    :marketplace-id="marketplaceId"
    @update:model-value="(v) => emit('update:modelValue', v)"
  />

  <!-- 多值组列表（maxUniqueItems > 1，多子键） -->
  <DynamicFieldGroupList
    v-else-if="category === 'multiArray'"
    :field-config="fieldConfig"
    :model-value="modelValue as Record<string, unknown>[]"
    :required-fields="requiredFields"
    :marketplace-id="marketplaceId"
    @update:model-value="(v) => emit('update:modelValue', v)"
  />

  <!-- 对象组（多子字段，全非对象） -->
  <DynamicFieldGroup
    v-else-if="category === 'multi'"
    :field-config="fieldConfig"
    :model-value="modelValue[0] as Record<string, unknown>"
    :required-fields="requiredFields"
    :marketplace-id="marketplaceId"
    @update:model-value="(v) => emit('update:modelValue', [{ ...v }])"
  />

  <!-- 混合类型组（多子字段，含对象） -->
  <DynamicFieldMultiGroup
    v-else-if="category === 'multiObj'"
    :field-config="fieldConfig"
    :model-value="modelValue[0] as Record<string, unknown>"
    :required-fields="requiredFields"
    :marketplace-id="marketplaceId"
    @update:model-value="(v) => emit('update:modelValue', [{ ...v }])"
  />

  <!-- 单嵌套对象 -->
  <DynamicFieldSingleGroup
    v-else-if="category === 'singleObject'"
    :field-config="fieldConfig"
    :model-value="modelValue[0] as Record<string, unknown>"
    :sub-key="fieldConfig.fields ? Object.keys(fieldConfig.fields)[0] : 'value'"
    :required-fields="requiredFields"
    :marketplace-id="marketplaceId"
    @update:model-value="(v) => emit('update:modelValue', [{ ...v }])"
  />

  <!-- 多值嵌套对象 -->
  <DynamicFieldSingleGroup
    v-else-if="category === 'singleArrayObject'"
    :field-config="fieldConfig"
    :model-value="modelValue[0] as Record<string, unknown>"
    :sub-key="fieldConfig.fields ? Object.keys(fieldConfig.fields)[0] : 'value'"
    :required-fields="requiredFields"
    :marketplace-id="marketplaceId"
    :is-as-child="true"
    @update:model-value="(v) => emit('update:modelValue', [{ ...v }])"
  />

  <!-- 未知分类 → 降级为简单渲染 -->
  <DynamicFieldItem
    v-else
    :field-config="fieldConfig"
    :model-value="((modelValue[0] as Record<string, unknown>)?.value as string) ?? ''"
    :disabled="disabled"
    @update:model-value="
      (v) => emit('update:modelValue', [{ ...((modelValue[0] as object) || {}), value: v }])
    "
  />
</template>

<script setup lang="ts">
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";
import type { FieldCategory } from "../composables/useFieldClassification";
import DynamicFieldItem from "./DynamicFieldItem.vue";
import DynamicFieldList from "./DynamicFieldList.vue";
import DynamicFieldGroup from "./DynamicFieldGroup.vue";
import DynamicFieldGroupList from "./DynamicFieldGroupList.vue";
import DynamicFieldSingleGroup from "./DynamicFieldSingleGroup.vue";
import DynamicFieldMultiGroup from "./DynamicFieldMultiGroup.vue";

interface Props {
  /**
   * 字段配置。
   *
   * @description 来自 useProductTypeSchema 的解析结果。
   * 包含字段名、类型、选项、验证规则等完整信息。
   */
  fieldConfig: ParsedFieldConfig;

  /**
   * 字段渲染分类。
   *
   * @description 由 useFieldClassification 计算得出的分类结果。
   * 决定使用哪个子组件渲染。
   *
   * 可选值：single | singleArray | multiArray | multi | multiObj | singleObject | singleArrayObject
   */
  category: FieldCategory;

  /**
   * 当前字段的完整表单值。
   *
   * @description 格式匹配领星结构：
   * - 简单字段：Array<{ value: string, marketplace_id?: string }>
   * - 组字段：Array<{ subKey: { value: string }, ..., marketplace_id?: string }>
   * - 默认至少 1 项。
   */
  modelValue: unknown[];

  /**
   * 必填的子字段名列表。
   *
   * @description 来自 useDynamicRequiredFields 的计算结果。
   * 标记当前表单值下哪些子字段必须填写。
   */
  requiredFields?: string[];

  /**
   * 市场 ID。
   *
   * @description 用于填充新添加项的 marketplace_id。
   * 来自 Schema 的 defaultFields 或用户选中的市场。
   */
  marketplaceId?: string;

  /** 是否禁用。 */
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  requiredFields: () => [],
  marketplaceId: "",
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: unknown[]];
}>();
</script>
