<template>
  <div class="auto-negative-targeting-panel ads-detail-panel">
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
        <el-option label="已归档" value="archived" />
      </el-select>
      <el-select
        v-model="filters.expType"
        size="small"
        class="filter-item w-130"
        placeholder="全部否定类型"
        clearable
      >
        <el-option label="否定ASIN" value="asin" />
        <el-option label="否定品牌" value="brand" />
      </el-select>
      <el-input
        v-model="filters.keyword"
        size="small"
        class="filter-item"
        style="width: 200px"
        placeholder="请输入ASIN或品牌"
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
              inactive-value="archived"
              disabled
            />
          </template>
        </el-table-column>

        <!-- 固定左：否定内容（ASIN 商品卡片） -->
        <el-table-column label="有效 否定内容" min-width="260" fixed="left" align="left">
          <template #default="{ row }">
            <div class="asin-cell">
              <!-- ASIN 编码 + 否定类型标签 -->
              <div class="asin-header">
                <span class="asin-code">{{ row.exp_value || "-" }}</span>
                <span class="exp-type-badge" :class="`exp-${row.exp_type}`">
                  {{ row.exp_type_label || row.exp_type || "-" }}
                </span>
              </div>
              <!-- 商品标题（仅 ASIN 类型有标题） -->
              <div v-if="row.asin_title" class="asin-title" :title="row.asin_title">
                {{ row.asin_title }}
              </div>
              <!-- 价格 / 评分 / 评论数 -->
              <div v-if="row.exp_type === 'asin'" class="asin-meta">
                <span v-if="row.asin_price !== '-'" class="meta-item meta-price">
                  {{ row.asin_price }}
                </span>
                <span v-if="row.asin_stars !== '-'" class="meta-item">
                  ★ {{ row.asin_stars }}
                </span>
                <span v-if="row.asin_review_count !== '-'" class="meta-item meta-reviews">
                  {{ row.asin_review_count }} 评论
                </span>
              </div>
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
              <span
                class="status-badge"
                :class="`status-${row.service_status_type || 'default'}`"
              >
                {{ row.service_status_label || row.service_status || "-" }}
              </span>
            </template>

            <!-- 广告活动（带状态图标） -->
            <template v-else-if="col.prop === 'campaign_name'">
              <div class="msku-cell">
                <span class="campaign-state-icon" :class="`state-${row.campaign_state || 'unknown'}`">
                  <template v-if="row.campaign_state === 'enabled'"><span class="dot-circle" /></template>
                  <template v-else-if="row.campaign_state === 'paused'"><el-icon><VideoPause /></el-icon></template>
                  <template v-else-if="row.campaign_state === 'archived'"><el-icon><CircleClose /></el-icon></template>
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
            <el-button
              type="primary"
              link
              size="small"
              @click="openDrawer(row)"
            >
              分析
            </el-button>
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
      :title="activeRow ? (activeRow.exp_value || '否定商品详情') : '否定商品详情'"
      size="680px"
      direction="rtl"
    >
      <div v-if="activeRow" class="analysis-drawer">
        <!-- 左侧：有效否定内容（商品卡片） -->
        <div class="drawer-left">
          <div class="drawer-section-title">有效 否定内容</div>
          <div class="product-info-card">
            <div class="product-asin-row">
              <span class="product-asin">{{ activeRow.exp_value }}</span>
              <span class="exp-type-badge" :class="`exp-${activeRow.exp_type}`">
                {{ activeRow.exp_type_label || activeRow.exp_type }}
              </span>
            </div>
            <div v-if="activeRow.asin_title" class="product-title">
              {{ activeRow.asin_title }}
            </div>
            <div v-if="activeRow.exp_type === 'asin'" class="product-meta">
              <span v-if="activeRow.asin_price !== '-'" class="meta-item meta-price">
                {{ activeRow.asin_price }}
              </span>
              <span v-if="activeRow.asin_stars !== '-'" class="meta-item">
                ★ {{ activeRow.asin_stars }}
              </span>
              <span v-if="activeRow.asin_review_count !== '-'" class="meta-item meta-reviews">
                {{ activeRow.asin_review_count }} 评论
              </span>
            </div>
            <div class="product-detail-row">
              <span class="detail-label">广告活动</span>
              <span class="detail-value">{{ activeRow.campaign_name || "-" }}</span>
            </div>
            <div class="product-detail-row">
              <span class="detail-label">广告组</span>
              <span class="detail-value">{{ activeRow.adgroup_name || "-" }}</span>
            </div>
            <div class="product-detail-row">
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
 * 自动广告否定商品面板：展示当前广告活动下所有否定定向（否定ASIN / 否定品牌）及其指标。
 * 所属板块：ads / 否定投放。
 */
import type { AutoNegativeTargetingParams } from "@/api/ads";

import { onMounted, reactive, ref } from "vue";
import { Operation, VideoPause, CircleClose } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import { getAutoNegativeTargeting } from "@/api/ads";

const props = defineProps<{
  campaignId: string;
  profileId: string;
  initialDateRange?: string[];
}>();

// ── 筛选状态 ──────────────────────────────────────────
const filters = reactive({
  range: props.initialDateRange ?? (null as string[] | null),
  state: "",
  expType: "",
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
  { prop: "exp_type_label", label: "否定类型", minWidth: 110 },
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
 * 打开分析抽屉，展示选中否定商品的详情与指标。
 *
 * @param {any} row - 点击的行数据
 */
function openDrawer(row: any): void {
  activeRow.value = row;
  drawerVisible.value = true;
}

// ── 查询 ────────────────────────────────────────────
// ── 查询 ──────────────────────────────────────────────
/**
 * 加载否定商品列表，调用后端 /ads/auto-negative-targeting 接口。
 */
function fetchData(): void {
  if (!props.campaignId || !props.profileId) return;
  loading.value = true;

  const params: AutoNegativeTargetingParams = {
    campaign_id: props.campaignId,
    profile_id: props.profileId,
    date_start: filters.range?.[0] || undefined,
    date_end: filters.range?.[1] || undefined,
    state: filters.state || undefined,
    exp_type: filters.expType || undefined,
    keyword: filters.keyword || undefined,
    pageNum: pagination.pageNum,
    pageSize: pagination.pageSize,
  };

  getAutoNegativeTargeting(params)
    .then((res) => {
      rows.value = res.list ?? [];
      pagination.total = res.total ?? 0;
      currencyIcon.value = res.currency_icon ?? "$";
    })
    .catch(() => {
      ElMessage.error("加载否定商品失败");
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
  filters.expType = "";
  filters.keyword = "";
  pagination.pageNum = 1;
  fetchData();
}

onMounted(fetchData);
</script>

<style scoped lang="scss">
.auto-negative-targeting-panel {
  .filter-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 0;
    flex-wrap: wrap;
  }

  .filter-item {
    &.w-110 { width: 110px; }
    &.w-130 { width: 130px; }
  }

  // ASIN 商品卡片单元格
  .asin-cell {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 4px 0;
  }

  .asin-header {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .asin-code {
    font-size: 13px;
    font-weight: 600;
    color: #303133;
  }

  .exp-type-badge {
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;

    &.exp-asin {
      background: #ecf5ff;
      color: #409eff;
      border: 1px solid #b3d8ff;
    }

    &.exp-brand {
      background: #f0f9eb;
      color: #67c23a;
      border: 1px solid #c2e7b0;
    }
  }

  .asin-title {
    font-size: 12px;
    color: #606266;
    max-width: 240px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.4;
  }

  .asin-meta {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .meta-item {
    font-size: 12px;
    color: #909399;
    white-space: nowrap;

    &.meta-price { color: #f56c6c; font-weight: 500; }
    &.meta-reviews { color: #909399; }
  }

  .status-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
  }

  .summary-label {
    color: #606266;
    font-weight: 600;
    font-size: 13px;
  }

  .msku-cell {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .msku-text { font-size: 13px; color: #303133; }

  .dot-circle {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #67c23a;
    flex-shrink: 0;
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
      border-right: 1px solid #ebeef5;
      padding-right: 16px;
    }

    .drawer-right {
      flex: 1;
    }

    .drawer-section-title {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
      margin-bottom: 12px;
    }

    .product-info-card {
      background: #f5f7fa;
      border-radius: 6px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;

      .product-asin-row {
        display: flex;
        align-items: center;
        gap: 8px;

        .product-asin {
          font-size: 15px;
          font-weight: 700;
          color: #303133;
          letter-spacing: 0.5px;
        }
      }

      .product-title {
        font-size: 13px;
        color: #606266;
        line-height: 1.5;
        word-break: break-all;
      }

      .product-meta {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
      }

      .product-detail-row {
        display: flex;
        gap: 8px;
        font-size: 13px;

        .detail-label {
          color: #909399;
          flex-shrink: 0;
          width: 60px;
        }

        .detail-value {
          color: #606266;
        }
      }
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;

      .metric-card {
        background: #f5f7fa;
        border-radius: 6px;
        padding: 14px 16px;

        .metric-label {
          font-size: 12px;
          color: #909399;
          margin-bottom: 6px;
        }

        .metric-value {
          font-size: 18px;
          font-weight: 600;
          color: #303133;
        }
      }
    }
  }
}

:deep(.el-table__fixed-right) {
  box-shadow: -2px 0 6px rgba(0, 0, 0, 0.06);
}
</style>
