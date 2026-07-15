<template>
  <div class="dynamic-field">
    <!-- group：子字段组（对齐领星 DynamicFormGroup） -->
    <div v-if="fieldConfig.fieldType === 'group'" class="dynamic-field__group">
      <!-- 组标题：中文 + 英文 -->
      <div class="dynamic-field__group-title-wrap">
        <span class="dynamic-field__group-title-zh">{{ fieldConfig.label[0] }}</span>
        <span class="dynamic-field__group-title-en">{{ fieldConfig.label[1] }}</span>
      </div>
      <!-- 子字段列表（垂直堆叠，每个子字段双语标签 + 输入框） -->
      <div class="dynamic-field__group-body">
        <div v-for="sf in fieldConfig.subFields" :key="sf.attrName" class="dynamic-field__sub-item">
          <div class="dynamic-field__sub-label">
            <p class="dynamic-field__sub-label-zh">
              <span v-if="sf.required" class="dynamic-field__sub-star">*</span>
              {{ sf.label[0] }}
            </p>
            <p class="dynamic-field__sub-label-en">{{ sf.label[1] }}</p>
          </div>
          <div class="dynamic-field__sub-control">
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
              class="dynamic-field__select"
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
              class="dynamic-field__date"
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
 *
 * group 类型对齐领星 DynamicFormGroup：
 * - 组标题：中文加粗 14px + 英文加粗 #999
 * - 子字段垂直堆叠，每个子字段双语标签（中文带* + 英文）+ 输入框
 * - 组容器背景 #fafbfc，padding 20px
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

  /* ── 组字段（对齐领星 DynamicFormGroup）── */
  &__group {
    background: rgb(250 251 252);
    padding: 20px 20px 1px;
    margin-bottom: 20px;
  }

  &__group-title-wrap {
    display: flex;
    align-items: center;
    margin-bottom: 20px;
  }

  &__group-title-zh {
    color: #000;
    font-weight: 700;
    font-size: 14px;
    margin-right: 10px;
  }

  &__group-title-en {
    font-weight: 700;
    color: #999;
  }

  &__group-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding-bottom: 19px;
  }

  /* ── 子字段行 ── */
  &__sub-item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
  }

  &__sub-label {
    flex-shrink: 0;
    width: 160px;
    padding-top: 5px;
    text-align: right;
  }

  &__sub-label-zh {
    margin: 0;
    font-size: 12px;
    line-height: 16px;
    color: #33363c;
  }

  &__sub-label-en {
    margin: 0;
    font-size: 12px;
    line-height: 16px;
    color: #888c94;
  }

  &__sub-star {
    color: #f5222d;
    font-size: 10px;
    margin-right: 4px;
  }

  &__sub-control {
    flex: 1;
    min-width: 0;

    .el-input,
    .el-select,
    .el-date-editor {
      width: 100%;
    }
  }
}
</style>
