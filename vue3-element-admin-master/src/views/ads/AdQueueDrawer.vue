<template>
  <el-drawer v-model="visible" title="广告新建队列" size="1150px" destroy-on-close>
    <div class="queue-drawer">
      <!-- 顶部工具栏 -->
      <div class="queue-toolbar">
        <el-button
          type="danger"
          :disabled="selectedIds.length === 0"
          :loading="deleteLoading"
          @click="handleBulkDelete"
        >
          批量删除（{{ selectedIds.length }}）
        </el-button>

        <div class="queue-toolbar__filters">
          <el-select
            v-model="filterStatus"
            placeholder="状态筛选"
            clearable
            style="width: 120px"
            @change="handleFilterChange"
          >
            <el-option label="队列中" :value="1" />
            <el-option label="失败" :value="0" />
            <el-option label="成功" :value="2" />
          </el-select>
        </div>
      </div>

      <!-- 队列表格 -->
      <el-table
        v-loading="tableLoading"
        :data="tableData"
        row-key="id"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />

        <el-table-column
          prop="campaign_name"
          label="广告活动"
          min-width="180"
          show-overflow-tooltip
        />

        <el-table-column prop="shop" label="店铺" width="90" show-overflow-tooltip />

        <el-table-column prop="country" label="国家" width="80" align="center" />

        <el-table-column prop="ad_type_label" label="广告类型" width="90" align="center" />

        <el-table-column prop="created_by_username" label="提交人" width="90" align="center" show-overflow-tooltip />

        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.parse_status === 2 ? 'success' : row.parse_status === 1 ? 'primary' : 'danger'" size="small">
              {{ row.parse_status_label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" align="center">
          <template #default="{ row }">
            <el-button
              v-if="row.parse_status === 0"
              type="danger"
              link
              size="small"
              @click="showFailReason(row)"
            >
              查看原因
            </el-button>
            <el-button
              v-if="row.parse_status === 0"
              type="warning"
              link
              size="small"
              :loading="retryingId === row.id"
              @click="handleRetry(row)"
            >
              重试
            </el-button>
            <el-button
              type="danger"
              link
              size="small"
              :loading="deletingId === row.id"
              @click="handleSingleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="queue-pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadQueue"
          @size-change="handlePageSizeChange"
        />
      </div>
    </div>
  </el-drawer>

  <!-- 失败原因弹窗 -->
  <el-dialog v-model="failDialogVisible" title="失败原因" width="480px">
    <p class="fail-reason-text">{{ currentFailMsg }}</p>
    <template #footer>
      <el-button @click="failDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 广告新建队列抽屉组件。
 * 展示当前所有广告新建队列记录，支持状态过滤、多选批量删除、单条删除、失败原因查看。
 * 所属板块：ads。
 */
import type { AdQueueItem, AdQueueQuery } from "@/api/ads/index";

import { ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { bulkDeleteAdQueue, getAdQueue, retryAdQueue } from "@/api/ads/index";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

/** 双向绑定抽屉显隐，打开时自动加载第一页 */
const visible = ref(props.visible);
watch(
  () => props.visible,
  (val) => {
    visible.value = val;
    if (val) {
      currentPage.value = 1;
      loadQueue();
    }
  }
);
watch(visible, (val) => emit("update:visible", val));

// 表格数据
const tableData = ref<AdQueueItem[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const tableLoading = ref(false);

// 多选状态
const selectedIds = ref<number[]>([]);
const deleteLoading = ref(false);

// 状态过滤
const filterStatus = ref<number | undefined>(undefined);

// 失败原因弹窗
const failDialogVisible = ref(false);
const currentFailMsg = ref("");

// 单条删除加载态
const deletingId = ref<number | null>(null);

// 单条重试加载态
const retryingId = ref<number | null>(null);

/**
 * 加载队列记录列表（分页）。
 *
 * @returns {Promise<void>}
 */
async function loadQueue(): Promise<void> {
  if (tableLoading.value) return;
  tableLoading.value = true;
  try {
    const params: AdQueueQuery = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (filterStatus.value !== undefined) {
      params.parse_status = filterStatus.value;
    }
    const res = await getAdQueue(params);
    tableData.value = res.list;
    total.value = res.total;
  } catch {
    ElMessage.error("加载队列失败，请重试");
  } finally {
    tableLoading.value = false;
  }
}

/**
 * 表格多选变更处理。
 *
 * @param {AdQueueItem[]} rows - 当前选中的行数组
 */
function handleSelectionChange(rows: AdQueueItem[]): void {
  selectedIds.value = rows.map((r) => r.id);
}

/**
 * 批量删除选中的队列记录。
 *
 * @returns {Promise<void>}
 */
async function handleBulkDelete(): Promise<void> {
  if (selectedIds.value.length === 0) return;
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedIds.value.length} 条队列记录？此操作不可恢复。`,
      "批量删除",
      { type: "warning", confirmButtonText: "确认删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }

  deleteLoading.value = true;
  try {
    const res = await bulkDeleteAdQueue(selectedIds.value);
    ElMessage.success(`已删除 ${res.deleted_count} 条记录`);
    selectedIds.value = [];
    currentPage.value = 1;
    await loadQueue();
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    deleteLoading.value = false;
  }
}

/**
 * 筛选条件变更时重置到第一页并重新加载。
 */
function handleFilterChange(): void {
  currentPage.value = 1;
  loadQueue();
}

/**
 * 每页条数变更处理。
 */
function handlePageSizeChange(): void {
  currentPage.value = 1;
  loadQueue();
}

/**
 * 删除单条队列记录。
 *
 * @param {AdQueueItem} row - 要删除的队列记录行
 * @returns {Promise<void>}
 */
async function handleSingleDelete(row: AdQueueItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认删除该条记录（${row.campaign_name} / ${row.country}）？`,
      "删除确认",
      { type: "warning", confirmButtonText: "确认删除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  deletingId.value = row.id;
  try {
    await bulkDeleteAdQueue([row.id]);
    ElMessage.success("删除成功");
    await loadQueue();
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    deletingId.value = null;
  }
}

/**
 * 展示失败记录的错误原因弹窗。
 *
 * @param {AdQueueItem} row - 失败的队列记录行
 */
function showFailReason(row: AdQueueItem): void {
  currentFailMsg.value = row.msg || "暂无错误信息";
  failDialogVisible.value = true;
}

/**
 * 将单条失败记录重置为待提交状态。
 *
 * @param {AdQueueItem} row - 要重试的队列记录行
 * @returns {Promise<void>}
 */
async function handleRetry(row: AdQueueItem): Promise<void> {
  retryingId.value = row.id;
  try {
    await retryAdQueue([row.id]);
    ElMessage.success("已重置为队列中");
    await loadQueue();
  } catch {
    ElMessage.error("重试失败，请重试");
  } finally {
    retryingId.value = null;
  }
}
</script>

<style scoped lang="scss">
.queue-drawer {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 4px 0;
}

.queue-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;

  &__filters {
    display: flex;
    gap: 8px;
  }
}

.queue-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 4px;
}

.text-muted {
  font-size: 13px;
  color: #c0c4cc;
}

.fail-reason-text {
  line-height: 1.6;
  color: #f56c6c;
  word-break: break-all;
}
</style>
