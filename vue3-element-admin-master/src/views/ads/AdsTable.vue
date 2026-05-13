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
          <span v-if="row._isSummary" style="font-size: 13px; font-weight: 700; color: #000">
            汇总
          </span>
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
          <template v-if="row._isSummary"><span class="summary-dash">---</span></template>
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
          <template v-if="row._isSummary"><span class="summary-dash">---</span></template>
          <template v-else>
            <div style="font-size: 13px; font-weight: 500">
              {{ row.profile_alias || row.profile_id }}
            </div>
            <div style="font-size: 12px; color: #999">{{ row.country_name || "-" }}</div>
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
          <span v-if="row._isSummary" class="summary-dash">---</span>
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
            <template v-if="row._isSummary">---</template>
            <span
              v-else
              class="status-badge"
              :class="`status-${row.service_status_type || 'default'}`"
            >
              {{ row.service_status_label || row.service_status || "-" }}
            </span>
          </template>
          <template v-else>
            <span v-if="row._isSummary && row[col.prop] == null">---</span>
            <span v-else>{{ row[col.prop] }}</span>
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
            @click="$emit('view-row', row)"
          >
            分析
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager-row">
      <span class="total-count">共 {{ total.toLocaleString() }} 条</span>
      <el-select
        v-model="localPageSize"
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
        :page-size="localPageSize"
        :total="total"
        layout="prev, pager, next, jumper"
        @current-change="$emit('current-change', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";

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
 * @param {{ row: any }} param0 - 当前行数据对象
 * @returns {string} 汇总行返回 "summary-row"，其余行返回空字符串
 */
function getRowClass({ row }: { row: any }): string {
  return row._isSummary ? "summary-row" : "";
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
</script>

<style scoped>
.pager-row {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: flex-end;
  padding: 8px 16px;
  background-color: #fff;
  border-top: 1px solid #f0f2f5;
  border-radius: 0 0 8px 8px;
}

/* 页数选择器高度与分页页码按钮对齐（background模式按钮为32px） */
.pager-row :deep(.el-select .el-input__wrapper) {
  height: 32px !important;
  min-height: 32px !important;
}
.pager-row :deep(.el-select .el-input__inner) {
  height: 30px !important;
  line-height: 30px !important;
}

.total-count {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

.data-table__content {
  border-top: none;
  border-right: none;
  border-left: none;
}

/* 去掉竖向分割线，仅保留行底部横向细线 */
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

/* 服务状态徽标 */
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

/* 表头：白底、深字、底部细分隔线 */
:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  font-size: 13px;
  font-weight: 600 !important;
  color: #1f2937 !important;
  text-align: center;
  background-color: #ffffff !important;
  border-bottom: 1px solid #e5e7eb !important;
}

:deep(.el-table__header th .cell) {
  display: block;
  width: 100%;
}

/* 表格内容：紧凑高度、干净字体 */
:deep(.el-table .el-table__cell) {
  padding: 4px 0 !important;
  font-size: 13px;
  color: #303133;
  border-right: none !important;
}
:deep(.el-table .cell) {
  padding-right: 10px;
  padding-left: 10px;
  line-height: 1.4;
}

/* 有效列 switch：缩小 + 开启状态绿色 */
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
/* 选中时：圆点归位到最右侧（30px - 12px圆点 - 2px右间距 = 16px，减去初始left:2px = translateX:14px）*/
:deep(.el-table .el-switch.is-checked .el-switch__core .el-switch__action) {
  left: 16px !important;
}
:deep(.el-table .el-switch.is-checked .el-switch__core) {
  background-color: #22c55e !important;
  border-color: #22c55e !important;
}

/* 单元格 hover */
:deep(.el-table .el-table__row) {
  transition: background-color 0.2s ease;
}
:deep(.el-table .el-table__row:hover > td.el-table__cell) {
  background-color: #f5f7fc !important;
}

/* 汇总行：置顶固定展示，中性背景区分 */
:deep(.summary-row > td.el-table__cell) {
  font-weight: 700;
  color: #303133;
  background-color: #fafbfc !important;
}
:deep(.summary-row:hover > td.el-table__cell) {
  background-color: #f0f2f5 !important;
}

/* 投放类型辅助行 */
.targeting-type-line {
  margin-top: 2px;
  font-size: 11px;
  line-height: 1.4;
  color: #909399;
}

/* 汇总行广告活动名称标签 */
.summary-label {
  font-weight: 700;
  color: #409eff;
  letter-spacing: 0.04em;
}

.summary-dash {
  font-size: 13px;
  color: #000;
}

/* 广告活动名称跳转链接 */
.campaign-name-link {
  color: #409eff;
  text-decoration: none;

  &:hover {
    color: #66b1ff;
    text-decoration: underline;
  }
}
</style>
