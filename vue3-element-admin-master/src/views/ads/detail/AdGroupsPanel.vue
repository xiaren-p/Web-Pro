<template>
  <div class="ad-groups-panel">
    <!-- 筛选栏（全部控件同一行，风格对齐广告活动页） -->
    <div class="filter-bar">
      <el-date-picker
        v-model="filters.range"
        size="small"
        class="filter-item date-picker"
        type="daterange"
        start-placeholder="开始"
        end-placeholder="结束"
        range-separator=" - "
        value-format="YYYY-MM-DD"
        style="width: 218px"
        unlink-panels
      />
      <el-select
        v-model="filters.state"
        size="small"
        class="filter-item w-110"
        placeholder="全部状态"
        clearable
      >
        <el-option label="全部状态" value="" />
        <el-option label="启用" value="enabled" />
        <el-option label="暂停" value="paused" />
        <el-option label="归档" value="archived" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item keyword-input"
        placeholder="请输入广告组"
        clearable
      />

      <!-- 列配置图标按钮（打开 ColumnManager 抽屉） -->
      <el-tooltip content="列配置" placement="top">
        <el-button
          text
          style="height: 32px; min-height: 32px; padding: 4px 9px; font-size: 16px; color: #606266"
          @click="columnConfigVisible = true"
        >
          <el-icon><Operation /></el-icon>
        </el-button>
      </el-tooltip>

      <!-- 筛选模板 / 查询 / 重置 -->
      <el-button size="small" :icon="Filter" class="btn-template">筛选模板</el-button>
      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>
    </div>

    <!-- 表格 -->
    <div class="data-table-container">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        :border="false"
        :row-class-name="rowClassName"
        height="calc(100vh - 380px)"
        style="width: 100%"
        @selection-change="onSelectionChange"
      >
        <!-- 固定左侧：勾选列 -->
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :selectable="(row: any) => !row._isSummary"
        />

        <!-- 固定左侧：有效 -->
        <el-table-column label="有效" width="80" fixed="left" align="center">
          <template #default="{ row }">
            <el-switch
              v-if="!row._isSummary"
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
          </template>
        </el-table-column>

        <!-- 固定左侧：广告组 -->
        <el-table-column
          label="广告组"
          min-width="280"
          fixed="left"
          align="left"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <span v-else class="group-name-text">{{ row.name || "-" }}</span>
          </template>
        </el-table-column>

        <!-- 动态列（由 ColumnManager 控制 visible） -->
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="(col as any).minWidth || 120"
          align="center"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <template v-if="row._isSummary">---</template>
              <span
                v-else
                class="status-badge"
                :class="`status-${row.service_status_type || 'default'}`"
              >
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'default_bid'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="bid-cell">
                <span class="bid-icon">{{ currencyIcon }}</span>
                <el-input
                  v-model="row.default_bid"
                  size="small"
                  class="bid-input"
                  @change="onBidChange(row)"
                />
              </div>
            </template>
            <template v-else-if="col.prop === 'campaign_name'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="campaign-name-cell">
                <span
                  class="state-dot"
                  :class="`dot-${row.campaign_state_type || 'default'}`"
                ></span>
                <span class="campaign-name-text">{{ row.campaign_name || "-" }}</span>
              </div>
            </template>
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右侧：分析 -->
        <el-table-column label="分析" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="row.ad_group_id && !row._isSummary" type="primary" link size="small">
              分析
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页栏 -->
      <div class="pager-row">
        <span class="total-count">共 {{ total.toLocaleString() }} 条</span>
        <el-select
          v-model="pageSize"
          placeholder="每页"
          style="width: 100px"
          @change="onPageSizeChange"
        >
          <el-option label="25条/页" :value="25" />
          <el-option label="50条/页" :value="50" />
          <el-option label="100条/页" :value="100" />
          <el-option label="250条/页" :value="250" />
        </el-select>
        <el-pagination
          background
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, jumper"
          @current-change="onPageChange"
        />
      </div>
    </div>

    <!-- 通用列配置抽屉 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Operation, Filter } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { getAdGroups } from "@/api/ads";

defineOptions({ name: "AdGroupsPanel" });

/**
 * 父页面透传过来的初始日期范围（路由 query 中的 date_start / date_end）。
 * 若存在则作为筛选栏的默认时间，用户可自行修改。
 *
 * @prop {string} campaignId - 广告活动 ID（必填，用于查询广告组）
 * @prop {string} profileId - 店铺 Profile ID（必填，用于数据隔离）
 * @prop {string[]} initialDateRange - 格式 ['YYYY-MM-DD', 'YYYY-MM-DD'] 或空数组
 */
const props = defineProps<{
  campaignId?: string;
  profileId?: string;
  initialDateRange?: string[];
}>();

/** 筛选条件状态，range 以父页面传入的日期范围初始化 */
const filters = ref({
  range: (props.initialDateRange?.length === 2 ? [...props.initialDateRange] : []) as string[],
  state: "",
  keyword: "",
});

/** 列配置抽屉显示状态 */
const columnConfigVisible = ref(false);

/** 数据加载状态 */
const loading = ref(false);

/** 分页状态 */
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(25);

/** 表格数据（后端返回的广告组列表） */
const tableData = ref<any[]>([]);

/** 汇总行数据（后端返回的 summary，挂载 _isSummary 标志后置顶） */
const summaryRow = ref<Record<string, unknown> | null>(null);

/** 货币符号（从接口响应中获取，用于默认竞价列前缀） */
const currencyIcon = ref<string>("$");

/**
 * 列定义（含 category，供 ColumnManager 分组展示）。
 * visible 控制是否在表格中渲染，由 ColumnManager @save 回调更新。
 */
const activeColumns = ref([
  // 设置
  { prop: "service_status", label: "服务状态", visible: true, category: "设置" },
  { prop: "portfolio_name", label: "广告组合", visible: true, category: "设置" },
  { prop: "campaign_name", label: "广告活动", visible: true, category: "设置", minWidth: 240 },
  { prop: "default_bid", label: "默认竞价", visible: true, category: "设置" },
  { prop: "product", label: "商品", visible: false, category: "设置" },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置" },
  // 转化
  { prop: "adsSales", label: "广告销售额", visible: true, category: "转化" },
  { prop: "adsSalesPercent", label: "广告销售额%", visible: true, category: "转化" },
  { prop: "directSales", label: "直接销售额", visible: false, category: "转化" },
  { prop: "acos", label: "ACoS", visible: true, category: "转化" },
  { prop: "roas", label: "ROAS", visible: true, category: "转化" },
  { prop: "adsOrders", label: "广告订单", visible: true, category: "转化" },
  { prop: "directOrders", label: "直接订单", visible: false, category: "转化" },
  { prop: "cvr", label: "CVR", visible: false, category: "转化" },
  { prop: "adsOrderPrice", label: "广告笔单价", visible: false, category: "转化" },
  { prop: "adsVolume", label: "广告销量", visible: false, category: "转化" },
  // 业绩
  { prop: "impressions", label: "曝光量", visible: true, category: "业绩" },
  { prop: "impressionsPercent", label: "曝光%", visible: false, category: "业绩" },
  { prop: "clicks", label: "点击", visible: true, category: "业绩" },
  { prop: "clicksPercent", label: "点击%", visible: false, category: "业绩" },
  { prop: "ctr", label: "CTR", visible: true, category: "业绩" },
  { prop: "cpc", label: "CPC", visible: true, category: "业绩" },
  { prop: "spends", label: "花费", visible: true, category: "业绩" },
  { prop: "spendsPercent", label: "花费%", visible: false, category: "业绩" },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩" },
]);

/**
 * 从所有列中过滤出 visible=true 的列，用于动态渲染表格列。
 *
 * @returns {当前需要展示的列定义数组}
 */
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

/**
 * 表格展示数据 = 汇总行（置顶）+ 分页数据列表。
 *
 * @returns {any[]} 拼接后的表格数据数组
 */
const displayData = computed<any[]>(() => {
  if (!summaryRow.value) return tableData.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...tableData.value];
});

/**
 * 表格行自定义类名，为汇总行附加样式类。
 *
 * @param {{ row: any }} 下构 - el-table 传入的行上下文
 * @returns {string} CSS 类名
 */
function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

/**
 * ColumnManager 保存回调，用新列配置替换 activeColumns。
 *
 * @param {typeof activeColumns.value} columns - 用户配置后的完整列数组
 */
function onColumnConfigSave(columns: typeof activeColumns.value): void {
  activeColumns.value = columns;
  ElMessage.success("列配置已保存");
}

/**
 * 触发搜索，重置到第一页后加载数据。
 */
function onSearch(): void {
  currentPage.value = 1;
  fetchData();
}

/**
 * 重置所有筛选条件并重新加载。
 */
function onReset(): void {
  filters.value.range = [];
  filters.value.state = "";
  filters.value.keyword = "";
  currentPage.value = 1;
  fetchData();
}

/**
 * 页码变更时触发。
 *
 * @param {number} page - 新页码
 */
function onPageChange(page: number): void {
  currentPage.value = page;
  fetchData();
}

/**
 * 每页条数变更时触发。
 *
 * @param {number} size - 新的每页条数
 */
function onPageSizeChange(size: number): void {
  pageSize.value = size;
  currentPage.value = 1;
  fetchData();
}

/**
 * 加载广告组列表数据，调用后端 /ads/ad-groups 接口。
 * campaign_id / profile_id 由父页面通过 props 传入。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;

  loading.value = true;
  getAdGroups({
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    date_start: filters.value.range?.[0] || undefined,
    date_end: filters.value.range?.[1] || undefined,
    state: filters.value.state || undefined,
    keyword: filters.value.keyword || undefined,
    pageNum: currentPage.value,
    pageSize: pageSize.value,
  })
    .then((res) => {
      tableData.value = res.list ?? [];
      total.value = res.total ?? 0;
      summaryRow.value = res.summary ?? null;
      currencyIcon.value = res.currency_icon ?? "$";
    })
    .catch(() => {
      ElMessage.error("广告组数据加载失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

/**
 * 默认竞价修改占位处理（后端接口待实现）。
 * 当前仅本地更新 row.default_bid，不提交后端。
 *
 * @param {any} _row - 当前行数据对象，包含 ad_group_id 与最新 default_bid
 */
function onBidChange(row: any): void {
  // TODO(后端联调): 调用修改广告组默认竞价接口，提交 ad_group_id + default_bid
  void row;
}

/** 当前已勾选的广告组行 */
const selectedRows = ref<any[]>([]);

/**
 * 表格勾选变化回调。
 *
 * @param {any[]} rows - 当前所有已勾选的行数据
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped lang="scss">
.ad-groups-panel {
  padding-top: 12px;
}

/* ────────────────────────────────
   筛选栏（固定宽度，允许换行到第二行）
───────────────────────────────── */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
  background: transparent;

  /* 统一控件高度 */
  :deep(.el-select__wrapper),
  :deep(.el-input__wrapper) {
    min-height: 32px;
  }

  :deep(.el-range-editor.el-input__wrapper) {
    min-height: 32px;
    padding-top: 0;
    padding-bottom: 0;
  }

  :deep(.el-button) {
    height: 32px;
  }

  :deep(.el-button + .el-button) {
    margin-left: 0;
  }
}

.filter-item {
  flex-shrink: 0;
}

.w-110 {
  width: 110px;
}

.date-picker {
  flex: 0 0 218px;

  /* 覆盖 el-date-picker 根元素及内部 wrapper 的宽度 */
  :deep(.el-date-editor.el-input__wrapper),
  :deep(.el-range-editor.el-input__wrapper) {
    width: 218px !important;
    padding: 0 8px;
  }
}

.keyword-input {
  flex: 0 0 180px;
  width: 180px;
}

/* 列配置：图标按钮 */
.btn-icon-only {
  padding: 0 9px;
  color: #606266;
  border-color: #dcdfe6;
}

/* 筛选模板按钮 */
.btn-template {
  color: #606266;
  border-color: #dcdfe6;

  &:hover {
    color: #409eff;
    background: #ecf5ff;
    border-color: #c6e2ff;
  }
}

/* ────────────────────────────────
   数据表格
───────────────────────────────── */
.data-table-container {
  overflow: hidden;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
}

.data-table__content {
  border-top: none;
  border-right: none;
  border-left: none;
}

/* 去掉竖向分割线，仅保留横向细线 */
:deep(.el-table::before),
:deep(.el-table--border::after),
:deep(.el-table--group::after) {
  display: none;
}

:deep(.el-table__header th.el-table__cell) {
  border-right: none !important;
}

:deep(.el-table__body td.el-table__cell) {
  border-bottom: 1px solid #f0f2f5 !important;
}

/* 表头 */
:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  font-size: 13px;
  font-weight: 600 !important;
  color: #374151 !important;
  text-align: center;
  background-color: #f9fafb !important;
  border-bottom: 1px solid #e5e7eb !important;
}

/* 单元格行高 */
:deep(.el-table .el-table__cell) {
  padding: 9px 0 !important;
  font-size: 13px;
  color: #303133;
  border-right: none !important;
}

:deep(.el-table .cell) {
  padding-right: 10px;
  padding-left: 10px;
  line-height: 1.4;
}

/* switch 小型化 + 开启绿色 */
:deep(.el-table .el-switch) {
  height: 16px;
}

:deep(.el-table .el-switch .el-switch__core) {
  width: 30px !important;
  min-width: 30px !important;
  height: 16px !important;
  border-radius: 8px !important;
}

:deep(.el-table .el-switch .el-switch__core .el-switch__action) {
  width: 12px !important;
  height: 12px !important;
}

:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) {
  left: 16px !important;
}

:deep(.el-table .el-switch.is-checked .el-switch__core) {
  background-color: #22c55e !important;
  border-color: #22c55e !important;
}

/* 行 hover */
:deep(.el-table .el-table__row) {
  transition: background-color 0.15s ease;
}

:deep(.el-table .el-table__row:hover > td.el-table__cell) {
  background-color: #f5f7fc !important;
}

/* 广告组名称蓝色链接样式 */
.group-name-text {
  font-size: 13px;
  color: #409eff;
}

/* ────────────────────────────────
   服务状态徽标
───────────────────────────────── */
.status-badge {
  display: inline-block;
  padding: 2px 9px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;
  white-space: nowrap;
  border: 1px solid transparent;
  border-radius: 10px;
}

.status-badge.status-success {
  color: #67c23a;
  background: #f0f9eb;
  border-color: #c2e7b0;
}

.status-badge.status-danger {
  color: #f56c6c;
  background: #fef0f0;
  border-color: #fab6b6;
}

.status-badge.status-warning {
  color: #e6a23c;
  background: #fdf6ec;
  border-color: #f5dab1;
}

.status-badge.status-default {
  color: #909399;
  background: #f4f4f5;
  border-color: #d3d4d6;
}

/* ────────────────────────────────
   分页栏
───────────────────────────────── */
.pager-row {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 16px;
  background-color: #fff;
  border-top: 1px solid #f0f2f5;

  :deep(.el-select .el-input__wrapper) {
    height: 32px !important;
    min-height: 32px !important;
  }

  :deep(.el-select .el-input__inner) {
    height: 30px !important;
    line-height: 30px !important;
  }
}

.total-count {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

/* 默认竞价可编辑小框 */
.bid-cell {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  width: 65px;

  .bid-icon {
    flex-shrink: 0;
    font-size: 12px;
    line-height: 1;
    color: #606266;
  }

  .bid-input {
    flex: 1;
    min-width: 0;

    :deep(.el-input__wrapper) {
      height: 26px;
      min-height: 26px;
      padding: 0 6px;
    }

    :deep(.el-input__inner) {
      height: 24px;
      font-size: 12px;
      text-align: right;
    }
  }
}

/* 广告活动状态圆点 + 名称 */
.campaign-name-cell {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  max-width: 100%;
  overflow: hidden;

  .state-dot {
    flex-shrink: 0;
    width: 8px;
    height: 8px;
    border-radius: 50%;

    &.dot-success {
      background: #67c23a;
    }

    &.dot-warning {
      background: #e6a23c;
    }

    &.dot-danger {
      background: #f56c6c;
    }

    &.dot-default {
      background: #c0c4cc;
    }
  }

  .campaign-name-text {
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 13px;
    white-space: nowrap;
  }
}

/* 汇总行标签 */
.summary-label {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
}

/* 汇总行样式 */
:deep(.el-table .is-summary-row > td.el-table__cell) {
  font-weight: 600;
  color: #1a1a2e;
  background-color: #f0f4ff !important;
  border-top: 1px solid #d0d8ef !important;
  border-bottom: 1px solid #d0d8ef !important;
}
</style>
