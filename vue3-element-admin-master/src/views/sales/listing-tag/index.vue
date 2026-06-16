<template>
  <div class="app-container">
    <ListingTagSearchForm :type-options="typeOptions" @search="handleSearch" @reset="handleReset" />

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--left">
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
        <div class="data-table__toolbar--right">
          <el-tooltip content="列配置" placement="top">
            <el-button text :icon="Setting" @click="columnConfigVisible = true" />
          </el-tooltip>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="tableData"
        class="data-table__content"
        border
        height="calc(100vh - 300px)"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" fixed="left" align="center" />
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
                <el-button link type="primary" size="small" @click="handleEdit(scope.row)">
                  编辑
                </el-button>
                <el-button link type="danger" size="small" @click="handleDelete(scope.row)">
                  删除
                </el-button>
              </div>
            </template>

            <span v-else>{{ scope.row[col.prop] || "-" }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          size="small"
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="pageNum"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <ListingTagEditDialog
      v-model:visible="editDialogVisible"
      :row="currentEditRow"
      :type-options="typeOptions"
      @success="handleQueryAndRefresh"
    />

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="columns"
      @save="handleConfigSave"
      @reset="handleConfigReset"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Plus, Delete, Setting } from "@element-plus/icons-vue";
import { useListingTag } from "@/views/sales/listing-tag/useListingTag";
import ListingTagSearchForm from "@/views/sales/listing-tag/components/ListingTagSearchForm.vue";
import ListingTagEditDialog from "@/views/sales/listing-tag/components/ListingTagEditDialog.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import type { ListingTagVO } from "@/api/sales/listing-tag";

defineOptions({ name: "SalesListingTag" });

const listingTagHooks = useListingTag();

const {
  loading,
  tableData,
  pageNum,
  pageSize,
  total,
  columns,
  tableColumns,
  selectedRows,
  columnConfigVisible,
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
  handleConfigSave,
  handleConfigReset,
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
.data-table {
  :deep(.el-card__body) {
    padding: 16px;
  }

  &__toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    &--left {
      display: flex;
      gap: 8px;
    }
  }

  &__content {
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
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
