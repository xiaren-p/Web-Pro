<template>
  <div class="data-table-container">
    <div class="data-table__scroll">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        :row-class-name="getRowClass"
        :border="false"
        style="width: 100%"
        @sort-change="$emit('sort-change', $event)"
      >
        <el-table-column type="selection" width="48" fixed="left" align="center" />

        <el-table-column label="有效" width="80" fixed="left" align="center">
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-dash">--</span>
            <el-switch
              v-else
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" fixed="left" align="center">
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
        <el-table-column label="店铺/国家" width="120" fixed="left" align="center">
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
          fixed="left"
          align="center"
          show-overflow-tooltip
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
          :sortable="col.sortable"
          min-width="120"
          align="center"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <template v-if="row._isSummary">--</template>
              <span
                v-else
                class="status-badge"
                :class="`status-badge--${row.service_status_type || 'info'}`"
              >
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>
            <template v-else>
              <span v-if="row._isSummary && row[col.prop] == null" class="data-null">--</span>
              <span v-else class="data-value" :class="getDataValueClass(row, col.prop)">
                <span
                  v-if="!row._isSummary && shouldShowTrend(col.prop, row[col.prop])"
                  class="trend-icon"
                  :class="getDataValueClass(row, col.prop)"
                >
                  <el-icon>
                    <TrendCharts v-if="getDataValueClass(row, col.prop) === 'data-up'" />
                    <TrendCharts
                      v-else-if="getDataValueClass(row, col.prop) === 'data-down'"
                      class="trend-icon-down"
                    />
                  </el-icon>
                </span>
                {{ formatValue(row[col.prop]) }}
              </span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="分析" width="80" fixed="right" align="center">
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

    <div class="pager-row">
      <div class="pager-left">
        <span class="total-count">
          <el-icon class="count-icon"><List /></el-icon>
          共 {{ total.toLocaleString() }} 条
        </span>
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
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { TrendCharts, List } from "@element-plus/icons-vue";

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

const emit = defineEmits(["current-change", "view-row", "page-size-change", "sort-change"]);
const localPageSize = ref(props.pageSize || 25);

/**
 * 将汇总行置于列表首位，与当前页数据合并展示。
 *
 * @returns {any[]} 以汇总行开头的完整表格数据
 */
const displayData = computed<any[]>(() => {
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

const POSITIVE_RATE_COLS = new Set([
  "impressionsPercent",
  "clicksPercent",
  "spendsPercent",
  "adsSalesPercent",
  "ctr",
  "cvr",
  "roas",
]);
const NEGATIVE_RATE_COLS = new Set(["acos", "cpa", "cpc"]);

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

  if (POSITIVE_RATE_COLS.has(prop)) {
    return Math.abs(val) > 0.01;
  }
  if (NEGATIVE_RATE_COLS.has(prop)) {
    return true;
  }
  return false;
}

/**
 * 根据列 prop 和数值返回数据染色类名。
 *
 * @param {*} row - 表格行数据
 * @param {string} prop - 列 prop 名
 * @returns {string} CSS 类名
 */
function getDataValueClass(row: any, prop: string): string {
  if (row._isSummary) return "data-bold";
  const val = parseFloat(row[prop]);
  if (isNaN(val)) return "";

  if (POSITIVE_RATE_COLS.has(prop)) {
    if (val > 0) return "data-up";
    if (val < 0) return "data-down";
    return "";
  }
  if (NEGATIVE_RATE_COLS.has(prop)) {
    if (val > 30) return "data-down";
    if (val < 10) return "data-up";
    return "";
  }
  return "";
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
  background: var(--surface-base);
}

.data-table__scroll {
  flex: 1;
  min-height: 0;
}

.el-table__header-wrapper {
  position: sticky;
  top: 72px;
  z-index: 10;
}

:deep(.el-table__header-wrapper) {
  position: sticky;
  top: 72px;
  z-index: 10;
  background: var(--surface-base);
}

:deep(.el-table thead) {
  position: sticky;
  top: 72px;
  z-index: 10;
}

:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  text-align: center;
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
  height: 20px;
}

:deep(.el-table .el-switch .el-switch__core) {
  width: 36px !important;
  min-width: 36px !important;
  height: 20px !important;
  border: 2px solid var(--border-strong);
  border-radius: 999px !important;
  transition: all 160ms ease;
}

:deep(.el-table .el-switch .el-switch__core .el-switch__action) {
  top: 1px;
  left: 1px;
  width: 14px !important;
  height: 14px !important;
  box-shadow: 0 1px 3px rgb(15 23 42 / 14%);
}

:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) {
  left: 19px !important;
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

.pager-row {
  position: sticky;
  bottom: 0;
  z-index: 11;
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 18px;
  background: var(--surface-base);
  border-top: 1px solid var(--border-base);
}

.pager-left,
.pager-center,
.pager-right {
  display: flex;
  flex: 1;
  align-items: center;
}

.pager-center {
  justify-content: center;
}

.pager-right {
  gap: 8px;
  justify-content: flex-end;
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

.data-table__content {
  border-top: none;
  border-right: none;
  border-left: none;
}
</style>
