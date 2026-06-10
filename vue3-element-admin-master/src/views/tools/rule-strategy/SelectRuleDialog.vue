<template>
  <el-dialog
    v-model="visible"
    title="选择规则添加到组"
    width="900px"
    destroy-on-close
    @closed="handleClosed"
  >
    <div class="select-rule-content">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索规则名称..."
          :prefix-icon="Search"
          style="width: 300px"
          clearable
        />
        <span class="search-spacer" />
        <el-tag>已选 {{ selectedRules.length }} 条规则</el-tag>
      </div>

      <!-- 规则表格 -->
      <el-table
        ref="tableRef"
        :data="filteredRules"
        style="width: 100%"
        row-key="id"
        class="rule-select-table"
        :header-cell-style="{
          background: 'var(--el-fill-color-lighter)',
          color: 'var(--el-text-color-primary)',
          fontWeight: 600,
        }"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="规则名称" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="rule-name-cell">
              <el-icon><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
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
        <el-table-column prop="comparisonTarget" label="比对对象" width="140">
          <template #default="{ row }">
            <el-tag size="small" type="primary" effect="light">
              {{ COMPARISON_LABEL[row.comparisonTarget] || row.comparisonTarget }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用店铺" min-width="120">
          <template #default="{ row }">
            {{ formatShops(row) }}
          </template>
        </el-table-column>
        <el-table-column label="触发条件" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="condition-preview">{{ getRuleSummary(row) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- 已选规则展示和插入位置设置 -->
      <div v-if="selectedRules.length > 0" class="selected-section">
        <div class="selected-header">
          <span class="selected-title">已选规则 - 设置插入位置</span>
        </div>
        <div class="insert-position-row">
          <span class="insert-label">插入位置：</span>
          <el-radio-group v-model="insertPosition" size="default">
            <el-radio-button value="end">添加到末尾</el-radio-button>
            <el-radio-button value="start">添加到开头</el-radio-button>
            <el-radio-button value="custom">指定位置</el-radio-button>
          </el-radio-group>
          <el-input-number
            v-if="insertPosition === 'custom'"
            v-model="customInsertIndex"
            :min="1"
            :max="(props.group?.rules?.length || 0) + 1"
            size="small"
            controls-position="right"
            style="width: 120px"
          />
          <span v-if="insertPosition === 'custom'" class="insert-hint">
            (共 {{ (props.group?.rules?.length || 0) + 1 }} 个位置)
          </span>
        </div>
        <div class="selected-list">
          <div v-for="(rule, index) in selectedRules" :key="rule.id" class="selected-item">
            <span class="item-index">{{ index + 1 }}</span>
            <div class="item-info">
              <span class="item-name">{{ rule.name }}</span>
              <span class="item-target">{{ COMPARISON_LABEL[rule.comparisonTarget] }}</span>
            </div>
            <el-button link type="danger" size="small" @click="removeSelected(rule)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="selectedRules.length === 0" @click="handleConfirm">
        添加到组
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 选择规则弹窗组件：用于从草稿箱选择多条规则添加到规则组
 */
import type { AdRule, AdRuleGroup } from "./types";

import { ref, computed } from "vue";
import { Search, Document, Delete } from "@element-plus/icons-vue";
import type { ElTable } from "element-plus";

defineOptions({ name: "SelectRuleDialog" });

const props = defineProps<{
  rules: AdRule[];
  group?: AdRuleGroup | null;
}>();

const emit = defineEmits<{
  (e: "confirm", rules: { rule: AdRule; insertIndex: number }[]): void;
}>();

const visible = ref(false);
const tableRef = ref<InstanceType<typeof ElTable>>();
const searchKeyword = ref("");
const selectedRules = ref<AdRule[]>([]);
const insertPosition = ref<"start" | "end" | "custom">("end");
const customInsertIndex = ref(1);

const COMPARISON_LABEL: Record<string, string> = {
  campaign: "广告活动",
  ad_group: "广告组",
  targeting: "定位组投放",
  keyword: "关键词投放",
  product_targeting: "商品投放",
  search_terms: "用户搜索词",
};

const existingRuleIds = computed(() => new Set(props.group?.rules.map((r) => r.id) || []));

const filteredRules = computed(() =>
  props.rules.filter((rule) => {
    const matchesSearch = !searchKeyword.value
      ? true
      : rule.name.toLowerCase().includes(searchKeyword.value.toLowerCase());
    const notInGroup = !existingRuleIds.value.has(rule.id);
    return matchesSearch && notInGroup;
  })
);

function open(_group: AdRuleGroup | null): void {
  visible.value = true;
  selectedRules.value = [];
  insertPosition.value = "end";
  customInsertIndex.value = 1;
}

function handleClosed(): void {
  searchKeyword.value = "";
  selectedRules.value = [];
  insertPosition.value = "end";
  customInsertIndex.value = 1;
}

function handleSelectionChange(selection: AdRule[]): void {
  selectedRules.value = selection;
}

function removeSelected(rule: AdRule): void {
  selectedRules.value = selectedRules.value.filter((r) => r.id !== rule.id);
  tableRef.value?.toggleRowSelection(rule, false);
}

function formatShops(rule: AdRule): string {
  if (!rule.shops || rule.shops.length === 0) return "-";
  if (rule.shops.length === 1) return String(rule.shops[0]);
  return `${rule.shops.length} 个店铺`;
}

function getRuleSummary(rule: AdRule): string {
  return rule.conditionSets
    .map(
      (cs) =>
        `≤${cs.days}天, ${cs.conditions.map((c) => `${c.metric}${c.operator}${c.value}`).join(" / ")}`
    )
    .join(" | ");
}

function handleConfirm(): void {
  let insertIndex: number;
  const currentLength = props.group?.rules?.length || 0;

  switch (insertPosition.value) {
    case "start":
      insertIndex = 0;
      break;
    case "end":
      insertIndex = currentLength;
      break;
    case "custom":
      insertIndex = customInsertIndex.value - 1; // 转换为 0-based
      break;
    default:
      insertIndex = currentLength;
  }

  // 确保 insertIndex 在有效范围内
  insertIndex = Math.max(0, Math.min(insertIndex, currentLength));

  const result = selectedRules.value.map((rule) => ({
    rule,
    insertIndex,
  }));

  emit("confirm", result);
  visible.value = false;
}

defineExpose({ open });
</script>

<style scoped lang="scss">
.select-rule-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 14px 18px;
  background: var(--el-fill-color-lighter);
  border-radius: 10px;
}

.search-spacer {
  flex: 1;
}

.rule-select-table {
  overflow: hidden;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;

  :deep(.el-table__row:hover) {
    background: var(--el-color-primary-light-9);
  }
}

.rule-name-cell {
  display: flex;
  gap: 8px;
  align-items: center;
  font-weight: 500;

  .el-icon {
    color: var(--el-color-primary);
  }
}

.condition-preview {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.selected-section {
  padding: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 10px;
}

.selected-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  margin-bottom: 12px;
  border-bottom: 1px dashed var(--el-border-color-lighter);
}

.selected-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--el-color-primary);
}

.insert-position-row {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  margin-bottom: 12px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.insert-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.insert-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.selected-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selected-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  transition: all 0.2s ease;

  &:hover {
    border-color: var(--el-color-primary-light-6);
  }
}

.item-index {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 6px;
}

.item-info {
  display: flex;
  flex: 1;
  gap: 12px;
  align-items: center;
  min-width: 0;
}

.item-name {
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.item-target {
  padding: 2px 10px;
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 4px;
}
</style>
