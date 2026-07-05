<template>
  <template v-if="tagType">
    <el-tag :type="tagType" :size="tagSize">{{ label }}</el-tag>
  </template>
  <template v-else>
    <span>{{ label }}</span>
  </template>
</template>

<script setup lang="ts">
/**
 * 字典标签组件：根据 dictCode + value 查找字典项，渲染为 el-tag 或纯文本。
 */
import { useDictStore } from "@/store";

interface Props {
  /** 字典编码 */
  code: string;
  /** 字典项的值 */
  modelValue?: string | number;
  /** 标签大小 */
  size?: string;
}

const props = withDefaults(defineProps<Props>(), { size: "default" });

const label = ref("");
const tagType = ref<"success" | "warning" | "info" | "primary" | "danger" | undefined>();
const tagSize = ref<"default" | "large" | "small">(props.size as "default" | "large" | "small");

const dictStore = useDictStore();

/**
 * 根据字典项的值获取对应的 label 和 tagType。
 *
 * @param dictCode - 字典编码。
 * @param value - 字典项的值。
 * @returns label 和 tagType。
 */
async function getLabelAndTagByValue(dictCode: string, value: string | number) {
  await dictStore.loadDictItems(dictCode);
  const dictItems = dictStore.getDictItems(dictCode);
  const dictItem = dictItems.find((item) => item.value == value);
  return { label: dictItem?.label || "", tagType: dictItem?.tagType };
}

/** 更新 label 和 tagType。 */
async function updateLabelAndTag() {
  if (!props.code || props.modelValue === undefined) return;
  const { label: newLabel, tagType: newTagType } = await getLabelAndTagByValue(
    props.code,
    props.modelValue
  );
  label.value = newLabel;
  tagType.value = newTagType as typeof tagType.value;
}

watch(
  [() => props.code, () => props.modelValue],
  async () => {
    if (props.code) await updateLabelAndTag();
  },
  { immediate: true }
);
</script>
