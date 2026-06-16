<template>
  <el-dialog
    :model-value="visible"
    title="批量设置分类"
    width="400px"
    @update:model-value="emit('update:visible', $event)"
  >
    <div
      style="
        min-height: 80px;
        padding: 20px 0;
        margin-top: -20px;
        border-top: 1px solid var(--el-border-color-lighter);
        border-bottom: 1px solid var(--el-border-color-lighter);
      "
    >
      <div style="margin-bottom: 20px; font-size: 14px; color: #606266">
        已选中 {{ selectedRows.length }} 个商品。请选择要应用的分类：
      </div>
      <el-select v-model="batchAssortValue" placeholder="请选择分类" clearable style="width: 100%">
        <el-option
          v-for="it in categoryOptions"
          :key="it.value"
          :label="it.label"
          :value="it.value"
        />
      </el-select>
    </div>
    <template #footer>
      <div style="display: flex; justify-content: flex-end; margin-top: -10px">
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="executeBatchAssort">确定</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { SalesProductListingAPI } from "@/api/sales/listing";

const props = defineProps<{
  visible: boolean;
  selectedRows: any[];
  categoryOptions: { label: string; value: string }[];
}>();

const emit = defineEmits(["update:visible", "success"]);

const batchAssortValue = ref("");

async function executeBatchAssort() {
  if (!batchAssortValue.value) {
    ElMessage.warning("请选择要设置的分类");
    return;
  }

  const updates: any[] = [];
  for (const row of props.selectedRows) {
    updates.push({ asin: row.asin, assort: batchAssortValue.value });
  }

  try {
    await SalesProductListingAPI.upsertAssort(updates);
    ElMessage.success("批量修改分类成功");
    emit("update:visible", false);
    emit("success");
    batchAssortValue.value = "";
  } catch (e) {
    console.error(e);
    ElMessage.error("批量修改分类失败");
  }
}

// 暴露一个 init 方法
defineExpose({
  init() {
    batchAssortValue.value = "";
  },
});
</script>
