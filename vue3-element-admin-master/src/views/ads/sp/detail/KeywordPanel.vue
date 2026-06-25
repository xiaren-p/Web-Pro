<template>
  <div class="keyword-panel ads-detail-panel">
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
        <el-option label="已启用" value="enabled" />
        <el-option label="已暂停" value="paused" />
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-select
        v-model="filters.matchType"
        size="small"
        class="filter-item w-130"
        placeholder="全部匹配方式"
        clearable
      >
        <el-option label="广泛匹配" value="broad" />
        <el-option label="词组匹配" value="phrase" />
        <el-option label="精准匹配" value="exact" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item"
        style="width: 180px"
        placeholder="请输入关键词"
        clearable
        @keyup.enter="onSearch"
      />
      <el-button type="primary" size="small" @click="onSearch">查询</el-button>
      <el-button size="small" @click="onReset">重置</el-button>
      <span style="flex: 1" />
      <el-tooltip content="切换查看不同投放类型" placement="top">
        <el-icon
          class="mode-switch-hint"
          style="margin-right: 6px; font-size: 14px; color: var(--text-tertiary); cursor: help"
        ><QuestionFilled /></el-icon>
      </el-tooltip>
      <el-button-group size="small" style="margin-right: 6px">
        <el-button type="primary" disabled>关键词</el-button>
        <el-button @click="emit('switch-mode')">商品</el-button>
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

    <!-- 表格 -->
    <div class="data-table-container">
      <el-table
        v-loading="loading"
        class="data-table__content"
        :data="displayData"
        :row-class-name="rowClassName"
        border
        height="calc(100vh - 460px)"
        style="width: 100%"
        @selection-change="onSelectionChange"
        @sort-change="handleSortChange"
      >
        <!-- 固定左：勾选 -->
        <el-table-column
          type="selection"
          width="42"
          fixed="left"
          align="center"
          :resizable="false"
        />

        <!-- 固定左：有效 -->
        <el-table-column label="有效" width="60" fixed="left" align="center" :resizable="false">
          <template #default="{ row }">
            <span v-if="row._isSummary">--</span>
            <div v-else class="state-cell">
              <el-switch
                v-model="row.state"
                size="small"
                style="--el-switch-width: 32px; --el-switch-height: 16px"
                active-value="enabled"
                inactive-value="paused"
                @change="(val: string | number | boolean) => onSwitchChange(row, val)"
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

        <!-- 固定左：关键词 -->
        <el-table-column label="关键词" min-width="220" fixed="left" align="left">
          <template #default="{ row }">
            <div class="keyword-cell">
              <span class="msku-text msku-text--dark">{{ row.keyword_text || "-" }}</span>
              <span class="match-badge" :class="`match-${row.match_type}`">
                {{ row.match_type_label || row.match_type || "-" }}
              </span>
            </div>
          </template>
        </el-table-column>

        <!-- 动态列（列配置控制） -->
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
            <!-- 服务状态徽标 -->
            <template v-if="col.prop === 'service_status'">
              <span class="status-badge" :class="`status-${row.service_status_type || 'default'}`">
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>

            <!-- 广告活动（带状态图标） -->
            <template v-else-if="col.prop === 'campaign_name'">
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
                <span class="msku-text">{{ row.campaign_name || "-" }}</span>
              </div>
            </template>

            <!-- 竞价可编辑 -->
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
                  <span class="recent-star" @click.stop>★</span>
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

            <!-- 其余列直接渲染 -->
            <template v-else>
              <span>{{ row[col.prop] ?? "-" }}</span>
            </template>
          </template>
        </el-table-column>

        <!-- 固定右：分析 -->
        <el-table-column label="分析" width="64" fixed="right" align="center" :resizable="false">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDrawer(row)">分析</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页 -->
    <div class="pagination-bar">
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

      <el-pagination
        v-model:current-page="pagination.pageNum"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[25, 50, 100]"
        layout="total, sizes, prev, pager, next"
        small
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </div>

    <!-- 列配置抽屉 -->
    <ColumnManager
      v-model="columnConfigVisible"
      :columns="activeColumns"
      @save="onColumnConfigSave"
    />

    <!-- 分析抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="activeRow?.keyword_text || '关键词详情'"
      size="680px"
      direction="rtl"
    >
      <div v-if="activeRow" class="analysis-drawer">
        <!-- 左侧：关键词信息 -->
        <div class="drawer-left">
          <div class="drawer-section-title">关键词</div>
          <div class="keyword-info-card">
            <div class="keyword-text">{{ activeRow.keyword_text }}</div>
            <div class="keyword-meta">
              <span class="match-badge" :class="`match-${activeRow.match_type}`">
                {{ activeRow.match_type_label || activeRow.match_type }}
              </span>
              <span class="keyword-state" :class="`state-tag-${activeRow.state}`">
                {{ formatState(activeRow.state) }}
              </span>
            </div>
            <div class="keyword-detail-row">
              <span class="detail-label">竞价</span>
              <span class="detail-value">{{ activeRow.bid ?? "-" }}</span>
            </div>
            <div class="keyword-detail-row">
              <span class="detail-label">广告活动</span>
              <span class="detail-value">{{ activeRow.campaign_name || "-" }}</span>
            </div>
            <div class="keyword-detail-row">
              <span class="detail-label">广告组</span>
              <span class="detail-value">{{ activeRow.adgroup_name || "-" }}</span>
            </div>
            <div class="keyword-detail-row">
              <span class="detail-label">创建时间</span>
              <span class="detail-value">{{ activeRow.created_at || "-" }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧：分析指标 -->
        <div class="drawer-right">
          <div class="drawer-section-title">分析</div>
          <div class="metrics-grid">
            <div class="metric-card">
              <div class="metric-label">花费</div>
              <div class="metric-value">{{ activeRow.spends ?? "-" }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">广告销售额</div>
              <div class="metric-value">{{ activeRow.adsSales ?? "-" }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">广告订单</div>
              <div class="metric-value">{{ activeRow.adsOrders ?? "-" }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">ACoS</div>
              <div class="metric-value">{{ activeRow.acos ?? "-" }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-drawer>

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
 * 关键词投放面板：展示手动广告活动下所有关键词投放及其指标。
 * 所属板块：ads / 投放（手动）。
 */
import type { KeywordParams } from "@/api/ads";

import { computed, onMounted, reactive, ref, watch } from "vue";
import { useLocalStorage } from "@vueuse/core";
import { Operation, VideoPause, CircleClose, ArrowDown, QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { getKeywords, batchAdjustKeywordState, batchAdjustKeywordBid } from "@/api/ads";
import BatchBidAdjustDialog from "@/components/BatchBidAdjustDialog/index.vue";
import ColumnManager from "@/components/ColumnManager/index.vue";
import { getDefaultDateRange, DATE_RANGE_KEY } from "@/utils/date";

const props = defineProps<{
  campaignId: string;
  profileId: string;
  initialDateRange?: string[];
}>();

const emit = defineEmits<{
  (e: "update-bid", payload: { row: any; bid: number }): void;
  (e: "update-state", payload: { row: any; state: "enabled" | "paused" }): void;
  (e: "switch-mode"): void;
}>();

// ── 筛选状态 ──────────────────────────────────────────
const filters = reactive({
  range: (props.initialDateRange?.length === 2
    ? [...props.initialDateRange]
    : getDefaultDateRange()) as string[],
  state: "",
  matchType: "",
  keyword: "",
});

// 主题：日期双向同步 — 写入 localStorage 供主页回读
watch(
  () => filters.range,
  (val) => {
    if (val?.length === 2) {
      localStorage.setItem(DATE_RANGE_KEY, JSON.stringify(val));
    }
  },
  { deep: true }
);

// ── 分页状态 ──────────────────────────────────────────
const pagination = reactive({ pageNum: 1, pageSize: 25, total: 0 });

// ── 数据状态 ──────────────────────────────────────────
const loading = ref(false);
const rows = ref<any[]>([]);
const currencyIcon = ref("$");
const summaryRow = ref<Record<string, unknown> | null>(null);
const selectedRows = ref<any[]>([]);

/** 排序状态 */
const sortParams = ref<Record<string, string>>({});

// ── 批量操作状态 ───────────────────────────────────────
const batchBidDialogVisible = ref(false);
const batchBidItems = ref<
  Array<{
    id: string | number;
    targetingText: string;
    campaignName: string;
    adgroupName: string;
    currentBid: number;
  }>
>([]);

const displayData = computed<any[]>(() => {
  if (rows.value.length === 0) return [];
  if (!summaryRow.value) return rows.value;
  return [{ ...summaryRow.value, _isSummary: true }, ...rows.value];
});

function rowClassName({ row }: { row: any }): string {
  return row._isSummary ? "is-summary-row" : "";
}

defineExpose({ summaryRow });

// ── 列配置 ──────────────────────────────────────────
const columnConfigVisible = ref(false);

const defaultColumns = [
  { prop: "service_status", label: "服务状态", visible: true, category: "设置", minWidth: 160 },
  { prop: "match_type_label", label: "匹配方式", visible: true, category: "设置", minWidth: 110 },
  { prop: "bid", label: "竞价", visible: true, category: "设置", minWidth: 100 },
  { prop: "time_pricing_bid", label: "分时竞价", visible: true, category: "设置", minWidth: 100 },
  { prop: "portfolio_name", label: "广告组合", visible: false, category: "设置", minWidth: 140 },
  { prop: "campaign_name", label: "广告活动", visible: true, category: "设置", minWidth: 200 },
  { prop: "adgroup_name", label: "广告组", visible: true, category: "设置", minWidth: 140 },
  { prop: "created_at", label: "创建时间", visible: false, category: "设置", minWidth: 160 },
  { prop: "adsSales", label: "广告销售额", visible: true, category: "转化", minWidth: 120 },
  {
    prop: "adsSalesPercent",
    label: "广告销售额%",
    visible: false,
    category: "转化",
    minWidth: 100,
  },
  { prop: "directSales", label: "直接销售额", visible: false, category: "转化", minWidth: 110 },
  { prop: "acos", label: "ACoS", visible: true, category: "转化", minWidth: 100 },
  { prop: "roas", label: "ROAS", visible: true, category: "转化", minWidth: 100 },
  { prop: "adsOrders", label: "广告订单", visible: true, category: "转化", minWidth: 100 },
  { prop: "directOrders", label: "直接订单", visible: false, category: "转化", minWidth: 100 },
  { prop: "cvr", label: "CVR", visible: false, category: "转化", minWidth: 80 },
  { prop: "adsOrderPrice", label: "广告笔单价", visible: false, category: "转化", minWidth: 100 },
  { prop: "adsVolume", label: "广告销量", visible: false, category: "转化", minWidth: 100 },
  { prop: "impressions", label: "曝光量", visible: true, category: "业绩", minWidth: 120 },
  { prop: "impressionsPercent", label: "曝光%", visible: false, category: "业绩", minWidth: 80 },
  { prop: "clicks", label: "点击", visible: true, category: "业绩", minWidth: 100 },
  { prop: "clicksPercent", label: "点击%", visible: false, category: "业绩", minWidth: 80 },
  { prop: "ctr", label: "CTR", visible: true, category: "业绩", minWidth: 90 },
  { prop: "cpc", label: "CPC", visible: true, category: "业绩", minWidth: 90 },
  { prop: "spends", label: "花费", visible: true, category: "业绩", minWidth: 110 },
  { prop: "spendsPercent", label: "花费%", visible: false, category: "业绩", minWidth: 80 },
  { prop: "cpa", label: "CPA", visible: false, category: "业绩", minWidth: 80 },
];

const _savedColVis = useLocalStorage<Record<string, boolean>>("keyword_panel_col_vis", {});

const activeColumns = ref(
  defaultColumns.map((col) => {
    const saved = _savedColVis.value[col.prop];
    return { ...col, visible: saved !== undefined ? saved : col.visible };
  })
);

const visibleColumns = computed(() => activeColumns.value.filter((c) => c.visible));

function onColumnConfigSave(cols: typeof defaultColumns): void {
  activeColumns.value = cols;
  const vis: Record<string, boolean> = {};
  for (const c of cols) {
    vis[c.prop] = c.visible;
  }
  _savedColVis.value = vis;
}

// ── 抽屉状态 ──────────────────────────────────────────
const drawerVisible = ref(false);
const activeRow = ref<any | null>(null);

/**
 * 将状态字段值格式化为中文显示。
 *
 * @param {string} val - state 原始值
 * @returns {string} 中文显示文字
 */
function formatState(val: string): string {
  const map: Record<string, string> = {
    enabled: "已启用",
    paused: "已暂停",
    archived: "已归档",
  };
  return map[val] ?? val ?? "-";
}

/**
 * 打开分析抽屉，展示选中行的详情与指标。
 *
 * @param {any} row - 点击的行数据
 */
function openDrawer(row: any): void {
  activeRow.value = row;
  drawerVisible.value = true;
}

/**
 * 表格勾选变化回调。
 *
 * @param {any[]} rows - 当前所有已勾选的行数据
 */
function onSelectionChange(rows: any[]): void {
  selectedRows.value = rows;
}

// ── 查询 ──────────────────────────────────────────────
/**
 * 加载关键词投放列表数据，调用后端 /ads/keywords 接口。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;
  loading.value = true;

  const params: KeywordParams = {
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    date_start: filters.range?.[0] || undefined,
    date_end: filters.range?.[1] || undefined,
    state: filters.state || undefined,
    match_type: filters.matchType || undefined,
    keyword: filters.keyword || undefined,
    pageNum: pagination.pageNum,
    pageSize: pagination.pageSize,
    sort_prop: sortParams.value.sort_prop || undefined,
    sort_order: sortParams.value.sort_order || undefined,
  };

  getKeywords(params)
    .then((res) => {
      rows.value = res.list ?? [];
      pagination.total = res.total ?? 0;
      currencyIcon.value = res.currency_icon ?? "$";
      summaryRow.value = res.summary ?? null;
      // 为每行注入 _bidInput 临时字段
      for (const row of rows.value) {
        if (!row._isSummary) row._bidInput = row.bid ?? 0;
      }
    })
    .catch(() => {
      ElMessage.error("加载关键词投放失败");
    })
    .finally(() => {
      loading.value = false;
    });
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
  fetchData();
}

function onSearch(): void {
  pagination.pageNum = 1;
  fetchData();
}

function onReset(): void {
  filters.range =
    props.initialDateRange?.length === 2 ? [...props.initialDateRange] : getDefaultDateRange();
  filters.state = "";
  filters.matchType = "";
  filters.keyword = "";
  pagination.pageNum = 1;
  fetchData();
}

// ── 竞价可编辑（emit 到父组件，不调 API）────────────────────────────────────
function confirmBid(row: any): void {
  if (row._confirming) return;
  const raw = Number(row._bidInput);
  // 保留 2 位小数（四舍五入）
  const val = Math.round(raw * 100) / 100;
  const original = Math.round(Number(row.bid ?? 0) * 100) / 100;
  if (!val || val <= 0 || isNaN(val)) {
    row._bidInput = row.bid ?? 0;
    return;
  }
  if (val === original) {
    // 即使值未变也同步显示规范化的两位小数
    row._bidInput = val;
    return;
  }
  row._confirming = true;
  // 输入框立即显示规范化值
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

function resetBid(row: any): void {
  row._bidInput = row.bid ?? 0;
}

// ── 状态可编辑（emit 到父组件，不调 API）──────────────────────────────────
function onSwitchChange(row: any, val: string | number | boolean): void {
  const s = String(val) as "enabled" | "paused";
  const oldVal = s === "enabled" ? "paused" : "enabled";
  const label = s === "enabled" ? "启用" : "暂停";
  ElMessageBox.confirm(`确认将关键词状态修改为「${label}」？`, "确认修改状态", {
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
      `确认将选中的 ${selectedRows.value.length} 条关键词状态修改为「${label}」？`,
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

  const ids = selectedRows.value.map((row) => row.keyword_id).filter(Boolean);
  if (ids.length === 0) {
    ElMessage.error("选中的行缺少有效标识");
    return;
  }

  try {
    const res = await batchAdjustKeywordState({
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
    id: row.keyword_id,
    targetingText: row.keyword_text || "-",
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
    const res = await batchAdjustKeywordBid({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      items,
    });

    ElMessage.success(
      `批量调整竞价完成：成功 ${res.success_count} 条，失败 ${res.failed_count} 条`
    );

    // 更新本地竞价
    items.forEach(({ id, bid }) => {
      const row = rows.value.find((r) => r.keyword_id === id);
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

onMounted(fetchData);
</script>

<style scoped lang="scss">
.keyword-panel {
  .keyword-info-card {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding: 14px;
    background: var(--surface-subtle);
    border-radius: 6px;

    .keyword-text {
      font-size: 14px;
      font-weight: 500;
      line-height: 1.5;
      color: var(--text-primary);
      word-break: break-all;
    }

    .keyword-meta {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .keyword-detail-row {
      display: flex;
      gap: 8px;
      font-size: 13px;

      .detail-label {
        flex-shrink: 0;
        width: 60px;
        color: var(--text-tertiary);
      }

      .detail-value {
        color: var(--text-secondary);
      }
    }
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

.bid-cell {
  position: relative;
  display: flex;
  gap: 4px;
  align-items: center;
  .bid-icon {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
  .bid-input {
    width: 60px;
  }
  .recent-star {
    position: relative;
    top: 0;
    right: 0;
  }
}
</style>
