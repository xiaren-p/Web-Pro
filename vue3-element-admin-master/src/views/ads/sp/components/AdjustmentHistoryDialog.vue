<template>
  <ElDialog
    v-model="visible"
    :title="title"
    width="780px"
    destroy-on-close
    class="adj-history-dialog"
  >
    <div class="adj-history-filters">
      <ElRadioGroup v-model="filterType" size="small" @change="handleFilter">
        <ElRadioButton value="">全部</ElRadioButton>
        <ElRadioButton value="BID_ADJUSTMENT">自动规则</ElRadioButton>
        <ElRadioButton value="MANUAL_ADJUSTMENT">手动修改</ElRadioButton>
        <ElRadioButton value="TIME_PRICING_START">分时开始</ElRadioButton>
        <ElRadioButton value="TIME_PRICING_CALLBACK">分时回调</ElRadioButton>
        <ElRadioButton value="BID_PAUSE,BID_ENABLE">暂停/启用</ElRadioButton>
        <ElRadioButton value="budget">预算调整</ElRadioButton>
      </ElRadioGroup>
    </div>

    <ElTable :data="filteredRecords" size="small" max-height="420" stripe>
      <ElTableColumn prop="adjustment_time" label="时间" min-width="155">
        <template #default="{ row }">
          {{ formatTime(row.adjustment_time) }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="execution_type" label="类型" width="100">
        <template #default="{ row }">
          <ElTooltip :content="typeDetail(row)" placement="top" :show-after="300">
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
      <ElTableColumn prop="operator" label="操作人" width="80">
        <template #default="{ row }">
          {{ row.operator || "-" }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="adjustment_status" label="状态" width="70" align="center">
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

    <div class="adj-history-footer">
      <span>共 {{ filteredRecords.length }} 条</span>
    </div>
  </ElDialog>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElDialog, ElTable, ElTableColumn, ElTag, ElRadioGroup, ElRadioButton, ElTooltip } from "element-plus";
import { getAdjustmentHistory, type AdjustmentHistoryItem } from "@/api/ads";

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

const visible = ref(false);
const title = ref("");
const filterType = ref("");
const allRecords = ref<AdjustmentHistoryItem[]>([]);
const loading = ref(false);

const filteredRecords = computed(() => {
  if (!filterType.value) return allRecords.value;
  const types = filterType.value.split(",");
  return allRecords.value.filter((r) => types.includes(r.execution_type));
});

function typeLabel(type: string): string {
  return TYPE_LABELS[type] || type;
}

function typeTag(type: string): "success" | "warning" | "info" | "danger" {
  return (TYPE_TAGS[type] as any) || "info";
}

function typeDetail(row: AdjustmentHistoryItem): string {
  const parts: string[] = [];
  if (row.auto_rule_id) {
    parts.push(`规则 ID: ${row.auto_rule_id}`);
  }
  if (row.time_pricing_rule_id) {
    parts.push(`分时策略 ID: ${row.time_pricing_rule_id}`);
  }
  if (parts.length === 0 && row.operator) {
    parts.push(`操作人: ${row.operator}`);
  }
  if (row.msg) {
    parts.push(row.msg);
  }
  return parts.join(" | ") || typeLabel(row.execution_type);
}

function formatTime(time: string): string {
  if (!time) return "-";
  const d = new Date(time);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function handleFilter(): void {
  // filterType computed already handles it
}

async function open(params: Record<string, number | string>): Promise<void> {
  visible.value = true;
  title.value = "调整历史";
  filterType.value = "";
  loading.value = true;
  try {
    const res = await getAdjustmentHistory(params);
    allRecords.value = res.records || [];
  } finally {
    loading.value = false;
  }
}

defineExpose({ open });
</script>

<style scoped>
.adj-history-dialog :deep(.el-dialog__body) {
  padding: 12px 20px;
}
.adj-history-filters {
  margin-bottom: 10px;
}
.adj-history-footer {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
  text-align: right;
}
</style>
