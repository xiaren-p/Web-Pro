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

    <!-- 列配置抽屉（占位） -->
    <el-drawer v-model="columnConfigVisible" title="列配置" size="360px" />

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
  </div>
</template>

<script setup lang="ts">
/**
 * 关键词投放面板：展示手动广告活动下所有关键词投放及其指标。
 * 所属板块：ads / 投放（手动）。
 */
import type { KeywordParams } from "@/api/ads";

import { computed, onMounted, reactive, ref } from "vue";
import { Operation, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { getKeywords, adjustKeywordBid, adjustKeywordState } from "@/api/ads";

const props = defineProps<{
  campaignId: string;
  profileId: string;
  initialDateRange?: string[];
}>();

// ── 筛选状态 ──────────────────────────────────────────
const filters = reactive({
  range: props.initialDateRange ?? (null as string[] | null),
  state: "",
  matchType: "",
  keyword: "",
});

// ── 分页状态 ──────────────────────────────────────────
const pagination = reactive({ pageNum: 1, pageSize: 25, total: 0 });

// ── 数据状态 ──────────────────────────────────────────
const loading = ref(false);
const rows = ref<any[]>([]);
const currencyIcon = ref("$");
const summaryRow = ref<Record<string, unknown> | null>(null);

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

const visibleColumns = [
  { prop: "service_status", label: "服务状态", minWidth: 160 },
  { prop: "match_type_label", label: "匹配方式", minWidth: 110 },
  { prop: "bid", label: "竞价", minWidth: 100 },
  { prop: "portfolio_name", label: "广告组合", minWidth: 140 },
  { prop: "campaign_name", label: "广告活动", minWidth: 200 },
  { prop: "adgroup_name", label: "广告组", minWidth: 140 },
  { prop: "created_at", label: "创建时间", minWidth: 160 },
  { prop: "spends", label: "花费", minWidth: 110 },
  { prop: "adsSales", label: "广告销售额", minWidth: 120 },
  { prop: "adsOrders", label: "广告订单", minWidth: 100 },
  { prop: "acos", label: "ACoS", minWidth: 100 },
];

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
  };

  getKeywords(params)
    .then((res) => {
      rows.value = res.list ?? [];
      pagination.total = res.total ?? 0;
      currencyIcon.value = res.currency_icon ?? "$";
      summaryRow.value = res.summary ?? null;
    })
    .catch(() => {
      ElMessage.error("加载关键词投放失败");
    })
    .finally(() => {
      loading.value = false;
    });
}

function onSearch(): void {
  pagination.pageNum = 1;
  fetchData();
}

function onReset(): void {
  filters.range = props.initialDateRange ?? null;
  filters.state = "";
  filters.matchType = "";
  filters.keyword = "";
  pagination.pageNum = 1;
  fetchData();
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
    await adjustKeywordBid({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      keyword_id: row.keyword_id,
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
    await ElMessageBox.confirm(`确认将关键词状态修改为「${label}」？`, "确认修改状态", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    row.state = oldVal;
    return;
  }
  try {
    await adjustKeywordState({
      campaign_id: props.campaignId,
      profile_id: props.profileId,
      keyword_id: row.keyword_id as string | number,
      state: s as "enabled" | "paused",
    });
    ElMessage.success(`${label}已记录`);
  } catch {
    row.state = oldVal;
    ElMessage.error("状态修改失败");
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
    width: 80px;
  }
  .recent-star {
    position: relative;
    top: 0;
    right: 0;
  }
}
</style>
