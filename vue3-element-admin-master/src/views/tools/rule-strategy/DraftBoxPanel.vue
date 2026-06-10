<template>
  <div class="draft-panel">
    <!-- 工具栏 -->
    <div class="draft-toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索规则名称"
        :prefix-icon="Search"
        style="width: 220px"
        size="default"
        clearable
      />
      <span class="toolbar-spacer" />
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建规则
      </el-button>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredRules.length === 0" class="draft-empty">
      <el-empty
        :description="
          props.rules.length === 0 ? '暂无草稿规则，点击「新建规则」创建第一条' : '未找到匹配的规则'
        "
        :image-size="100"
      />
    </div>

    <!-- 规则列表 -->
    <div v-else class="draft-list">
      <div v-for="rule in filteredRules" :key="rule.id" class="draft-card">
        <div class="draft-card-header">
          <div class="draft-card-title-row">
            <span class="draft-card-title">{{ rule.name }}</span>
            <el-tag
              :type="rule.status === 'active' ? 'success' : 'info'"
              size="small"
              effect="plain"
            >
              {{ rule.status === "active" ? "启用" : "暂停" }}
            </el-tag>
          </div>
        </div>

        <div class="draft-card-body">
          <div class="draft-meta-grid">
            <div class="draft-meta-item">
              <span class="draft-meta-label">适用店铺</span>
              <span class="draft-meta-value">{{ formatShops(rule) }}</span>
            </div>
            <div class="draft-meta-item">
              <span class="draft-meta-label">比对对象</span>
              <el-tag size="small" type="primary" effect="light" class="target-tag">
                {{ COMPARISON_LABEL[rule.comparisonTarget] || rule.comparisonTarget }}
              </el-tag>
            </div>
          </div>

          <div class="draft-condition-box">
            <span class="draft-condition-label">条件规则</span>
            <span class="draft-condition-text">{{ getRuleSummary(rule) }}</span>
          </div>

          <div class="draft-action-box">
            <span class="draft-action-label">执行操作</span>
            <span class="draft-action-value">{{ formatActions(rule) }}</span>
          </div>
        </div>

        <div class="draft-card-footer">
          <el-button text type="primary" size="small" @click="handleEdit(rule)">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button text type="danger" size="small" @click="handleDelete(rule)">
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </div>
      </div>
    </div>

    <!-- 规则表单弹窗 -->
    <RuleFormDialog ref="formRef" @saved="onFormSaved as any" />
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告规则草稿箱面板：规则的 CRUD 列表，直接内嵌展示。
 *
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule } from "@/views/tools/rule-strategy/types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, Search } from "@element-plus/icons-vue";

import RuleFormDialog from "@/views/tools/rule-strategy/RuleFormDialog.vue";
import { createRule, updateRule, deleteRule } from "@/api/ads/rule-strategy";

defineOptions({ name: "DraftBoxPanel" });

// ── Props / Emits ──
const props = defineProps<{
  rules: AdRule[];
}>();

const emit = defineEmits<{
  (e: "update:rules", rules: AdRule[]): void;
}>();

const formRef = ref<any>(null);
const editingRule = ref<AdRule | null>(null);
const searchKeyword = ref("");

const filteredRules = computed(() =>
  !searchKeyword.value
    ? props.rules
    : props.rules.filter((r) => r.name.toLowerCase().includes(searchKeyword.value.toLowerCase()))
);

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

const NO_VALUE_ACTIONS = new Set([
  "no_adjust",
  "pause",
  "archive",
  "negative_exact",
  "negative_phrase",
  "add_keyword",
]);

function getRuleSummary(rule: AdRule): string {
  return rule.conditionSets
    .map(
      (cs) =>
        `≤${cs.days}天, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(" / ")}`
    )
    .join("\n");
}

function handleCreate(): void {
  editingRule.value = null;
  formRef.value?.open(null);
}

function handleEdit(row: AdRule): void {
  editingRule.value = row;
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
    await deleteRule(row.id);
    const updated = props.rules.filter((r) => r.id !== row.id);
    emit("update:rules", updated);
    ElMessage.success("已删除");
  } catch {
    ElMessage.error("删除失败，请重试");
  }
}

async function onFormSaved(data: AdRule): Promise<void> {
  try {
    if (editingRule.value) {
      // 编辑：调 API 更新
      const updated = await updateRule(editingRule.value.id, data as any);
      const rules = [...props.rules];
      const idx = rules.findIndex((r) => r.id === editingRule.value!.id);
      if (idx !== -1) rules[idx] = updated;
      emit("update:rules", rules);
    } else {
      // 创建：调 API 新增
      const created = await createRule(data as any);
      emit("update:rules", [...props.rules, created]);
    }
    editingRule.value = null;
  } catch {
    ElMessage.error("保存失败，请重试");
  }
}
</script>

<style scoped lang="scss">
.draft-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.toolbar-spacer {
  flex: 1;
}

.draft-empty {
  padding: 40px 0;
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.draft-card {
  padding: 16px 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  transition: box-shadow 0.25s;

  &:hover {
    box-shadow: var(--el-box-shadow-light);
  }
}

// ── 卡片头部 ──
.draft-card-header {
  margin-bottom: 10px;
}

.draft-card-title-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.draft-card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.draft-card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

// ── 元信息 ──
.draft-meta-grid {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.draft-meta-item {
  display: flex;
  gap: 6px;
  align-items: center;
}

.draft-meta-label {
  color: var(--el-text-color-secondary);
}

.draft-meta-value {
  color: var(--el-text-color-regular);
}

// ── 条件规则 ──
.draft-condition-box {
  display: flex;
  gap: 6px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: var(--el-border-radius-base);
}

.draft-condition-label {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.draft-condition-text {
  font-size: 13px;
  color: var(--el-color-primary);
  word-break: break-all;
  white-space: pre-line;
}

// ── 执行操作 ──
.draft-action-box {
  display: flex;
  gap: 6px;
  align-items: center;
}

.draft-action-label {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.draft-action-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-warning);
}

// ── 尾部 ──
.draft-card-footer {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  margin-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
