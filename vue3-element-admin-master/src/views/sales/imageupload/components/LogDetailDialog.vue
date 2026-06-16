<template>
  <el-dialog v-model="visible" title="日志详情" width="600px">
    <pre class="log-content">{{ content }}</pre>
    <template #footer>
      <el-button @click="visible = false">关 闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from "vue";

const visible = ref(false);
const content = ref("");

function open(log: string) {
  content.value = log || "";
  visible.value = true;
}

defineExpose({ open });
</script>

<style scoped>
.log-content {
  max-height: 400px;
  padding: 10px;
  overflow-y: auto;
  font-family: monospace;
  word-break: break-all;
  white-space: pre-wrap;
  background-color: #f5f7fa;
  border-radius: 4px;
}
</style>
