<template>
  <section class="draft-action-bar">
    <div class="draft-action-bar__left">
      <el-button type="primary" :icon="Plus" size="small">添加草稿</el-button>
      <el-button disabled size="small">发布</el-button>
      <el-button disabled size="small">删除</el-button>
    </div>

    <div class="draft-action-bar__right">
      <el-icon :size="20" class="action-icon">
        <Refresh />
      </el-icon>
      <el-icon :size="20" class="action-icon">
        <QuestionFilled />
      </el-icon>
      <el-icon :size="20" class="action-icon">
        <Setting />
      </el-icon>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * 草稿箱操作按钮区：左侧主操作按钮（添加草稿/发布/删除），右侧工具栏图标（刷新/帮助/设置）。
 * 发布与删除初始禁用（无数据），右侧图标纯占位无交互。
 */
import { Plus, Refresh, QuestionFilled, Setting } from "@element-plus/icons-vue";

defineOptions({ name: "DraftActionBar" });
</script>

<style scoped lang="scss">
.draft-action-bar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 var(--spacing-4);
  background: var(--surface-base);

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

.action-icon {
  color: var(--text-tertiary);
  cursor: pointer;
  transition: color var(--transition-ui);

  &:hover {
    color: var(--text-primary);
  }
}

/* 响应式：≤768px 竖排 */
@media (width <= 768px) {
  .draft-action-bar {
    flex-direction: column;
    gap: var(--spacing-2);
    height: auto;
    padding: var(--spacing-2) var(--spacing-4);
  }
}
</style>
