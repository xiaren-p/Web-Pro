<template>
  <el-dialog
    :model-value="visible"
    title="编辑标签"
    width="400px"
    @update:model-value="emit('update:visible', $event)"
  >
    <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 20px">
      <el-tag
        v-for="(tag, index) in currentTags"
        :key="index"
        closable
        :disable-transitions="false"
        @close="handleRemoveTag(tag)"
      >
        {{ tag }}
      </el-tag>
      <el-input
        v-if="inputVisible"
        ref="inputRef"
        v-model="newTagInput"
        style="width: 100px"
        size="small"
        @keyup.enter="handleInputConfirm"
        @blur="handleInputConfirm"
      />
      <el-button v-else size="small" @click="showInput">+ 新标签</el-button>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="handleSaveTags">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from "vue";
import { ElMessage } from "element-plus";
import { SalesProductListingAPI } from "@/backend";

const props = defineProps<{
  visible: boolean;
  row: any;
}>();

const emit = defineEmits(["update:visible", "success"]);

const currentTags = ref<string[]>([]);
const newTagInput = ref("");
const inputVisible = ref(false);
const inputRef = ref();

const getRowTags = (row: any): string[] => {
  if (!row?.tags) return [];
  if (Array.isArray(row.tags)) return row.tags;
  if (typeof row.tags === "string") {
    try {
      const parsed = JSON.parse(row.tags.replace(/'/g, '"'));
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return row.tags.split(",").filter((t: string) => t.trim() !== "");
    }
  }
  return [];
};

watch(
  () => props.visible,
  (val) => {
    if (val && props.row) {
      currentTags.value = getRowTags(props.row);
      newTagInput.value = "";
      inputVisible.value = false;
    }
  }
);

function showInput() {
  inputVisible.value = true;
  nextTick(() => {
    const el = inputRef.value;
    if (el) {
      if (el.input?.focus) {
        el.input.focus();
      } else {
        el.focus?.();
      }
    }
  });
}

function handleInputConfirm() {
  const val = newTagInput.value.trim();
  if (val) {
    if (!currentTags.value.includes(val)) {
      currentTags.value.push(val);
    }
  }
  inputVisible.value = false;
  newTagInput.value = "";
}

function handleRemoveTag(tag: string) {
  currentTags.value = currentTags.value.filter((t) => t !== tag);
}

function handleSaveTags() {
  if (!props.row?.asin) return;
  SalesProductListingAPI.upsertLabels([
    {
      asin: props.row.asin,
      tags: currentTags.value,
    },
  ]).then(() => {
    ElMessage.success("保存成功");
    emit("update:visible", false);
    emit("success");
  });
}
</script>
