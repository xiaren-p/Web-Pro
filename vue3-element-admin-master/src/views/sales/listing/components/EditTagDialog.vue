<template>
  <el-dialog
    :model-value="visible"
    title="编辑标签"
    width="480px"
    class="listing-dialog"
    @update:model-value="emit('update:visible', $event)"
    @open="handleDialogOpen"
  >
    <div class="tag-display-area">
      <TransitionGroup name="tag-item" tag="div" class="tag-list">
        <el-tag
          v-for="tag in currentTags"
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
      <span v-if="currentTags.length === 0" class="tag-placeholder">
        暂无标签，请从下方搜索选择
      </span>
    </div>

    <el-divider />

    <div class="tag-select-area">
      <el-select
        v-model="pendingTagId"
        filterable
        placeholder="搜索标签名称..."
        :filter-method="handleTagSearch"
        :loading="searchLoading"
        clearable
        class="tag-search"
        @change="handleTagSelect"
        @clear="searchKeyword = ''"
      >
        <el-option
          v-for="opt in filteredOptions"
          :key="opt.globalTagId"
          :label="opt.tagName"
          :value="opt.globalTagId"
          :disabled="currentTags.some((t) => t.globalTagId === opt.globalTagId)"
        >
          <div class="tag-option-item">
            <span class="tag-option-dot" :style="{ backgroundColor: opt.color || '#409eff' }" />
            <span>{{ opt.tagName }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSaveTags">保存</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 单条 Listing 标签编辑弹窗：从已有标签库搜索选择，支持动画增删。
 * 所属板块：listing。
 */
import type { TagOption } from "@/api/sales/listing-tag";

import { ref, computed } from "vue";
import { ElMessage } from "element-plus";

import { ListingTagAPI } from "@/api/sales/listing-tag";
import { SalesProductListingAPI } from "@/api/sales/listing";

interface CurrentTag {
  globalTagId: string;
  tagName: string;
  color: string;
}

const props = defineProps<{
  visible: boolean;
  row: any;
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
const currentTags = ref<CurrentTag[]>([]);

const filteredOptions = computed(() => {
  if (!searchKeyword.value) return allTagOptions.value;
  const kw = searchKeyword.value.toLowerCase();
  return allTagOptions.value.filter((opt) => opt.tagName.toLowerCase().includes(kw));
});

function extractExistingTags(row: any): CurrentTag[] {
  if (!row?.label || !Array.isArray(row.label)) return [];
  return row.label
    .filter((t: any) => t && t.tagName)
    .map((t: any) => ({
      globalTagId: t.globalTagId || "",
      tagName: t.tagName || "",
      color: t.color || "",
    }));
}

function handleDialogOpen(): void {
  currentTags.value = extractExistingTags(props.row);
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
  if (currentTags.value.some((t) => t.globalTagId === opt.globalTagId)) {
    ElMessage.warning("标签已存在");
    pendingTagId.value = "";
    return;
  }
  currentTags.value.push({
    globalTagId: opt.globalTagId,
    tagName: opt.tagName,
    color: opt.color,
  });
  pendingTagId.value = "";
  searchKeyword.value = "";
}

function handleRemoveTag(tag: CurrentTag): void {
  currentTags.value = currentTags.value.filter((t) => t.globalTagId !== tag.globalTagId);
}

async function handleSaveTags(): Promise<void> {
  if (!props.row?.id) return;
  saving.value = true;
  try {
    await SalesProductListingAPI.upsertLabels([
      {
        id: props.row.id,
        asin: props.row.asin,
        tags: currentTags.value.map((t) => ({
          globalTagId: t.globalTagId,
          tagName: t.tagName,
          color: t.color,
        })),
      },
    ]);
    ElMessage.success("保存成功");
    emit("update:visible", false);
    emit("success");
  } catch {
    ElMessage.error("保存失败");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped lang="scss">
/* Listing Dialog 统一规范 */
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

.tag-display-area {
  min-height: 40px;
  padding: 4px 0;

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-2);
  }

  .tag-placeholder {
    font-size: var(--font-size-sm);
    color: var(--text-disabled);
  }
}

.tag-search {
  width: 100%;
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

.dialog-footer {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;
  justify-content: flex-end;
}

.tag-item-enter-active,
.tag-item-leave-active {
  transition: all var(--transition-base);
}

.tag-item-enter-from {
  opacity: 0;
  transform: translateY(-4px) scale(0.95);
}

.tag-item-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.95);
}

.tag-item-move {
  transition: transform var(--transition-base);
}
</style>
