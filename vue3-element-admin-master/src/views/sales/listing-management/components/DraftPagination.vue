<template>
  <div class="draft-pager">
    <div class="draft-pager__row">
      <div class="draft-pager__left">
        <span class="draft-pager__total">
          <el-icon :size="14"><List /></el-icon>
          共 {{ total }} 条
        </span>
      </div>

      <div class="draft-pager__center">
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

      <div class="draft-pager__right">
        <span class="draft-pager__label">每页</span>
        <el-select
          :model-value="pageSize"
          size="small"
          class="draft-pager__size-select"
          @change="handleSizeChange"
        >
          <el-option label="20条" :value="20" />
          <el-option label="50条" :value="50" />
          <el-option label="100条" :value="100" />
        </el-select>
        <span class="draft-pager__label">条/页</span>

        <span class="draft-pager__label">前往</span>
        <el-input v-model="jumpPage" size="small" class="draft-pager__jump-input" placeholder="1" />
        <span class="draft-pager__label">页</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 草稿箱分页器：listing-tag 风格卡片，左侧总条数，中部 el-pagination，右侧每页条数 + 前往。
 * 当前 total=0，所有数据为空占位。
 */
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
.draft-pager {
  flex-shrink: 0;
  background: var(--surface-base);
  border-top: 1px solid var(--border-subtle);

  &__row {
    display: flex;
    gap: var(--spacing-3);
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-3) 18px;
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

    :deep(.el-input__wrapper) {
      padding: 0 8px;
      border-radius: var(--radius-sm);
    }
  }
}
</style>
