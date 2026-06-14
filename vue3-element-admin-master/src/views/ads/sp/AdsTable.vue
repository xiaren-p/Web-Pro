<template>
  <div class="ads-table-root">
    <div class="ads-table-body">
      <el-table
        v-loading="loading"
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
            <el-switch v-else v-model="row.state" active-value="enabled" inactive-value="paused" disabled />
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100" fixed="left" align="center">
          <template #default="{ row }">
            <template v-if="row._isSummary"><span class="summary-dash">--</span></template>
            <template v-else>
              <div>{{ row.sponsored_type }}</div>
              <div v-if="row.targeting_type" class="targeting-type-line">[{{ formatTargetingType(row.targeting_type) }}]</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="店铺/国家" width="120" fixed="left" align="center">
          <template #default="{ row }">
            <template v-if="row._isSummary">
              <span class="summary-indicator"><el-icon class="summary-icon"><TrendCharts /></el-icon>汇总</span>
            </template>
            <template v-else>
              <div class="profile-name">{{ row.profile_alias || row.profile_id }}</div>
              <div class="country-tag">{{ row.country_name || "-" }}</div>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="广告活动" min-width="180" fixed="left" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-dash">--</span>
            <router-link v-else class="campaign-name-link" :to="{ name: 'AdCampaignDetail', query: { campaign_id: row.campaign_id, profile_id: row.profile_id, date_start: props.dateRange?.[0] || '', date_end: props.dateRange?.[1] || '' } }">{{ row.name }}</router-link>
          </template>
        </el-table-column>
        <el-table-column v-for="col in columns" :key="col.prop" :prop="col.prop" :label="col.label" :fixed="col.fixed" :sortable="col.sortable" min-width="120" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <template v-if="row._isSummary">--</template>
              <span v-else class="status-badge" :class="`status-badge--${row.service_status_type || 'info'}`">{{ row.service_status_label || row.service_status || "-" }}</span>
            </template>
            <template v-else>
              <span v-if="row._isSummary && row[col.prop] == null" class="data-null">--</span>
              <span v-else class="data-value" :class="getDataValueClass(row, col.prop)">
                <span v-if="!row._isSummary && shouldShowTrend(col.prop, row[col.prop])" class="trend-icon" :class="getDataValueClass(row, col.prop)">
                  <el-icon><TrendCharts v-if="getDataValueClass(row, col.prop) === 'data-up'" /><TrendCharts v-else-if="getDataValueClass(row, col.prop) === 'data-down'" class="trend-icon-down" /></el-icon>
                </span>
                {{ formatValue(row[col.prop]) }}
              </span>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="分析" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="!row._isSummary" type="primary" link size="small" class="analyze-btn" @click="$emit('view-row', row)">分析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="pager-row">
      <div class="pager-left">
        <span class="total-count"><el-icon class="count-icon"><List /></el-icon>共 {{ total.toLocaleString() }} 条</span>
      </div>
      <div class="pager-mid">
        <el-pagination background :current-page="currentPage" :page-size="localPageSize" :total="total" layout="prev, pager, next" @current-change="$emit('current-change', $event)" />
      </div>
      <div class="pager-right">
        <span class="page-size-label">每页</span>
        <el-select v-model="localPageSize" class="page-size-select" @change="onPageSizeChange">
          <el-option label="25条" :value="25" /><el-option label="50条" :value="50" /><el-option label="100条" :value="100" /><el-option label="250条" :value="250" />
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
    tableData: any[]; pageSize: number; currentPage: number; total: number; columns: any[];
    loading?: boolean; summary?: Record<string, unknown> | null; dateRange?: string[];
  }>(),
  { loading: false, summary: null, dateRange: () => [] }
);

const emit = defineEmits(["current-change", "view-row", "page-size-change", "sort-change"]);
const localPageSize = ref(props.pageSize || 25);

const displayData = computed<any[]>(() => {
  if (!props.summary) return props.tableData;
  return [{ _isSummary: true, name: "汇总", ...props.summary }, ...props.tableData];
});

watch(() => props.pageSize, (v) => { localPageSize.value = v; });
function onPageSizeChange(v: number) { emit("page-size-change", v); }
function getRowClass({ row, rowIndex }: { row: any; rowIndex: number }): string {
  if (row._isSummary) return "summary-row";
  return ((rowIndex - (props.summary ? 1 : 0)) % 2 === 1) ? "zebra-row" : "";
}
function formatTargetingType(val: string): string {
  if (!val) return "";
  return ({ AUTO: "自动", MANUAL: "手动" } as any)[val.toUpperCase()] ?? val;
}

const POS = new Set(["impressionsPercent","clicksPercent","spendsPercent","adsSalesPercent","ctr","cvr","roas"]);
const NEG = new Set(["acos","cpa","cpc"]);
function shouldShowTrend(prop: string, value: any): boolean {
  const v = parseFloat(value); if (isNaN(v)) return false;
  return POS.has(prop) ? Math.abs(v) > 0.01 : NEG.has(prop) || false;
}
function getDataValueClass(row: any, prop: string): string {
  if (row._isSummary) return "data-bold";
  const v = parseFloat(row[prop]); if (isNaN(v)) return "";
  if (POS.has(prop)) return v > 0 ? "data-up" : v < 0 ? "data-down" : "";
  if (NEG.has(prop)) return v > 30 ? "data-down" : v < 10 ? "data-up" : "";
  return "";
}
function formatValue(val: any): string {
  if (val == null) return "-";
  const n = Number(val); if (isNaN(n)) return String(val);
  if (Math.abs(n) < 0.01 && Math.abs(n) > 0) return String(val);
  return Math.abs(n) >= 1000 ? n.toLocaleString("en-US",{ minimumFractionDigits:0, maximumFractionDigits:2 }) : String(val);
}
</script>

<style scoped>
.ads-table-root {
  background: var(--surface-base);
  border-radius: 0 0 18px 18px;
}

/* 表格体不做内部 overflow，自然撑高页面，使用页面滚动 */
.ads-table-body :deep(.el-table__body-wrapper) {
  overflow-y: visible !important;
}
.ads-table-body :deep(.el-scrollbar__wrap) {
  overflow-y: visible !important;
}
.ads-table-body :deep(.el-scrollbar__view) {
  overflow-y: visible !important;
}

/* 表头 sticky 吸在顶部，留 12px 间隙 */
.ads-table-body :deep(.el-table__header-wrapper) {
  position: sticky;
  top: 12px;
  z-index: 20;
  background: var(--surface-base);
}

.pager-row {
  display: flex;
  align-items: center;
  padding: 10px 18px;
  background: var(--surface-base);
  border-top: 1px solid var(--border-base);
  border-radius: 0 0 18px 18px;
}
.pager-left { flex: 1; }
.pager-mid { display: flex; justify-content: flex-end; padding-right: 12px; }
.pager-right { display: flex; gap: 8px; align-items: center; }

.total-count { display: inline-flex; gap: 6px; align-items: center; font-size: 12px; color: var(--text-secondary); white-space: nowrap; }
.count-icon { color: var(--text-tertiary); }
.page-size-label,.page-size-suffix { font-size: 12px; color: var(--text-secondary); }
.page-size-select { width: 88px; }

.pager-row :deep(.el-select .el-input__wrapper) { height: 30px !important; min-height: 30px !important; border-color: var(--border-strong); border-radius: var(--radius-md); box-shadow: none; }
.pager-row :deep(.el-select .el-input__inner) { height: 28px !important; font-size: 12px; line-height: 28px !important; }
.pager-row :deep(.el-pagination) { font-size: 12px; }
.pager-row :deep(.el-pager li) { min-width: 28px; height: 28px; font-size: 12px; font-weight: 600; line-height: 28px; border-radius: var(--radius-md); }
.pager-row :deep(.el-pagination button) { min-width: 28px; height: 28px; font-size: 12px; }
.pager-row :deep(.el-pagination .btn-prev),.pager-row :deep(.el-pagination .btn-next) { font-size: 13px; }

:deep(.el-table__header-wrapper th.el-table__cell),:deep(.el-table__header th) { text-align: center; }
:deep(.el-table__header th .caret-wrapper) { margin-left: 6px; transform: scale(1.04); }
:deep(.el-table__header th .el-icon) { color: var(--text-tertiary); }
:deep(.el-table__header th .is-active .el-icon) { color: var(--color-primary-600); }
:deep(.el-table__header th .cell) { display: flex; align-items: center; justify-content: center; width: 100%; }
:deep(.el-table__header th.el-table__cell) { border-right: none !important; }
:deep(.el-table .el-table__cell) { padding: 11px 0 !important; font-size: 13px; color: var(--text-primary); border-right: none !important; }
:deep(.el-table .cell) { padding-right: 14px; padding-left: 14px; line-height: 1.55; }
:deep(.el-table__body td.el-table__cell) { border-bottom: 1px solid var(--border-subtle) !important; }

.data-value { display: inline-flex; gap: 3px; align-items: center; font-variant-numeric: tabular-nums; }
.data-bold { font-weight: 700; }
.data-null { color: var(--border-strong); }
.data-up { font-weight: 700; color: var(--color-success-600); }
.data-down { font-weight: 700; color: var(--color-danger-600); }
.trend-icon { display: inline-flex; align-items: center; margin-right: 2px; font-size: 12px; }
.trend-icon-down { transform: rotate(180deg); }

:deep(.zebra-row > td.el-table__cell) { background-color: var(--surface-subtle); }
:deep(.el-table .el-table__row) { transition: background 160ms ease, box-shadow 160ms ease; }
:deep(.el-table .el-table__row:hover > td.el-table__cell) { background-color: var(--surface-hover) !important; }
:deep(.el-table__body-wrapper .el-table__row) { position: relative; }
:deep(.el-table__body-wrapper .el-table__row:hover td:first-child::before) { position: absolute; top: 0; left: 0; width: 3px; height: 100%; content: ""; background: var(--color-primary-600); border-radius: 0 2px 2px 0; }
:deep(.summary-row > td.el-table__cell) { position: relative; font-weight: 700; color: var(--text-primary); background: var(--surface-hover) !important; box-shadow: 0 1px 0 var(--color-primary-200) inset; }
:deep(.summary-row > td.el-table__cell:first-child::before) { position: absolute; top: 12%; left: 0; width: 3px; height: 76%; content: ""; background: var(--color-primary-600); border-radius: 0 3px 3px 0; }
:deep(.summary-row:hover > td.el-table__cell) { background: var(--color-primary-100) !important; }
.summary-indicator { display: inline-flex; gap: 6px; align-items: center; font-size: 13px; font-weight: 700; color: var(--color-primary-700); }
.summary-icon { font-size: 16px; color: var(--color-primary-600); }
:deep(.el-table .el-switch) { height: 20px; }
:deep(.el-table .el-switch .el-switch__core) { width: 36px !important; min-width: 36px !important; height: 20px !important; border: 2px solid var(--border-strong); border-radius: 999px !important; transition: all 160ms ease; }
:deep(.el-table .el-switch .el-switch__core .el-switch__action) { top: 1px; left: 1px; width: 14px !important; height: 14px !important; box-shadow: 0 1px 3px rgb(15 23 42 / 14%); }
:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) { left: 19px !important; }
:deep(.el-table .el-switch.is-checked .el-switch__core) { background-color: var(--color-success-500) !important; border-color: var(--color-success-500) !important; }
:deep(.el-table .el-switch.is-disabled .el-switch__core) { opacity: 0.72; }
.profile-name { font-size: 13px; font-weight: 700; color: var(--text-primary); }
.country-tag { display: inline-block; padding: 1px 8px; margin-top: 3px; font-size: 11px; font-weight: 600; color: var(--text-secondary); background: var(--surface-subtle); border: 1px solid var(--border-base); border-radius: 999px; }
.targeting-type-line { margin-top: 2px; font-size: 11px; line-height: 1.4; color: var(--text-secondary); }
.summary-dash { font-size: 13px; color: var(--border-strong); }
.campaign-name-link { font-weight: 700; color: var(--color-primary-600); text-decoration: none; transition: color 160ms ease, text-decoration-color 160ms ease; }
.campaign-name-link:hover { color: var(--color-primary-700); text-decoration: underline; text-underline-offset: 3px; }
.analyze-btn { font-weight: 700; color: var(--color-primary-600); }
.analyze-btn:hover { color: var(--color-primary-700); }
.data-table__content { border-top: none; border-right: none; border-left: none; }
</style>
