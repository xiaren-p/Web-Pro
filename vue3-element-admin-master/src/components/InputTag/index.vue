<template>
  <el-scrollbar>
    <div class="flex-y-center gap-2">
      <el-tag
        v-for="tag in tags"
        :key="tag"
        closable
        :disable-transitions="false"
        v-bind="config.tagAttrs"
        @close="handleClose(tag)"
      >
        {{ tag }}
      </el-tag>
      <el-input
        v-if="isInputVisible"
        ref="inputRef"
        v-model.trim="inputValue"
        style="min-width: 100px"
        @keyup.enter.stop.prevent="handleInputConfirm"
        @blur.stop.prevent="handleInputConfirm"
      />
      <el-button v-else v-bind="config.buttonAttrs" @click="showInput">
        {{ config.buttonAttrs.btnText ? config.buttonAttrs.btnText : "+ New Tag" }}
      </el-button>
    </div>
  </el-scrollbar>
</template>

<script setup lang="ts">
/**
 * 标签输入组件：支持动态添加/删除标签，v-model 绑定标签数组。
 */
import type { InputInstance } from "element-plus";

const inputValue = ref("");
const isInputVisible = ref(false);
const inputRef = ref<InputInstance>();

const tags = defineModel<string[]>();

interface InputTagConfig {
  buttonAttrs: Record<string, unknown>;
  inputAttrs: Record<string, unknown>;
  tagAttrs: Record<string, unknown>;
}

withDefaults(defineProps<{ config?: InputTagConfig }>(), {
  config: () => ({ buttonAttrs: {}, inputAttrs: {}, tagAttrs: {} }),
});

/** 移除指定标签。 */
function handleClose(tag: string) {
  if (tags.value) {
    tags.value = tags.value.filter((t) => t !== tag);
  }
}

/** 展示输入框并聚焦。 */
function showInput() {
  isInputVisible.value = true;
  nextTick(() => inputRef.value?.focus());
}

/** 确认输入：将输入值加入标签列表。 */
function handleInputConfirm() {
  if (inputValue.value) {
    tags.value = [...(tags.value || []), inputValue.value];
  }
  isInputVisible.value = false;
  inputValue.value = "";
}
</script>
