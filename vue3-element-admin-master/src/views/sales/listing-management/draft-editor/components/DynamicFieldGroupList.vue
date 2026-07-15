/** * 多值对象组列表组件。 * * @description 匹配领星 DynamicFormGroupList。 * 用于 maxUniqueItems >
1 且含多个子字段的数组字段。 * 每个数组项渲染一个 DynamicFieldGroup 子组，支持 add/remove。 *
白色卡片背景包裹每项的子字段，底部按钮控制添加。 */
<template>
  <div class="dynamic-group-list">
    <div class="dynamic-group-list__title-wrap">
      <span class="dynamic-group-list__title-zh">{{ fieldConfig.label[0] }}</span>
      <span class="dynamic-group-list__title-en">{{ fieldConfig.label[1] }}</span>
    </div>
    <div
      v-for="(group, groupIndex) in modelValue"
      :key="groupIndex"
      class="dynamic-group-list__item"
    >
      <div class="dynamic-group-list__fields">
        <div
          v-for="(subConfig, subKey) in fieldConfig.fields"
          :key="subKey"
          class="dynamic-group-list__field"
        >
          <div class="dynamic-group-list__label">
            <p class="dynamic-group-list__label-zh">
              <span
                v-if="requiredFields.includes(subKey) || subConfig.required"
                class="dynamic-group-list__star"
              >
                *
              </span>
              {{ subConfig.label[0] }}
            </p>
            <p class="dynamic-group-list__label-en">{{ subConfig.label[1] }}</p>
          </div>
          <div class="dynamic-group-list__control">
            <DynamicFieldItem
              :field-config="subConfig"
              :model-value="
                ((group[subKey] as Record<string, unknown>)?.value as string | undefined) ?? ''
              "
              @update:model-value="(v) => onSubInput(groupIndex, subKey, v)"
            />
          </div>
        </div>
      </div>
      <div class="dynamic-group-list__actions">
        <el-button
          v-if="modelValue.length > 1"
          text
          size="small"
          type="danger"
          @click="removeGroup(groupIndex)"
        >
          删除
        </el-button>
      </div>
    </div>
    <el-button
      v-if="modelValue.length < (fieldConfig.maxUniqueItems ?? Infinity)"
      size="small"
      @click="addGroup"
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
  requiredFields?: string[];
  marketplaceId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  requiredFields: () => [],
  marketplaceId: "",
});

const emit = defineEmits<{
  "update:modelValue": [value: Record<string, unknown>[]];
}>();

function onSubInput(
  groupIndex: number,
  subKey: string,
  val: string | number | boolean | undefined
) {
  const next = [...props.modelValue];
  next[groupIndex] = {
    ...next[groupIndex],
    [subKey]: { value: val, marketplace_id: props.marketplaceId },
  };
  emit("update:modelValue", next);
}

function addGroup() {
  const base: Record<string, unknown> = {
    marketplace_id: props.marketplaceId,
  };
  if (props.fieldConfig.fields) {
    for (const key of Object.keys(props.fieldConfig.fields)) {
      base[key] = { value: "" };
    }
  }
  const next = [...props.modelValue, base];
  emit("update:modelValue", next);
}

function removeGroup(index: number) {
  const next = props.modelValue.filter((_, i) => i !== index);
  emit("update:modelValue", next);
}
</script>

<style scoped lang="scss">
.dynamic-group-list {
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

  &__item {
    display: flex;
    gap: 8px;
    padding: 20px;
    margin-bottom: 12px;
    background: #fff;
    border-radius: 4px;
  }

  &__fields {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 12px;
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

  &__actions {
    display: flex;
    flex-shrink: 0;
    align-items: flex-start;
    padding-top: 24px;
  }
}
</style>
