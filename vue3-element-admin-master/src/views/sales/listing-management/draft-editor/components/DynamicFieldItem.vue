/** * 单值字段渲染组件。 * * @description 匹配领星 DynamicFormGroupItem / DynamicFormItem。 * 根据
ParsedFieldConfig.type 渲染对应的 Element Plus 控件： * string → el-input、select →
el-select、number/integer → el-input（数字过滤）、 * date → el-date-picker、radio → el-radio-group。
* * 支持文本型字段的 maxLength 字数限制显示、数字字段的范围后缀提示。 */
<template>
  <el-input
    v-if="fieldConfig.type === 'string'"
    :model-value="String(modelValue ?? '')"
    :maxlength="fieldConfig.maxLength || undefined"
    :minlength="fieldConfig.minLength || undefined"
    :show-word-limit="!!fieldConfig.maxLength"
    :placeholder="fieldConfig.placeholder || '请输入'"
    :disabled="disabled"
    clearable
    size="small"
    @update:model-value="onInput"
  />
  <el-select
    v-else-if="fieldConfig.type === 'select'"
    :model-value="String(modelValue ?? '')"
    :placeholder="fieldConfig.placeholder || '请选择'"
    :allow-create="fieldConfig.allowCreate"
    :disabled="disabled"
    filterable
    clearable
    default-first-option
    size="small"
    class="dynamic-field__select"
    @update:model-value="onInput"
  >
    <el-option
      v-for="opt in fieldConfig.options"
      :key="opt.value"
      :label="opt.name"
      :value="opt.value"
    />
  </el-select>
  <el-input
    v-else-if="fieldConfig.type === 'number' || fieldConfig.type === 'integer'"
    :model-value="String(modelValue ?? '')"
    :placeholder="fieldConfig.placeholder || '请输入数字'"
    :disabled="disabled"
    clearable
    size="small"
    @update:model-value="onNumberInput"
  >
    <template v-if="suffixText" #suffix>
      <span class="dynamic-field__suffix">{{ suffixText }}</span>
    </template>
  </el-input>
  <el-date-picker
    v-else-if="fieldConfig.type === 'date'"
    :model-value="dateModelValue"
    type="date"
    value-format="YYYY-MM-DD"
    placeholder="请选择日期"
    :disabled="disabled"
    clearable
    size="small"
    class="dynamic-field__date"
    @update:model-value="onInput"
  />
  <el-radio-group
    v-else-if="fieldConfig.type === 'radio'"
    :model-value="modelValue"
    :disabled="disabled"
    size="small"
    @update:model-value="onInput"
  >
    <el-radio v-for="opt in fieldConfig.options" :key="opt.value" :value="opt.value">
      {{ opt.name }}
    </el-radio>
  </el-radio-group>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";

interface Props {
  fieldConfig: ParsedFieldConfig;
  modelValue: string | number | boolean | undefined;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), { disabled: false });

const emit = defineEmits<{
  "update:modelValue": [value: string | number | boolean | undefined];
}>();

const dateModelValue = computed(() => {
  if (typeof props.modelValue === "string" || typeof props.modelValue === "number")
    return props.modelValue;
  return undefined;
});

const suffixText = computed(() => {
  const { minimum, maximum } = props.fieldConfig;
  if (minimum != null && maximum != null) return `${minimum} ~ ${maximum}`;
  if (minimum != null) return `≥ ${minimum}`;
  if (maximum != null) return `≤ ${maximum}`;
  return "";
});

function onInput(val: string | number | boolean | undefined) {
  emit("update:modelValue", val);
}

function onNumberInput(val: string | number | boolean | undefined) {
  if (val == null || val === "") {
    emit("update:modelValue", "");
    return;
  }
  const raw = String(val);
  const isInteger = props.fieldConfig.type === "integer";
  const cleaned = isInteger ? raw.replace(/[^\d-]/g, "") : raw.replace(/[^\d.-]/g, "");
  emit("update:modelValue", cleaned);
}
</script>

<style scoped lang="scss">
.dynamic-field {
  &__select,
  &__date {
    width: 100%;
  }

  &__suffix {
    font-size: var(--font-size-xs);
    color: var(--text-tertiary);
  }
}
</style>
