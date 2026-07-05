<template>
  <div cursor-pointer flex-center rounded class="el" :class="padding">
    <slot></slot>
  </div>
</template>

<script setup lang="ts">
/**
 * 通用包装器组件。提供统一的圆角容器和 hover 效果。
 */
defineProps<{ padding?: string }>();
</script>

<style scoped lang="scss">
.el {
  cursor: pointer;
  transition: 0.3s var(--el-transition-function-ease-in-out-bezier);
  &:hover {
    background-color: var(--el-fill-color);
  }
}
</style>
