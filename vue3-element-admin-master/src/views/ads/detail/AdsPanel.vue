<template>
  <div class="ads-panel">
    <!-- 筛选栏 -->
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
      <el-select
        v-model="filters.productTag"
        size="small"
        class="filter-item w-120"
        placeholder="商品标签"
        clearable
      >
        <el-option label="全部标签" value="" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item keyword-input"
        placeholder="请输入ASIN或MSKU"
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
        :data="tableData"
        :border="false"
        height="calc(100vh - 380px)"
        style="width: 100%"
      >
        <!-- 固定左：有效 -->
        <el-table-column label="有效" width="68" fixed="left" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
          </template>
        </el-table-column>

        <!-- 固定左：图片 -->
        <el-table-column label="图片" width="68" fixed="left" align="center">
          <template #default="{ row }">
            <img v-if="row.image_url" :src="row.image_url" class="product-thumb" alt="商品图片" />
            <span v-else class="thumb-placeholder" />
          </template>
        </el-table-column>

        <!-- 固定左：ASIN -->
        <el-table-column label="ASIN" width="120" fixed="left" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="asin-text">{{ row.asin || "-" }}</span>
          </template>
        </el-table-column>

        <!-- 固定左：MSKU -->
        <el-table-column label="MSKU" width="140" fixed="left" align="center" show-overflow-tooltip>
          <template #default="{ row }">
            <span>{{ row.msku || "-" }}</span>
          </template>
        </el-table-column>

        <!-- 动态列（由 ColumnManager 控制） -->
        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          min-width="120"
          align="center"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <span class="status-badge" :class="`status-${row.service_status_type || 'default'}`">
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'rating'">
              <span>{{ row.rating != null ? `${row.rating} ★` : "-" }}</span>
            </template>
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右：分析 -->
        <el-table-column label="分析" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button v-if="row.ad_id" type="primary" link size="small">分析</el-button>
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
import { ref, computed } from "vue";
import { Operation, Filter } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import ColumnManager from "@/components/ColumnManager/index.vue";

defineOptions({ name: "AdsPanel" });

/**
 * 父页面透传的初始日期范围（来自路由 query 的 date_start / date_end）。
 *
 * @prop {string[]} initialDateRange - 格式 ['YYYY-MM-DD', 'YYYY-MM-DD'] 或空数组
 */
const props = defineProps<{
  initialDateRange?: string[];
}>();

/** 筛选条件，range 以父页面传入日期初始化 */
const filters = ref({
  range: (props.initialDateRange?.length === 2 ? [...props.initialDateRange] : []) as string[],
  state: "",
  productTag: "",
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

/** 表格数据（后端接入后替换为实际数据） */
const tableData = ref<any[]>([]);

/**
 * 列定义（含 category，供 ColumnManager 分组展示）。
 * visible 由 ColumnManager @save 回调更新。
 */
const activeColumns = ref([
  // 设置
  { prop: "service_status", label: "服务状态", visible: true, category: "设置" },
  { prop: "portfolio_name", label: "广告组合", visible: true, category: "设置" },
  { prop: "campaign_name", label: "广告活动", visible: true, category: "设置" },
  { prop: "adgroup_name", label: "广告组", visible: true, category: "设置" },
  { prop: "targeting", label: "投放", visible: false, category: "设置" },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置" },
  // LISTING
  { prop: "title", label: "标题", visible: false, category: "LISTING" },
  { prop: "price", label: "价格", visible: true, category: "LISTING" },
  { prop: "stock", label: "可售库存", visible: true, category: "LISTING" },
  { prop: "rating", label: "星级", visible: false, category: "LISTING" },
  { prop: "reviews", label: "评论数", visible: false, category: "LISTING" },
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
 * @returns {typeof activeColumns.value} 当前需要展示的列定义数组。
 */
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

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
  filters.value.productTag = "";
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
 * 加载广告列表数据。
 * 后端接口暂未实现，此处为占位逻辑。
 */
function fetchData(): void {
  // TODO(后端联调): 调用广告列表接口，传入 filters + currentPage + pageSize
  loading.value = true;
  setTimeout(() => {
    tableData.value = [];
    total.value = 0;
    loading.value = false;
  }, 300);
}
</script>

<style scoped lang="scss">
.ads-panel {
  padding-top: 12px;
}

/* ────────────────────────────────
   筛选栏
───────────────────────────────── */
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-bottom: 8px;
  background: transparent;

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

.w-120 {
  width: 120px;
}

.date-picker {
  flex: 0 0 218px;

  :deep(.el-date-editor.el-input__wrapper),
  :deep(.el-range-editor.el-input__wrapper) {
    width: 218px !important;
    padding: 0 8px;
  }
}

.keyword-input {
  flex: 0 0 200px;
  width: 200px;
}

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

:deep(.el-table__header-wrapper th.el-table__cell),
:deep(.el-table__header th) {
  font-size: 13px;
  font-weight: 600 !important;
  color: #374151 !important;
  text-align: center;
  background-color: #f9fafb !important;
  border-bottom: 1px solid #e5e7eb !important;
}

:deep(.el-table .el-table__cell) {
  padding: 5px 0 !important;
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

/* 商品图片缩略图 */
.product-thumb {
  display: block;
  width: 44px;
  height: 44px;
  margin: 0 auto;
  object-fit: cover;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
}

.thumb-placeholder {
  display: block;
  width: 44px;
  height: 44px;
  margin: 0 auto;
  background: #f4f4f5;
  border-radius: 4px;
}

/* ASIN 蓝色链接样式 */
.asin-text {
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
  color: #909399;
  white-space: nowrap;
}
</style>
