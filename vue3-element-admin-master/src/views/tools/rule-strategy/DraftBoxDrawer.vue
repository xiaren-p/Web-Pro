<template>
  <el-drawer
    v-model="visible"
    title="草稿箱"
    size="780px"
    direction="rtl"
    destroy-on-close
    @closed="handleClose"
  >
    <!-- 工具栏 -->
    <div class="draft-toolbar">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索规则名称"
        :prefix-icon="Search"
        style="width: 240px"
        clearable
      />
      <span style="flex: 1" />
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
        :image-size="120"
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
            <div class="draft-condition-label">条件规则</div>
            <div class="draft-condition-text">{{ getRuleSummary(rule) }}</div>
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
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * SP 广告规则草稿箱抽屉：规则的 CRUD 列表。
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule } from "@/views/tools/rule-strategy/types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, Search } from "@element-plus/icons-vue";

import RuleFormDialog from "@/views/tools/rule-strategy/RuleFormDialog.vue";

defineOptions({ name: "DraftBoxDrawer" });

// ── Props / Emits ──
const props = defineProps<{
  rules: AdRule[];
}>();

const emit = defineEmits<{
  (e: "update:rules", rules: AdRule[]): void;
}>();

const visible = ref(false);
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
  // 竞价操作
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
  // 预算操作
  const bg = rule.budgetAction;
  if (bg?.type && bg.type !== "no_adjust") {
    const label = ACTION_LABEL[bg.type] || bg.type;
    const suffix = bg.type.includes("increase") ? "↑" : "↓";
    parts.push(`${label} €${bg.value}/天 ${suffix}`);
  }
  // 搜索词操作
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

function open(): void {
  searchKeyword.value = "";
  visible.value = true;
}

function handleClose(): void {
  visible.value = false;
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
    await ElMessageBox.confirm(`确定要删除规则「${row.name}」吗？此操作不可撤销。`, "删除确认", {
      type: "warning",
    });
    const updated = props.rules.filter((r) => r.id !== row.id);
    emit("update:rules", updated);
    ElMessage.success("已删除");
  } catch {
    // 取消
  }
}

function onFormSaved(data: AdRule): void {
  const rules = [...props.rules];
  if (editingRule.value) {
    const idx = rules.findIndex((r) => r.id === editingRule.value!.id);
    if (idx !== -1) {
      rules[idx] = { ...rules[idx], ...data, updatedAt: new Date().toISOString() };
    }
  } else {
    rules.push({
      ...data,
      id: `draft_${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
  }
  emit("update:rules", rules);
  editingRule.value = null;
}

defineExpose({ open });
</script>

<style scoped lang="scss">
.draft-toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
}

.draft-empty {
  padding: 60px 0;
}

.draft-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.draft-card {
  padding: 18px 20px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  transition:
    box-shadow 0.2s,
    border-color 0.2s;

  &:hover {
    border-color: #c6ddfc;
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.06);
  }
}

.draft-card-header {
  margin-bottom: 12px;
}

.draft-card-title-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.draft-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

// ── 元信息网格 ──
.draft-meta-grid {
  display: flex;
  gap: 24px;
  margin-bottom: 12px;
}

.draft-meta-item {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 13px;
}

.draft-meta-label {
  color: #909399;
}

.draft-meta-value {
  color: #606266;
}

.target-tag {
  padding: 1px 8px !important;
  font-size: 12px !important;
}

// ── 条件规则区块 ──
.draft-condition-box {
  padding: 10px 14px;
  margin-bottom: 10px;
  background: #f8fafd;
  border: 1px solid #e8edf2;
  border-radius: 6px;
}

.draft-condition-label {
  margin-bottom: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.draft-condition-text {
  font-family: "SF Mono", "Menlo", monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #409eff;
  word-break: break-all;
  white-space: pre-line;
}

// ── 执行操作 ──
.draft-action-box {
  display: flex;
  gap: 10px;
  align-items: center;
}

.draft-action-label {
  font-size: 13px;
  color: #909399;
}

.draft-action-value {
  display: inline-block;
  padding: 2px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #e6a23c;
  background: linear-gradient(135deg, #fef5e7 0%, #fdf0dc 100%);
  border: 1px solid #fce4bf;
  border-radius: 5px;
}

.draft-card-footer {
  display: flex;
  gap: 8px;
  padding-top: 12px;
  margin-top: 14px;
  border-top: 1px solid #f2f3f5;
}
</style>
