<template>
  <div class="listing-tag-page">
    <section class="content-block filter-block">
      <ListingTagSearchForm
        :type-options="typeOptions"
        @search="handleSearch"
        @reset="handleReset"
      />
    </section>

    <section class="content-block table-block">
      <div class="table-controls">
        <div class="left-controls">
          <el-button type="primary" class="primary-action-btn" :icon="Plus" @click="handleAdd">
            新增标签
          </el-button>
          <el-button
            class="danger-action-btn"
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
                {{ scope.row.tagName || "-" }}
              </template>

              <template v-else-if="col.prop === 'type'">
                {{ scope.row.type || "-" }}
              </template>

              <template v-else-if="col.prop === 'color'">
                <span class="color-dot" :style="{ backgroundColor: scope.row.color }"></span>
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
                    :disabled="scope.row.status === 'creating' || scope.row.status === 'deleting'"
                    @click="handleEdit(scope.row)"
                  >
                    编辑
                  </el-button>
                  <el-button
                    link
                    type="danger"
                    size="small"
                    :disabled="scope.row.status === 'creating' || scope.row.status === 'deleting'"
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
            <el-select
              :model-value="pageSize"
              size="small"
              class="page-size-select"
              @change="handleSizeChange"
            >
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
  padding: 20px 24px 0;
  background:
    radial-gradient(circle at top left, rgba(37, 99, 235, 0.06), transparent 32rem),
    linear-gradient(180deg, #f8fafc 0%, #f6f8fb 48%, #eef2f7 100%);
}

.content-block {
  flex-shrink: 0;
  margin-bottom: 16px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px rgba(15, 23, 42, 0.04);
}

.filter-block {
  padding: 18px 24px;
}

.table-block {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: 0;
  overflow: hidden;
  --table-bg: #f8f9fb;
}

.table-controls {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-bottom: 1px solid #e2e8f0;
  border-radius: 18px 18px 0 0;
}

.left-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.primary-action-btn {
  padding: 0 16px;
  font-weight: 600;
  color: #ffffff;
  background: #2563eb;
  border-color: #2563eb;
  border-radius: 10px;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18);

  &:hover {
    color: #ffffff;
    background: #1d4ed8;
    border-color: #1d4ed8;
  }
}

.danger-action-btn {
  padding: 0 16px;
  font-weight: 600;
  color: #ffffff;
  background: #dc2626;
  border-color: #dc2626;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(220, 38, 38, 0.2);

  &:hover {
    color: #ffffff;
    background: #b91c1c;
    border-color: #b91c1c;
  }

  &.is-disabled {
    color: #94a3b8;
    background: #f1f5f9;
    border-color: #e2e8f0;
    box-shadow: none;
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
    background: var(--table-bg, #f8f9fb);
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

  :deep(.el-table__header-wrapper) {
    background: #f0f2f5;
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

  :deep(.el-table__header th.el-table__cell) {
    background: #f0f2f5;
    border-right: none !important;
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

  .color-dot {
    display: inline-block;
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    vertical-align: middle;
    border-radius: 5px;
    box-shadow: 0 0 0 1px var(--border-base);
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
  border-radius: 0 0 18px 18px;
}

.pager-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 18px;
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
