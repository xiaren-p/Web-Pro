<template>
  <div class="product-targeting-panel ads-detail-panel">
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
        <el-option label="已启用" value="enabled" />
        <el-option label="已暂停" value="paused" />
      </el-select>

      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>

      <span style="flex: 1" />

      <el-tooltip content="列配置" placement="top">
        <el-button
          text
          style="height: 32px; min-height: 32px; padding: 4px 9px; font-size: 16px; color: #606266"
          @click="columnConfigVisible = true"
        >
          <el-icon><Operation /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <div class="data-table-container">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        border
        :row-class-name="rowClassName"
        height="calc(100vh - 380px)"
        style="width: 100%"
        @selection-change="onSelectionChange"
        @header-dragend="onHeaderDragEnd"
      >
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :resizable="false"
          :selectable="(row: any) => !row._isSummary"
        />

        <el-table-column label="有效" width="80" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <div v-if="!row._isSummary" class="state-cell">
              <el-switch
                v-model="row.state"
                size="small"
                active-value="enabled"
                inactive-value="paused"
                @change="(val: string | number | boolean) => onStateChange(row, val)"
              />
              <el-tooltip
                v-if="row.latest_adjustment?.has_recent"
                placement="top"
                popper-class="latest-adj-tooltip"
              >
                <span class="recent-star" @click.stop>★</span>
                <template #content>
                  <div class="latest-adj-content">
                    <div v-for="(line, idx) in row.latest_adjustment.lines" :key="idx">
                      {{ line }}
                    </div>
                  </div>
                </template>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="商品投放" width="180" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <span v-else class="msku-text msku-text--dark">
              {{ formatTargetingExpr(row.expression) }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="广告组" min-width="220" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <template v-if="row._isSummary">---</template>
            <template v-else>
              <div class="adgroup-name-cell">
                <el-icon v-if="row.adgroup_state === 'paused'" class="state-warn" :size="14">
                  <VideoPause />
                </el-icon>
                <span :class="{ 'text-muted': row.adgroup_state === 'paused' }">
                  {{ row.adgroup_name || "-" }}
                </span>
              </div>
            </template>
          </template>
        </el-table-column>

        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth || 120"
          align="center"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <template v-if="col.prop === 'service_status'">
              <template v-if="row._isSummary">---</template>
              <span
                v-else
                class="status-badge"
                :class="`status-badge--${row.service_status_type || 'info'}`"
              >
                {{ row.service_status_label || row.serving_status || "-" }}
              </span>
            </template>
            <template v-else-if="col.prop === 'bid'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="bid-cell">
                <span class="bid-icon">{{ currencyIcon }}</span>
                <el-input
                  v-model="row.bid"
                  size="small"
                  class="bid-input"
                  @change="onBidChange(row)"
                />
                <el-tooltip
                  v-if="row.latest_adjustment?.has_recent"
                  placement="top"
                  popper-class="latest-adj-tooltip"
                >
                  <span class="recent-star" @click.stop>★</span>
                  <template #content>
                    <div class="latest-adj-content">
                      <div v-for="(line, idx) in row.latest_adjustment.lines" :key="idx">
                        {{ line }}
                      </div>
                    </div>
                  </template>
                </el-tooltip>
              </div>
            </template>
            <template v-else>
              <span>{{ row[col.prop] != null ? row[col.prop] : "---" }}</span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="分析" width="80" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button
              v-if="row.target_id && !row._isSummary"
              type="primary"
              link
              size="small"
              class="analyze-btn"
            >
              分析
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="footer-bar">
      <span>共 {{ total }} 条</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        layout="prev, pager, next"
        :total="total"
        small
        @current-change="loadData"
        @size-change="loadData"
      />
    </div>

    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 商品投放面板（手动广告的商品定位投放条款列表）。
 *
 * 数据源：LxSpTarget(expression_type="manual") + LxSpTargetReport。
 * 支持手动调整竞价与启停状态。
 */
import { computed, onMounted, reactive, ref } from "vue";
import { Operation, VideoPause } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { getProductTargeting, adjustProductTargetBid, adjustProductTargetState } from "@/api/ads";

defineOptions({ name: "ProductTargetingPanel" });

const props = defineProps<{ campaignId: string; profileId: string }>();

const loading = ref(false);
const tableData = ref<any[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(25);
const currencyIcon = ref("$");
const summaryRow = ref<Record<string, unknown> | null>(null);
const selectedRows = ref<any[]>([]);
const columnConfigVisible = ref(false);

const filters = reactive({
  range: [] as string[],
  state: "",
});

const defaultColumns = [
  { prop: "service_status", label: "服务状态", category: "设置", visible: true, minWidth: 160 },
  { prop: "campaign_name", label: "广告活动", category: "设置", visible: true, minWidth: 200 },
  { prop: "bid", label: "竞价", category: "设置", visible: true, minWidth: 100 },
  { prop: "impressions", label: "曝光量", category: "业绩", visible: true, minWidth: 120 },
  { prop: "clicks", label: "点击", category: "业绩", visible: true, minWidth: 100 },
  { prop: "spends", label: "花费", category: "业绩", visible: true, minWidth: 120 },
  { prop: "adsSales", label: "广告销售额", category: "转化", visible: true, minWidth: 130 },
  { prop: "adsOrders", label: "广告订单", category: "转化", visible: true, minWidth: 110 },
  { prop: "acos", label: "ACoS", category: "转化", visible: true, minWidth: 100 },
];

const activeColumns = ref(defaultColumns);
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

const displayData = computed<any[]>(() => {
  if (tableData.value.length === 0) return [];
  if (!summaryRow.value) return tableData.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...tableData.value];
});

defineExpose({ summaryRow });

const targetingLabelMap: Record<string, string> = {
  asinSameAs: "ASIN 同类商品",
  asinSubstituteRelated: "ASIN 替代商品",
  asinComplementRelated: "ASIN 互补商品",
  asinAccessoryRelated: "ASIN 配件关联",
  asinBrandSameAs: "ASIN 品牌同类",
};

function formatTargetingExpr(expression: any): string {
  if (!expression || !Array.isArray(expression) || expression.length === 0) return "-";
  const first = expression[0];
  if (first?.type) return targetingLabelMap[first.type] || first.type;
  return JSON.stringify(expression);
}

function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

function onHeaderDragEnd(newWidth: number, _oldWidth: number, column: any): void {
  const minW = column.minWidth ? Number(column.minWidth) : 80;
  if (newWidth < minW) {
    column.width = minW;
    column.realWidth = minW;
  }
}

function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

function onColumnConfigSave(cols: any[]): void {
  activeColumns.value = cols;
  ElMessage.success("列配置已保存");
}

function onSearch(): void {
  currentPage.value = 1;
  loadData();
}

function onReset(): void {
  filters.range = [];
  filters.state = "";
  currentPage.value = 1;
  loadData();
}

async function loadData(): Promise<void> {
  loading.value = true;
  try {
    const res = await getProductTargeting({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      date_start: filters.range?.[0] || "",
      date_end: filters.range?.[1] || "",
      state: filters.state || "",
      pageNum: currentPage.value,
      pageSize: pageSize.value,
    });
    tableData.value = res.list || [];
    total.value = res.total || 0;
    summaryRow.value = res.summary ?? null;
    currencyIcon.value = res.currency_icon || "$";
  } catch {
    ElMessage.error("获取商品投放数据失败");
  } finally {
    loading.value = false;
  }
}

async function onBidChange(row: any): Promise<void> {
  const val = Number(row.bid);
  if (!val || val <= 0 || isNaN(val)) {
    ElMessage.warning("竞价必须为大于 0 的数值");
    return;
  }
  try {
    await ElMessageBox.confirm(`确认将竞价修改为 ${val.toFixed(2)}？`, "确认修改竞价", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await adjustProductTargetBid({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      target_id: row.target_id as string | number,
      bid_after: val,
    });
    ElMessage.success("竞价修改已记录");
  } catch {
    ElMessage.error("竞价修改失败");
  }
}

async function onStateChange(row: any, val: string | number | boolean): Promise<void> {
  const s = String(val);
  if (row.state === s) return;
  const oldVal = s === "enabled" ? "paused" : "enabled";
  const label = s === "enabled" ? "启用" : "暂停";
  try {
    await ElMessageBox.confirm(`确认将商品投放状态修改为「${label}」？`, "确认修改状态", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    row.state = oldVal;
    return;
  }
  try {
    await adjustProductTargetState({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      target_id: row.target_id as string | number,
      state: s as "enabled" | "paused",
    });
    ElMessage.success(`${label}已记录`);
  } catch {
    row.state = oldVal;
    ElMessage.error("状态修改失败");
  }
}

onMounted(() => {
  loadData();
});
</script>

<style scoped lang="scss">
.product-targeting-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.filter-bar {
  display: flex;
  flex-shrink: 0;
  gap: 10px;
  align-items: center;
  padding: 8px 0;

  .filter-item {
    flex-shrink: 0;
  }
  .w-110 {
    width: 110px;
  }
}

.data-table-container {
  flex: 1;
  min-height: 0;
}

.footer-bar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.bid-cell {
  display: flex;
  gap: 4px;
  align-items: center;
  .bid-icon {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
  .bid-input {
    width: 80px;
  }
}

.summary-label {
  font-weight: 700;
  color: var(--el-color-primary);
}

.adgroup-name-cell {
  display: flex;
  gap: 4px;
  align-items: center;
  .state-warn {
    color: var(--el-color-warning);
  }
  .text-muted {
    color: var(--el-text-color-secondary);
  }
}

.state-cell {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

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

.bid-cell .recent-star {
  position: relative;
  top: 0;
  right: 0;
}
</style>
