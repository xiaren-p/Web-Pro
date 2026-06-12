<template>
  <div class="data-table-container">
    <el-table
      v-loading="loading"
      class="data-table__content"
      :data="displayData"
      :row-class-name="getRowClass"
      :border="false"
      height="calc(100vh - 280px)"
      style="width: 100%"
      @sort-change="$emit('sort-change', $event)"
    >
      <el-table-column type="selection" width="48" fixed="left" align="center" />

      <!-- 固定的基础业务列 -->
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
          <span v-if="row._isSummary" class="summary-label">汇总</span>
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

      <!-- 动态从列配置里面拉取的列 -->
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
              :class="`status-${row.service_status_type || 'default'}`"
            >
              {{ row.service_status_label || row.service_status || "-" }}
            </span>
          </template>
          <!-- 数值列：智能染色 + 趋势箭头 -->
          <template v-else>
            <span v-if="row._isSummary && row[col.prop] == null" class="data-null">--</span>
            <span v-else class="data-value" :class="getDataValueClass(row, col.prop)">
              <!-- 趋势箭头 -->
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
  // 斑马纹：偶数数据行（第二个数据行起，因为汇总行是第0行）
  const dataIndex = rowIndex - (props.summary ? 1 : 0);
  return dataIndex % 2 === 1 ? "zebra-row" : "";
}

const emit = defineEmits(["current-change", "view-row", "page-size-change", "sort-change"]);

const localPageSize = ref(props.pageSize || 25);

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

/** 正增长率的关键指标列prop */
const POSITIVE_RATE_COLS = new Set([
  "impressionsPercent",
  "clicksPercent",
  "spendsPercent",
  "adsSalesPercent",
  "ctr",
  "cvr",
  "roas",
]);

/** 负增长率更好的指标列prop */
const NEGATIVE_RATE_COLS = new Set(["acos", "cpa", "cpc"]);

/**
 * 判断是否应该显示趋势箭头
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
 * 根据列prop和数值返回数据染色类名。
 *
 * @param {*} row - 表格行数据
 * @param {string} prop - 列prop名
 * @returns {string} CSS类名 "data-up" / "data-down" / "data-neutral" / ""
 */
function getDataValueClass(row: any, prop: string): string {
  if (row._isSummary) return "data-bold";
  const val = parseFloat(row[prop]);
  if (isNaN(val)) return "";

  // 百分比列：根据正负染色
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

  // 百分比值保留原样（后端已格式化）
  if (Math.abs(num) < 0.01 && Math.abs(num) > 0) return String(val);

  // 大数值加千分位
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
  background: #ffffff;
}

:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  position: sticky;
  top: 0;
  z-index: 10;
  padding: 12px 0 !important;
  font-size: 12px;
  font-weight: 700 !important;
  color: #475569 !important;
  text-align: center;
  background-color: #f8fafc !important;
  border-bottom: 1px solid #e2e8f0 !important;
  box-shadow: none;
}

:deep(.el-table__header th .caret-wrapper) {
  margin-left: 6px;
  transform: scale(1.04);
}

:deep(.el-table__header th .el-icon) {
  color: #94a3b8;
}

:deep(.el-table__header th .is-active .el-icon) {
  color: #2563eb;
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

:deep(.el-table::before),
:deep(.el-table--border::after),
:deep(.el-table--group::after) {
  display: none;
}

:deep(.el-table .el-table__cell) {
  padding: 11px 0 !important;
  font-size: 13px;
  color: #334155;
  border-right: none !important;
}

:deep(.el-table .cell) {
  padding-right: 14px;
  padding-left: 14px;
  line-height: 1.55;
}

:deep(.el-table__body td.el-table__cell) {
  border-bottom: 1px solid #edf2f7 !important;
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
  color: #cbd5e1;
}

.data-up {
  font-weight: 700;
  color: #16a34a;
}

.data-down {
  font-weight: 700;
  color: #dc2626;
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
  background-color: #fbfdff;
}

:deep(.el-table .el-table__row) {
  transition:
    background 160ms ease,
    box-shadow 160ms ease;
}

:deep(.el-table .el-table__row:hover > td.el-table__cell) {
  background-color: #eff6ff !important;
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
  background: #2563eb;
  border-radius: 0 2px 2px 0;
}

:deep(.summary-row > td.el-table__cell) {
  position: relative;
  font-weight: 700;
  color: #0f172a;
  background: #eff6ff !important;
  box-shadow: 0 1px 0 #bfdbfe inset;
}

:deep(.summary-row > td.el-table__cell:first-child::before) {
  position: absolute;
  top: 12%;
  left: 0;
  width: 3px;
  height: 76%;
  content: "";
  background: #2563eb;
  border-radius: 0 3px 3px 0;
}

:deep(.summary-row:hover > td.el-table__cell) {
  background: #dbeafe !important;
}

.summary-indicator {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
}

.summary-icon {
  font-size: 16px;
  color: #2563eb;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  white-space: nowrap;
  border-radius: 999px;
}

.status-badge.status-success {
  color: #166534;
  background: #dcfce7;
  border: 1px solid #bbf7d0;
}

.status-badge.status-danger {
  color: #991b1b;
  background: #fee2e2;
  border: 1px solid #fecaca;
}

.status-badge.status-warning {
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fde68a;
}

.status-badge.status-default {
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}

:deep(.el-table .el-switch) {
  height: 20px;
}

:deep(.el-table .el-switch .el-switch__core) {
  width: 36px !important;
  min-width: 36px !important;
  height: 20px !important;
  border: 2px solid #cbd5e1;
  border-radius: 999px !important;
  transition: all 160ms ease;
}

:deep(.el-table .el-switch .el-switch__core .el-switch__action) {
  top: 1px;
  left: 1px;
  width: 14px !important;
  height: 14px !important;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.14);
}

:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) {
  left: 19px !important;
}

:deep(.el-table .el-switch.is-checked .el-switch__core) {
  background-color: #16a34a !important;
  border-color: #16a34a !important;
}

:deep(.el-table .el-switch.is-disabled .el-switch__core) {
  opacity: 0.72;
}

.profile-name {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.country-tag {
  display: inline-block;
  padding: 1px 8px;
  margin-top: 3px;
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
}

.targeting-type-line {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.4;
  color: #64748b;
}

.summary-dash {
  font-size: 13px;
  color: #cbd5e1;
}

.summary-label {
  font-size: 13px;
  font-weight: 700;
  color: #1d4ed8;
  letter-spacing: 0.04em;
}

.campaign-name-link {
  font-weight: 700;
  color: #2563eb;
  text-decoration: none;
  transition:
    color 160ms ease,
    text-decoration-color 160ms ease;
}

.campaign-name-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.analyze-btn {
  font-weight: 700;
  color: #2563eb;
}

.analyze-btn:hover {
  color: #1d4ed8;
}

.pager-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: #ffffff;
  border-top: 1px solid #e2e8f0;
}

.pager-left {
  flex: 1;
}

.pager-center {
  display: flex;
  flex: 1;
  justify-content: center;
}

.pager-right {
  display: flex;
  flex: 1;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

.total-count {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 13px;
  color: #64748b;
  white-space: nowrap;
}

.count-icon {
  color: #94a3b8;
}

.page-size-label,
.page-size-suffix {
  font-size: 13px;
  color: #64748b;
}

.page-size-select {
  width: 90px;
}

.pager-row :deep(.el-select .el-input__wrapper) {
  height: 32px !important;
  min-height: 32px !important;
  border-color: #cbd5e1;
  border-radius: 10px;
  box-shadow: none;
}

.pager-row :deep(.el-select .el-input__inner) {
  height: 30px !important;
  line-height: 30px !important;
}

.pager-row :deep(.el-pager li) {
  font-weight: 600;
  border-radius: 10px;
}

.data-table__content {
  border-top: none;
  border-right: none;
  border-left: none;
}
</style>
