<template>
  <div class="dynamic-field">
    <!-- string：文本输入 -->
    <el-input
      v-if="fieldConfig.fieldType === 'string'"
      :model-value="modelValue"
      :maxlength="fieldConfig.maxLength || undefined"
      :minlength="fieldConfig.minLength || undefined"
      :show-word-limit="!!fieldConfig.maxLength"
      :placeholder="fieldConfig.placeholder || '请输入'"
      clearable
      @update:model-value="onInput"
    />

    <!-- select：下拉选择 -->
    <el-select
      v-else-if="fieldConfig.fieldType === 'select'"
      :model-value="modelValue"
      :placeholder="fieldConfig.placeholder || '请选择'"
      :allow-create="fieldConfig.allowCreate"
      filterable
      clearable
      default-first-option
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

    <!-- number / integer：数字输入 -->
    <el-input
      v-else-if="fieldConfig.fieldType === 'number' || fieldConfig.fieldType === 'integer'"
      :model-value="modelValue"
      :placeholder="fieldConfig.placeholder || '请输入数字'"
      clearable
      @update:model-value="onNumberInput"
    >
      <template v-if="suffixText" #suffix>
        <span class="dynamic-field__suffix">{{ suffixText }}</span>
      </template>
    </el-input>

    <!-- date：日期选择 -->
    <el-date-picker
      v-else-if="fieldConfig.fieldType === 'date'"
      :model-value="modelValue"
      type="date"
      value-format="YYYY-MM-DD"
      placeholder="请选择日期"
      clearable
      class="dynamic-field__date"
      @update:model-value="onInput"
    />

    <!-- radio：单选 -->
    <el-radio-group
      v-else-if="fieldConfig.fieldType === 'radio'"
      :model-value="modelValue"
      @update:model-value="onInput"
    >
      <el-radio v-for="opt in fieldConfig.options" :key="opt.value" :value="opt.value">
        {{ opt.name }}
      </el-radio>
    </el-radio-group>
  </div>
</template>

<script setup lang="ts">
/**
 * 动态字段渲染组件。
 *
 * 根据 ParsedFieldConfig.fieldType 渲染对应的 Element Plus 控件：
 * string -> el-input、select -> el-select、number/integer -> el-input（数字过滤）、
 * date -> el-date-picker、radio -> el-radio-group。
 * 组字段已在 parseAllFields 中展平为独立条目，无需 group 分支。
 */
import { computed } from "vue";
import type { ParsedFieldConfig } from "@/composables/useProductTypeSchema";

interface Props {
  /** 字段配置。 */
  fieldConfig: ParsedFieldConfig;
  /** 字段值（字符串形式）。 */
  modelValue: string;
  /** 是否禁用。 */
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
});

const emit = defineEmits<{
  "update:modelValue": [value: string];
}>();

/** 数字字段的范围提示后缀。 */
const suffixText = computed(() => {
  const { minimum, maximum } = props.fieldConfig;
  if (minimum != null && maximum != null) return `${minimum} ~ ${maximum}`;
  if (minimum != null) return `≥ ${minimum}`;
  if (maximum != null) return `≤ ${maximum}`;
  return "";
});

/** 文本/选择/日期/单选的统一输入处理。 */
function onInput(val: string | number | boolean | undefined) {
  emit("update:modelValue", val != null ? String(val) : "");
}

/** 数字输入过滤：仅保留数字和小数点。 */
function onNumberInput(val: string | number | boolean | undefined) {
  if (val == null || val === "") {
    emit("update:modelValue", "");
    return;
  }
  const raw = String(val);
  const isInteger = props.fieldConfig.fieldType === "integer";
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
