<template>
  <el-drawer
    v-model="visible"
    title="自动规则"
    size="960px"
    direction="rtl"
    destroy-on-close
    @closed="handleClose"
  >
    <div class="auto-rule-body">
      <!-- 左侧：规则组列表 -->
      <div class="group-panel">
        <div class="group-panel__header">
          <span class="group-panel__title">规则组</span>
          <el-button text type="primary" size="small" @click="openCreateGroup">
            <el-icon><FolderAdd /></el-icon>
            新建
          </el-button>
        </div>

        <div class="group-list">
          <div v-if="ruleGroups.length === 0" class="empty-hint">暂无规则组，点击「新建」创建</div>
          <div
            v-for="group in ruleGroups"
            :key="group.id"
            class="group-item"
            :class="{ 'is-selected': selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <div class="group-item__info">
              <span class="group-item__name">{{ group.name }}</span>
              <div class="group-item__meta">
                <span class="group-item__count">{{ group.rules.length }} 条规则</span>
                <span class="group-item__divider">·</span>
                <span class="group-item__cycle">每 {{ group.executionCycle ?? 1 }} 天执行</span>
              </div>
            </div>
            <div class="group-item__actions">
              <el-button text size="small" @click.stop="openEditGroup(group)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button text size="small" type="danger" @click.stop="deleteGroup(group)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：选中规则组 → 规则列表 + 草稿池 -->
      <div class="rule-panel">
        <div class="rule-panel__section">
          <div class="section-header">
            <span class="section-title">
              {{ selectedGroup ? `「${selectedGroup.name}」的规则` : "请先选择规则组" }}
            </span>
            <span v-if="selectedGroup" class="section-sub">
              每 {{ selectedGroup.executionCycle ?? 1 }} 天执行一次，组内规则按序匹配，命中即停
            </span>
          </div>
          <div v-if="selectedGroup && selectedGroup.rules.length === 0" class="empty-hint">
            暂无规则，从下方草稿池点击添加
          </div>
          <div
            v-for="(rule, idx) in selectedGroup?.rules ?? []"
            :key="rule.id"
            class="group-rule-card"
          >
            <div class="group-rule__order">{{ idx + 1 }}</div>
            <div class="group-rule__info">
              <div class="group-rule__header">
                <span class="group-rule__name">{{ rule.name }}</span>
                <el-tag :type="getRuleStatusType(rule.status)" size="small" effect="plain">
                  {{ getRuleStatusText(rule.status) }}
                </el-tag>
              </div>
              <span class="group-rule__summary">{{ getRuleSummary(rule) }}</span>
            </div>
            <el-button text type="danger" size="small" @click="removeRuleFromGroup(rule)">
              <el-icon><Delete /></el-icon>
              移出
            </el-button>
          </div>
        </div>

        <!-- 草稿池 -->
        <div class="rule-panel__section">
          <div class="section-header">
            <span class="section-title">草稿池</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索规则"
              style="width: 200px"
              size="small"
              clearable
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>
          <div v-if="filteredDraftRules.length === 0" class="empty-hint">草稿箱为空</div>
          <div
            v-for="rule in filteredDraftRules"
            :key="rule.id"
            class="draft-rule-row"
            :class="{ 'is-added': isRuleInCurrentGroup(rule.id) }"
          >
            <div class="draft-rule__info">
              <span class="draft-rule__name">{{ rule.name }}</span>
              <span class="draft-rule__target">
                {{ CMP_LABEL[rule.comparisonTarget] || rule.comparisonTarget }}
              </span>
              <span class="draft-rule__summary">{{ getRuleSummary(rule) }}</span>
            </div>
            <el-button
              v-if="selectedGroup && !isRuleInCurrentGroup(rule.id)"
              type="primary"
              size="small"
              plain
              @click="addRuleToGroup(rule)"
            >
              <el-icon><Plus /></el-icon>
              添加
            </el-button>
            <el-tag
              v-else-if="isRuleInCurrentGroup(rule.id)"
              type="success"
              size="small"
              effect="plain"
            >
              已添加
            </el-tag>
          </div>
        </div>
      </div>
    </div>

    <!-- 规则组表单弹窗 -->
    <el-dialog
      v-model="groupDialogVisible"
      :title="editingGroup ? '编辑规则组' : '新建规则组'"
      width="460px"
      destroy-on-close
    >
      <el-form :model="groupForm" label-width="100px" @submit.prevent="confirmGroup">
        <el-form-item label="规则组名称" required>
          <el-input
            v-model="groupForm.name"
            placeholder="请输入规则组名称"
            maxlength="50"
            @keyup.enter="confirmGroup"
          />
        </el-form-item>
        <el-form-item label="执行周期">
          <div class="cycle-row">
            <span class="cycle-prefix">每</span>
            <el-input-number
              v-model="groupForm.executionCycle"
              :min="1"
              :max="365"
              :step="1"
              controls-position="right"
              style="width: 140px"
            />
            <span class="cycle-suffix">天执行一次</span>
          </div>
          <div class="cycle-hint">
            <el-icon size="14"><InfoFilled /></el-icon>
            例如设为 3，则该组规则每 3 天自动运行一次。设为 1 表示每天执行。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmGroup">确定</el-button>
      </template>
    </el-dialog>
  </el-drawer>
</template>

<script setup lang="ts">
/**
 * SP 广告自动规则抽屉：规则组管理 + 草稿规则拖入/移出。
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule, AdRuleGroup } from "@/views/tools/rule-strategy/types";
import { COMPARISON_LABEL } from "@/views/tools/rule-strategy/types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, FolderAdd, Search, InfoFilled } from "@element-plus/icons-vue";

defineOptions({ name: "AutoRuleDrawer" });

// ─── Props / Emits ───────────────────────────────────────────────────────────
const props = defineProps<{
  rules: AdRule[];
  ruleGroups: AdRuleGroup[];
}>();

const emit = defineEmits<{
  (e: "update:ruleGroups", groups: AdRuleGroup[]): void;
}>();

const visible = ref(false);
const groupDialogVisible = ref(false);
const editingGroup = ref<AdRuleGroup | null>(null);
const groupForm = ref({ name: "", executionCycle: 1 });
const selectedGroupId = ref<string>("");
const searchKeyword = ref("");

const selectedGroup = computed(
  () => props.ruleGroups.find((g) => g.id === selectedGroupId.value) ?? null
);

const filteredDraftRules = computed(() =>
  !searchKeyword.value
    ? props.rules
    : props.rules.filter((r) => r.name.toLowerCase().includes(searchKeyword.value.toLowerCase()))
);

/** 比对对象标签（同时支持 snake_case 和 camelCase 查找） */
const CMP_LABEL = { ...COMPARISON_LABEL } as Record<string, string>;
CMP_LABEL.adGroup = COMPARISON_LABEL.ad_group;
CMP_LABEL.productTargeting = COMPARISON_LABEL.product_targeting;
CMP_LABEL.searchTerms = COMPARISON_LABEL.search_terms;
CMP_LABEL.negativeTargeting = COMPARISON_LABEL.negative_targeting;

function getRuleStatusType(status: string): "success" | "info" {
  return status === "active" ? "success" : "info";
}

function getRuleStatusText(status: string): string {
  return status === "active" ? "启用" : "暂停";
}

function getRuleSummary(rule: AdRule): string {
  return rule.conditionSets
    .map(
      (cs) =>
        `≤${cs.days}d, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(",")}`
    )
    .join(" | ");
}

function open(): void {
  visible.value = true;
  selectedGroupId.value = props.ruleGroups[0]?.id ?? "";
}

function handleClose(): void {
  visible.value = false;
}

function openCreateGroup(): void {
  editingGroup.value = null;
  groupForm.value = { name: "", executionCycle: 1 };
  groupDialogVisible.value = true;
}

function openEditGroup(group: AdRuleGroup): void {
  editingGroup.value = group;
  groupForm.value = { name: group.name, executionCycle: group.executionCycle ?? 1 };
  groupDialogVisible.value = true;
}

function confirmGroup(): void {
  if (!groupForm.value.name.trim()) {
    ElMessage.warning("请输入规则组名称");
    return;
  }
  const groups = [...props.ruleGroups];
  if (editingGroup.value) {
    const idx = groups.findIndex((g) => g.id === editingGroup.value!.id);
    if (idx !== -1) {
      groups[idx] = {
        ...groups[idx],
        name: groupForm.value.name.trim(),
        executionCycle: groupForm.value.executionCycle,
      };
    }
  } else {
    groups.push({
      id: `group_${Date.now()}`,
      name: groupForm.value.name.trim(),
      rules: [],
      executionCycle: groupForm.value.executionCycle,
      createdAt: new Date().toISOString(),
    });
  }
  emit("update:ruleGroups", groups);
  groupDialogVisible.value = false;
  editingGroup.value = null;
}

async function deleteGroup(group: AdRuleGroup): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定要删除规则组「${group.name}」吗？组内的规则将移回草稿箱。`,
      "删除确认",
      { type: "warning" }
    );
    const groups = props.ruleGroups.filter((g) => g.id !== group.id);
    emit("update:ruleGroups", groups);
    if (selectedGroupId.value === group.id) {
      selectedGroupId.value = groups[0]?.id ?? "";
    }
    ElMessage.success("已删除规则组");
  } catch {
    // 取消
  }
}

function addRuleToGroup(rule: AdRule): void {
  if (!selectedGroup.value) return;
  const groups = [...props.ruleGroups];
  const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
  if (idx !== -1) {
    if (groups[idx].rules.some((r) => r.id === rule.id)) {
      ElMessage.warning("该规则已在当前组中");
      return;
    }
    groups[idx] = {
      ...groups[idx],
      rules: [...groups[idx].rules, rule],
    };
    emit("update:ruleGroups", groups);
    ElMessage.success(`已将「${rule.name}」添加到「${groups[idx].name}」`);
  }
}

function removeRuleFromGroup(rule: AdRule): void {
  if (!selectedGroup.value) return;
  const groups = [...props.ruleGroups];
  const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
  if (idx !== -1) {
    groups[idx] = {
      ...groups[idx],
      rules: groups[idx].rules.filter((r) => r.id !== rule.id),
    };
    emit("update:ruleGroups", groups);
    ElMessage.success(`已将「${rule.name}」移出规则组`);
  }
}

function isRuleInCurrentGroup(ruleId: string): boolean {
  return selectedGroup.value?.rules.some((r) => r.id === ruleId) ?? false;
}

defineExpose({ open });
</script>

<style scoped lang="scss">
.auto-rule-body {
  display: flex;
  gap: 0;
  height: 100%;
}

// ─── 左侧规则组面板 ───────────────────────────────────────────────────────────
.group-panel {
  display: flex;
  flex: 0 0 260px;
  flex-direction: column;
  padding-right: 20px;
  border-right: 1px solid var(--color-gray-200);
}

.group-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--color-gray-100);
}

.group-panel__title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-900);
}

.group-list {
  flex: 1;
  padding-top: 12px;
  overflow-y: auto;
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--bg-card);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);

  &:hover {
    background: var(--color-primary-50);
    border-color: var(--color-primary-200);
    transform: translateX(2px);
  }
}

.group-item__name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-800);
  white-space: nowrap;
}

.group-item.is-selected {
  background: var(--color-primary-50);
  border-color: var(--color-primary-400);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.12);

  .group-item__name {
    color: var(--color-primary-700);
  }
}

.group-item__info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.group-item__meta {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
}

.group-item__divider {
  color: var(--color-gray-300);
  user-select: none;
}

.group-item__actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
  margin-left: 6px;
  opacity: 0;
  transition: opacity var(--transition-fast);

  .group-item:hover & {
    opacity: 1;
  }

  .group-item.is-selected & {
    opacity: 1;
  }
}

// ─── 右侧规则面板 ───────────────────────────────────────────────────────────
.rule-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding-left: 24px;
  overflow-y: auto;
}

.rule-panel__section {
  margin-bottom: 28px;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--color-gray-100);
}

.section-title {
  font-size: var(--font-size-lg);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-900);
}

.section-sub {
  font-size: var(--font-size-sm);
  color: var(--color-gray-500);
}

.empty-hint {
  padding: 48px 20px;
  font-size: var(--font-size-sm);
  color: var(--color-gray-400);
  text-align: center;
}

// ─── 组内规则卡片 ────────────────────────────────────────────────────────────
.group-rule-card {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 16px 18px;
  margin-bottom: 12px;
  background: var(--bg-card);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);

  &:hover {
    border-color: var(--color-primary-300);
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
  }
}

.group-rule__order {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-bold);
  color: var(--color-primary-600);
  background: var(--color-primary-50);
  border-radius: var(--radius-md);
}

.group-rule__info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
}

.group-rule__header {
  display: flex;
  gap: 10px;
  align-items: center;
}

.group-rule__name {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-800);
}

.group-rule__summary {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: var(--font-size-xs);
  color: var(--color-gray-500);
  white-space: nowrap;
}

// ─── 草稿池规则行 ────────────────────────────────────────────────────────────
.draft-rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 10px;
  background: var(--bg-card);
  border: 1px solid var(--color-gray-200);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);

  &:hover {
    background: var(--color-primary-50);
    border-color: var(--color-primary-200);
    transform: translateX(2px);
  }

  &.is-added {
    background: var(--color-success-50);
    border-color: var(--color-success-200);
    opacity: 0.7;
  }
}

.draft-rule__info {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}

.draft-rule__name {
  flex-shrink: 0;
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--color-gray-700);
}

.draft-rule__target {
  flex-shrink: 0;
  padding: 3px 10px;
  font-size: 11px;
  font-weight: var(--font-weight-medium);
  color: var(--color-primary-700);
  background: var(--color-primary-50);
  border-radius: var(--radius-full);
}

.draft-rule__summary {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: "SF Mono", "Menlo", "Consolas", monospace;
  font-size: 11px;
  color: var(--color-gray-500);
  white-space: nowrap;
}

// ─── 规则组表单弹窗 ──────────────────────────────────────────────────────────
.cycle-row {
  display: flex;
  gap: 10px;
  align-items: center;
}

.cycle-prefix,
.cycle-suffix {
  font-size: var(--font-size-base);
  font-weight: var(--font-weight-medium);
  color: var(--color-gray-600);
  white-space: nowrap;
}

.cycle-hint {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 10px 12px;
  margin-top: 10px;
  font-size: var(--font-size-xs);
  line-height: 1.6;
  color: var(--color-gray-600);
  background: var(--color-gray-50);
  border: 1px solid var(--color-gray-100);
  border-radius: var(--radius-md);
}
</style>
