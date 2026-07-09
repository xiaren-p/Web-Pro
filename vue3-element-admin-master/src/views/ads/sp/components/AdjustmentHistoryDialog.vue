<template>
  <el-dialog
    v-model="visible"
    :title="title"
    width="900px"
    destroy-on-close
    class="adj-history-dialog"
  >
    <div class="adj-history-filters">
      <el-radio-group v-model="filterType" size="small" @change="handleFilter">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="BID_ADJUSTMENT">自动规则</el-radio-button>
        <el-radio-button value="MANUAL_ADJUSTMENT">手动修改</el-radio-button>
        <el-radio-button value="TIME_PRICING_START">分时开始</el-radio-button>
        <el-radio-button value="TIME_PRICING_CALLBACK">分时回调</el-radio-button>
        <el-radio-button value="BID_PAUSE,BID_ENABLE">暂停/启用</el-radio-button>
        <el-radio-button value="budget">预算调整</el-radio-button>
      </el-radio-group>
    </div>

    <el-table :data="filteredRecords" size="small" max-height="420" stripe>
      <el-table-column prop="adjustment_time" label="时间" min-width="155">
        <template #default="{ row }">
          {{ formatTime(row.adjustment_time) }}
        </template>
      </el-table-column>
      <el-table-column prop="execution_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tooltip :content="typeDetail(row)" placement="top" :show-after="300">
            <el-tag :type="typeTag(row.execution_type)" size="small" effect="plain">
              {{ typeLabel(row.execution_type) }}
            </el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="before" label="调整前" width="80" align="right">
        <template #default="{ row }">
          {{ row.bid_before ?? row.budget_before ?? "-" }}
        </template>
      </el-table-column>
      <el-table-column prop="after" label="调整后" width="80" align="right">
        <template #default="{ row }">
          {{ row.bid_after ?? row.budget_after ?? "-" }}
        </template>
      </el-table-column>
      <el-table-column label="操作人/规则" width="140" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.rule_name || row.strategy_name || row.operator || "-" }}
        </template>
        </template>
      </el-table-column>
      <el-table-column prop="adjustment_status" label="状态" width="70" align="center">
        <template #default="{ row }">
          <el-tag
            :type="row.adjustment_status === 'SUCCESS' ? 'success' : 'warning'"
            size="small"
            effect="dark"
          >
            {{ row.adjustment_status === "SUCCESS" ? "已执行" : "待执行" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="msg" label="说明" min-width="150" show-overflow-tooltip />
    </el-table

    <div class="adj-history-footer">
      <span>共 {{ filteredRecords.length }} 条</span>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
/** 投放实体调整历史记录弹窗。
 *  展示关键词/定位组/商品投放/广告活动的完整竞价和状态变更历史，
 *  支持按类型筛选（自动规则/手动修改/分时开始/分时回调/暂停启用/预算调整）。
 *  通过 ref.open(params) 调用，params 需包含 entity_id + profile_id。
 */
import { ref, computed } from "vue";
import { ElDialog, ElTable, ElTableColumn, ElTag, ElRadioGroup, ElRadioButton, ElTooltip } from "element-plus";
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
/** 加载状态 */
const loading = ref(false);

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
  return (TYPE_TAGS[type] || TYPE_TAGS[type.toUpperCase()]) as any || "info";
}

/**
 * 悬停时显示的完整调整详情。
 * 自动规则：显示规则名 + 竞价变化 + msg
 * 分时调价：显示策略名 + 竞价变化 + msg
 * 手动修改：显示操作人 + 竞价变化 + msg
 */
function typeDetail(row: AdjustmentHistoryItem): string {
  const parts: string[] = []

  if (row.rule_name) {
    parts.push(`「${row.rule_name}」规则修改`)
  } else if (row.strategy_name) {
    parts.push(`分时策略「${row.strategy_name}」`)
  } else if (row.operator) {
    parts.push(`由 ${row.operator} 完成`)
  }

  if (row.bid_before !== undefined && row.bid_before !== null) {
    parts.push(`竞价 ${row.bid_before} → ${row.bid_after}`)
  } else if (row.budget_before !== undefined && row.budget_before !== null) {
    parts.push(`预算 ${row.budget_before} → ${row.budget_after}`)
  }

  if (row.msg) {
    parts.push(row.msg)
  }

  return parts.join(" | ") || typeLabel(row.execution_type)
}

/**
 * 将 UTC ISO 时间按店铺时区格式化为本地时间字符串。
 * 时区信息由后端 getAdjustmentHistory 响应的 timezone 字段提供。
 */
function formatTime(time: string): string {
  return formatTimeInZone(time, storeTimezone.value || undefined);
}

/** 筛选类型切换回调（computed 已自动处理，函数仅用于绑定） */
function handleFilter(): void {
  // noop — filteredRecords computed 已响应 filterType 变化
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
  loading.value = true;
  try {
    const res = await getAdjustmentHistory(params);
    allRecords.value = res.records || [];
    storeTimezone.value = (res as any).timezone || "";
  } finally {
    loading.value = false;
  }
}

defineExpose({ open });</script>

<style scoped>
.adj-history-dialog :deep(.el-dialog__body) {
  padding: 12px 20px;
}
.adj-history-filters {
  margin-bottom: var(--spacing-2, 10px);
}
.adj-history-footer {
  margin-top: 8px;
  text-align: right;
  font-size: 12px;
  color: var(--text-secondary, #909399);
}
</style>
