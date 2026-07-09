<template>
  <ElDialog
    v-model="visible"
    :title="title"
    width="920px"
    destroy-on-close
    class="adj-history-dialog"
    @opened="onDialogOpened"
  >
    <div class="adj-history-filters">
      <ElRadioGroup v-model="filterType" size="small">
        <ElRadioButton value="">全部</ElRadioButton>
        <ElRadioButton value="BID_ADJUSTMENT">自动规则</ElRadioButton>
        <ElRadioButton value="MANUAL_ADJUSTMENT">手动修改</ElRadioButton>
        <ElRadioButton value="TIME_PRICING_START">分时开始</ElRadioButton>
        <ElRadioButton value="TIME_PRICING_CALLBACK">分时回调</ElRadioButton>
        <ElRadioButton value="BID_PAUSE,BID_ENABLE">暂停/启用</ElRadioButton>
        <ElRadioButton value="budget">预算调整</ElRadioButton>
      </ElRadioGroup>
    </div>

    <div class="adj-history-table">
      <ElTable :data="filteredRecords" size="small" max-height="420" stripe empty-text="暂无数据">
        <ElTableColumn prop="adjustment_time" label="时间" min-width="155">
          <template #default="{ row }">
            {{ formatTime(row.adjustment_time) }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="execution_type" label="类型" width="100">
          <template #default="{ row }">
            <ElTooltip
              :content="typeDetail(row)"
              placement="top"
              :show-after="300"
              popper-class="adj-detail-tooltip"
            >
              <ElTag :type="typeTag(row.execution_type)" size="small" effect="plain">
                {{ typeLabel(row.execution_type) }}
              </ElTag>
            </ElTooltip>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="before" label="调整前" width="80" align="right">
          <template #default="{ row }">
            {{ row.bid_before ?? row.budget_before ?? "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="after" label="调整后" width="80" align="right">
          <template #default="{ row }">
            {{ row.bid_after ?? row.budget_after ?? "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作人/规则" width="140" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.rule_name || row.strategy_name || row.operator || "-" }}
          </template>
        </ElTableColumn>
        <ElTableColumn prop="adjustment_status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <ElTag
              :type="row.adjustment_status === 'SUCCESS' ? 'success' : 'warning'"
              size="small"
              effect="dark"
            >
              {{ row.adjustment_status === "SUCCESS" ? "已执行" : "待执行" }}
            </ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn prop="msg" label="说明" min-width="150" show-overflow-tooltip />
      </ElTable>
    </div>

    <div class="adj-history-footer">
      <span>共 {{ filteredRecords.length }} 条</span>
    </div>
  </ElDialog>
</template>

<script setup lang="ts">
/**
 * 投放实体调整历史记录弹窗。
 * 展示关键词/定位组/商品投放/广告活动的完整竞价和状态变更历史，
 * 支持按类型筛选（自动规则/手动修改/分时开始/分时回调/暂停启用/预算调整）。
 * 通过 ref.open(params) 调用，params 需包含 entity_id + profile_id。
 */
import { ref, computed, nextTick } from "vue";
import {
  ElDialog,
  ElTable,
  ElTableColumn,
  ElTag,
  ElRadioGroup,
  ElRadioButton,
  ElTooltip,
} from "element-plus";
import { getAdjustmentHistory, type AdjustmentHistoryItem } from "@/api/ads";
import { formatTimeInZone } from "@/utils/timezones";

/** 执行类型中文标签映射，与后端 ExecutionTypeChoices 保持一致 */
const TYPE_LABELS: Record<string, string> = {
  BID_ADJUSTMENT: "自动规则",
  MANUAL_ADJUSTMENT: "手动修改",
  TIME_PRICING_START: "分时开始",
  TIME_PRICING_CALLBACK: "分时回调",
  BID_PAUSE: "暂停",
  BID_ENABLE: "启用",
  RULE_BUDGET_ADJUSTMENT: "预算(规则)",
  MANUAL_BUDGET_ADJUSTMENT: "预算(手动)",
  CAMPAIGN_PAUSE: "活动暂停",
  CAMPAIGN_ENABLE: "活动启用",
};

/** 执行类型 Element Plus Tag 颜色映射 */
const TYPE_TAGS: Record<string, string> = {
  BID_ADJUSTMENT: "",
  MANUAL_ADJUSTMENT: "success",
  TIME_PRICING_START: "warning",
  TIME_PRICING_CALLBACK: "info",
  BID_PAUSE: "danger",
  BID_ENABLE: "success",
  RULE_BUDGET_ADJUSTMENT: "",
  MANUAL_BUDGET_ADJUSTMENT: "success",
  CAMPAIGN_PAUSE: "danger",
  CAMPAIGN_ENABLE: "success",
};

/** 弹窗可见性 */
const visible = ref(false);
/** 弹窗标题 */
const title = ref("");
/** 当前选中的类型筛选值，空字符串=全部 */
const filterType = ref("");
/** 店铺站点时区（IANA 名），用于时间显示 */
const storeTimezone = ref("");
/** 全量调整记录 */
const allRecords = ref<AdjustmentHistoryItem[]>([]);

/**
 * 根据当前 filterType 筛选记录。
 * 空值=全部，可支持逗号分隔的多类型筛选。
 */
const filteredRecords = computed(() => {
  if (!filterType.value) return allRecords.value;
  const types = filterType.value.split(",");
  return allRecords.value.filter((r) => types.includes(r.execution_type));
});

/** 执行类型 → 中文标签（大小写不敏感） */
function typeLabel(type: string): string {
  return TYPE_LABELS[type] || TYPE_LABELS[type.toUpperCase()] || type;
}

/** 执行类型 → Element Plus Tag 颜色（大小写不敏感） */
function typeTag(type: string): "success" | "warning" | "info" | "danger" {
  return ((TYPE_TAGS[type] || TYPE_TAGS[type.toUpperCase()]) as any) || "info";
}

/**
 * 悬停时显示的完整调整详情，与竞价 * 星标格式一致。
 *
 * 自动规则：规则组「超 90 天自动广告」—「自动广告特殊规则一」规则
 *           时间  竞价 0.12 → 0.14
 *           竞价调整成功 0.12 → 0.14
 * 分时调价：分时策略「通用竞价分时」
 * 手动修改：由 陈慧瑩 完成
 */
function typeDetail(row: AdjustmentHistoryItem): string {
  const lines: string[] = [];

  if (row.rule_name) {
    const prefix = row.group_name ? `规则组「${row.group_name}」—` : "";
    lines.push(`${prefix}「${row.rule_name}」规则`);
  } else if (row.strategy_name) {
    lines.push(`分时策略「${row.strategy_name}」`);
  } else if (row.operator) {
    lines.push(`由 ${row.operator} 完成`);
  } else {
    lines.push(typeLabel(row.execution_type));
  }

  const timeInfo: string[] = [];
  if (row.adjustment_time) {
    timeInfo.push(formatTime(row.adjustment_time));
  }
  if (row.bid_before !== undefined && row.bid_before !== null) {
    timeInfo.push(`竞价 ${row.bid_before} → ${row.bid_after}`);
  } else if (row.budget_before !== undefined && row.budget_before !== null) {
    timeInfo.push(`预算 ${row.budget_before} → ${row.budget_after}`);
  }
  if (timeInfo.length) {
    lines.push(timeInfo.join("  "));
  }

  if (row.msg) {
    lines.push(row.msg);
  }

  return lines.join("\n") || typeLabel(row.execution_type);
}

/**
 * 将 UTC ISO 时间按店铺时区格式化为本地时间字符串。
 * 时区信息由后端 getAdjustmentHistory 响应的 timezone 字段提供。
 */
function formatTime(time: string): string {
  return formatTimeInZone(time, storeTimezone.value || undefined);
}

/**
 * 弹窗打开完成回调：强制 filterType 刷新一次，
 * 解决页面刷新后 el-radio-button 未正确渲染的时序问题。
 */
let refreshTimer: ReturnType<typeof setTimeout> | null = null;
function onDialogOpened(): void {
  if (refreshTimer) clearTimeout(refreshTimer);
  refreshTimer = setTimeout(() => {
    filterType.value = "";
    nextTick(() => {
      filterType.value = "";
    });
  }, 50);
}

/**
 * 打开弹窗并加载调整历史数据。
 * 由父组件通过 defineExpose 的 ref 调用。
 *
 * @param params - { keyword_id | target_id | campaign_id, profile_id }
 */
async function open(params: Record<string, number | string>): Promise<void> {
  visible.value = true;
  title.value = "调整历史";
  filterType.value = "";
  storeTimezone.value = "";
  try {
    const res = await getAdjustmentHistory(params);
    allRecords.value = res.records || [];
    storeTimezone.value = (res as any).timezone || "";
  } finally {
    // loading handled by parent if needed
  }
}

defineExpose({ open });
</script>

<style scoped>
.adj-history-dialog :deep(.el-dialog__body) {
  padding: 12px 20px;
}
.adj-history-filters {
  margin-bottom: var(--spacing-2, 10px);
}
.adj-history-table {
  min-height: 360px;
}
.adj-history-footer {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary, #909399);
  text-align: right;
}
</style>

<style>
.adj-detail-tooltip {
  max-width: 420px;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-line;
}

/* 覆盖各父组件泄漏到弹窗的 el-table 表头样式 */
.adj-history-dialog .el-table__header-wrapper th.el-table__cell {
  height: 32px !important;
  padding: 2px 0 !important;
  font-size: 12px;
  line-height: 28px;
  background: var(--el-table-header-bg-color, #f5f7fa);
}
.adj-history-dialog .el-table td.el-table__cell {
  padding: 6px 0;
}
.adj-history-dialog .el-table .cell {
  padding: 0 8px;
}
</style>
