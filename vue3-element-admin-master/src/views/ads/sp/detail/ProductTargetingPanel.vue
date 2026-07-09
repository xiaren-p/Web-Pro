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
        :shortcuts="DATE_SHORTCUTS"
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
        <el-option label="已归档" value="archived" />
      </el-select>

      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>

      <span style="flex: 1" />

      <el-tooltip content="切换查看不同投放类型" placement="top">
        <el-icon
          class="mode-switch-hint"
          style="margin-right: 6px; font-size: 14px; color: var(--text-tertiary); cursor: help"
        >
          <QuestionFilled />
        </el-icon>
      </el-tooltip>
      <el-button-group size="small" style="margin-right: 6px">
        <el-button @click="emit('switch-mode')">关键词</el-button>
        <el-button type="primary" disabled>商品</el-button>
      </el-button-group>

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
        @sort-change="handleSortChange"
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
                @change="(val: string | number | boolean) => onSwitchChange(row, val)"
              />
              <el-tooltip
                v-if="row.latest_state_adjustment?.has_recent"
                placement="top"
                popper-class="latest-adj-tooltip"
              >
                <span class="recent-star" @click.stop>*</span>
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

        <el-table-column label="商品投放" min-width="280" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <div v-else class="targeting-expr-cell">
              <img v-if="row.expression_img" :src="row.expression_img" class="targeting-img" />
              <div class="targeting-info">
                <span class="targeting-type-label">{{ formatTargetingExpr(row.expression) }}</span>
                <small v-if="row.expression_asin" class="targeting-asin">
                  {{ row.expression_asin }}
                </small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column
          v-for="col in visibleColumns"
          :key="col.prop"
          :prop="col.prop"
          :label="col.label"
          :min-width="col.minWidth || 120"
          :sortable="(col as any).sortable || false"
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
                  v-model="row._bidInput"
                  size="small"
                  class="bid-input"
                  type="text"
                  inputmode="decimal"
                  @keyup.enter="confirmBid(row)"
                  @keyup.esc="resetBid(row)"
                  @blur="confirmBid(row)"
                />
                <el-tooltip
                  v-if="row.latest_bid_adjustment?.has_recent"
                  placement="top"
                  popper-class="latest-adj-tooltip"
                >
                  <span class="recent-star" @click.stop>*</span>
                  <template #content>
                    <div class="latest-adj-content">
                      <div v-for="(line, idx) in row.latest_bid_adjustment.lines" :key="idx">
                        {{ line }}
                      </div>
                    </div>
                  </template>
                </el-tooltip>
              </div>
            </template>
            <!-- 分时竞价（含星标） -->
            <template v-else-if="col.prop === 'time_pricing_bid'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="bid-cell">
                <span>{{ row.time_pricing_bid ?? "-" }}</span>
                <el-tooltip
                  v-if="row.latest_time_pricing_adjustment?.has_recent"
                  placement="top"
                  popper-class="latest-adj-tooltip"
                >
                  <span class="recent-star" @click.stop>*</span>
                  <template #content>
                    <div class="latest-adj-content">
                      <div
                        v-for="(line, idx) in row.latest_time_pricing_adjustment.lines"
                        :key="idx"
                      >
                        {{ line }}
                      </div>
                    </div>
                  </template>
                </el-tooltip>
              </div>
            </template>
            <template v-else-if="col.prop === 'campaign_name'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="msku-cell">
                <span
                  class="campaign-state-icon"
                  :class="`state-${row.campaign_state || 'unknown'}`"
                >
                  <template v-if="row.campaign_state === 'enabled'">
                    <span class="dot-circle" />
                  </template>
                  <template v-else-if="row.campaign_state === 'paused'">
                    <el-icon><VideoPause /></el-icon>
                  </template>
                  <template v-else-if="row.campaign_state === 'archived'">
                    <el-icon><CircleClose /></el-icon>
                  </template>
                </span>
                <span class="msku-text">{{ row.campaign_name || "-" }}</span>
              </div>
            </template>
            <template v-else-if="col.prop === 'adgroup_name'">
              <template v-if="row._isSummary">---</template>
              <div v-else class="msku-cell">
                <el-icon v-if="row.adgroup_state === 'paused'" class="state-warn" :size="14">
                  <VideoPause />
                </el-icon>
                <span class="msku-text" :class="{ 'text-muted': row.adgroup_state === 'paused' }">
                  {{ row.adgroup_name || "-" }}
                </span>
              </div>
            </template>
            <template v-else>
              <span>{{ row[col.prop] != null ? row[col.prop] : "---" }}</span>
            </template>
          </template>
        </el-table-column>

        <el-table-column label="分析" width="64" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <template v-if="row.target_id && !row._isSummary">
              <el-tooltip content="查看历史调整" placement="left">
                <el-icon class="analysis-icon" :size="16" @click.stop="openHistory(row)">
                  <Clock />
                </el-icon>
              </el-tooltip>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="footer-bar">
      <!-- 批量操作按钮 -->
      <el-dropdown v-if="selectedRows.length > 0" trigger="click" style="margin-right: 12px">
        <el-button type="primary" size="small">
          调状态
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="batchSetState('enabled')">启用</el-dropdown-item>
            <el-dropdown-item @click="batchSetState('paused')">暂停</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <el-dropdown v-if="selectedRows.length > 0" trigger="click" style="margin-right: 12px">
        <el-button size="small">
          批量调竞价
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item @click="openBatchBidDialog">批量调整竞价</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>

      <span>共 {{ total }} 条</span>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        layout="total, sizes, prev, pager, next"
        :page-sizes="[25, 50, 100]"
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

    <!-- 批量调整竞价对话框 -->
    <BatchBidAdjustDialog
      v-model="batchBidDialogVisible"
      :items="batchBidItems"
      :currency-icon="currencyIcon"
      @confirm="onBatchBidConfirm"
    />
    <AdjustmentHistoryDialog ref="adjHistoryDialog" />
  </div>
</template>

<script setup lang="ts">
/**
 * 商品投放面板（手动广告的商品定位投放条款列表）。
 *
 * 数据源：LxSpTarget(expression_type="manual") + LxSpTargetReport。
 * 支持手动调整竞价与启停状态。
 */
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useLocalStorage } from "@vueuse/core";
import {
  Operation,
  VideoPause,
  ArrowDown,
  QuestionFilled,
  CircleClose,
  Clock,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ColumnManager from "@/components/ColumnManager/index.vue";
import BatchBidAdjustDialog from "@/components/BatchBidAdjustDialog/index.vue";
import AdjustmentHistoryDialog from "@/views/ads/sp/components/AdjustmentHistoryDialog.vue";
import {
  getProductTargeting,
  batchAdjustProductTargetState,
  batchAdjustProductTargetBid,
} from "@/api/ads";
import { getDefaultDateRange, DATE_RANGE_KEY } from "@/utils/date";
import { DATE_SHORTCUTS } from "@/utils/ads-date-shortcuts";

defineOptions({ name: "ProductTargetingPanel" });

const props = defineProps<{
  campaignId: string;
  profileId: string;
  initialDateRange?: string[];
}>();
const emit = defineEmits<{
  (e: "target-bid", payload: { row: any; bid: number }): void;
  (e: "target-state", payload: { row: any; state: "enabled" | "paused" }): void;
  (e: "switch-mode"): void;
}>();

const loading = ref(false);
const tableData = ref<any[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(25);
const currencyIcon = ref("$");
const summaryRow = ref<Record<string, unknown> | null>(null);
const selectedRows = ref<any[]>([]);
const columnConfigVisible = ref(false);

/** 排序状态 */
const sortParams = ref<Record<string, string>>({});

// ── 批量操作状态 ───────────────────────────────────────
const batchBidDialogVisible = ref(false);
const adjHistoryDialog = ref<InstanceType<typeof AdjustmentHistoryDialog>>();

function openHistory(row: any): void {
  adjHistoryDialog.value?.open({
    target_id: row.target_id || row.id,
    profile_id: props.profileId,
  });
}
const batchBidItems = ref<
  Array<{
    id: string | number;
    targetingText: string;
    campaignName: string;
    adgroupName: string;
    currentBid: number;
  }>
>([]);

const filters = reactive({
  range: props.initialDateRange?.length === 2 ? [...props.initialDateRange] : getDefaultDateRange(),
  state: "",
});

watch(
  () => filters.range,
  (val) => {
    if (val?.length === 2) {
      localStorage.setItem(DATE_RANGE_KEY, JSON.stringify(val));
    }
  }
);

const defaultColumns = [
  { prop: "service_status", label: "服务状态", category: "设置", visible: true, minWidth: 160 },
  {
    prop: "portfolio_name",
    label: "广告组合",
    visible: false,
    category: "设置",
    minWidth: 140,
    sortable: "custom",
  },
  {
    prop: "campaign_name",
    label: "广告活动",
    category: "设置",
    visible: true,
    minWidth: 200,
    sortable: "custom",
  },
  {
    prop: "adgroup_name",
    label: "广告组",
    visible: true,
    category: "设置",
    minWidth: 140,
    sortable: "custom",
  },
  {
    prop: "bid",
    label: "竞价",
    category: "设置",
    visible: true,
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "time_pricing_bid",
    label: "分时竞价",
    category: "设置",
    visible: true,
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "created_at",
    label: "创建时间",
    visible: false,
    category: "设置",
    minWidth: 160,
    sortable: "custom",
  },
  {
    prop: "adsSales",
    label: "广告销售额",
    category: "转化",
    visible: true,
    minWidth: 130,
    sortable: "custom",
  },
  {
    prop: "adsSalesPercent",
    label: "广告销售额%",
    visible: false,
    category: "转化",
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "directSales",
    label: "直接销售额",
    visible: false,
    category: "转化",
    minWidth: 110,
    sortable: "custom",
  },
  {
    prop: "acos",
    label: "ACoS",
    category: "转化",
    visible: true,
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "roas",
    label: "ROAS",
    category: "转化",
    visible: true,
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "adsOrders",
    label: "广告订单",
    category: "转化",
    visible: true,
    minWidth: 110,
    sortable: "custom",
  },
  {
    prop: "directOrders",
    label: "直接订单",
    visible: false,
    category: "转化",
    minWidth: 100,
    sortable: "custom",
  },
  { prop: "cvr", label: "CVR", visible: false, category: "转化", minWidth: 80, sortable: "custom" },
  {
    prop: "adsOrderPrice",
    label: "广告笔单价",
    visible: false,
    category: "转化",
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "adsVolume",
    label: "广告销量",
    visible: false,
    category: "转化",
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "impressions",
    label: "曝光量",
    category: "业绩",
    visible: true,
    minWidth: 120,
    sortable: "custom",
  },
  {
    prop: "impressionsPercent",
    label: "曝光%",
    visible: false,
    category: "业绩",
    minWidth: 80,
    sortable: "custom",
  },
  {
    prop: "clicks",
    label: "点击",
    category: "业绩",
    visible: true,
    minWidth: 100,
    sortable: "custom",
  },
  {
    prop: "clicksPercent",
    label: "点击%",
    visible: false,
    category: "业绩",
    minWidth: 80,
    sortable: "custom",
  },
  { prop: "ctr", label: "CTR", category: "业绩", visible: true, minWidth: 90, sortable: "custom" },
  { prop: "cpc", label: "CPC", category: "业绩", visible: true, minWidth: 90, sortable: "custom" },
  {
    prop: "spends",
    label: "花费",
    category: "业绩",
    visible: true,
    minWidth: 120,
    sortable: "custom",
  },
  {
    prop: "spendsPercent",
    label: "花费%",
    visible: false,
    category: "业绩",
    minWidth: 80,
    sortable: "custom",
  },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩", minWidth: 80, sortable: "custom" },
];

const _savedColumns = useLocalStorage<any[]>("product_targeting_panel_columns", []);

const activeColumns = ref(
  (() => {
    const cached = _savedColumns.value;
    if (cached && cached.length > 0) {
      const defaultMap = new Map(defaultColumns.map((c) => [c.prop, c]));
      const cachedProps = new Set<string>();
      const merged: any[] = [];
      for (const c of cached) {
        const def = defaultMap.get(c.prop);
        if (def) {
          cachedProps.add(c.prop);
          merged.push({ ...c, ...def });
        }
      }
      for (const c of defaultColumns) {
        if (!cachedProps.has(c.prop)) merged.push(c);
      }
      return merged;
    }
    return defaultColumns.map((col) => ({ ...col }));
  })()
);
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

const displayData = computed<any[]>(() => {
  for (const row of tableData.value) {
    if (row._isSummary) continue;
    if (row._bidInput === undefined || row._bidInput === null) {
      row._bidInput = row.bid ?? 0;
    }
  }
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
  _savedColumns.value = JSON.parse(JSON.stringify(cols));
  ElMessage.success("列配置已保存");
}

/**
 * 表格排序变化回调。
 *
 * @param {{ prop: string; order: string }} sort - Element Plus 排序事件参数
 */
function handleSortChange({ prop, order }: { prop: string; order: string }): void {
  sortParams.value = {
    sort_prop: prop || "",
    sort_order: order === "ascending" ? "asc" : order === "descending" ? "desc" : "",
  };
  loadData();
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
      sort_prop: sortParams.value.sort_prop || undefined,
      sort_order: sortParams.value.sort_order || undefined,
    });
    tableData.value = res.list || [];
    total.value = res.total || 0;
    summaryRow.value = res.summary ?? null;
    currencyIcon.value = res.currency_icon || "$";
    for (const row of tableData.value) {
      if (!row._isSummary) row._bidInput = row.bid ?? 0;
    }
  } catch {
    ElMessage.error("获取商品投放数据失败");
  } finally {
    loading.value = false;
  }
}

function confirmBid(row: any): void {
  if (row._confirming) return;
  const raw = Number(row._bidInput);
  const val = Math.round(raw * 100) / 100;
  const original = Math.round(Number(row.bid ?? 0) * 100) / 100;
  if (!val || val <= 0 || isNaN(val)) {
    row._bidInput = row.bid ?? 0;
    return;
  }
  if (val === original) {
    row._bidInput = val;
    return;
  }
  row._confirming = true;
  row._bidInput = val;
  ElMessageBox.confirm(`确认将竞价修改为 ${val.toFixed(2)}？`, "确认修改竞价", {
    confirmButtonText: "确认",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => {
      emit("target-bid", { row, bid: val });
    })
    .catch(() => {
      row._bidInput = row.bid ?? 0;
    })
    .finally(() => {
      row._confirming = false;
    });
}

function resetBid(row: any): void {
  row._bidInput = row.bid ?? 0;
}

function onSwitchChange(row: any, val: string | number | boolean): void {
  const s = String(val) as "enabled" | "paused";
  emit("target-state", { row, state: s });
}

/**
 * 批量设置状态（启用/暂停）。
 *
 * @param {"enabled" | "paused"} state - 目标状态
 */
async function batchSetState(state: "enabled" | "paused"): Promise<void> {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先选择要操作的行");
    return;
  }

  const label = state === "enabled" ? "启用" : "暂停";

  const ids = selectedRows.value.map((row) => row.target_id).filter(Boolean);
  if (ids.length === 0) {
    ElMessage.error("选中的行缺少有效标识");
    return;
  }

  try {
    const res = await batchAdjustProductTargetState({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      ids,
      state,
    });

    ElMessage.success(
      `批量${label}完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`
    );

    // 更新本地状态
    selectedRows.value.forEach((row) => {
      row.state = state;
    });

    // 清空选中
    selectedRows.value = [];
  } catch (error) {
    console.error("[batchSetState] 批量修改状态失败", error);
    ElMessage.error("批量修改状态失败");
  }
}

/**
 * 打开批量调整竞价对话框。
 */
function openBatchBidDialog(): void {
  if (selectedRows.value.length === 0) {
    ElMessage.warning("请先选择要操作的行");
    return;
  }

  batchBidItems.value = selectedRows.value.map((row) => ({
    id: row.target_id,
    targetingText: formatTargetingExpr(row.expression),
    campaignName: row.campaign_name || "-",
    adgroupName: row.adgroup_name || "-",
    currentBid: row.bid ?? 0,
  }));

  batchBidDialogVisible.value = true;
}

/**
 * 确认批量调整竞价。
 *
 * @param {Array<{ id: string | number; bid: number }>} items - 调整项列表
 */
async function onBatchBidConfirm(
  items: Array<{ id: string | number; bid: number }>
): Promise<void> {
  if (items.length === 0) {
    ElMessage.warning("没有要调整的竞价项");
    return;
  }

  try {
    const res = await batchAdjustProductTargetBid({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      items,
    });

    ElMessage.success(
      `批量调整竞价完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`
    );

    // 更新本地竞价
    items.forEach(({ id, bid }) => {
      const row = tableData.value.find((r) => r.target_id === id);
      if (row) {
        row.bid = bid;
        row._bidInput = bid;
      }
    });

    // 清空选中
    selectedRows.value = [];
  } catch (error) {
    console.error("[onBatchBidConfirm] 批量调整竞价失败", error);
    ElMessage.error("批量调整竞价失败");
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
    width: 60px;
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
  color: var(--color-danger-500);
  cursor: help;
}

.adj-history-icon {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
  color: #909399;
  cursor: pointer;
}
.adj-history-icon:hover {
  color: var(--el-color-primary);
}

.analysis-icon {
  cursor: pointer;
  color: #909399;
}
.analysis-icon:hover {
  color: var(--el-color-primary);
}

.bid-cell .recent-star {
  position: relative;
  top: 0;
  right: 0;
}

.targeting-expr-cell {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 2px 0;

  .targeting-img {
    flex-shrink: 0;
    width: 44px;
    height: 44px;
    object-fit: cover;
    border-radius: 4px;
  }

  .targeting-info {
    display: flex;
    flex: 1;
    flex-direction: column;
    gap: 4px;
    min-width: 0;
  }

  .targeting-type-label {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .targeting-asin {
    font-size: 12px;
    color: var(--color-primary-600);
  }
}
</style>
