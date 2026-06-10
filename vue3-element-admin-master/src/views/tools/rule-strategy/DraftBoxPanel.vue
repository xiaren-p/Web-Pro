<template>
  <div class="draft-panel">
    <!-- 工具栏 -->
    <div class="draft-toolbar">
      <div class="toolbar-left">
        <!-- 状态筛选 -->
        <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px">
          <el-option label="全部" value="" />
          <el-option label="启用" value="active" />
          <el-option label="暂停" value="inactive" />
        </el-select>

        <!-- 比对对象筛选 -->
        <el-select v-model="filterTarget" placeholder="比对对象" clearable style="width: 160px">
          <el-option label="全部" value="" />
          <el-option
            v-for="item in targetOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>

        <!-- 搜索框 -->
        <el-input
          v-model="searchKeyword"
          placeholder="搜索规则名称..."
          :prefix-icon="Search"
          style="width: 280px"
          clearable
        />
      </div>
      <span class="toolbar-spacer" />
      <div class="toolbar-right">
        <span class="stat-text">共 {{ filteredRules.length }} 条规则</span>
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          新建规则
        </el-button>
      </div>
    </div>

    <!-- 规则表格 -->
    <div class="draft-table-wrapper">
      <el-table
        v-loading="loading"
        :data="filteredRules"
        style="width: 100%"
        row-key="id"
        class="draft-table"
        :header-cell-style="{
          background:
            'linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%)',
          color: 'var(--el-text-color-primary)',
          fontWeight: 700,
          borderBottom: '1px solid var(--el-border-color-lighter)',
        }"
        stripe
      >
        <el-table-column type="index" label="序号" width="70" align="center" />
        <el-table-column prop="name" label="规则名称" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="name-cell">
              <el-icon color="var(--el-color-primary)"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'active' ? 'success' : 'info'"
              size="small"
              effect="light"
            >
              {{ row.status === "active" ? "启用" : "暂停" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="comparisonTarget" label="比对对象" width="140" align="center">
          <template #default="{ row }">
            <el-tag size="small" type="primary" effect="light">
              {{ COMPARISON_LABEL[row.comparisonTarget] || row.comparisonTarget }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用店铺" min-width="140">
          <template #default="{ row }">
            <span>{{ formatShops(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="触发条件" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="condition-preview">{{ getRuleSummary(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="执行操作" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="action-preview">{{ formatActions(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="170">
          <template #default="{ row }">
            <span class="time-text">{{ formatDate(row.updatedAt) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredRules.length === 0 && !loading" class="draft-empty">
      <el-empty
        :image-size="100"
        :description="
          props.rules.length === 0 ? '暂无草稿规则，点击「新建规则」创建第一条' : '未找到匹配的规则'
        "
      >
        <template v-if="props.rules.length === 0">
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建规则
          </el-button>
        </template>
      </el-empty>
    </div>

    <!-- 规则表单弹窗 -->
    <RuleFormDialog ref="formRef" @saved="onFormSaved" />
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告规则草稿箱面板：规则列表表格展示，带分类筛选
 */
import type { AdRule } from "./types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, Search, Document } from "@element-plus/icons-vue";

import RuleFormDialog from "./RuleFormDialog.vue";
import { createRule, updateRule, deleteRule } from "@/api/ads/rule-strategy";

defineOptions({ name: "DraftBoxPanel" });

const props = defineProps<{
  rules: AdRule[];
}>();

const emit = defineEmits<{
  (e: "update:rules", rules: AdRule[]): void;
}>();

const formRef = ref<any>(null);
const loading = ref(false);
const searchKeyword = ref("");
const filterStatus = ref<string>("");
const filterTarget = ref<string>("");

const targetOptions = [
  { value: "campaign", label: "广告活动" },
  { value: "ad_group", label: "广告组" },
  { value: "targeting", label: "定位组投放" },
  { value: "keyword", label: "关键词投放" },
  { value: "product_targeting", label: "商品投放" },
  { value: "search_terms", label: "用户搜索词" },
];

const COMPARISON_LABEL: Record<string, string> = {
  campaign: "广告活动",
  ad_group: "广告组",
  targeting: "定位组投放",
  keyword: "关键词投放",
  product_targeting: "商品投放",
  search_terms: "用户搜索词",
};

const ACTION_LABEL: Record<string, string> = {
  bid_percent_decrease: "竞价降低",
  bid_percent_increase: "竞价提高",
  bid_fixed_decrease: "竞价减少",
  bid_fixed_increase: "竞价增加",
  budget_increase: "预算增加",
  budget_decrease: "预算减少",
  no_adjust: "不调整",
  pause: "暂停",
  archive: "归档",
  negative_exact: "精准否定",
  negative_phrase: "否定词组",
  add_keyword: "添加关键词",
};

const NO_VALUE_ACTIONS = new Set([
  "no_adjust",
  "pause",
  "archive",
  "negative_exact",
  "negative_phrase",
  "add_keyword",
]);

const filteredRules = computed(() => {
  return props.rules.filter((rule) => {
    const matchesSearch = !searchKeyword.value
      ? true
      : rule.name.toLowerCase().includes(searchKeyword.value.toLowerCase());
    const matchesStatus = !filterStatus.value ? true : rule.status === filterStatus.value;
    const matchesTarget = !filterTarget.value ? true : rule.comparisonTarget === filterTarget.value;
    return matchesSearch && matchesStatus && matchesTarget;
  });
});

function formatShops(rule: AdRule): string {
  if (!rule.shops || rule.shops.length === 0) return "-";
  if (rule.shops.length === 1) return String(rule.shops[0]);
  return `${rule.shops.length} 个店铺`;
}

function formatActions(rule: AdRule): string {
  const parts: string[] = [];
  const ba = rule.bidAction;
  if (ba?.type) {
    const label = ACTION_LABEL[ba.type] || ba.type;
    if (NO_VALUE_ACTIONS.has(ba.type)) {
      parts.push(label);
    } else {
      const suffix = ba.type.includes("decrease") ? "↓" : "↑";
      const val = ba.type.includes("percent") ? `${ba.value}%` : `€${ba.value}`;
      parts.push(`${label} ${val} ${suffix}`);
    }
  }
  const bg = rule.budgetAction;
  if (bg?.type && bg.type !== "no_adjust") {
    const label = ACTION_LABEL[bg.type] || bg.type;
    const suffix = bg.type.includes("increase") ? "↑" : "↓";
    parts.push(`${label} €${bg.value}/天 ${suffix}`);
  }
  if (rule.negativeAction) parts.push(ACTION_LABEL[rule.negativeAction] || rule.negativeAction);
  if (rule.addKeywordAction)
    parts.push(ACTION_LABEL[rule.addKeywordAction] || rule.addKeywordAction);
  return parts.length > 0 ? parts.join(" · ") : "-";
}

function getRuleSummary(rule: AdRule): string {
  return rule.conditionSets
    .map(
      (cs) =>
        `≤${cs.days}天, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(" / ")}`
    )
    .join(" | ");
}

function formatDate(dateString: string): string {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function handleCreate(): void {
  formRef.value?.open(null);
}

function handleEdit(row: AdRule): void {
  formRef.value?.open(row);
}

async function handleDelete(row: AdRule): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除规则「${row.name}」吗？`, "删除确认", {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    loading.value = true;
    await deleteRule(row.id);
    const updated = props.rules.filter((r) => r.id !== row.id);
    emit("update:rules", updated);
    ElMessage.success("已删除");
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    loading.value = false;
  }
}

async function onFormSaved(data: AdRule): Promise<void> {
  try {
    const isEdit = data.id && props.rules.some((r) => r.id === data.id);
    if (isEdit) {
      const updated = await updateRule(data.id, data as any);
      const rules = [...props.rules];
      const idx = rules.findIndex((r) => r.id === data.id);
      if (idx !== -1) rules[idx] = updated;
      emit("update:rules", rules);
      ElMessage.success("规则已更新");
    } else {
      const created = await createRule(data as any);
      emit("update:rules", [...props.rules, created]);
      ElMessage.success("规则已创建");
    }
  } catch {
    ElMessage.error("保存失败，请重试");
  }
}
</script>

<style scoped lang="scss">
.draft-panel {
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.draft-toolbar {
  display: flex;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  margin-bottom: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.toolbar-spacer {
  flex: 1;
}

.toolbar-right {
  display: flex;
  gap: 14px;
  align-items: center;
}

.stat-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.draft-table-wrapper {
  flex: 1;
  padding: 0 2px 20px;
  overflow: auto;
}

.draft-table {
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;

  :deep(.el-table__row:hover) {
    background: var(--el-color-primary-light-9);
  }

  :deep(.el-table__row--striped) {
    background: var(--el-fill-color-lighter);

    &:hover {
      background: var(--el-color-primary-light-9);
    }
  }
}

.name-cell {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 500;
}

.condition-preview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.action-preview {
  font-size: 12px;
  color: var(--el-color-warning);
}

.time-text {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.draft-empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}
</style>
