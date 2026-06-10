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
              <el-button text size="small" type="danger" @click.stop="deleteGroupHandler(group)">
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
import {
  createGroup,
  updateGroup,
  deleteGroup,
  addRulesToGroup,
  removeRuleFromGroup as removeRuleFromGroupApi,
} from "@/api/ads/rule-strategy";

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

async function confirmGroup(): Promise<void> {
  if (!groupForm.value.name.trim()) {
    ElMessage.warning("请输入规则组名称");
    return;
  }
  const payload = {
    name: groupForm.value.name.trim(),
    executionCycle: groupForm.value.executionCycle,
  };
  try {
    if (editingGroup.value) {
      const updated = await updateGroup(editingGroup.value.id, payload);
      const groups = [...props.ruleGroups];
      const idx = groups.findIndex((g) => g.id === editingGroup.value!.id);
      if (idx !== -1) groups[idx] = updated;
      emit("update:ruleGroups", groups);
    } else {
      const created = await createGroup({ ...payload, ruleOrder: [] });
      emit("update:ruleGroups", [...props.ruleGroups, created]);
    }
    groupDialogVisible.value = false;
    editingGroup.value = null;
  } catch {
    ElMessage.error("保存失败，请重试");
  }
}

async function deleteGroupHandler(group: AdRuleGroup): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定要删除规则组「${group.name}」吗？`, "删除确认", {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await deleteGroup(group.id);
    const groups = props.ruleGroups.filter((g) => g.id !== group.id);
    emit("update:ruleGroups", groups);
    if (selectedGroupId.value === group.id) {
      selectedGroupId.value = groups[0]?.id ?? "";
    }
    ElMessage.success("已删除规则组");
  } catch {
    ElMessage.error("删除失败，请重试");
  }
}

async function addRuleToGroup(rule: AdRule): Promise<void> {
  if (!selectedGroup.value) return;
  if (selectedGroup.value.rules.some((r) => r.id === rule.id)) {
    ElMessage.warning("该规则已在当前组中");
    return;
  }
  try {
    const updated = await addRulesToGroup(selectedGroup.value.id, [rule.id]);
    const groups = [...props.ruleGroups];
    const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
    if (idx !== -1) groups[idx] = updated;
    emit("update:ruleGroups", groups);
    ElMessage.success(`已将「${rule.name}」添加到「${updated.name}」`);
  } catch {
    ElMessage.error("添加失败，请重试");
  }
}

async function removeRuleFromGroup(rule: AdRule): Promise<void> {
  if (!selectedGroup.value) return;
  try {
    const updated = await removeRuleFromGroupApi(selectedGroup.value.id, rule.id);
    const groups = [...props.ruleGroups];
    const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
    if (idx !== -1) groups[idx] = updated;
    emit("update:ruleGroups", groups);
    ElMessage.success(`已将「${rule.name}」移出规则组`);
  } catch {
    ElMessage.error("移除失败，请重试");
  }
}

function isRuleInCurrentGroup(ruleId: string): boolean {
  return selectedGroup.value?.rules.some((r) => r.id === ruleId) ?? false;
}
</script>

<style scoped lang="scss">
.auto-rule-panel {
  min-height: 600px;
}

.auto-rule-body {
  display: flex;
  gap: 20px;
  min-height: 560px;
}

.empty-hint {
  padding: 40px 20px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--el-text-color-placeholder);
  text-align: center;
}

// ── 左侧规则组 ──
.group-panel {
  display: flex;
  flex: 0 0 260px;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
}

.group-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;

  .group-panel-title {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.3px;
  }

  .el-button {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 500;
    color: #fff;
    background: rgba(255, 255, 255, 0.18);
    border: none;
    border-radius: 8px;
    transition: all 0.25s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: translateY(-1px);
    }
  }
}

.group-list {
  flex: 1;
  padding: 10px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;
  }

  .empty-hint {
    padding: 40px 20px;
    font-size: 13px;
    line-height: 1.6;
    color: var(--el-text-color-placeholder);
    text-align: center;
  }
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 6px;
  cursor: pointer;
  background: var(--el-bg-color);
  border: 1px solid transparent;
  border-radius: 10px;
  transition: all 0.25s ease;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-7);
    transform: translateX(2px);
  }

  &.is-selected {
    background: linear-gradient(
      135deg,
      rgba(102, 126, 234, 0.08) 0%,
      rgba(118, 75, 162, 0.08) 100%
    );
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  }
}

.group-item-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow: hidden;
}

.group-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;

  .group-item.is-selected & {
    font-weight: 700;
    color: var(--el-color-primary);
  }
}

.group-item-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);

  .group-item.is-selected & {
    color: var(--el-color-primary);
    opacity: 0.8;
  }
}

.group-item-sep {
  font-weight: 700;
  color: var(--el-border-color);
  user-select: none;
}

.group-item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
  margin-left: 4px;
  opacity: 0;
  transition: opacity 0.2s;

  .group-item:hover &,
  .group-item.is-selected & {
    opacity: 1;
  }
}

// ── 右侧区域 ──
.rule-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 20px;
  overflow-y: auto;
}

.rule-panel-section {
  padding: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.section-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: 0.2px;
}

.section-hint {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

// ── 组内规则卡片 ──
.group-rule-card {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 16px 18px;
  margin-bottom: 10px;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  transition: all 0.25s ease;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    border-color: var(--el-color-primary-light-6);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.1);
    transform: translateY(-1px);
  }
}

.group-rule-order {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.group-rule-info {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  overflow: hidden;
}

.group-rule-top {
  display: flex;
  gap: 10px;
  align-items: center;
}

.group-rule-name {
  font-size: 14px;
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
  padding: 14px 16px;
  margin-bottom: 8px;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  transition: all 0.25s ease;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    border-color: var(--el-color-primary-light-6);
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.08);
  }

  &.is-added {
    background: linear-gradient(135deg, rgba(103, 194, 58, 0.06) 0%, rgba(16, 185, 129, 0.06) 100%);
    border-color: var(--el-color-success-light-5);
  }
}

.draft-rule-info {
  display: flex;
  gap: 14px;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}

.draft-rule-name {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);

  .draft-rule-row.is-added & {
    color: var(--el-color-success);
  }
}

.draft-rule-target {
  flex-shrink: 0;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  color: var(--el-color-primary);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
  border-radius: 6px;
}

// ── 弹窗内 ──
.cycle-row {
  display: flex;
  gap: 10px;
  align-items: center;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.cycle-hint {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 14px;
  margin-top: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--el-text-color-secondary);
  background: var(--el-color-info-light-9);
  border-radius: 8px;
}
</style>
