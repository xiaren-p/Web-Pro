<template>
  <el-dialog
    :model-value="visible"
    title="批量设置节气标签"
    width="400px"
    @update:model-value="emit('update:visible', $event)"
  >
    <div
      style="
        padding: 20px 0;
        margin-top: -20px;
        border-top: 1px solid var(--el-border-color-lighter);
        border-bottom: 1px solid var(--el-border-color-lighter);
      "
    >
      <div style="margin-bottom: 20px; font-size: 14px; color: #606266">
        输入标签后回车确认，可输入多个。
      </div>
      <div style="display: flex; flex-wrap: wrap; gap: 8px; min-height: 40px">
        <el-tag v-for="tag in batchTags" :key="tag" closable @close="handleBatchRemoveTag(tag)">
          {{ tag }}
        </el-tag>
        <el-input
          v-if="batchInputVisible"
          ref="batchInputRef"
          v-model="batchInput"
          style="width: 100px"
          @keyup.enter="handleBatchInputConfirm"
          @blur="handleBatchInputConfirm"
        />
        <el-button v-else @click="showBatchInput">+ New Tag</el-button>
      </div>
    </div>
    <template #footer>
      <div
        style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-top: -10px;
        "
      >
        <div>
          <el-button @click="handleBatchClear">清空</el-button>
          <el-button @click="emit('update:visible', false)">返回</el-button>
        </div>
        <div>
          <el-button type="danger" @click="confirmBatchAction('delete')">删除</el-button>
          <el-button type="primary" @click="confirmBatchAction('add')">添加</el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, nextTick } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { SalesProductListingAPI } from "@/api/sales/listing";

const props = defineProps<{
  visible: boolean;
  selectedRows: any[];
}>();

const emit = defineEmits(["update:visible", "success"]);

const batchTags = ref<string[]>([]);
const batchInput = ref("");
const batchInputVisible = ref(false);
const batchInputRef = ref();

function showBatchInput() {
  batchInputVisible.value = true;
  nextTick(() => {
    batchInputRef.value?.focus();
  });
}

function handleBatchInputConfirm() {
  const val = batchInput.value.trim();
  if (val) {
    if (!batchTags.value.includes(val)) {
      batchTags.value.push(val);
    }
  }
  batchInputVisible.value = false;
  batchInput.value = "";
}

function handleBatchRemoveTag(tag: string) {
  batchTags.value = batchTags.value.filter((t) => t !== tag);
}

function handleBatchClear() {
  batchTags.value = [];
}

const getRowTags = (row: any): string[] => {
  if (!row.tags) return [];
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

function confirmBatchAction(action: "add" | "delete") {
  if (batchTags.value.length === 0) {
    ElMessage.warning("请先输入标签");
    return;
  }
  const actionText = action === "add" ? "添加" : "删除";
  ElMessageBox.confirm(
    `确定要对选中的 ${props.selectedRows.length} 个商品${actionText}以下标签吗？\n${batchTags.value.join(", ")}`,
    "确认操作",
    { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
  ).then(() => {
    executeBatchAction(action);
  });
}

async function executeBatchAction(action: "add" | "delete") {
  const updates: any[] = [];
  for (const row of props.selectedRows) {
    const originalTags = getRowTags(row);
    let newTags = [...originalTags];

    if (action === "add") {
      const set = new Set([...newTags, ...batchTags.value]);
      newTags = Array.from(set);
    } else {
      newTags = newTags.filter((t) => !batchTags.value.includes(t));
    }

    updates.push({ asin: row.asin, tags: newTags });
  }

  try {
    await SalesProductListingAPI.upsertLabels(updates);
    ElMessage.success("批量操作成功");
    emit("update:visible", false);
    emit("success");
    batchTags.value = [];
  } catch (e) {
    console.error(e);
    ElMessage.error("操作失败");
  }
}

defineExpose({
  init() {
    batchTags.value = [];
    batchInput.value = "";
  },
});
</script>
