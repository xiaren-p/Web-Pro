<template>
  <div class="auto-rule-panel">
    <div class="auto-rule-body">
      <!-- 左侧：规则组列表 -->
      <div class="group-panel">
        <div class="group-panel-header">
          <span class="group-panel-title">规则组</span>
          <el-button text type="primary" size="small" @click="openCreateGroup">
            <el-icon><FolderAdd /></el-icon>
            新建
          </el-button>
        </div>

        <div class="group-list">
          <div
            v-for="group in ruleGroups"
            :key="group.id"
            class="group-item"
            :class="{ 'is-selected': selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <div class="group-item-info">
              <span class="group-item-name">{{ group.name }}</span>
              <div class="group-item-meta">
                <span>{{ group.rules.length }} 条规则</span>
                <span class="group-item-sep">·</span>
                <span>每 {{ group.executionCycle ?? 1 }} 天</span>
              </div>
            </div>
            <div class="group-item-actions">
              <el-button text size="small" @click.stop="openEditGroup(group)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button text size="small" type="danger" @click.stop="deleteGroup(group)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="ruleGroups.length === 0" class="empty-hint">暂无规则组，点击「新建」创建</div>
        </div>
      </div>

      <!-- 右侧：规则列表 + 草稿池 -->
      <div class="rule-panel">
        <!-- 选中的规则组详情 -->
        <div class="rule-panel-section">
          <div class="section-header">
            <span class="section-title">
              {{ selectedGroup ? `「${selectedGroup.name}」` : "请选择规则组" }}
            </span>
            <span v-if="selectedGroup" class="section-hint">
              每 {{ selectedGroup.executionCycle ?? 1 }} 天执行一次，按序匹配，命中即停
            </span>
          </div>

          <!-- 组内规则 -->
          <template v-if="selectedGroup">
            <div v-if="selectedGroup.rules.length === 0" class="empty-hint">
              暂无规则，从下方草稿池添加
            </div>
            <div v-for="(rule, idx) in selectedGroup.rules" :key="rule.id" class="group-rule-card">
              <span class="group-rule-order">{{ idx + 1 }}</span>
              <div class="group-rule-info">
                <div class="group-rule-top">
                  <span class="group-rule-name">{{ rule.name }}</span>
                  <el-tag
                    :type="rule.status === 'active' ? 'success' : 'info'"
                    size="small"
                    effect="plain"
                  >
                    {{ rule.status === "active" ? "启用" : "暂停" }}
                  </el-tag>
                </div>
                <span class="group-rule-summary">{{ getRuleSummary(rule) }}</span>
              </div>
              <el-button text type="danger" size="small" @click="removeRuleFromGroup(rule)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </template>
        </div>

        <!-- 草稿池 -->
        <div class="rule-panel-section">
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
          <div v-if="filteredDraftRules.length === 0" class="empty-hint">
            草稿箱为空，请先在「草稿箱」中创建规则
          </div>
          <div
            v-for="rule in filteredDraftRules"
            :key="rule.id"
            class="draft-rule-row"
            :class="{ 'is-added': isRuleInCurrentGroup(rule.id) }"
          >
            <div class="draft-rule-info">
              <span class="draft-rule-name">{{ rule.name }}</span>
              <span class="draft-rule-target">
                {{ COMPARISON_LABEL[rule.comparisonTarget] || rule.comparisonTarget }}
              </span>
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
            <span>每</span>
            <el-input-number
              v-model="groupForm.executionCycle"
              :min="1"
              :max="365"
              :step="1"
              controls-position="right"
              style="width: 140px"
            />
            <span>天执行一次</span>
          </div>
          <div class="cycle-hint">
            <el-icon size="14"><InfoFilled /></el-icon>
            设为 3 表示每 3 天执行一次，设为 1 表示每天执行
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmGroup">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告自动规则面板：左侧规则组 + 右侧规则详情及草稿池。
 *
 * 所属板块：tools / 广告规则策略。
 */
import type { AdRule, AdRuleGroup } from "@/views/tools/rule-strategy/types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, FolderAdd, Search, InfoFilled } from "@element-plus/icons-vue";

defineOptions({ name: "AutoRulePanel" });

const props = defineProps<{
  rules: AdRule[];
  ruleGroups: AdRuleGroup[];
}>();

const emit = defineEmits<{
  (e: "update:ruleGroups", groups: AdRuleGroup[]): void;
}>();

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

const COMPARISON_LABEL: Record<string, string> = {
  campaign: "广告活动",
  ad_group: "广告组",
  targeting: "投放",
  keyword: "关键词投放",
  product_targeting: "商品投放",
  search_terms: "用户搜索词",
};

function getRuleSummary(rule: AdRule): string {
  return rule.conditionSets
    .map(
      (cs) =>
        `≤${cs.days}d, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(",")}`
    )
    .join(" | ");
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
    groups[idx] = { ...groups[idx], rules: [...groups[idx].rules, rule] };
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
</script>

<style scoped lang="scss">
.auto-rule-panel {
  min-height: 360px;
}

.auto-rule-body {
  display: flex;
}

// ── 左侧规则组 ──
.group-panel {
  display: flex;
  flex: 0 0 230px;
  flex-direction: column;
  padding-right: 20px;
  border-right: 1px solid var(--el-border-color-lighter);
}

.group-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.group-panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.group-list {
  flex: 1;
  overflow-y: auto;
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 4px;
  cursor: pointer;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  transition: all 0.25s;

  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-5);
  }
}

.group-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.group-item.is-selected {
  background: var(--el-color-primary-light-9);
  border-color: var(--el-color-primary);

  .group-item-name {
    color: var(--el-color-primary);
  }
}

.group-item-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
}

.group-item-meta {
  display: flex;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.group-item-sep {
  color: var(--el-border-color);
  user-select: none;
}

.group-item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
  margin-left: 4px;
}

// ── 右侧区域 ──
.rule-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding-left: 20px;
  overflow-y: auto;
}

.rule-panel-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.section-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.empty-hint {
  padding: 30px 0;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  text-align: center;
}

// ── 组内规则卡片 ──
.group-rule-card {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 14px;
  margin-bottom: 6px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  transition: border-color 0.25s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }
}

.group-rule-order {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 12px;
  font-weight: 600;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: var(--el-border-radius-base);
}

.group-rule-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  overflow: hidden;
}

.group-rule-top {
  display: flex;
  gap: 8px;
  align-items: center;
}

.group-rule-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.group-rule-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

// ── 草稿池规则行 ──
.draft-rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 4px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  transition: all 0.25s;

  &:hover {
    border-color: var(--el-color-primary-light-5);
  }

  &.is-added {
    background: var(--el-color-success-light-9);
    border-color: var(--el-color-success-light-5);
  }
}

.draft-rule-info {
  display: flex;
  gap: 12px;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}

.draft-rule-name {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.draft-rule-target {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: var(--el-border-radius-base);
}

// ── 弹窗内 ──
.cycle-row {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.cycle-hint {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
