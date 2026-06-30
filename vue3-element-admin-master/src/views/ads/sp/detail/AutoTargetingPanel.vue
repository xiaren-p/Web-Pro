<template>
  <div class="auto-targeting-panel ads-detail-panel">
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

      <el-button size="small" :icon="Filter" class="btn-template">筛选模板</el-button>
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

    <!-- 表格 -->
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
        <!-- 固定左侧：勾选 -->
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :resizable="false"
          :selectable="(row: any) => !row._isSummary"
        />

        <!-- 固定左侧：有效 -->
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

        <!-- 固定左侧：自动定位组（targeting_text） -->
        <el-table-column label="自动定位组" width="120" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <span v-if="row._isSummary" class="summary-label">汇总</span>
            <span v-else class="msku-text msku-text--dark">{{ row.targeting_text || "-" }}</span>
          </template>
        </el-table-column>

        <!-- 固定左侧：广告组（adgroup_name + 状态图标） -->
        <el-table-column label="广告组" min-width="220" fixed="left" align="left" sortable>
          <template #default="{ row }">
            <template v-if="row._isSummary">---</template>
            <el-tooltip
              v-else
              :content="row.adgroup_name ?? ''"
              placement="top"
              :show-after="400"
              :disabled="!isLikelyOverflow(row.adgroup_name, 185)"
            >
              <div class="msku-cell">
                <span
                  class="campaign-state-icon"
                  :class="`state-${row.adgroup_state || 'unknown'}`"
                >
                  <template v-if="row.adgroup_state === 'enabled'">
                    <span class="dot-circle" />
                  </template>
                  <template v-else-if="row.adgroup_state === 'paused'">
                    <el-icon><VideoPause /></el-icon>
                  </template>
                  <template v-else-if="row.adgroup_state === 'archived'">
                    <el-icon><CircleClose /></el-icon>
                  </template>
                </span>
                <span class="msku-text msku-text--dark">{{ row.adgroup_name || "-" }}</span>
                <el-icon class="copy-icon" @click.stop="copyText(row.adgroup_name)">
                  <CopyDocument />
                </el-icon>
              </div>
            </el-tooltip>
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
          :sortable="(col as any).sortable ?? false"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <!-- 服务状态徽标 -->
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

            <!-- 竞价可编辑框 -->
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

            <!-- 建议竞价（带范围提示） -->
            <template v-else-if="col.prop === 'recommended_bid'">
              <template v-if="row._isSummary">---</template>
              <el-tooltip
                v-else
                :content="`建议范围：${row.recommend_range_start} ~ ${row.recommend_range_end}`"
                placement="top"
                :disabled="row.recommended_bid === '-'"
              >
                <span class="recommended-bid">
                  {{ row.recommended_bid === "-" ? "-" : `${currencyIcon}${row.recommended_bid}` }}
                </span>
              </el-tooltip>
            </template>

            <!-- 广告活动（带状态图标） -->
            <template v-else-if="col.prop === 'campaign_name'">
              <template v-if="row._isSummary">---</template>
              <el-tooltip
                v-else
                :content="row.campaign_name ?? ''"
                placement="top"
                :show-after="400"
                :disabled="!isLikelyOverflow(row.campaign_name, 205)"
              >
                <div class="msku-cell">
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
                  <span class="msku-text msku-text--dark">{{ row.campaign_name || "-" }}</span>
                  <el-icon class="copy-icon" @click.stop="copyText(row.campaign_name)">
                    <CopyDocument />
                  </el-icon>
                </div>
              </el-tooltip>
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

            <!-- 默认文本渲染 -->
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右侧：分析 -->
        <el-table-column label="分析" width="80" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button v-if="row.target_id && !row._isSummary" type="primary" link size="small">
              分析
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页栏 -->
      <div class="pager-row">
        <span class="total-count">共 {{ total.toLocaleString() }} 条</span>

        <!-- 批量操作按钮 -->
        <el-dropdown v-if="selectedRows.length > 0" trigger="click" style="margin-left: 12px">
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

        <el-dropdown v-if="selectedRows.length > 0" trigger="click" style="margin-left: 8px">
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

        <el-select
          v-model="pageSize"
          placeholder="每页"
          style="width: 100px; margin-left: auto"
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

    <!-- 批量调整竞价对话框 -->
    <BatchBidAdjustDialog
      v-model="batchBidDialogVisible"
      :items="batchBidItems"
      :currency-icon="currencyIcon"
      @confirm="onBatchBidConfirm"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 自动投放定向条款列表面板。
 * 所属板块：ads / detail。
 * 展示广告活动下四种自动定位组（紧密匹配 / 宽泛匹配 / 同类商品 / 关联商品）
 * 的竞价信息与聚合指标。
 */
import { computed, onMounted, ref, watch } from "vue";
import { useLocalStorage } from "@vueuse/core";
import {
  CopyDocument,
  Filter,
  Operation,
  VideoPause,
  CircleClose,
  ArrowDown,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import ColumnManager from "@/components/ColumnManager/index.vue";
import BatchBidAdjustDialog from "@/components/BatchBidAdjustDialog/index.vue";
import { getAutoTargeting, batchAdjustTargetState, batchAdjustTargetBid } from "@/api/ads";
import { DATE_SHORTCUTS } from "@/utils/ads-date-shortcuts";

defineOptions({ name: "AutoTargetingPanel" });

/**
 * @prop {string} campaignId - 广告活动 ID（必填）
 * @prop {string} profileId - 店铺 Profile ID（必填）
 * @prop {string[]} initialDateRange - 格式 ['YYYY-MM-DD', 'YYYY-MM-DD'] 或空数组
 */
const props = defineProps<{
  campaignId?: string;
  profileId?: string;
  initialDateRange?: string[];
}>();

const emit = defineEmits<{
  (e: "update-bid", payload: { row: any; bid: number }): void;
  (e: "update-state", payload: { row: any; state: "enabled" | "paused" }): void;
}>();

/** 列可见性持久化 */
const _savedColVis = useLocalStorage<Record<string, boolean>>("auto_targeting_panel_col_vis", {});

/** 筛选条件持久化（不含日期范围） */
const _savedFilters = useLocalStorage("auto_targeting_panel_filters", { state: "" });

/** 筛选条件，range 以父页面传入的日期范围初始化 */
const filters = ref({
  range: (props.initialDateRange?.length === 2 ? [...props.initialDateRange] : []) as string[],
  state: _savedFilters.value.state,
});

/** 列配置抽屉显示状态（持久化） */
const columnConfigVisible = useLocalStorage<boolean>("auto_targeting_panel_drawer", false);

/** 数据加载状态 */
const loading = ref(false);

/** 分页状态 */
const total = ref(0);
const currentPage = ref(1);
const pageSize = useLocalStorage<number>("auto_targeting_panel_page_size", 25);

/** 表格数据 */
const tableData = ref<any[]>([]);

/** 汇总行 */
const summaryRow = ref<Record<string, unknown> | null>(null);

defineExpose({ summaryRow });

/** 货币符号 */
const currencyIcon = ref<string>("$");

/** 排序状态 */
const sortParams = ref<Record<string, string>>({});

/** 当前已勾选的行 */
const selectedRows = ref<any[]>([]);

/** 批量调整竞价对话框显示状态 */
const batchBidDialogVisible = ref(false);

/** 批量调整竞价项列表 */
const batchBidItems = ref<
  Array<{
    id: string | number;
    targetingText: string;
    campaignName: string;
    adgroupName: string;
    currentBid: number;
  }>
>([]);

/**
 * 列定义（含 category，供 ColumnManager 分组展示）。
 * visible 控制渲染，由 ColumnManager @save 回调更新。
 */
const activeColumns = ref([
  // 设置
  { prop: "service_status", label: "服务状态", visible: true, category: "设置" },
  {
    prop: "recommended_bid",
    label: "建议竞价",
    visible: true,
    category: "设置",
    sortable: "custom",
  },
  { prop: "bid", label: "竞价", visible: true, category: "设置", sortable: "custom" },
  {
    prop: "time_pricing_bid",
    label: "分时竞价",
    visible: true,
    category: "设置",
    sortable: "custom",
  },
  {
    prop: "portfolio_name",
    label: "广告组合",
    visible: true,
    category: "设置",
    sortable: "custom",
  },
  {
    prop: "campaign_name",
    label: "广告活动",
    visible: true,
    category: "设置",
    minWidth: 240,
    sortable: "custom",
  },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置", sortable: "custom" },
  { prop: "tag", label: "标签", visible: false, category: "设置" },
  // 转化
  { prop: "is", label: "IS", visible: true, category: "转化", sortable: "custom" },
  { prop: "adsSales", label: "广告销售额", visible: true, category: "转化", sortable: "custom" },
  {
    prop: "adsSalesPercent",
    label: "广告销售额%",
    visible: true,
    category: "转化",
    sortable: "custom",
  },
  {
    prop: "directSales",
    label: "直接销售额",
    visible: false,
    category: "转化",
    sortable: "custom",
  },
  { prop: "acos", label: "ACoS", visible: true, category: "转化", sortable: "custom" },
  { prop: "roas", label: "ROAS", visible: true, category: "转化", sortable: "custom" },
  { prop: "adsOrders", label: "广告订单", visible: true, category: "转化", sortable: "custom" },
  { prop: "directOrders", label: "直接订单", visible: false, category: "转化", sortable: "custom" },
  { prop: "cvr", label: "CVR", visible: false, category: "转化", sortable: "custom" },
  {
    prop: "adsOrderPrice",
    label: "广告笔单价",
    visible: false,
    category: "转化",
    sortable: "custom",
  },
  { prop: "adsVolume", label: "广告销量", visible: false, category: "转化", sortable: "custom" },
  // 业绩
  { prop: "impressions", label: "曝光量", visible: true, category: "业绩", sortable: "custom" },
  {
    prop: "impressionsPercent",
    label: "曝光%",
    visible: false,
    category: "业绩",
    sortable: "custom",
  },
  { prop: "clicks", label: "点击", visible: true, category: "业绩", sortable: "custom" },
  { prop: "clicksPercent", label: "点击%", visible: false, category: "业绩", sortable: "custom" },
  { prop: "ctr", label: "CTR", visible: true, category: "业绩", sortable: "custom" },
  { prop: "cpc", label: "CPC", visible: true, category: "业绩", sortable: "custom" },
  { prop: "spends", label: "花费", visible: true, category: "业绩", sortable: "custom" },
  { prop: "spendsPercent", label: "花费%", visible: false, category: "业绩", sortable: "custom" },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩", sortable: "custom" },
]);

// 用存储的可见性覆盖代码默认定义（仅覆盖有记录的列）
activeColumns.value.forEach((col) => {
  if (_savedColVis.value[col.prop] !== undefined) {
    col.visible = _savedColVis.value[col.prop];
  }
});

/**
 * 过滤出 visible=true 的列用于动态渲染。
 *
 * @returns {列定义数组}
 */
const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

/**
 * 表格展示数据 = 汇总行（置顶）+ 分页数据。
 *
 * @returns {any[]}
 */
const displayData = computed<any[]>(() => {
  if (!summaryRow.value) return tableData.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...tableData.value];
});

/**
 * 为汇总行附加样式类。
 *
 * @param {{ row: any }} 下构 - el-table 行上下文
 * @returns {string}
 */
function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

/**
 * ColumnManager 保存回调，更新列配置并持久化可见性。
 *
 * @param {typeof activeColumns.value} columns - 用户配置后的完整列数组
 */
function onColumnConfigSave(columns: typeof activeColumns.value): void {
  activeColumns.value = columns;
  _savedColVis.value = Object.fromEntries(columns.map((c) => [c.prop, c.visible]));
  ElMessage.success("列配置已保存");
}

// 筛选条件变化时自动持久化（不含日期范围）
watch(
  () => filters.value.state,
  () => {
    _savedFilters.value = { state: filters.value.state };
  }
);

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
  fetchData();
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
  _savedFilters.value = { state: "" };
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
 * 加载自动投放条款列表，调用后端 /ads/auto-targeting 接口。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;

  loading.value = true;
  getAutoTargeting({
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    date_start: filters.value.range?.[0] || undefined,
    date_end: filters.value.range?.[1] || undefined,
    state: filters.value.state || undefined,
    pageNum: currentPage.value,
    pageSize: pageSize.value,
    sort_prop: sortParams.value.sort_prop || undefined,
    sort_order: sortParams.value.sort_order || undefined,
  })
    .then((res) => {
      tableData.value = res.list ?? [];
      total.value = res.total ?? 0;
      summaryRow.value = res.summary ?? null;
      currencyIcon.value = res.currency_icon ?? "$";
      for (const row of tableData.value) {
        if (!row._isSummary) row._bidInput = row.bid ?? 0;
      }
    })
    .catch(() => {
      ElMessage.error("自动投放数据加载失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

/**
 * 确认竞价修改：弹窗确认后 emit update-bid，父组件调 API。
 */
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
      emit("update-bid", { row, bid: val });
    })
    .catch(() => {
      row._bidInput = row.bid ?? 0;
    })
    .finally(() => {
      row._confirming = false;
    });
}

/**
 * 还原竞价输入框为当前 row.bid（esc 或取消时调用）。
 */
function resetBid(row: any): void {
  row._bidInput = row.bid ?? 0;
}

/**
 * 状态 switch 变更：弹窗确认后 emit update-state，取消时还原 switch。
 */
function onSwitchChange(row: any, val: string | number | boolean): void {
  const s = String(val) as "enabled" | "paused";
  const oldVal = s === "enabled" ? "paused" : "enabled";
  const label = s === "enabled" ? "启用" : "暂停";
  ElMessageBox.confirm(`确认将投放状态修改为「${label}」？`, "确认修改状态", {
    confirmButtonText: "确认",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => {
      emit("update-state", { row, state: s });
    })
    .catch(() => {
      row.state = oldVal;
    });
}

/**
 * 表格勾选变化回调。
 *
 * @param {any[]} rows - 当前所有已勾选的行数据
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

/**
 * 粗估文本是否会溢出指定显示宽度，用于按需启用 tooltip。
 *
 * @param {string | null | undefined} text - 显示文本
 * @param {number} displayWidth - 可用文本宽度（px）
 * @param {number} maxLines - 最大行数，默认 2
 * @returns {boolean}
 */
function isLikelyOverflow(
  text: string | null | undefined,
  displayWidth: number,
  maxLines = 2
): boolean {
  if (!text) return false;
  const charsPerLine = Math.max(1, Math.floor(displayWidth / 9));
  return text.length > charsPerLine * maxLines;
}

/**
 * 复制文本到剪贴板，成功后弹出提示。
 *
 * @param {string | undefined} text - 要复制的文本内容
 */
async function copyText(text: string | undefined): Promise<void> {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success("已复制");
  } catch {
    ElMessage.error("复制失败");
  }
}

/**
 * 列宽拖拽结束回调，强制列宽不低于各列的 minWidth。
 *
 * @param {number} newWidth - 拖拽后的新宽度
 * @param {number} _oldWidth - 拖拽前的旧宽度
 * @param {any} column - Element Plus 内部列对象
 */
function onHeaderDragEnd(newWidth: number, _oldWidth: number, column: any): void {
  const minW = column.minWidth ? Number(column.minWidth) : 80;
  if (newWidth < minW) {
    column.width = minW;
    column.realWidth = minW;
  }
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
  try {
    await ElMessageBox.confirm(
      `确认将选中的 ${selectedRows.value.length} 条投放状态修改为「${label}」？`,
      "确认批量修改状态",
      {
        confirmButtonText: "确认",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
  } catch {
    return;
  }

  const ids = selectedRows.value.map((row) => row.target_id).filter(Boolean);
  if (ids.length === 0) {
    ElMessage.error("选中的行缺少有效标识");
    return;
  }

  try {
    const res = await batchAdjustTargetState({
      campaign_id: props.campaignId!,
      profile_id: props.profileId!,
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
    targetingText: row.targeting_text || "-",
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
    const res = await batchAdjustTargetBid({
      campaign_id: props.campaignId!,
      profile_id: props.profileId!,
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
  fetchData();
});
</script>

<style scoped lang="scss">
/* 通用筛选栏、表格、徽标、分页样式 → src/styles/ads-panel.scss → .ads-detail-panel */

/* 图标按钮（列配置触发器） */
.btn-icon-only {
  padding: 0 9px;
  color: var(--text-secondary);
  border-color: var(--border-base);
}

/* 单元格行高 */
:deep(.el-table .el-table__cell) {
  padding: 9px 0 !important;
}

/* 竞价可编辑小框 */
.bid-cell {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  width: 65px;

  .bid-icon {
    flex-shrink: 0;
    font-size: 12px;
    line-height: 1;
    color: var(--text-secondary);
  }

  .bid-input {
    flex: none;
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

/* 建议竞价文字 */
.recommended-bid {
  font-size: 13px;
  color: var(--color-primary-500);
  cursor: default;
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

.bid-cell .recent-star {
  position: relative;
  top: 0;
  right: 0;
}
</style>
