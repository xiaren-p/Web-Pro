<template>
  <el-drawer v-model="visible" title="广告新建队列" size="1200px" destroy-on-close>
    <div class="queue-drawer">
      <!-- 顶部工具栏 -->
      <div class="queue-toolbar">
        <div class="queue-toolbar__left">
          <el-button
            type="danger"
            plain
            :disabled="selectedIds.length === 0"
            :loading="deleteLoading"
            @click="handleBulkDelete"
          >
            批量删除
            <span v-if="selectedIds.length > 0" class="selected-badge">
              {{ selectedIds.length }}
            </span>
          </el-button>
          <el-button
            type="warning"
            plain
            :disabled="selectedRetryableIds.length === 0"
            :loading="bulkRetryLoading"
            @click="handleBulkRetry"
          >
            批量重试
            <span v-if="selectedRetryableIds.length > 0" class="selected-badge">
              {{ selectedRetryableIds.length }}
            </span>
          </el-button>
        </div>

        <div class="queue-toolbar__right">
          <!-- 用户筛选器：仅拥有 ads:queue:view-all 权限时可见 -->
          <el-select
            v-if="canViewAll"
            v-model="filterUserId"
            placeholder="全部用户"
            clearable
            style="width: 150px"
            @change="handleFilterChange"
          >
            <el-option v-for="u in userOptions" :key="u.value" :label="u.label" :value="u.value" />
          </el-select>
          <el-date-picker
            v-model="filterDateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            range-separator="—"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 230px"
            @change="handleFilterChange"
          />
          <el-select
            v-model="filterStatus"
            placeholder="全部状态"
            clearable
            style="width: 110px"
            @change="handleFilterChange"
          >
            <el-option label="队列中" :value="1" />
            <el-option label="成功" :value="2" />
            <el-option label="失败" :value="0" />
            <el-option label="异常" :value="3" />
          </el-select>
        </div>
      </div>

      <!-- 队列表格 -->
      <el-table
        v-loading="tableLoading"
        :data="tableData"
        row-key="id"
        stripe
        border
        highlight-current-row
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="46" />

        <el-table-column
          prop="campaign_name"
          label="广告活动"
          min-width="200"
          show-overflow-tooltip
        />

        <el-table-column prop="shop" label="店铺" width="100" show-overflow-tooltip />

        <el-table-column prop="country" label="国家" width="70" align="center" />

        <el-table-column prop="ad_type_label" label="类型" width="70" align="center" />

        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.parse_status)" size="small" round>
              {{ row.parse_status_label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at_display" label="创建时间" width="142" align="center" />

        <el-table-column label="操作" width="148" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.parse_status === 0 || row.parse_status === 3"
              type="info"
              link
              size="small"
              @click="showFailReason(row)"
            >
              原因
            </el-button>
            <el-button
              v-if="row.parse_status === 0 || row.parse_status === 3"
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

  <!-- 失败/异常原因弹窗 -->
  <el-dialog v-model="failDialogVisible" title="执行原因" width="480px">
    <div class="fail-reason-box">
      <p class="fail-reason-text">{{ currentFailMsg }}</p>
    </div>
    <template #footer>
      <el-button @click="failDialogVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 广告新建队列抽屉组件。
 * 展示广告新建队列记录，支持日期范围 + 状态过滤、多选批量删除、
 * 单条删除、失败/异常原因查看与颗粒重试。
 * 拥有 ads:queue:view-all 权限的用户可加载用户筛选器，查看其他用户的队列。
 * 所属板块：ads。
 */
import type { AdQueueItem, AdQueueQuery } from "@/api/ads/index";
import type { UserPageVO } from "@/api/user";

import { computed, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { bulkDeleteAdQueue, getAdQueue, retryAdQueue } from "@/api/ads/index";
import { UserAPI } from "@/api/user";
import { hasPerm } from "@/utils/auth";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

/** 拥有 ads:queue:view-all 权限的用户可看到用户筛选器 */
const canViewAll = computed(() => hasPerm("ads:queue:view-all"));

/** 双向绑定抽屉显隐，打开时自动加载第一页 */
const visible = ref(props.visible);
watch(
  () => props.visible,
  (val) => {
    visible.value = val;
    if (val) {
      currentPage.value = 1;
      if (canViewAll.value) loadUserOptions();
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

// 用户筛选（仅拥有 ads:queue:view-all 权限时可用）
const filterUserId = ref<number | undefined>(undefined);
const userOptions = ref<{ label: string; value: number }[]>([]);

// 状态过滤
const filterStatus = ref<number | undefined>(undefined);

// 日期范围过滤，默认近三天
const filterDateRange = ref<[string, string] | null>(getDefaultDateRange());

// 失败/异常原因弹窗
const failDialogVisible = ref(false);
const currentFailMsg = ref("");

// 单条删除加载态
const deletingId = ref<number | null>(null);

// 单条重试加载态
const retryingId = ref<number | null>(null);

// 批量重试加载态
const bulkRetryLoading = ref(false);

/** 当前选中行中处于失败（0）或异常（3）状态的 ID 列表 */
const selectedRetryableIds = computed(() => {
  return tableData.value
    .filter(
      (r) => selectedIds.value.includes(r.id) && (r.parse_status === 0 || r.parse_status === 3)
    )
    .map((r) => r.id);
});

/**
 * 获取近三天日期范围（含今天），格式为 YYYY-MM-DD。
 * 使用本地日期而非 UTC，避免东八区用户凌晨出现日期偏差。
 *
 * @returns {[string, string]} [起始日期, 截止日期]
 */
function getDefaultDateRange(): [string, string] {
  const fmt = (d: Date): string => {
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  };
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 2);
  return [fmt(start), fmt(end)];
}

/** * 加载用户列表，用于管理员筛选器。
 * 仅在 canViewAll=true 时调用，重复调用不会重复请求。
 *
 * @returns {Promise<void>}
 */
async function loadUserOptions(): Promise<void> {
  if (userOptions.value.length > 0) return;
  try {
    const res = await UserAPI.getPage({ pageNum: 1, pageSize: 100 });
    userOptions.value = (res.list ?? []).map((u: UserPageVO) => ({
      label: u.nickname ? `${u.nickname} (${u.username})` : (u.username ?? String(u.id)),
      value: Number(u.id),
    }));
  } catch {
    // 用户列表加载失败不阻断主流程，静默失败
  }
}

/** * 根据 parse_status 值返回对应的 el-tag type。
 *
 * @param {number} status - 状态值（0=失败 1=队列中 2=成功 3=异常）
 * @returns {"primary" | "success" | "warning" | "info" | "danger"} Element Plus tag 类型
 */
function statusTagType(status: number): "primary" | "success" | "warning" | "info" | "danger" {
  if (status === 2) return "success";
  if (status === 1) return "primary";
  if (status === 3) return "warning";
  return "danger";
}

/**
 * 加载队列记录列表（分页），携带日期范围与状态过滤参数。
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
    if (filterDateRange.value) {
      params.date_start = filterDateRange.value[0];
      params.date_end = filterDateRange.value[1];
    }
    // 管理员选了具体用户时，传 user_id 参数到后端
    if (canViewAll.value && filterUserId.value !== undefined) {
      params.user_id = filterUserId.value;
    }
    const res = await getAdQueue(params);
    tableData.value = res.list;
    total.value = res.total;
    selectedIds.value = [];
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
    if (res.deleted_count > 0) {
      ElMessage.success(`已删除 ${res.deleted_count} 条记录`);
    } else {
      ElMessage.warning("未删除任何记录，请确认是否有操作权限或记录已被删除");
    }
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
    const res = await bulkDeleteAdQueue([row.id]);
    if (res.deleted_count > 0) {
      ElMessage.success("删除成功");
    } else {
      ElMessage.warning("未删除记录，请确认是否有操作权限或记录已被删除");
    }
    await loadQueue();
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    deletingId.value = null;
  }
}

/**
 * 展示失败/异常记录的执行原因弹窗。
 *
 * @param {AdQueueItem} row - 失败或异常的队列记录行
 */
function showFailReason(row: AdQueueItem): void {
  currentFailMsg.value = row.msg || "暂无错误信息";
  failDialogVisible.value = true;
}

/**
 * 将失败/异常记录重置为队列中（PENDING）状态，保留已完成步骤 ID，从断点继续。
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

/**
 * 批量重试：将选中的失败/异常记录重置为队列中状态。
 * 非失败/异常状态的选中行将自动忽略，仅对可重试项操作。
 *
 * @returns {Promise<void>}
 */
async function handleBulkRetry(): Promise<void> {
  if (selectedRetryableIds.value.length === 0) return;
  try {
    await ElMessageBox.confirm(
      `确认批量重试选中的 ${selectedRetryableIds.value.length} 条失败/异常记录？`,
      "批量重试",
      { type: "warning", confirmButtonText: "确认重试", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }

  bulkRetryLoading.value = true;
  try {
    const res = await retryAdQueue(selectedRetryableIds.value);
    ElMessage.success(`已重置 ${res.retried_count} 条记录为队列中`);
    selectedIds.value = [];
    await loadQueue();
  } catch {
    ElMessage.error("批量重试失败，请重试");
  } finally {
    bulkRetryLoading.value = false;
  }
}
</script>

<style scoped lang="scss">
.queue-drawer {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 2px 0 8px;
}

/* 工具栏 */
.queue-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: var(--el-fill-color-extra-light);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;

  &__left {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  &__right {
    display: flex;
    gap: 10px;
    align-items: center;
  }
}

/* 已选数量角标 */
.selected-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  margin-left: 4px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  color: #fff;
  background: var(--el-color-danger);
  border-radius: 9px;
}

/* 分页 */
.queue-pagination {
  display: flex;
  justify-content: flex-end;
  padding-top: 4px;
}

/* 失败/异常原因弹窗 */
.fail-reason-box {
  padding: 4px 2px;
}

.fail-reason-text {
  margin: 0;
  line-height: 1.7;
  color: var(--el-color-danger);
  word-break: break-all;
  white-space: pre-wrap;
}
</style>
