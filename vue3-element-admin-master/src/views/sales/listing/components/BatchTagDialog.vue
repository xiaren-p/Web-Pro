<template>
  <el-dialog
    :model-value="visible"
    title="批量设置标签"
    width="480px"
    class="listing-dialog"
    @update:model-value="emit('update:visible', $event)"
    @open="handleDialogOpen"
  >
    <div class="batch-tag-select-area">
      <div class="batch-hint">
        选择标签后，点击「添加」将为全部选中商品追加标签，点击「删除」将移除。
      </div>

      <TransitionGroup name="batch-tag-item" tag="div" class="batch-tag-list">
        <el-tag
          v-for="tag in selectedTags"
          :key="tag.globalTagId || tag.tagName"
          :color="tag.color || '#409eff'"
          effect="plain"
          closable
          :disable-transitions="false"
          @close="handleRemoveTag(tag)"
        >
          {{ tag.tagName }}
        </el-tag>
      </TransitionGroup>

      <el-select
        v-model="pendingTagId"
        filterable
        placeholder="搜索标签名称..."
        :filter-method="handleTagSearch"
        :loading="searchLoading"
        clearable
        class="batch-tag-search"
        @change="handleTagSelect"
        @clear="searchKeyword = ''"
      >
        <el-option
          v-for="opt in filteredOptions"
          :key="opt.globalTagId"
          :label="opt.tagName"
          :value="opt.globalTagId"
          :disabled="selectedTags.some((t) => t.globalTagId === opt.globalTagId)"
        >
          <div class="tag-option-item">
            <span class="tag-option-dot" :style="{ backgroundColor: opt.color || '#409eff' }" />
            <span>{{ opt.tagName }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <template #footer>
      <div class="dialog-footer dialog-footer--split">
        <div class="dialog-footer__group">
          <el-button @click="handleClearAll">清空</el-button>
          <el-button @click="emit('update:visible', false)">返回</el-button>
        </div>
        <div class="dialog-footer__group">
          <el-button type="danger" :loading="saving" @click="confirmBatchAction('delete')">
            删除
          </el-button>
          <el-button type="primary" :loading="saving" @click="confirmBatchAction('add')">
            添加
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 批量标签设置弹窗：从已有标签库搜索选择，支持批量添加/删除。
 * 所属板块：listing。
 */
import type { TagOption } from "@/api/sales/listing-tag";

import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { ListingTagAPI } from "@/api/sales/listing-tag";
import { SalesProductListingAPI } from "@/api/sales/listing";

interface BatchTagItem {
  globalTagId: string;
  tagName: string;
  color: string;
}

const props = defineProps<{
  visible: boolean;
  selectedRows: any[];
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "success"): void;
}>();

const allTagOptions = ref<TagOption[]>([]);
const searchKeyword = ref("");
const searchLoading = ref(false);
const pendingTagId = ref("");
const saving = ref(false);
const selectedTags = ref<BatchTagItem[]>([]);

const filteredOptions = computed(() => {
  if (!searchKeyword.value) return allTagOptions.value;
  const kw = searchKeyword.value.toLowerCase();
  return allTagOptions.value.filter((opt) => opt.tagName.toLowerCase().includes(kw));
});

function handleDialogOpen(): void {
  selectedTags.value = [];
  pendingTagId.value = "";
  searchKeyword.value = "";
  loadOptions();
}

async function loadOptions(): Promise<void> {
  if (allTagOptions.value.length > 0) return;
  searchLoading.value = true;
  try {
    allTagOptions.value = await ListingTagAPI.getOptions();
  } catch {
    ElMessage.error("加载标签选项失败");
  } finally {
    searchLoading.value = false;
  }
}

function handleTagSearch(keyword: string): void {
  searchKeyword.value = keyword;
}

function handleTagSelect(globalTagId: string): void {
  if (!globalTagId) return;
  const opt = allTagOptions.value.find((o) => o.globalTagId === globalTagId);
  if (!opt) return;
  if (selectedTags.value.some((t) => t.globalTagId === opt.globalTagId)) {
    ElMessage.warning("标签已在操作列表中");
    pendingTagId.value = "";
    return;
  }
  selectedTags.value.push({
    globalTagId: opt.globalTagId,
    tagName: opt.tagName,
    color: opt.color,
  });
  pendingTagId.value = "";
  searchKeyword.value = "";
}

function handleRemoveTag(tag: BatchTagItem): void {
  selectedTags.value = selectedTags.value.filter((t) => t.globalTagId !== tag.globalTagId);
}

function handleClearAll(): void {
  selectedTags.value = [];
}

function getExistingTags(row: any): BatchTagItem[] {
  if (!row?.label || !Array.isArray(row.label)) return [];
  return row.label
    .filter((t: any) => t && t.tagName)
    .map((t: any) => ({
      globalTagId: t.globalTagId || "",
      tagName: t.tagName || "",
      color: t.color || "",
    }));
}

function confirmBatchAction(action: "add" | "delete"): void {
  if (selectedTags.value.length === 0) {
    ElMessage.warning("请先选择标签");
    return;
  }
  const actionText = action === "add" ? "添加" : "删除";
  ElMessageBox.confirm(
    `确定要对选中的 ${props.selectedRows.length} 个商品${actionText}以下标签吗？\n${selectedTags.value.map((t) => t.tagName).join(", ")}`,
    "确认操作",
    { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
  ).then(() => {
    executeBatchAction(action);
  });
}

async function executeBatchAction(action: "add" | "delete"): Promise<void> {
  saving.value = true;
  try {
    const operationTagIds = new Set(selectedTags.value.map((t) => t.globalTagId));
    const updates: any[] = [];

    for (const row of props.selectedRows) {
      const existing = getExistingTags(row);
      let newTags: BatchTagItem[];

      if (action === "add") {
        const existingIds = new Set(existing.map((t) => t.globalTagId));
        const toAdd = selectedTags.value.filter((t) => !existingIds.has(t.globalTagId));
        newTags = [...existing, ...toAdd];
      } else {
        newTags = existing.filter((t) => !operationTagIds.has(t.globalTagId));
      }

      updates.push({
        id: row.id,
        asin: row.asin,
        tags: newTags.map((t) => ({
          globalTagId: t.globalTagId,
          tagName: t.tagName,
          color: t.color,
        })),
      });
    }

    await SalesProductListingAPI.upsertLabels(updates);
    ElMessage.success("批量操作成功");
    emit("update:visible", false);
    emit("success");
  } catch {
    ElMessage.error("操作失败");
  } finally {
    saving.value = false;
  }
}

defineExpose({
  init() {
    selectedTags.value = [];
    pendingTagId.value = "";
    searchKeyword.value = "";
  },
});
</script>

<style scoped lang="scss">
/* Listing Dialog 统一规范 — 与 EditTagDialog / BatchAssortDialog 共用 */
.listing-dialog {
  :deep(.el-dialog) {
    border-radius: var(--radius-2xl);
    box-shadow: var(--shadow-dialog);
  }

  :deep(.el-dialog__header) {
    padding: 18px 24px 14px;
    border-bottom: 1px solid var(--border-subtle);
  }

  :deep(.el-dialog__title) {
    font-size: var(--font-size-xl);
    font-weight: var(--font-weight-bold);
    color: var(--text-primary);
  }

  :deep(.el-dialog__body) {
    padding: 20px 24px;
  }

  :deep(.el-dialog__footer) {
    padding: 14px 24px 18px;
    border-top: 1px solid var(--border-subtle);
  }
}

.batch-tag-select-area {
  .batch-hint {
    margin-bottom: 12px;
    font-size: var(--font-size-sm);
    color: var(--text-tertiary);
  }

  .batch-tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-2);
    min-height: 32px;
  }
}

.batch-tag-search {
  width: 100%;
  margin-top: 12px;
}

.tag-option-item {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;

  .tag-option-dot {
    flex-shrink: 0;
    width: 10px;
    height: 10px;
    border: 1px solid rgb(0 0 0 / 8%);
    border-radius: 50%;
  }
}

/* 通用 dialog footer */
.dialog-footer {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;
  justify-content: flex-end;

  &--split {
    justify-content: space-between;
  }

  &__group {
    display: flex;
    gap: var(--spacing-2);
    align-items: center;
  }
}

/* 标签元素入场/离场动画 — duration 与全局 transition-base 对齐 */
.batch-tag-item-enter-active,
.batch-tag-item-leave-active {
  transition: all var(--transition-base);
}

.batch-tag-item-enter-from {
  opacity: 0;
  transform: translateY(-4px) scale(0.95);
}

.batch-tag-item-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.batch-tag-item-move {
  transition: transform var(--transition-base);
}
</style>
