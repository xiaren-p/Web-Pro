<template>
  <div class="drafts-page">
    <DraftFilterBar />
    <DraftActionBar />
    <div class="drafts-page__table-block content-block content-block--flush">
      <DraftTable />
      <DraftPagination />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 草稿箱页面：组合筛选区、操作栏、数据表格、分页器四个子组件。
 * 当前为纯 UI 占位，所有数据为空，由各子组件管理自身状态。
 */
import DraftFilterBar from "./components/DraftFilterBar.vue";
import DraftActionBar from "./components/DraftActionBar.vue";
import DraftTable from "./components/DraftTable.vue";
import DraftPagination from "./components/DraftPagination.vue";

defineOptions({ name: "ListingDraftsPage" });
</script>

<style scoped lang="scss">
.drafts-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;

  &__table-block {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }
}
</style>
