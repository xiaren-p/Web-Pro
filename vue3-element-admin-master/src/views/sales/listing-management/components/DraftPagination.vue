<template>
  <div class="drafts-pager">
    <div class="drafts-pager__row">
      <div class="drafts-pager__left">
        <span class="drafts-pager__total">
          <el-icon :size="14"><List /></el-icon>
          共 {{ total }} 条
        </span>
      </div>

      <div class="drafts-pager__center">
        <el-pagination
          small
          background
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="pageNum"
          @current-change="handleCurrentChange"
        />
      </div>

      <div class="drafts-pager__right">
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

        <span class="drafts-pager__label">前往</span>
        <el-input
          v-model="jumpPage"
          size="small"
          class="drafts-pager__jump-input"
          placeholder="1"
        />
        <span class="drafts-pager__label">页</span>
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

const jumpPage = ref("");

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
    justify-content: space-between;
    padding: 10px 18px;
  }

  &__left {
    flex-shrink: 0;
  }

  &__center {
    display: flex;
    flex-shrink: 0;
    align-items: center;
    justify-content: center;
  }

  &__right {
    display: flex;
    flex-shrink: 0;
    gap: var(--spacing-2);
    align-items: center;
  }

  &__total {
    display: flex;
    gap: 6px;
    align-items: center;
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  &__label {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
  }

  &__size-select {
    width: 88px;
  }

  &__jump-input {
    width: 64px;
  }
}
</style>
