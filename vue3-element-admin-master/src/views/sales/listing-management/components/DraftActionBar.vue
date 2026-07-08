<template>
  <div class="drafts-toolbar">
    <div class="drafts-toolbar__left">
      <el-button type="primary" :icon="Plus" size="small">添加草稿</el-button>
      <el-button disabled size="small">发布</el-button>
      <el-button disabled size="small">删除</el-button>
    </div>

    <div class="drafts-toolbar__right">
      <el-icon :size="20" class="toolbar-icon"><Refresh /></el-icon>
      <el-icon :size="20" class="toolbar-icon"><QuestionFilled /></el-icon>
      <el-icon :size="20" class="toolbar-icon"><Setting /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Plus, Refresh, QuestionFilled, Setting } from "@element-plus/icons-vue";

defineOptions({ name: "DraftActionBar" });
</script>

<style scoped lang="scss">
.drafts-toolbar {
  position: sticky;
  top: 0;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: linear-gradient(180deg, var(--surface-base) 0%, var(--surface-subtle) 100%);
  border-bottom: 1px solid var(--border-base);

  &__left {
    display: flex;
    gap: var(--spacing-2);
    align-items: center;
  }

  &__right {
    display: flex;
    gap: var(--spacing-4);
    align-items: center;
  }
}

.toolbar-icon {
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-ui);

  &:hover {
    color: var(--text-primary);
  }
}
</style>
