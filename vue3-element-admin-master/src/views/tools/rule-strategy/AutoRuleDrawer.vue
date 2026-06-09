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
        <div class="group-panel-header">
          <span class="group-panel-title">规则组</span>
          <el-button text type="primary" size="small" @click="openCreateGroup">
            <el-icon><FolderAdd /></el-icon>
            新建
          </el-button>
        </div>

        <div class="group-list">
          <div v-if="ruleGroups.length === 0" class="empty-hint">暂无规则组</div>
          <div
            v-for="group in ruleGroups"
            :key="group.id"
            class="group-item"
            :class="{ 'is-selected': selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <div class="group-item-info">
              <span class="group-item-name">{{ group.name }}</span>
              <span class="group-item-count">{{ group.rules.length }} 条规则</span>
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
        </div>
      </div>

      <!-- 右侧：选中规则组 → 规则列表 + 草稿池 -->
      <div class="rule-panel">
        <div class="rule-panel-section">
          <div class="section-header">
            <span class="section-title">
              {{ selectedGroup ? `「${selectedGroup.name}」的规则` : "请先选择规则组" }}
            </span>
          </div>
          <div v-if="selectedGroup && selectedGroup.rules.length === 0" class="empty-hint">
            暂无规则，从下方草稿池中点击添加
          </div>
          <div v-for="rule in selectedGroup?.rules ?? []" :key="rule.id" class="group-rule-card">
            <div class="group-rule-info">
              <span class="group-rule-name">{{ rule.name }}</span>
              <span class="group-rule-summary">{{ getRuleSummary(rule) }}</span>
            </div>
            <el-button text type="danger" size="small" @click="removeRuleFromGroup(rule)">
              <el-icon><Delete /></el-icon>
              移出
            </el-button>
          </div>
        </div>

        <!-- 草稿池 -->
        <div class="rule-panel-section">
          <div class="section-header">
            <span class="section-title">草稿池</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索规则"
              style="width: 180px"
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
            <div class="draft-rule-info">
              <span class="draft-rule-name">{{ rule.name }}</span>
              <span class="draft-rule-target">
                {{ COMPARISON_LABEL[rule.comparisonTarget] || rule.comparisonTarget }}
              </span>
              <span class="draft-rule-summary">{{ getRuleSummary(rule) }}</span>
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
            <el-tag v-else-if="isRuleInCurrentGroup(rule.id)" type="success" size="small">
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
      width="420px"
    >
      <el-form :model="groupForm" @submit.prevent="confirmGroup">
        <el-form-item label="规则组名称" label-width="100px">
          <el-input
            v-model="groupForm.name"
            placeholder="请输入规则组名称"
            maxlength="50"
            @keyup.enter="confirmGroup"
          />
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

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Edit, Delete, FolderAdd, Search } from "@element-plus/icons-vue";

defineOptions({ name: "AutoRuleDrawer" });

// ── Props / Emits ──
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
const groupForm = ref({ name: "" });
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
  targeting: "定位组投放",
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

function open(): void {
  visible.value = true;
  selectedGroupId.value = props.ruleGroups[0]?.id ?? "";
}

function handleClose(): void {
  visible.value = false;
}

function openCreateGroup(): void {
  editingGroup.value = null;
  groupForm.value = { name: "" };
  groupDialogVisible.value = true;
}

function openEditGroup(group: AdRuleGroup): void {
  editingGroup.value = group;
  groupForm.value = { name: group.name };
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
      groups[idx] = { ...groups[idx], name: groupForm.value.name.trim() };
    }
  } else {
    groups.push({
      id: `group_${Date.now()}`,
      name: groupForm.value.name.trim(),
      rules: [],
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

.group-panel {
  display: flex;
  flex: 0 0 240px;
  flex-direction: column;
  padding-right: 16px;
  border-right: 1px solid #e5e7eb;
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
  color: #1f2937;
}

.group-list {
  flex: 1;
  overflow-y: auto;
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  margin-bottom: 6px;
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: 6px;
  transition: all 0.15s;

  &:hover {
    background: #f5f7fa;
  }

  &.is-selected {
    background: #ecf5ff;
    border-color: #409eff;
  }
}

.group-item-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.group-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
}

.group-item-count {
  font-size: 12px;
  color: #909399;
}

.group-item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
}

.rule-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  padding-left: 16px;
  overflow-y: auto;
}

.rule-panel-section {
  margin-bottom: 20px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.empty-hint {
  padding: 24px 0;
  font-size: 13px;
  color: #c0c4cc;
  text-align: center;
}

.group-rule-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
}

.group-rule-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}

.group-rule-name {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.group-rule-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}

.draft-rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  margin-bottom: 6px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  transition: background 0.15s;

  &:hover {
    background: #fafbfc;
  }

  &.is-added {
    background: #f0fdf4;
    border-color: #bbf7d0;
    opacity: 0.6;
  }
}

.draft-rule-info {
  display: flex;
  gap: 10px;
  align-items: center;
  overflow: hidden;
}

.draft-rule-name {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}

.draft-rule-target {
  flex-shrink: 0;
  padding: 1px 6px;
  font-size: 11px;
  color: #409eff;
  background: #ecf5ff;
  border-radius: 3px;
}

.draft-rule-summary {
  overflow: hidden;
  text-overflow: ellipsis;
  font-family: monospace;
  font-size: 11px;
  color: #909399;
  white-space: nowrap;
}
</style>
