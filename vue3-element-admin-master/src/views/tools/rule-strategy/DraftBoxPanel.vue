<template>
  <div class="draft-panel">
    <!-- 工具栏 -->
    <div class="draft-toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索规则名称..."
        :prefix-icon="Search"
        style="width: 280px"
        size="default"
        clearable
      />
      <span class="toolbar-spacer" />
      <el-button type="primary" size="default" @click="handleCreate">
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
            <span class="draft-condition-label">触发条件</span>
            <span class="draft-condition-text">{{ getRuleSummary(rule) }}</span>
          </div>

          <div class="draft-action-box">
            <span class="draft-action-label">执行操作</span>
            <span class="draft-action-value">{{ formatActions(rule) }}</span>
          </div>
        </div>

        <div class="draft-card-footer">
          <el-button type="primary" size="small" plain @click="handleEdit(rule)">
            <el-icon><Edit /></el-icon>
            编辑规则
          </el-button>
          <el-button type="danger" size="small" plain @click="handleDelete(rule)">
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

.toolbar-spacer {
  flex: 1;
}

.draft-empty {
  padding: 80px 20px;
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.draft-card {
  padding: 0;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
  transition: all 0.25s ease;

  &:hover {
    border-color: var(--el-color-primary-light-6);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
    transform: translateY(-2px);
  }
}

.draft-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 12px;
  margin-bottom: 0;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.draft-card-title-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.draft-card-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: -0.2px;
}

.draft-card-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 18px 22px;
}

.draft-meta-grid {
  display: flex;
  gap: 24px;
  font-size: 13px;
}

.draft-meta-item {
  display: flex;
  gap: 8px;
  align-items: center;
}

.draft-meta-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.draft-meta-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.target-tag {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
}

.draft-condition-box {
  padding: 14px 18px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-color-primary);
  word-break: break-all;
  white-space: pre-line;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 10px;
}

.draft-condition-label {
  display: block;
  margin-bottom: 4px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.draft-action-box {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 12px 16px;
  font-size: 13px;
  background: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-7);
  border-radius: 10px;
}

.draft-action-label {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-warning);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.draft-action-value {
  font-weight: 500;
  line-height: 1.6;
  color: var(--el-color-warning);
}

.draft-card-footer {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  padding: 14px 22px 18px;
  margin-top: 0;
  background: var(--el-fill-color-lighter);
  border-top: 1px solid var(--el-border-color-lighter);
}
</style>
