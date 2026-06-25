<template>
  <div ref="tableContainerRef" class="data-table-container">
    <div class="data-table__scroll">
      <el-table
        ref="tableRef"
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        :row-class-name="getRowClass"
        border
        style="width: 100%"
        @sort-change="$emit('sort-change', $event)"
        @header-dragend="onHeaderDragEnd"
        @selection-change="onSelectionChange"
      >
        <template #empty>
          <div class="table-empty">
            <div class="table-empty__icon">
              <el-icon :size="48"><List /></el-icon>
            </div>
            <p class="table-empty__text">暂无数据</p>
          </div>
        </template>
        <el-table-column
          type="selection"
          width="48"
          fixed="left"
          align="center"
          :resizable="false"
          :selectable="(row: any) => !row._isSummary"
        >
          <template #default="{ row }">
            <span v-if="row._isSummary" />
          </template>
        </el-table-column>

        <el-table-column label="有效" width="80" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-dash">--</span>
            <div v-else class="state-cell">
              <el-switch
                v-model="row.state"
                active-value="enabled"
                inactive-value="paused"
                @change="(val: string | number | boolean) => onStateChange(row, val)"
              />
              <el-tooltip
                v-if="row.latest_state_adjustment?.has_recent"
                placement="top"
                popper-class="latest-adj-tooltip"
              >
                <span class="recent-star" @click.stop>★</span>
                <template #content>
                  <div class="latest-adj-content">
                    <div v-for="(line, idx) in row.latest_state_adjustment.lines" :key="idx">
                      {{ line }}
                    </div>
                  </div>
                </template>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <template v-if="row._isSummary"><span class="summary-dash">--</span></template>
            <template v-else>
              <div>{{ row.sponsored_type }}</div>
              <div v-if="row.targeting_type" class="targeting-type-line">
                [{{ formatTargetingType(row.targeting_type) }}]
              </div>
            </template>
          </template>
        </el-table-column>
        <el-table-column
          label="店铺/国家"
          width="120"
          prop="profile_alias"
          fixed="left"
          align="center"
          sortable="custom"
          :resizable="false"
        >
          <template #default="{ row }">
            <template v-if="row._isSummary">
              <span class="summary-indicator">
                <el-icon class="summary-icon"><TrendCharts /></el-icon>
                汇总
              </span>
            </template>
            <template v-else>
              <div class="profile-name">{{ row.profile_alias || row.profile_id }}</div>
              <div class="country-tag">{{ row.country_name || "-" }}</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column
          label="广告活动"
          min-width="180"
          prop="name"
          fixed="left"
          align="center"
          sortable="custom"
          :resizable="false"
          show-overflow-tooltip
          :show-overflow-tooltip-delay="500"
        >
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-dash">--</span>
            <router-link
              v-else
              class="campaign-name-link"
              :to="{
                name: 'AdCampaignDetail',
                query: {
                  campaign_id: row.campaign_id,
                  profile_id: row.profile_id,
                  date_start: props.dateRange?.[0] || '',
                  date_end: props.dateRange?.[1] || '',
                },
              }"
            >
              {{ row.name }}
            </router-link>
          </template>
        </el-table-column>

        <el-table-column
          v-for="col in columns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :fixed="col.fixed"
          :sortable="col.sortable ? 'custom' : false"
          :min-width="getColumnMinWidth(col.prop)"
          align="center"
          :show-overflow-tooltip="col.prop !== 'budget'"
          :show-overflow-tooltip-delay="500"
        >
          <template #default="scope">
            <template v-if="col.prop === 'service_status'">
              <template v-if="scope.row._isSummary">--</template>
              <span
                v-else
                class="status-badge"
                :class="`status-badge--${scope.row.service_status_type || 'info'}`"
              >
                {{ scope.row.service_status_label || scope.row.service_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'budget'">
              <!-- 预算列：货币符号 + 直接可编辑输入框 + 最近修改星标 -->
              <span v-if="scope.row._isSummary" class="data-value data-bold">
                {{ scope.row.budget != null ? formatValue(scope.row.budget) : "--" }}
              </span>
              <el-tooltip
                v-else-if="scope.row.latest_budget_adjustment?.has_recent"
                placement="top"
                popper-class="latest-adj-tooltip"
              >
                <div class="budget-cell">
                  <el-input
                    v-model="scope.row._budgetInput"
                    size="small"
                    class="budget-input"
                    type="number"
                    @keyup.enter="confirmBudget(scope.row)"
                    @keyup.esc="resetBudget(scope.row)"
                    @blur="confirmBudget(scope.row)"
                  >
                    <template #prefix>
                      <span class="budget-icon">{{ scope.row.currency_icon || "$" }}</span>
                    </template>
                  </el-input>
                  <span class="recent-star" @click.stop>★</span>
                </div>
                <template #content>
                  <div class="latest-adj-content">
                    <div v-for="(line, idx) in scope.row.latest_budget_adjustment.lines" :key="idx">
                      {{ line }}
                    </div>
                  </div>
                </template>
              </el-tooltip>
              <div v-else class="budget-cell">
                <el-input
                  v-model="scope.row._budgetInput"
                  size="small"
                  class="budget-input"
                  type="number"
                  @keyup.enter="confirmBudget(scope.row)"
                  @keyup.esc="resetBudget(scope.row)"
                  @blur="confirmBudget(scope.row)"
                >
                  <template #prefix>
                    <span class="budget-icon">{{ scope.row.currency_icon || "$" }}</span>
                  </template>
                </el-input>
              </div>
            </template>
            <template v-else>
              <span v-if="scope.row._isSummary && scope.row[col.prop] == null" class="data-null">
                --
              </span>
              <span v-else class="data-value" :class="getDataValueClass(scope.row, col.prop)">
                <span
                  v-if="!scope.row._isSummary && shouldShowTrend(col.prop, scope.row[col.prop])"
                  class="trend-icon"
                  :class="getDataValueClass(scope.row, col.prop)"
                >
                  <el-icon>
                    <TrendCharts v-if="getDataValueClass(scope.row, col.prop) === 'data-up'" />
                    <TrendCharts
                      v-else-if="getDataValueClass(scope.row, col.prop) === 'data-down'"
                      class="trend-icon-down"
                    />
                  </el-icon>
                </span>
                <template v-if="col.prop === 'startDate'">
                  {{ formatDateValue(scope.row[col.prop]) }}
                </template>
                <template v-else>
                  {{ formatValue(scope.row[col.prop]) }}
                </template>
              </span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="分析" width="80" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button
              v-if="!row._isSummary"
              type="primary"
              link
              size="small"
              class="analyze-btn"
              @click="$emit('view-row', row)"
            >
              分析
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="table-footer-sticky">
      <div
        v-show="showHorizontalScroll"
        ref="horizontalScrollRef"
        class="table-horizontal-scroll"
        @scroll="handleProxyScroll"
      >
        <div
          class="table-horizontal-scroll__inner"
          :style="{ width: `${horizontalScrollWidth}px` }"
        />
      </div>

      <div class="pager-row">
        <div class="pager-left">
          <span class="total-count">
            <el-icon class="count-icon"><List /></el-icon>
            共 {{ total.toLocaleString() }} 条
          </span>
          <template v-if="selectedRows.length > 0">
            <span class="batch-divider" />
            <span class="batch-info">已选 {{ selectedRows.length }} 条</span>
            <el-dropdown trigger="click" @command="handleBatchStateCommand">
              <el-button size="small" class="batch-btn">调状态</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="enabled">启用</el-dropdown-item>
                  <el-dropdown-item command="paused">暂停</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-button size="small" class="batch-btn" @click="$emit('batch-budget', selectedRows)">
              调预算
            </el-button>
          </template>
        </div>
        <div class="pager-center">
          <el-pagination
            background
            :current-page="currentPage"
            :page-size="localPageSize"
            :total="total"
            layout="prev, pager, next"
            @current-change="$emit('current-change', $event)"
          />
        </div>
        <div class="pager-right">
          <span class="page-size-label">每页</span>
          <el-select v-model="localPageSize" class="page-size-select" @change="onPageSizeChange">
            <el-option label="25条" :value="25" />
            <el-option label="50条" :value="50" />
            <el-option label="100条" :value="100" />
            <el-option label="250条" :value="250" />
          </el-select>
          <span class="page-size-suffix">条/页</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted, onBeforeUnmount } from "vue";
import { TrendCharts, List } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";

const props = withDefaults(
  defineProps<{
    tableData: any[];
    pageSize: number;
    currentPage: number;
    total: number;
    columns: any[];
    loading?: boolean;
    summary?: Record<string, unknown> | null;
    /** 父页面当前选中的日期范围，透传给详情页作为默认值 */
    dateRange?: string[];
  }>(),
  {
    loading: false,
    summary: null,
    dateRange: () => [],
  }
);

const emit = defineEmits([
  "current-change",
  "view-row",
  "page-size-change",
  "sort-change",
  "update-budget",
  "update-state",
  "batch-state",
  "batch-budget",
]);
const tableRef = ref();
const selectedRows = ref<any[]>([]);
const localPageSize = ref(props.pageSize || 25);
const tableContainerRef = ref<HTMLElement | null>(null);
const horizontalScrollRef = ref<HTMLElement | null>(null);
const horizontalScrollWidth = ref(0);
const showHorizontalScroll = ref(false);
let bodyWrapperElement: HTMLElement | null = null;
let isSyncingScroll = false;

/**
 * 获取 Element Plus 表格横向滚动容器。
 *
 * @returns {HTMLElement | null} 表格主体滚动容器
 */
function getBodyWrapperElement(): HTMLElement | null {
  const table = tableContainerRef.value;
  if (!table) return null;
  return (
    table.querySelector(".el-table__body-wrapper .el-scrollbar__wrap") ??
    table.querySelector(".el-table__body-wrapper")
  );
}

/**
 * 同步悬浮横向滚动条尺寸。
 *
 * @returns {Promise<void>} 完成 DOM 尺寸读取后返回
 */
async function updateHorizontalScrollState(): Promise<void> {
  await nextTick();
  const nextBodyWrapperElement = getBodyWrapperElement();
  if (!nextBodyWrapperElement) return;
  if (bodyWrapperElement !== nextBodyWrapperElement) {
    bodyWrapperElement?.removeEventListener("scroll", handleBodyScroll);
    bodyWrapperElement = nextBodyWrapperElement;
    bodyWrapperElement.addEventListener("scroll", handleBodyScroll, { passive: true });
  }
  const bodyTable = tableContainerRef.value?.querySelector(".el-table__body") as HTMLElement | null;
  const estimatedWidth = 608 + props.columns.length * 120;
  const scrollWidth = Math.max(
    bodyTable?.scrollWidth ?? 0,
    bodyWrapperElement.scrollWidth,
    estimatedWidth
  );
  horizontalScrollWidth.value = scrollWidth;
  showHorizontalScroll.value = scrollWidth > bodyWrapperElement.clientWidth;
}

/**
 * 代理滚动条滚动时同步表格主体横向位置。
 *
 * @returns {void} 无返回值
 */
function handleProxyScroll(): void {
  if (!horizontalScrollRef.value || !bodyWrapperElement || isSyncingScroll) return;
  isSyncingScroll = true;
  bodyWrapperElement.scrollLeft = horizontalScrollRef.value.scrollLeft;
  requestAnimationFrame(() => {
    isSyncingScroll = false;
  });
}

/**
 * 表格主体横向滚动时同步代理滚动条位置。
 *
 * @returns {void} 无返回值
 */
function handleBodyScroll(): void {
  if (!horizontalScrollRef.value || !bodyWrapperElement || isSyncingScroll) return;
  isSyncingScroll = true;
  horizontalScrollRef.value.scrollLeft = bodyWrapperElement.scrollLeft;
  requestAnimationFrame(() => {
    isSyncingScroll = false;
  });
}

onMounted(async () => {
  await updateHorizontalScrollState();
  window.addEventListener("resize", updateHorizontalScrollState);
});

onBeforeUnmount(() => {
  bodyWrapperElement?.removeEventListener("scroll", handleBodyScroll);
  window.removeEventListener("resize", updateHorizontalScrollState);
});

watch(
  () => [props.tableData, props.columns],
  () => {
    updateHorizontalScrollState();
  },
  { deep: true }
);

/**
 * 将汇总行置于列表首位，与当前页数据合并展示。
 * 无行数据时不展示汇总行，交由 empty 插槽处理。
 *
 * @returns {any[]} 以汇总行开头的完整表格数据；无数据时返回空数组
 */
const displayData = computed<any[]>(() => {
  if (!props.tableData || props.tableData.length === 0) return [];
  // 为每个数据行注入预算输入框临时绑定字段（响应式）
  for (const row of props.tableData) {
    if (row._isSummary) continue;
    if (row._budgetInput === undefined || row._budgetInput === null) {
      row._budgetInput = row.budget;
    }
  }
  if (!props.summary) return props.tableData;
  const summaryRow: Record<string, unknown> = {
    _isSummary: true,
    name: "汇总",
    ...props.summary,
  };
  return [summaryRow, ...props.tableData];
});

/**
 * 为汇总行附加专属 CSS 类名，用于高亮显示。
 *
 * @param {{ row: any; rowIndex: number }} param0 - 当前行数据对象
 * @returns {string} 汇总行返回 "summary-row"，偶数行返回 "zebra-row"
 */
function getRowClass({ row, rowIndex }: { row: any; rowIndex: number }): string {
  if (row._isSummary) return "summary-row";
  const dataIndex = rowIndex - (props.summary ? 1 : 0);
  return dataIndex % 2 === 1 ? "zebra-row" : "";
}

watch(
  () => props.pageSize,
  (v) => {
    localPageSize.value = v;
  }
);

function onPageSizeChange(v: number) {
  emit("page-size-change", v);
}

/**
 * 表格选中行变更：过滤汇总行，仅保留数据行。
 *
 * @param {any[]} rows - Element Plus 返回的当前选中行
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows.filter((r) => !r._isSummary);
}

/**
 * 批量调状态命令处理：向上 emit batch-state 事件。
 *
 * @param {string} state - 目标状态 enabled / paused
 */
function handleBatchStateCommand(state: string): void {
  if (selectedRows.value.length === 0) return;
  emit("batch-state", { rows: selectedRows.value, state });
}

// ── 预算/状态可编辑 ─────────────────────────────────────────────────────────────
// 预算输入框直接渲染，每行用 _budgetInput 临时字段绑定；confirmBudget 校验后 emit。

/**
 * 确认预算修改：弹窗确认后向上 emit update-budget，由父组件调 API 并回写 row.budget。
 * 值未变化时拦截，避免写无意义调整记录。父组件失败时会还原 row.budget，
 * 此处同步还原 _budgetInput。
 *
 * @param {any} row - 表格行
 * @returns {Promise<void>}
 */
async function confirmBudget(row: any): Promise<void> {
  // 防抖：blur 与 enter 可能同时触发，避免重复弹窗
  if (row._confirming) return;
  const val = Number(row._budgetInput);
  const original = Number(row.budget);
  if (!val || val <= 0 || isNaN(val)) {
    row._budgetInput = row.budget;
    return;
  }
  if (val === original) {
    return;
  }
  row._confirming = true;
  try {
    await ElMessageBox.confirm(
      `确认将预算从 ${original.toFixed(2)} 修改为 ${val.toFixed(2)}？`,
      "确认修改预算",
      { confirmButtonText: "确认", cancelButtonText: "取消", type: "warning" }
    );
    emit("update-budget", { row, budget: val });
  } catch {
    // 用户取消：还原输入框
    row._budgetInput = row.budget;
  } finally {
    row._confirming = false;
  }
}

/**
 * 还原预算输入框为当前 row.budget（esc 或点击取消图标时调用）。
 *
 * @param {any} row - 表格行
 */
function resetBudget(row: any): void {
  row._budgetInput = row.budget;
}

/**
 * 状态 switch 变更：弹窗确认后向上 emit update-state，由父组件调 API 并回写行。
 * 用户取消时还原 switch 为原值。
 *
 * @param {any} row - 表格行
 * @param {string | number | boolean} val - switch 新值（enabled / paused）
 * @returns {Promise<void>}
 */
async function onStateChange(row: any, val: string | number | boolean): Promise<void> {
  const oldVal = val === "enabled" ? "paused" : "enabled";
  const targetLabel = val === "enabled" ? "启用" : "暂停";
  try {
    await ElMessageBox.confirm(`确认将广告活动状态修改为「${targetLabel}」？`, "确认修改状态", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    // 用户取消：还原 switch
    row.state = oldVal;
    return;
  }
  emit("update-state", { row, state: val });
}

/**
 * 将投放类型字段值格式化为中文显示。
 *
 * @param {string} val - targeting_type 原始值（AUTO / MANUAL）
 * @returns {string} 中文显示文字；无法识别则原样返回
 */
function formatTargetingType(val: string): string {
  if (!val) return "";
  const map: Record<string, string> = { AUTO: "自动", MANUAL: "手动" };
  return map[val.toUpperCase()] ?? val;
}

/** 需要染色的正向指标（值越高越好） */
/**
 * 根据列 prop 返回合理的列宽，以表头不折叠为原则。
 *
 * @param {string} prop - 列字段名
 * @returns {number} 最小列宽（px）
 */
function getColumnMinWidth(prop: string): number {
  const widthMap: Record<string, number> = {
    is: 80,
    acos: 120,
    roas: 120,
    cvr: 100,
    ctr: 80,
    cpc: 80,
    cpa: 80,
    budget: 110,
    startDate: 120,
    service_status: 140,
    bidding_type: 100,
    portfolio_name: 130,
    tags: 100,
    impressions: 120,
    impressionsPercent: 130,
    clicks: 110,
    clicksPercent: 130,
    spends: 120,
    spendsPercent: 130,
    adsSales: 130,
    adsSalesPercent: 140,
    directSales: 130,
    adsOrders: 120,
    directOrders: 120,
    adsOrderPrice: 140,
    adsVolume: 120,
  };
  return widthMap[prop] ?? 120;
}

/**
 * 拖拽列宽后确保不低于 min-width（Element Plus @header-dragend 回调）。
 *
 * @param {number} newWidth - 拖拽后的新列宽
 * @param {number} _oldWidth - 拖拽前的旧列宽（未使用）
 * @param {any} column - Element Plus 内部列对象（含 minWidth 属性）
 */
function onHeaderDragEnd(newWidth: number, _oldWidth: number, column: any): void {
  const minW = column.minWidth ? Number(column.minWidth) : 80;
  if (newWidth < minW) {
    column.width = minW;
    column.realWidth = minW;
  }
}

/** 需要染色的正向指标（值越高越好） */
const POSITIVE_COLS = new Set(["roas", "cvr"]);
/** 需要染色的负向指标（值越低越好） */
const NEGATIVE_COLS = new Set(["acos"]);

/**
 * 判断是否应该显示趋势箭头。
 *
 * @param {string} prop - 当前列字段名
 * @param {*} value - 当前单元格原始值
 * @returns {boolean} 需要展示趋势箭头时返回 true
 */
function shouldShowTrend(prop: string, value: any): boolean {
  const val = parseFloat(value);
  if (isNaN(val)) return false;
  if (POSITIVE_COLS.has(prop) || NEGATIVE_COLS.has(prop)) {
    return true;
  }
  return false;
}

/**
 * 根据列 prop 和数值返回数据染色类名。
 *
 * ACoS: < 10 绿色，10-30 不变，> 30 红色
 * ROAS / CVR: > 0 绿色，< 0 红色
 *
 * @param {*} row - 表格行数据
 * @param {string} prop - 列 prop 名
 * @returns {string} CSS 类名
 */
function getDataValueClass(row: any, prop: string): string {
  if (row._isSummary) return "data-bold";
  const val = parseFloat(row[prop]);
  if (isNaN(val)) return "";
  if (prop === "acos") {
    if (val > 30) return "data-down";
    if (val < 10) return "data-up";
    return "";
  }
  if (POSITIVE_COLS.has(prop)) {
    if (val > 0) return "data-up";
    if (val < 0) return "data-down";
    return "";
  }
  return "";
}

/**
 * 格式化日期值：仅保留年月日部分。
 *
 * @param {*} val - 原始日期字符串（可能含时分秒）
 * @returns {string} 格式化后的日期字符串
 */
function formatDateValue(val: any): string {
  if (val == null) return "-";
  const str = String(val);
  return str.slice(0, 10);
}

/**
 * 格式化表格数值展示：千分位处理。
 *
 * @param {*} val - 原始值
 * @returns {string} 格式化后的字符串
 */
function formatValue(val: any): string {
  if (val == null) return "-";
  const num = Number(val);
  if (isNaN(num)) return String(val);
  if (Math.abs(num) < 0.01 && Math.abs(num) > 0) return String(val);
  if (Math.abs(num) >= 1000) {
    return num.toLocaleString("en-US", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
  }
  return String(val);
}
</script>

<style scoped>
.data-table-container {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: visible;
  background: var(--table-bg, #fafbfc);
}

.data-table__scroll {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: visible;
}

/* el-table 撑满整个 data-table__scroll */
.data-table__scroll :deep(.el-table) {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.data-table__scroll :deep(.el-table__inner-wrapper) {
  display: flex;
  flex: 1;
  flex-direction: column;
}

.data-table__scroll :deep(.el-table__body-wrapper) {
  flex: 1;
}

/* 解除表格默认 overflow 裁剪，让 sticky 元素定位到外层页面滚动容器 */
.data-table__content {
  overflow: visible !important;
  background: var(--table-bg);
  border-top: none;
  border-right: none;
  border-left: none;
}

:deep(.el-table__body-wrapper) {
  overflow-x: auto !important;
  overflow-y: visible !important;
  scrollbar-width: none;
  background: var(--table-bg);
}

:deep(.el-table__body-wrapper::-webkit-scrollbar),
:deep(.el-table__body-wrapper .el-scrollbar__bar),
:deep(.el-table__body-wrapper .el-scrollbar__bar.is-horizontal),
:deep(.el-table__body-wrapper .el-scrollbar__bar.is-vertical) {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
  opacity: 0 !important;
}

:deep(.el-table__inner-wrapper) {
  background: var(--table-bg);
}

:deep(.el-table) {
  background: var(--table-bg);
}

:deep(.el-table__header-wrapper) {
  position: sticky;
  top: 74px;
  z-index: 10;
  background: #eef1f6;
}

:deep(.el-table thead) {
  position: sticky;
  top: 74px;
  z-index: 10;
}

:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  text-align: center;
  background: #f0f2f5;
}

:deep(.el-table__header th .caret-wrapper) {
  margin-left: 6px;
  transform: scale(1.04);
}

:deep(.el-table__header th .el-icon) {
  color: var(--text-tertiary);
}

:deep(.el-table__header th .is-active .el-icon) {
  color: var(--color-primary-600);
}

:deep(.el-table__header th .cell) {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}

:deep(.el-table__header th.el-table__cell) {
  border-right: none !important;
}

:deep(.el-table .el-table__cell) {
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

.data-value {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  font-variant-numeric: tabular-nums;
}

.data-bold {
  font-weight: 700;
}

.data-null {
  color: var(--border-strong);
}

.data-up {
  font-weight: 700;
  color: var(--color-success-600);
}

.data-down {
  font-weight: 700;
  color: var(--color-danger-600);
}

.trend-icon {
  display: inline-flex;
  align-items: center;
  margin-right: 2px;
  font-size: 12px;
}

.trend-icon-down {
  transform: rotate(180deg);
}

:deep(.zebra-row > td.el-table__cell) {
  background-color: var(--surface-subtle);
}

:deep(.el-table .el-table__row) {
  transition:
    background 160ms ease,
    box-shadow 160ms ease;
}

:deep(.el-table .el-table__row:hover > td.el-table__cell) {
  background-color: var(--surface-hover) !important;
}

:deep(.el-table__body-wrapper .el-table__row) {
  position: relative;
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

:deep(.summary-row > td.el-table__cell) {
  position: relative;
  font-weight: 700;
  color: var(--text-primary);
  background: var(--surface-hover) !important;
  box-shadow: 0 1px 0 var(--color-primary-200) inset;
}

:deep(.summary-row > td.el-table__cell:first-child::before) {
  position: absolute;
  top: 12%;
  left: 0;
  width: 3px;
  height: 76%;
  content: "";
  background: var(--color-primary-600);
  border-radius: 0 3px 3px 0;
}

:deep(.summary-row:hover > td.el-table__cell) {
  background: var(--color-primary-100) !important;
}

.summary-indicator {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-primary-700);
}

.summary-icon {
  font-size: 16px;
  color: var(--color-primary-600);
}

:deep(.el-table .el-switch) {
  height: 16px;
}

:deep(.el-table .el-switch .el-switch__core) {
  width: 28px !important;
  min-width: 28px !important;
  height: 16px !important;
  border: 1.5px solid var(--border-strong);
  border-radius: 999px !important;
  transition: all 160ms ease;
}

:deep(.el-table .el-switch .el-switch__core .el-switch__action) {
  top: 1px;
  left: 1px;
  width: 10px !important;
  height: 10px !important;
  box-shadow: 0 1px 2px rgb(15 23 42 / 14%);
}

:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) {
  left: 15px !important;
}

:deep(.el-table .el-switch.is-checked .el-switch__core) {
  background-color: var(--color-success-500) !important;
  border-color: var(--color-success-500) !important;
}

:deep(.el-table .el-switch.is-disabled .el-switch__core) {
  opacity: 0.72;
}

.profile-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.country-tag {
  display: inline-block;
  padding: 1px 8px;
  margin-top: 3px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--surface-subtle);
  border: 1px solid var(--border-base);
  border-radius: 999px;
}

.targeting-type-line {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--text-secondary);
}

.summary-dash {
  font-size: 13px;
  color: var(--border-strong);
}

.campaign-name-link {
  font-weight: 700;
  color: var(--color-primary-600);
  text-decoration: none;
  transition:
    color 160ms ease,
    text-decoration-color 160ms ease;
}

.campaign-name-link:hover {
  color: var(--color-primary-700);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.analyze-btn {
  font-weight: 700;
  color: var(--color-primary-600);
}

.analyze-btn:hover {
  color: var(--color-primary-700);
}

.table-empty {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  padding-top: 72px;
}

.table-empty__icon {
  color: var(--text-tertiary);
  opacity: 0.4;
}

.table-empty__text {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary);
}

.pager-sentinel {
  height: 1px;
}

.table-footer-sticky {
  position: sticky;
  bottom: 0;
  z-index: 13;
  background: var(--surface-base);
  border-right: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
  border-left: 1px solid #e2e8f0;
  border-radius: 0 0 18px 18px;
}

.table-horizontal-scroll {
  height: 12px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-color: var(--border-strong) var(--border-subtle);
  scrollbar-width: thin;
  background: var(--surface-base);
  border-top: 1px solid #e2e8f0;
}

.table-horizontal-scroll__inner {
  height: 1px;
}

.table-horizontal-scroll::-webkit-scrollbar {
  height: 8px;
}

.table-horizontal-scroll::-webkit-scrollbar-track {
  background: var(--border-subtle);
  border-radius: 4px;
}

.table-horizontal-scroll::-webkit-scrollbar-thumb {
  background: var(--border-strong);
  border-radius: 4px;
}

.table-horizontal-scroll::-webkit-scrollbar-thumb:hover {
  background: var(--text-tertiary);
}

.pager-row {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  background: var(--surface-base);
  border-top: 1px solid #e2e8f0;
}

.pager-row > * {
  flex-shrink: 0;
}
.pager-center,
.pager-right {
  display: flex;
  flex-shrink: 0;
  align-items: center;
}

.pager-left {
  display: flex;
  flex: 1;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

.batch-divider {
  width: 1px;
  height: 16px;
  background: var(--border-strong);
}

.batch-info {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary-600);
}

.batch-btn {
  font-size: 12px;
  font-weight: 600;
}

.pager-center {
  margin-right: 12px;
}

.pager-right {
  gap: 8px;
  justify-content: flex-end;
  white-space: nowrap;
}

.total-count {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}

.count-icon {
  color: var(--text-tertiary);
}

.page-size-label,
.page-size-suffix {
  font-size: 12px;
  color: var(--text-secondary);
}

.page-size-select {
  width: 88px;
}

.pager-row :deep(.el-select .el-input__wrapper) {
  height: 30px !important;
  min-height: 30px !important;
  border-color: var(--border-strong);
  border-radius: var(--radius-md);
  box-shadow: none;
}

.pager-row :deep(.el-select .el-input__inner) {
  height: 28px !important;
  font-size: 12px;
  line-height: 28px !important;
}

.pager-row :deep(.el-pagination) {
  font-size: 12px;
}

.pager-row :deep(.el-pager li) {
  min-width: 28px;
  height: 28px;
  font-size: 12px;
  font-weight: 600;
  line-height: 28px;
  border-radius: var(--radius-md);
}

.pager-row :deep(.el-pagination button) {
  min-width: 28px;
  height: 28px;
  font-size: 12px;
}

.pager-row :deep(.el-pagination .btn-prev),
.pager-row :deep(.el-pagination .btn-next) {
  font-size: 13px;
}

/* ── 状态单元格（switch + 最近修改星标）────────────────────────────────── */
.state-cell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* ── 最近修改星标（状态列 + 预算列共用）────────────────────────────────── */
.recent-star {
  position: absolute;
  top: -6px;
  right: -6px;
  z-index: 2;
  font-size: 12px;
  color: #f59e0b;
  text-shadow: 0 0 2px rgb(245 158 11 / 40%);
  cursor: help;
}

.budget-cell .recent-star {
  top: -4px;
  right: -8px;
}

/* tooltip 多行展示 */
:global(.latest-adj-tooltip) {
  max-width: 360px;
  padding: 10px 14px;
  font-size: 12px;
  line-height: 1.7;
  color: #1e293b;
  white-space: pre-line;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgb(15 23 42 / 10%);
}

/* ── 预算可编辑单元格 ──────────────────────────────────────────────────── */
.budget-cell {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  justify-content: center;
}

.budget-cell .budget-input {
  width: 80px;
}

/* 货币符号前缀 */
.budget-cell :deep(.el-input__prefix) {
  display: inline-flex;
  align-items: center;
  padding-right: 4px;
}

.budget-icon {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #64748b);
}

/* 输入框主体：浅灰底、圆角、聚焦主色光晕 */
.budget-cell :deep(.el-input__wrapper) {
  height: 28px;
  padding: 0 8px;
  background: var(--surface-subtle, #f8fafc);
  border: 1px solid var(--border-base, #e2e8f0);
  border-radius: 8px;
  box-shadow: none;
  transition:
    background 160ms ease,
    border-color 160ms ease,
    box-shadow 160ms ease;
}

.budget-cell :deep(.el-input__wrapper:hover) {
  background: var(--surface-base, #fff);
  border-color: var(--color-primary-300, #93c5fd);
}

.budget-cell :deep(.el-input__wrapper.is-focus) {
  background: var(--surface-base, #fff);
  border-color: var(--color-primary-600, #2563eb);
  box-shadow: 0 0 0 3px var(--focus-ring, rgb(37 99 235 / 18%));
}

.budget-cell :deep(.el-input__inner) {
  height: 26px;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary, #0f172a);
}

/* 隐藏 number 输入框的旋钮箭头，保持整洁 */
.budget-cell :deep(.el-input__inner[type="number"])::-webkit-outer-spin-button,
.budget-cell :deep(.el-input__inner[type="number"])::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}
</style>
