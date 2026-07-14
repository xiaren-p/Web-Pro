<template>
  <div class="dynamic-field">
    <!-- group：子字段组 -->
    <div v-if="fieldConfig.fieldType === 'group'" class="dynamic-field__group">
      <div v-for="sf in fieldConfig.subFields" :key="sf.attrName" class="dynamic-field__group-item">
        <label class="dynamic-field__group-label">
          <span v-if="sf.required" class="dynamic-field__group-star">*</span>
          {{ sf.label[1] || sf.label[0] }}
        </label>
        <!-- string -->
        <el-input
          v-if="sf.fieldType === 'string'"
          :model-value="groupValues[sf.attrName] || ''"
          :maxlength="sf.maxLength || undefined"
          :minlength="sf.minLength || undefined"
          :show-word-limit="!!sf.maxLength"
          :placeholder="sf.placeholder || ''"
          clearable
          size="small"
          @update:model-value="
            (v: string | number | boolean | undefined) => onGroupInput(sf.attrName, v)
          "
        />
        <!-- select -->
        <el-select
          v-else-if="sf.fieldType === 'select'"
          :model-value="groupValues[sf.attrName] || ''"
          :placeholder="sf.placeholder || ''"
          :allow-create="sf.allowCreate"
          filterable
          clearable
          size="small"
          default-first-option
          @update:model-value="
            (v: string | number | boolean | undefined) => onGroupInput(sf.attrName, v)
          "
        >
          <el-option
            v-for="opt in sf.options"
            :key="opt.value"
            :label="opt.name"
            :value="opt.value"
          />
        </el-select>
        <!-- number / integer -->
        <el-input
          v-else-if="sf.fieldType === 'number' || sf.fieldType === 'integer'"
          :model-value="groupValues[sf.attrName] || ''"
          :placeholder="sf.placeholder || ''"
          clearable
          size="small"
          @update:model-value="
            (v: string | number | boolean | undefined) =>
              onGroupNumberInput(sf.attrName, v, sf.fieldType === 'integer')
          "
        />
        <!-- date -->
        <el-date-picker
          v-else-if="sf.fieldType === 'date'"
          :model-value="groupValues[sf.attrName] || ''"
          type="date"
          value-format="YYYY-MM-DD"
          placeholder="请选择日期"
          clearable
          size="small"
          @update:model-value="
            (v: string | number | boolean | undefined) => onGroupInput(sf.attrName, v)
          "
        />
        <!-- radio -->
        <el-radio-group
          v-else-if="sf.fieldType === 'radio'"
          :model-value="groupValues[sf.attrName] || ''"
          size="small"
          @update:model-value="
            (v: string | number | boolean | undefined) => onGroupInput(sf.attrName, v)
          "
        >
          <el-radio v-for="opt in sf.options" :key="opt.value" :value="opt.value">
            {{ opt.name }}
          </el-radio>
        </el-radio-group>
      </div>
    </div>

    <!-- string：文本输入 -->
    <el-input
      v-else-if="fieldConfig.fieldType === 'string'"
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
 * date -> el-date-picker、radio -> el-radio-group、group -> 子字段组。
 */
import { computed, reactive } from "vue";
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

/** 组字段各子字段的值。 */
const groupValues = reactive<Record<string, string>>({});

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

/** 组字段子字段输入处理。 */
function onGroupInput(attrName: string, val: string | number | boolean | undefined) {
  groupValues[attrName] = val != null ? String(val) : "";
}

/** 组字段子字段数字输入处理。 */
function onGroupNumberInput(
  attrName: string,
  val: string | number | boolean | undefined,
  isInt: boolean
) {
  if (val == null || val === "") {
    groupValues[attrName] = "";
    return;
  }
  const raw = String(val);
  const cleaned = isInt ? raw.replace(/[^\d-]/g, "") : raw.replace(/[^\d.-]/g, "");
  groupValues[attrName] = cleaned;
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

  &__group {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__group-item {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  &__group-label {
    flex-shrink: 0;
    width: 120px;
    font-size: 12px;
    line-height: 30px;
    text-align: right;
    color: #33363c;
    white-space: nowrap;
  }

  &__group-star {
    color: #f5222d;
    font-size: 10px;
    margin-right: 2px;
  }
}
</style>
