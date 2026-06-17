<template>
  <el-dialog
    :model-value="visible"
    title="编辑标签"
    width="480px"
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
      <span v-if="currentTags.length === 0" class="tag-placeholder">暂无标签，请从下方搜索选择</span>
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
        style="width: 100%"
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
            <span
              class="tag-option-dot"
              :style="{ backgroundColor: opt.color || '#409eff' }"
            />
            <span>{{ opt.tagName }}</span>
          </div>
        </el-option>
      </el-select>
    </div>

    <template #footer>
      <el-button @click="emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSaveTags">保存</el-button>
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
  return allTagOptions.value.filter((opt) =>
    opt.tagName.toLowerCase().includes(kw)
  );
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
  currentTags.value = currentTags.value.filter(
    (t) => t.globalTagId !== tag.globalTagId
  );
}

async function handleSaveTags(): Promise<void> {
  if (!props.row?.asin) return;
  saving.value = true;
  try {
    await SalesProductListingAPI.upsertLabels([
      {
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
.tag-display-area {
  min-height: 40px;
  padding: 4px 0;

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .tag-placeholder {
    color: #c0c4cc;
    font-size: 13px;
  }
}

.tag-option-item {
  display: flex;
  align-items: center;
  gap: 8px;

  .tag-option-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
}

.tag-item-enter-active,
.tag-item-leave-active {
  transition: all 0.25s ease;
}

.tag-item-enter-from {
  opacity: 0;
  transform: translateY(-8px) scale(0.85);
}

.tag-item-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.85);
}

.tag-item-move {
  transition: transform 0.25s ease;
}
</style>
