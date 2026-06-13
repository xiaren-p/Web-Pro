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
        :data="rows"
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
            <el-switch
              v-model="row.state"
              active-value="enabled"
              inactive-value="paused"
              disabled
            />
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

import { onMounted, reactive, ref } from "vue";
import { Operation, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { getKeywords } from "@/api/ads";

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

onMounted(fetchData);
</script>

<style scoped lang="scss">
.keyword-panel {
  .filter-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    padding: 12px 0;
  }

  .filter-item {
    &.w-110 {
      width: 110px;
    }

    &.w-130 {
      width: 130px;
    }
  }

  .keyword-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .match-badge {
    display: inline-block;
    padding: 1px 6px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
    border-radius: 3px;

    &.match-exact {
      color: var(--color-success-500);
      background: var(--color-success-50);
      border: 1px solid var(--color-success-200);
    }

    &.match-phrase {
      color: var(--color-warning-600);
      background: var(--color-warning-50);
      border: 1px solid var(--color-warning-200);
    }

    &.match-broad {
      color: var(--color-primary-500);
      background: var(--color-primary-50);
      border: 1px solid var(--color-primary-200);
    }
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    font-size: 12px;
    border-radius: 4px;
  }

  .summary-label {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .msku-cell {
    display: flex;
    gap: 4px;
    align-items: center;
  }

  .msku-text {
    font-size: 13px;
    color: var(--text-primary);
  }

  .dot-circle {
    display: inline-block;
    flex-shrink: 0;
    width: 8px;
    height: 8px;
    background: var(--color-success-500);
    border-radius: 50%;
  }

  .pagination-bar {
    display: flex;
    justify-content: flex-end;
    padding: 12px 0 4px;
  }

  // 分析抽屉
  .analysis-drawer {
    display: flex;
    gap: 20px;
    height: 100%;
    padding: 4px 0;

    .drawer-left {
      flex: 0 0 260px;
      padding-right: 16px;
      border-right: 1px solid var(--border-subtle);
    }

    .drawer-right {
      flex: 1;
    }

    .drawer-section-title {
      margin-bottom: 12px;
      font-size: 14px;
      font-weight: 600;
      color: var(--text-primary);
    }

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

      .keyword-state {
        padding: 1px 6px;
        font-size: 12px;
        border-radius: 3px;

        &.state-tag-enabled {
          color: var(--color-success-500);
          background: var(--color-success-50);
          border: 1px solid var(--color-success-200);
        }

        &.state-tag-paused {
          color: #e6a23c;
          background: #fdf6ec;
          border: 1px solid #f5dab1;
        }

        &.state-tag-archived {
          color: var(--text-tertiary);
          background: #f4f4f5;
          border: 1px solid #d3d4d6;
        }
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

    .metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;

      .metric-card {
        padding: 14px 16px;
        background: var(--surface-subtle);
        border-radius: 6px;

        .metric-label {
          margin-bottom: 6px;
          font-size: 12px;
          color: var(--text-tertiary);
        }

        .metric-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--text-primary);
        }
      }
    }
  }
}

:deep(.el-table__fixed-right) {
  box-shadow: -2px 0 6px rgba(0, 0, 0, 0.06);
}
</style>
