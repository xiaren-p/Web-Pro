<template>
  <div class="drafts-pager">
    <div class="drafts-pager__row">
      <span class="drafts-pager__total">
        <el-icon :size="14"><List /></el-icon>
        共 {{ total }} 条
      </span>

      <div class="drafts-pager__controls">
        <el-pagination
          small
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="pageNum"
          @current-change="handleCurrentChange"
        />

        <span class="drafts-pager__label">每页</span>
        <el-select
          :model-value="pageSize"
          size="small"
          class="drafts-pager__size-select"
          @change="handleSizeChange"
        >
          <el-option label="20条" :value="20" />
          <el-option label="50条" :value="50" />
          <el-option label="100条" :value="100" />
        </el-select>
        <span class="drafts-pager__label">条/页</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { List } from "@element-plus/icons-vue";

defineOptions({ name: "DraftPagination" });

const pageNum = ref(1);
const pageSize = ref(20);
const total = ref(0);

function handleSizeChange(val: number) {
  pageSize.value = val;
}

function handleCurrentChange(val: number) {
  pageNum.value = val;
}
</script>

<style scoped lang="scss">
.drafts-pager {
  position: sticky;
  bottom: 0;
  z-index: 13;
  flex-shrink: 0;
  background: var(--surface-base);
  border-top: 1px solid var(--border-base);

  &__row {
    display: flex;
    gap: var(--spacing-3);
    align-items: center;
    justify-content: flex-end;
    padding: 10px 18px;
  }

  &__total {
    display: flex;
    gap: 6px;
    align-items: center;
    margin-right: auto;
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  &__controls {
    display: flex;
    gap: var(--spacing-2);
    align-items: center;
  }

  &__label {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  &__size-select {
    width: 88px;
  }
}
</style>
