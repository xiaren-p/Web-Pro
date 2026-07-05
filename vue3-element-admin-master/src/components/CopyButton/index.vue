<template>
  <el-button link :style="style" @click="handleClipboard">
    <slot>
      <el-icon><DocumentCopy color="var(--el-color-primary)" /></el-icon>
    </slot>
  </el-button>
</template>

<script setup lang="ts">
/**
 * 复制按钮组件。点击将传入文本复制到剪贴板。
 */
defineOptions({ name: "CopyButton", inheritAttrs: false });

const props = defineProps<{ content?: string; style?: Record<string, string> }>();
const emit = defineEmits<{ (e: "success"): void }>();

async function handleClipboard() {
  if (!props.content) return;
  try {
    await navigator.clipboard.writeText(props.content);
    emit("success");
  } catch {
    // clipboard API not available
  }
}
</script>
