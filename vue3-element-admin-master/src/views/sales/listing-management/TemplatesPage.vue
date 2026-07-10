<template>
  <div class="templates-page">
    <!-- 筛选区 -->
    <section class="templates-page__filters content-block">
      <el-form :inline="true" :model="filterParams" size="small" class="templates-filter-form">
        <el-form-item label="模板名称" prop="keyword">
          <el-input
            v-model="filterParams.keyword"
            placeholder="请输入模板名称"
            clearable
            class="filter-search-input"
            @keyup.enter="handleSearch"
          >
            <template #append>
              <el-button type="primary" :icon="Search" @click="handleSearch">搜索</el-button>
            </template>
          </el-input>
        </el-form-item>
      </el-form>
    </section>

    <!-- 表格区 -->
    <section class="templates-page__table content-block content-block--flush">
      <!-- 工具栏 -->
      <div class="templates-toolbar">
        <div class="templates-toolbar__left">
          <el-button type="primary" :icon="Plus" size="small" @click="handleAdd">
            添加模板
          </el-button>
          <el-button size="small" :disabled="!selectedRows.length" @click="handleBatchDelete">
            删除
          </el-button>
        </div>
        <div class="templates-toolbar__right">
          <el-icon :size="20" class="toolbar-icon" @click="loadData"><Refresh /></el-icon>
        </div>
      </div>

      <!-- 表格 -->
      <div ref="wrapperRef" class="templates-table__wrapper">
        <el-table
          v-loading="loading"
          :data="tableData"
          :height="tableHeight"
          class="templates-table"
          empty-text="暂无数据"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="48" align="center" />
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column prop="templateName" label="模板名称" width="200" />
          <el-table-column prop="marketplaceId" label="市场ID" width="160" />
          <el-table-column prop="productType" label="商品类型" width="160" />
          <el-table-column prop="createUserName" label="创建人" width="120" />
          <el-table-column prop="updateUserName" label="更新人" width="120" />
          <el-table-column prop="updatedAt" label="更新时间" width="180" />
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <div class="cell-actions">
                <el-tooltip content="编辑" placement="top">
                  <el-button
                    link
                    type="primary"
                    size="small"
                    :icon="Edit"
                    @click="handleEdit(row)"
                  />
                </el-tooltip>
                <el-tooltip content="删除" placement="top">
                  <el-button
                    link
                    type="danger"
                    size="small"
                    :icon="Delete"
                    @click="handleDelete(row)"
                  />
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 分页 -->
      <div class="templates-pager">
        <div class="templates-pager__row">
          <span class="templates-pager__total">
            <el-icon :size="14"><List /></el-icon>
            共 {{ total }} 条
          </span>
          <div class="templates-pager__controls">
            <el-pagination
              small
              background
              layout="prev, pager, next"
              :total="total"
              :page-size="pageSize"
              :current-page="pageNum"
              @current-change="handlePageChange"
            />
            <span class="templates-pager__label">每页</span>
            <el-select
              :model-value="pageSize"
              size="small"
              class="templates-pager__size-select"
              @change="handleSizeChange"
            >
              <el-option label="20条" :value="20" />
              <el-option label="50条" :value="50" />
              <el-option label="100条" :value="100" />
            </el-select>
            <span class="templates-pager__label">条/页</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
/**
 * 刊登模板列表页。
 *
 * 仿草稿箱风格：自定义 FilterBar + ActionBar + Table + Pagination。
 * 搜索：按模板名称模糊搜索。
 * 新增/编辑：跳转独立编辑页（template-editor）。
 * 删除：软删除（is_deleted=True），支持批量。
 */
import { ref, reactive, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Plus, Refresh, Edit, Delete, List } from "@element-plus/icons-vue";
import { ListingPublishAPI } from "@/api/sales/listing-publish";
import type { PublishTemplateListVO } from "@/api/sales/listing-publish";

defineOptions({ name: "TemplatesPage" });

const router = useRouter();

/** 筛选参数。 */
const filterParams = reactive({ keyword: "" });

/** 表格数据。 */
const tableData = ref<PublishTemplateListVO[]>([]);
const loading = ref(false);
const selectedRows = ref<PublishTemplateListVO[]>([]);

/** 分页参数。 */
const pageNum = ref(1);
const pageSize = ref(20);
const total = ref(0);

/** 表格高度自适应。 */
const wrapperRef = ref<HTMLElement>();
const tableHeight = ref<number | undefined>(undefined);
let resizeObserver: ResizeObserver | null = null;

/**
 * 加载模板列表数据。
 */
async function loadData() {
  loading.value = true;
  try {
    const res = await ListingPublishAPI.getTemplatePage({
      pageNum: pageNum.value,
      pageSize: pageSize.value,
      keyword: filterParams.keyword || undefined,
    });
    tableData.value = res.list;
    total.value = res.total;
  } catch {
    tableData.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
  }
}

/** 搜索：重置页码后加载。 */
function handleSearch() {
  pageNum.value = 1;
  loadData();
}

/** 页码变更。 */
function handlePageChange(val: number) {
  pageNum.value = val;
  loadData();
}

/** 每页条数变更。 */
function handleSizeChange(val: number) {
  pageSize.value = val;
  pageNum.value = 1;
  loadData();
}

/** 复选框选中变更。 */
function handleSelectionChange(selection: PublishTemplateListVO[]) {
  selectedRows.value = selection;
}

/** 新增：跳转编辑页。 */
function handleAdd() {
  router.push("/sales/listing-management/template-editor");
}

/** 编辑：跳转编辑页（带 id）。 */
function handleEdit(row: PublishTemplateListVO) {
  router.push({
    path: "/sales/listing-management/template-editor",
    query: { id: String(row.id) },
  });
}

/** 单条删除。 */
async function handleDelete(row: PublishTemplateListVO) {
  try {
    await ElMessageBox.confirm(`确认删除模板"${row.templateName}"？`, "提示", {
      type: "warning",
    });
    await ListingPublishAPI.deleteTemplate(String(row.id));
    ElMessage.success("删除成功");
    loadData();
  } catch {
    // 用户取消或删除失败
  }
}

/** 批量删除。 */
async function handleBatchDelete() {
  if (!selectedRows.value.length) return;
  try {
    await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 个模板？`, "提示", {
      type: "warning",
    });
    for (const row of selectedRows.value) {
      await ListingPublishAPI.deleteTemplate(String(row.id));
    }
    ElMessage.success("批量删除成功");
    loadData();
  } catch {
    // 用户取消或删除失败
  }
}

/** 测量表格容器高度。 */
function measureHeight() {
  if (wrapperRef.value) {
    tableHeight.value = wrapperRef.value.clientHeight;
  }
}

onMounted(() => {
  loadData();
  nextTick(() => {
    measureHeight();
    if (wrapperRef.value) {
      resizeObserver = new ResizeObserver(measureHeight);
      resizeObserver.observe(wrapperRef.value);
    }
  });
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  resizeObserver = null;
});
</script>

<style scoped lang="scss">
.templates-page {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  padding: var(--spacing-6);

  &__filters {
    padding-bottom: 12px;
  }

  &__table {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 420px;
  }
}

.templates-filter-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.filter-search-input {
  width: 240px;
}

/* 工具栏 */
.templates-toolbar {
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

/* 表格 */
.templates-table__wrapper {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.templates-table {
  :deep(.el-table__header-wrapper th.el-table__cell) {
    text-align: center;
  }

  :deep(.el-table .el-table__row:hover > td.el-table__cell:first-child) {
    box-shadow: inset 3px 0 0 var(--color-primary-600);
  }
}

.cell-actions {
  display: flex;
  gap: 2px;
  align-items: center;
  justify-content: center;

  :deep(.el-button) {
    min-height: unset;
    padding: 4px;
  }
}

/* 分页 */
.templates-pager {
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
