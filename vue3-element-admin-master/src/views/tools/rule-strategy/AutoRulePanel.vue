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
            v-for="group in props.ruleGroups"
            :key="group.id"
            class="group-item"
            :class="{ 'is-selected': selectedGroupId === group.id }"
            @click="selectedGroupId = group.id"
          >
            <div class="group-item-info">
              <span class="group-item-name">{{ group.name }}</span>
              <div class="group-item-meta">
                <span>{{ group.rules?.length || 0 }} 条规则</span>
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
          <div v-if="props.ruleGroups.length === 0" class="empty-hint">
            <el-empty :image-size="60" description="暂无规则组，点击「新建」创建" />
          </div>
        </div>
      </div>

      <!-- 右侧：规则列表表格 -->
      <div class="rule-panel">
        <template v-if="selectedGroup">
          <!-- 工具栏 -->
          <div class="rule-toolbar">
            <div class="toolbar-left">
              <div class="group-info">
                <el-icon><FolderOpened /></el-icon>
                <span class="group-name">{{ selectedGroup.name }}</span>
                <el-tag size="small" type="info" effect="light">
                  {{ selectedGroup.rules?.length || 0 }} 条规则
                </el-tag>
              </div>
            </div>
            <div class="toolbar-right">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索规则名称..."
                :prefix-icon="Search"
                style="width: 240px"
                size="default"
                clearable
              />
              <el-button type="primary" @click="openSelectRules">
                <el-icon><Plus /></el-icon>
                添加规则
              </el-button>
            </div>
          </div>

          <!-- 规则表格 -->
          <div class="rule-table-wrapper">
            <el-table
              v-loading="loading"
              :data="filteredGroupRules"
              style="width: 100%"
              row-key="id"
              class="rule-table"
              :header-cell-style="{
                background:
                  'linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%)',
                color: 'var(--el-text-color-primary)',
                fontWeight: 700,
                borderBottom: '1px solid var(--el-border-color-lighter)',
              }"
            >
              <el-table-column prop="weight" label="权重" width="100" align="center">
                <template #default="{ row, $index }">
                  <div class="weight-cell">
                    <el-input-number
                      v-model="row.weight"
                      :min="0"
                      :step="1"
                      size="small"
                      controls-position="right"
                      style="width: 90px"
                      @change="handleWeightChange(row, $index)"
                    />
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="name" label="规则名称" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <div class="name-cell">
                    <el-icon><Document /></el-icon>
                    <span>{{ row.rule.name }}</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100" align="center">
                <template #default="{ row }">
                  <el-tag
                    :type="row.rule.status === 'active' ? 'success' : 'info'"
                    size="small"
                    effect="light"
                  >
                    {{ row.rule.status === "active" ? "启用" : "暂停" }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="比对对象" width="140" align="center">
                <template #default="{ row }">
                  <el-tag size="small" type="primary" effect="light">
                    {{ COMPARISON_LABEL[row.rule.comparisonTarget] || row.rule.comparisonTarget }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="适用店铺" min-width="120">
                <template #default="{ row }">
                  {{ formatShops(row.rule) }}
                </template>
              </el-table-column>
              <el-table-column label="触发条件" min-width="220" show-overflow-tooltip>
                <template #default="{ row }">
                  <span class="condition-summary">{{ getRuleSummary(row.rule) }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="viewRuleDetail(row)">
                    查看
                  </el-button>
                  <el-button link type="danger" size="small" @click="removeRuleHandler(row)">
                    移除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- 空状态 -->
          <div v-if="filteredGroupRules.length === 0 && !loading" class="empty-state">
            <el-empty :image-size="100" description="暂无规则，点击「添加规则」来添加">
              <el-button type="primary" @click="openSelectRules">
                <el-icon><Plus /></el-icon>
                添加规则
              </el-button>
            </el-empty>
          </div>
        </template>

        <!-- 未选择规则组 -->
        <template v-else>
          <div class="empty-group-state">
            <el-empty :image-size="120" description="请先选择一个规则组">
              <template #image>
                <div class="empty-icon">
                  <el-icon :size="80"><DocumentCopy /></el-icon>
                </div>
              </template>
            </el-empty>
          </div>
        </template>
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

    <!-- 选择规则弹窗 -->
    <SelectRuleDialog
      ref="selectDialogRef"
      :rules="props.rules"
      :group="selectedGroup"
      @confirm="handleAddRules"
    />

    <!-- 查看规则详情弹窗 -->
    <RuleFormDialog ref="detailDialogRef" />
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告自动规则面板：左侧规则组 + 右侧规则表格展示
 */
import type { AdRule, AdRuleGroup, AdRuleGroupItem } from "./types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus,
  Edit,
  Delete,
  FolderAdd,
  Search,
  InfoFilled,
  FolderOpened,
  Document,
  DocumentCopy,
} from "@element-plus/icons-vue";
import {
  createGroup,
  updateGroup,
  deleteGroup,
  addRulesToGroup,
  removeRuleFromGroup,
} from "@/api/ads/rule-strategy";

import SelectRuleDialog from "./SelectRuleDialog.vue";
import RuleFormDialog from "./RuleFormDialog.vue";

defineOptions({ name: "AutoRulePanel" });

const props = defineProps<{
  rules: AdRule[];
  ruleGroups: AdRuleGroup[];
}>();

const emit = defineEmits<{
  (e: "update:ruleGroups", groups: AdRuleGroup[]): void;
}>();

const loading = ref(false);
const groupDialogVisible = ref(false);
const editingGroup = ref<AdRuleGroup | null>(null);
const groupForm = ref({ name: "", executionCycle: 1 });
const selectedGroupId = ref<string>("");
const searchKeyword = ref("");
const selectDialogRef = ref<any>(null);
const detailDialogRef = ref<any>(null);

const selectedGroup = computed(
  () => props.ruleGroups.find((g) => g.id === selectedGroupId.value) || null
);

const groupRulesWithWeight = computed(() => {
  const group = selectedGroup.value;
  if (!group) return [];
  return (group.rules || []).map((rule, index) => ({
    rule,
    weight:
      (group as any).ruleItems?.find((item: any) => item.rule.id === rule.id)?.weight ?? index,
  }));
});

const filteredGroupRules = computed(() => {
  const rules = groupRulesWithWeight.value;
  const keyword = searchKeyword.value.toLowerCase();
  const filtered = keyword
    ? rules.filter((item) => item.rule.name.toLowerCase().includes(keyword))
    : rules;
  return [...filtered].sort((a, b) => a.weight - b.weight);
});

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
        `≤${cs.days}天, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(" / ")}`
    )
    .join(" | ");
}

function formatShops(rule: AdRule): string {
  if (!rule.shops || rule.shops.length === 0) return "-";
  if (rule.shops.length === 1) return String(rule.shops[0]);
  return `${rule.shops.length} 个店铺`;
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
    ElMessage.success("保存成功");
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

function openSelectRules(): void {
  selectDialogRef.value?.open(selectedGroup.value);
}

async function handleAddRules(items: { rule: AdRule; weight: number }[]): Promise<void> {
  if (!selectedGroup.value) return;
  try {
    loading.value = true;
    const ruleIds = items.map((item) => item.rule.id);
    const updated = await addRulesToGroup(selectedGroup.value.id, ruleIds);

    const groups = [...props.ruleGroups];
    const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
    if (idx !== -1) groups[idx] = updated;
    emit("update:ruleGroups", groups);
    ElMessage.success(`已添加 ${items.length} 条规则到「${updated.name}」`);
  } catch {
    ElMessage.error("添加失败，请重试");
  } finally {
    loading.value = false;
  }
}

async function removeRuleHandler(item: AdRuleGroupItem): Promise<void> {
  if (!selectedGroup.value) return;
  try {
    await ElMessageBox.confirm(`确定要从组中移除规则「${item.rule.name}」吗？`, "移除确认", {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    const updated = await removeRuleFromGroup(selectedGroup.value.id, item.rule.id);
    const groups = [...props.ruleGroups];
    const idx = groups.findIndex((g) => g.id === selectedGroup.value!.id);
    if (idx !== -1) groups[idx] = updated;
    emit("update:ruleGroups", groups);
    ElMessage.success("已移除规则");
  } catch {
    ElMessage.error("移除失败，请重试");
  }
}

function handleWeightChange(item: AdRuleGroupItem, index: number): void {
  ElMessage.success(`规则「${item.rule.name}」权重已更新为 ${item.weight}`);
}

function viewRuleDetail(item: AdRuleGroupItem): void {
  detailDialogRef.value?.open(item.rule, true);
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

// ── 左侧规则组 ──
.group-panel {
  display: flex;
  flex: 0 0 280px;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.group-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;

  .group-panel-title {
    font-size: 15px;
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
  padding: 12px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;
  }
}

.group-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  margin-bottom: 8px;
  cursor: pointer;
  background: var(--el-bg-color-page);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  transition: all 0.25s ease;

  &:last-child {
    margin-bottom: 0;
  }

  &:hover {
    background: var(--el-color-primary-light-9);
    border-color: var(--el-color-primary-light-6);
    transform: translateX(2px);
  }

  &.is-selected {
    background: linear-gradient(
      135deg,
      rgba(102, 126, 234, 0.08) 0%,
      rgba(118, 75, 162, 0.08) 100%
    );
    border-color: var(--el-color-primary);
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.15);
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
  font-weight: 700;
  color: var(--el-text-color-primary);
  white-space: nowrap;

  .group-item.is-selected & {
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

.empty-hint {
  padding: 40px 20px;
}

// ── 右侧区域 ──
.rule-panel {
  display: flex;
  flex: 1;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.rule-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.toolbar-left {
  display: flex;
  gap: 12px;
  align-items: center;
}

.group-info {
  display: flex;
  gap: 10px;
  align-items: center;

  .el-icon {
    font-size: 18px;
    color: var(--el-color-primary);
  }
}

.group-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.toolbar-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.rule-table-wrapper {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.rule-table {
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;

  :deep(.el-table__row:hover) {
    background: var(--el-color-primary-light-9);
  }
}

.weight-cell {
  display: flex;
  justify-content: center;
}

.name-cell {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 500;

  .el-icon {
    color: var(--el-color-primary);
  }
}

.condition-summary {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.empty-state {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-group-state {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 120px;
  height: 120px;
  color: var(--el-color-primary);
  opacity: 0.3;
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
