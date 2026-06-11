<template>
  <div class="draft-panel">
    <div class="draft-body">
      <!-- 左侧：类目侧边栏 -->
      <div class="category-sidebar">
        <div class="category-header">
          <span class="category-title">规则类目</span>
        </div>
        <div class="category-list">
          <div
            class="category-item"
            :class="{ 'is-active': selectedCategory === ALL_CATEGORY }"
            @click="selectedCategory = ALL_CATEGORY"
          >
            <div class="category-item-left">
              <el-icon><Folder /></el-icon>
              <span class="category-item-name">全部规则</span>
            </div>
            <el-tag size="small" round>{{ props.rules.length }}</el-tag>
          </div>
          <div
            v-for="cat in categoryList"
            :key="cat.name"
            class="category-item"
            :class="{ 'is-active': selectedCategory === cat.name }"
            @click="selectedCategory = cat.name"
          >
            <div class="category-item-left">
              <el-icon><Folder /></el-icon>
              <span class="category-item-name">{{ cat.name }}</span>
              <span class="category-item-count">({{ cat.count }})</span>
            </div>
            <div class="category-item-actions">
              <el-button
                v-if="editingCategoryName === cat.name"
                link
                size="small"
                @click.stop="finishRenameCategory(cat.name)"
              >
                <el-icon><Check /></el-icon>
              </el-button>
              <el-button
                v-if="editingCategoryName !== cat.name"
                link
                size="small"
                @click.stop="startRenameCategory(cat.name)"
              >
                <el-icon><EditPen /></el-icon>
              </el-button>
              <el-button link size="small" type="danger" @click.stop="deleteCategory(cat.name)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="categoryList.length === 0" class="category-empty">
            暂无类目，点击下方按钮创建
          </div>
        </div>
        <div class="category-footer">
          <div v-if="isAddingCategory" class="add-category-row">
            <el-input
              v-model="newCategoryName"
              placeholder="输入类目名称"
              size="small"
              maxlength="20"
              @keyup.enter="confirmAddCategory"
              @keyup.escape="cancelAddCategory"
            />
            <el-button size="small" type="primary" @click="confirmAddCategory">
              <el-icon><Check /></el-icon>
            </el-button>
            <el-button size="small" @click="cancelAddCategory">
              <el-icon><Close /></el-icon>
            </el-button>
          </div>
          <el-button v-else text size="small" class="add-category-btn" @click="startAddCategory">
            <el-icon><Plus /></el-icon>
            新建类目
          </el-button>
        </div>
      </div>

      <!-- 右侧：规则内容区域 -->
      <div class="draft-content">
        <!-- 工具栏 -->
        <div class="draft-toolbar">
          <div class="toolbar-left">
            <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px">
              <el-option label="全部" value="" />
              <el-option label="启用" value="active" />
              <el-option label="暂停" value="inactive" />
            </el-select>

            <el-select v-model="filterTarget" placeholder="比对对象" clearable style="width: 160px">
              <el-option label="全部" value="" />
              <el-option
                v-for="item in targetOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>

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

        <!-- 编辑类目名内联输入框 -->
        <div v-if="editingCategoryName && selectedCategory !== ALL_CATEGORY" class="rename-banner">
          <el-input
            v-model="editCategoryInput"
            placeholder="输入新类目名"
            size="small"
            style="width: 240px"
            maxlength="20"
            @keyup.enter="finishRenameCategory(selectedCategory)"
            @keyup.escape="cancelRenameCategory"
          />
          <el-button size="small" type="primary" @click="finishRenameCategory(selectedCategory)">
            确认
          </el-button>
          <el-button size="small" @click="cancelRenameCategory">取消</el-button>
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
            <el-table-column label="类目" width="120" align="center">
              <template #default="{ row }">
                <el-tag size="small" type="warning" effect="light">
                  {{ formatCategories(row) }}
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
              props.rules.length === 0
                ? '暂无草稿规则，点击「新建规则」创建第一条'
                : '未找到匹配的规则'
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
      </div>
    </div>

    <!-- 规则表单弹窗 -->
    <RuleFormDialog ref="formRef" @saved="onFormSaved" />
  </div>
</template>

<script setup lang="ts">
/**
 * SP 广告规则草稿箱面板：左侧规则类目 + 右侧规则表格展示
 */
import type { AdRule, RuleFormData } from "./types";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Plus,
  Edit,
  Delete,
  Search,
  Document,
  Folder,
  EditPen,
  Check,
  Close,
} from "@element-plus/icons-vue";

import RuleFormDialog from "./RuleFormDialog.vue";
import { createRule, updateRule, deleteRule } from "@/api/ads/rule-strategy";

defineOptions({ name: "DraftBoxPanel" });

const props = defineProps<{
  rules: AdRule[];
}>();

const emit = defineEmits<{
  (e: "update:rules", rules: AdRule[]): void;
}>();

const ALL_CATEGORY = "__all__";

const formRef = ref<any>(null);
const loading = ref(false);
const searchKeyword = ref("");
const filterStatus = ref<string>("");
const filterTarget = ref<string>("");
const selectedCategory = ref<string>(ALL_CATEGORY);

// ── 类目管理状态 ──
const isAddingCategory = ref(false);
const newCategoryName = ref("");
const editingCategoryName = ref("");
const editCategoryInput = ref("");

/**
 * 从规则中提取类目列表（按规则数量降序）
 */
const categoryList = computed(() => {
  const map = new Map<string, number>();
  for (const rule of props.rules) {
    const cats = rule.categories || [];
    for (const cat of cats) {
      if (cat) {
        map.set(cat, (map.get(cat) || 0) + 1);
      }
    }
  }
  return Array.from(map.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count);
});

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
    const matchesCategory =
      selectedCategory.value === ALL_CATEGORY
        ? true
        : (rule.categories || []).includes(selectedCategory.value);
    return matchesSearch && matchesStatus && matchesTarget && matchesCategory;
  });
});

function formatShops(rule: AdRule): string {
  if (!rule.shops || rule.shops.length === 0) return "-";
  if (rule.shops.length === 1) return String(rule.shops[0]);
  return `${rule.shops.length} 个店铺`;
}

function formatCategories(rule: AdRule): string {
  const cats = rule.categories || [];
  if (cats.length === 0) return "-";
  return cats.join("、");
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

async function onFormSaved(data: RuleFormData): Promise<void> {
  try {
    // 编辑模式：id 非空且在已有规则列表中
    const isEdit = data.id && props.rules.some((r) => r.id === data.id);
    if (isEdit) {
      // 检查规则名是否与已有规则重复（排除自身）
      const nameConflict = props.rules.some((r) => r.name === data.name && r.id !== data.id);
      if (nameConflict) {
        ElMessage.warning("规则名称已存在，请使用其他名称");
        return;
      }
      const updated = await updateRule(data.id, data as any);
      const rules = [...props.rules];
      const idx = rules.findIndex((r) => r.id === data.id);
      if (idx !== -1) rules[idx] = updated;
      emit("update:rules", rules);
      ElMessage.success("规则已更新");
    } else {
      // 新建模式：检查规则名唯一性
      const nameConflict = props.rules.some((r) => r.name === data.name);
      if (nameConflict) {
        ElMessage.warning("规则名称已存在，请使用其他名称");
        return;
      }
      const created = await createRule(data as any);
      emit("update:rules", [...props.rules, created]);
      ElMessage.success("规则已创建");
    }
  } catch {
    ElMessage.error("保存失败，请重试");
  }
}

// ── 类目 CRUD ──

function startAddCategory(): void {
  isAddingCategory.value = true;
  newCategoryName.value = "";
}

function cancelAddCategory(): void {
  isAddingCategory.value = false;
  newCategoryName.value = "";
}

function confirmAddCategory(): void {
  const name = newCategoryName.value.trim();
  if (!name) {
    ElMessage.warning("请输入类目名称");
    return;
  }
  if (categoryList.value.some((c) => c.name === name)) {
    ElMessage.warning("类目名称已存在");
    return;
  }
  // 新建类目后自动切换到该类目（空类目，无规则）
  selectedCategory.value = name;
  isAddingCategory.value = false;
  newCategoryName.value = "";
  ElMessage.success(`已创建类目「${name}」`);
}

function startRenameCategory(name: string): void {
  editingCategoryName.value = name;
  editCategoryInput.value = name;
}

function cancelRenameCategory(): void {
  editingCategoryName.value = "";
  editCategoryInput.value = "";
}

/**
 * 重命名类目：更新所有关联规则的 categories 字段
 */
async function finishRenameCategory(oldName: string): Promise<void> {
  const newName = (editCategoryInput.value || oldName).trim();
  if (!newName || newName === oldName) {
    editingCategoryName.value = "";
    return;
  }
  if (categoryList.value.some((c) => c.name === newName)) {
    ElMessage.warning("类目名称已存在");
    return;
  }

  try {
    loading.value = true;
    const affectedRules = props.rules.filter((r) => (r.categories || []).includes(oldName));
    const updatedRules = [...props.rules];

    for (const rule of affectedRules) {
      const newCategories = (rule.categories || []).map((c) => (c === oldName ? newName : c));
      const updated = await updateRule(rule.id, { categories: newCategories } as any);
      const idx = updatedRules.findIndex((r) => r.id === rule.id);
      if (idx !== -1) updatedRules[idx] = updated;
    }

    emit("update:rules", updatedRules);
    if (selectedCategory.value === oldName) {
      selectedCategory.value = newName;
    }
    editingCategoryName.value = "";
    ElMessage.success(`已重命名类目「${oldName}」→「${newName}」`);
  } catch {
    ElMessage.error("重命名失败，请重试");
  } finally {
    loading.value = false;
  }
}

/**
 * 删除类目：清除所有关联规则的该 categories 值
 */
async function deleteCategory(name: string): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定要删除类目「${name}」吗？不会删除规则，仅清除规则的类目关联。`,
      "删除确认",
      { type: "warning" }
    );
  } catch {
    return;
  }

  try {
    loading.value = true;
    const affectedRules = props.rules.filter((r) => (r.categories || []).includes(name));
    const updatedRules = [...props.rules];

    for (const rule of affectedRules) {
      const newCategories = (rule.categories || []).filter((c) => c !== name);
      const updated = await updateRule(rule.id, { categories: newCategories } as any);
      const idx = updatedRules.findIndex((r) => r.id === rule.id);
      if (idx !== -1) updatedRules[idx] = updated;
    }

    emit("update:rules", updatedRules);
    if (selectedCategory.value === name) {
      selectedCategory.value = ALL_CATEGORY;
    }
    ElMessage.success(`已删除类目「${name}」`);
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped lang="scss">
.draft-panel {
  display: flex;
  flex-direction: column;
  min-height: 500px;
}

.draft-body {
  display: flex;
  gap: 20px;
  min-height: 520px;
}

// ── 左侧类目侧边栏 ──
.category-sidebar {
  display: flex;
  flex: 0 0 220px;
  flex-direction: column;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
}

.category-header {
  padding: 16px 18px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-bottom: none;

  .category-title {
    font-size: 15px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.3px;
  }
}

.category-list {
  flex: 1;
  padding: 10px 12px;
  overflow-y: auto;

  &::-webkit-scrollbar {
    width: 5px;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--el-border-color);
    border-radius: 3px;
  }
}

.category-item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.category-item-actions {
  display: flex;
  flex-shrink: 0;
  gap: 0;
  opacity: 0;
  transition: opacity 0.2s;
}

.category-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 4px;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;

  &:hover {
    background: var(--el-color-primary-light-9);

    .category-item-actions {
      opacity: 1;
    }
  }

  &.is-active {
    background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
    border-left: 3px solid var(--el-color-primary);

    .category-item-name {
      font-weight: 600;
      color: var(--el-color-primary);
    }
  }
}

.category-item-left {
  display: flex;
  gap: 8px;
  align-items: center;
  min-width: 0;
  overflow: hidden;

  .el-icon {
    flex-shrink: 0;
    font-size: 15px;
    color: var(--el-color-primary);
    opacity: 0.7;
  }
}

.category-item-count {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.category-empty {
  padding: 30px 16px;
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  text-align: center;
}

.category-footer {
  padding: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.add-category-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.add-category-btn {
  width: 100%;
  font-size: 13px;
  color: var(--el-color-primary);

  &:hover {
    background: var(--el-color-primary-light-9);
  }
}

// ── 右侧内容区 ──
.draft-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.rename-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 22px;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  background: var(--el-color-warning-light-9);
  border: 1px solid var(--el-color-warning-light-5);
  border-radius: 8px;
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
