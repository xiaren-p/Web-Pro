<template>
  <el-dialog
    :model-value="visible"
    title="批量设置分类"
    width="460px"
    class="listing-dialog"
    @update:model-value="emit('update:visible', $event)"
  >
    <div class="assort-content">
      <div class="dialog-hint">已选中 {{ selectedRows.length }} 个商品。请选择要应用的分类：</div>
      <el-select
        v-model="batchAssortValue"
        placeholder="请选择分类"
        clearable
        class="assort-select"
      >
        <el-option
          v-for="it in categoryOptions"
          :key="it.value"
          :label="it.label"
          :value="it.value"
        />
      </el-select>
    </div>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" @click="executeBatchAssort">确定</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 批量分类设置弹窗：将所选商品统一归类到目标分类。
 * 所属板块：listing。
 */
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
    updates.push({ id: row.id, asin: row.asin, assort: batchAssortValue.value });
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

// 暴露 init 方法
defineExpose({
  init() {
    batchAssortValue.value = "";
  },
});
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

.assort-content {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-3);
  min-height: 80px;
}

.dialog-hint {
  font-size: var(--font-size-sm);
  color: var(--text-tertiary);
}

.assort-select {
  width: 100%;
}

.dialog-footer {
  display: flex;
  gap: var(--spacing-2);
  align-items: center;
  justify-content: flex-end;
}
</style>
