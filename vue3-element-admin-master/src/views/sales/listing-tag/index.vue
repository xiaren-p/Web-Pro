<template>
  <div class="listing-tag-page">
    <section class="filter-block">
      <ListingTagSearchForm
        :type-options="typeOptions"
        @search="handleSearch"
        @reset="handleReset"
      />
    </section>

    <section class="table-block">
      <div class="table-toolbar">
        <div class="table-toolbar__left">
          <el-button type="primary" :icon="Plus" @click="handleAdd">新增标签</el-button>
          <el-button
            type="danger"
            :icon="Delete"
            :disabled="selectedRows.length === 0"
            @click="handleBatchDelete"
          >
            批量删除
          </el-button>
        </div>
      </div>

      <div class="table-scroll">
        <el-table
          v-loading="loading"
          :data="tableData"
          class="table-content"
          :border="false"
          @selection-change="handleSelectionChange"
        >
          <template #empty>
            <div class="table-empty">
              <div class="table-empty__icon">
                <el-icon :size="48"><List /></el-icon>
              </div>
              <p class="table-empty__text">暂无数据</p>
            </div>
          </template>
          <el-table-column type="selection" width="48" fixed="left" align="center" />
          <el-table-column v-for="col in tableColumns" :key="col.prop" v-bind="col">
            <template #default="scope">
              <template v-if="col.prop === 'tagName'">
                <div class="tag-name-cell">
                  <el-tag :color="scope.row.color" effect="light">
                    {{ scope.row.tagName }}
                  </el-tag>
                </div>
              </template>

              <template v-else-if="col.prop === 'type'">
                {{ scope.row.type || "-" }}
              </template>

              <template v-else-if="col.prop === 'color'">
                <div class="color-display">
                  <span class="color-dot" :style="{ backgroundColor: scope.row.color }"></span>
                  <span class="color-text">{{ scope.row.color }}</span>
                </div>
              </template>

              <template v-else-if="col.prop === 'status'">
                <el-tag :type="getStatusType(scope.row.status)" effect="light">
                  {{ getStatusTag(scope.row.status) }}
                </el-tag>
              </template>

              <template v-else-if="col.prop === 'actions'">
                <div class="action-buttons">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :disabled="scope.row.status === 'deleting'"
                    @click="handleEdit(scope.row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    size="small"
                    :disabled="scope.row.status === 'deleting'"
                    @click="handleDelete(scope.row)"
                  >
                    删除
                  </el-button>
                </div>
              </template>

              <span v-else>{{ scope.row[col.prop] || "-" }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="table-footer-sticky">
        <div class="pager-row">
          <div class="pager-left">
            <span class="total-count">
              <el-icon class="count-icon" :size="14"><List /></el-icon>
              共 {{ total }} 条
            </span>
          </div>
          <div class="pager-right">
            <span class="page-size-label">每页</span>
            <el-select :model-value="pageSize" class="page-size-select" @change="handleSizeChange">
              <el-option label="10条" :value="10" />
              <el-option label="20条" :value="20" />
              <el-option label="50条" :value="50" />
              <el-option label="100条" :value="100" />
            </el-select>
            <span class="page-size-suffix">条/页</span>
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
        </div>
      </div>
    </section>

    <ListingTagEditDialog
      v-model:visible="editDialogVisible"
      :row="currentEditRow"
      @success="handleQueryAndRefresh"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Plus, Delete, List } from "@element-plus/icons-vue";
import { useListingTag } from "@/views/sales/listing-tag/useListingTag";
import ListingTagSearchForm from "@/views/sales/listing-tag/components/ListingTagSearchForm.vue";
import ListingTagEditDialog from "@/views/sales/listing-tag/components/ListingTagEditDialog.vue";
import type { ListingTagVO } from "@/api/sales/listing-tag";

defineOptions({ name: "SalesListingTag" });

const listingTagHooks = useListingTag();

const {
  loading,
  tableData,
  pageNum,
  pageSize,
  total,
  tableColumns,
  selectedRows,
  typeOptions,
  getStatusTag,
  getStatusType,
  handleQueryAndRefresh,
  handleSearch,
  handleReset,
  handleDelete,
  handleBatchDelete,
  handleSizeChange,
  handleCurrentChange,
} = listingTagHooks;

const editDialogVisible = ref(false);
const currentEditRow = ref<ListingTagVO | null>(null);

const handleAdd = () => {
  currentEditRow.value = null;
  editDialogVisible.value = true;
};

const handleEdit = (row: ListingTagVO) => {
  currentEditRow.value = { ...row };
  editDialogVisible.value = true;
};

const handleSelectionChange = (selection: ListingTagVO[]) => {
  selectedRows.value = selection;
};
</script>

<style scoped lang="scss">
.listing-tag-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  height: calc(100vh - 84px);
  min-height: 0;
  padding: 0;
}

.filter-block {
  flex-shrink: 0;
}

.table-block {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: var(--surface-base);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
}

.table-toolbar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  padding: 12px 18px;

  &__left {
    display: flex;
    gap: 8px;
  }
}

.table-scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;

  :deep(.el-table) {
    display: flex;
    flex: 1;
    flex-direction: column;
    background: var(--surface-base);
  }

  :deep(.el-table__inner-wrapper) {
    display: flex;
    flex: 1;
    flex-direction: column;
  }

  :deep(.el-table__body-wrapper) {
    flex: 1;
    overflow-y: auto !important;
  }
}

.table-content {
  :deep(.el-table__cell) {
    padding: 11px 0 !important;
    font-size: 13px;
    color: var(--text-primary);
    border-right: none !important;
  }

  :deep(.el-table .cell) {
    padding-right: 14px;
    padding-left: 14px;
    line-height: 1.55;
  }

  :deep(.el-table__body td.el-table__cell) {
    border-bottom: 1px solid var(--border-subtle) !important;
  }

  :deep(.el-table .el-table__row) {
    transition: background 160ms ease;
  }

  :deep(.el-table .el-table__row:hover > td.el-table__cell) {
    background-color: var(--surface-hover) !important;
  }

  :deep(.el-table__body-wrapper .el-table__row:hover td:first-child::before) {
    position: absolute;
    top: 0;
    left: 0;
    width: 3px;
    height: 100%;
    content: "";
    background: var(--color-primary-600);
    border-radius: 0 2px 2px 0;
  }

  .tag-name-cell {
    display: flex;
    align-items: center;
  }

  .color-display {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: center;

    .color-dot {
      flex-shrink: 0;
      width: 24px;
      height: 24px;
      border-radius: 50%;
      box-shadow: 0 0 0 1px var(--border-base);
    }

    .color-text {
      font-family: monospace;
      font-size: 12px;
      color: var(--text-tertiary);
    }
  }

  .action-buttons {
    display: flex;
    gap: 4px;
    align-items: center;
    justify-content: center;
  }
}

.table-empty {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding-top: 72px;

  &__icon {
    color: var(--text-tertiary);
    opacity: 0.4;
  }

  &__text {
    margin: 0;
    font-size: 14px;
    color: var(--text-secondary);
  }
}

.table-footer-sticky {
  position: sticky;
  bottom: 0;
  z-index: 13;
  flex-shrink: 0;
  background: var(--surface-base);
  border-top: 1px solid var(--border-subtle);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}

.pager-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
}

.pager-left {
  flex-shrink: 0;
}

.pager-right {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.total-count {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--text-secondary);
}

.page-size-label,
.page-size-suffix {
  font-size: 12px;
  color: var(--text-secondary);
}

.page-size-select {
  width: 88px;
}
</style>
