<template>
  <el-dialog
    v-model="isVisible"
    title="批量修改投放竞价"
    width="90%"
    :close-on-click-modal="false"
    @close="onClose"
  >
    <div class="batch-bid-header">
      <el-dropdown trigger="click" @command="handleBatchSetCommand">
        <el-button size="small">
          将竞价调整为
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="fixed">固定值</el-dropdown-item>
            <el-dropdown-item command="increase">增加</el-dropdown-item>
            <el-dropdown-item command="decrease">减少</el-dropdown-item>
            <el-dropdown-item command="multiply">乘以</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-input
        v-if="batchSetMode"
        v-model="batchSetValue"
        placeholder="输入数值"
        style="width: 120px; margin-left: 8px"
        size="small"
        type="number"
        inputmode="decimal"
      />
      <el-button size="small" :disabled="!batchSetValue || !batchSetMode" @click="applyBatchSet">
        预览
      </el-button>
    </div>
    <el-table
      :data="tableData"
      border
      max-height="400px"
      style="width: 100%; margin-top: 16px"
      row-key="id"
    >
      <el-table-column label="投放对象" min-width="200" align="left">
        <template #default="{ row }">
          <span class="targeting-text">{{ row.targetingText }}</span>
        </template>
      </el-table-column>
      <el-table-column label="广告活动" min-width="150" align="left">
        <template #default="{ row }">
          <span>{{ row.campaignName }}</span>
        </template>
      </el-table-column>
      <el-table-column label="广告组" min-width="150" align="left">
        <template #default="{ row }">
          <span>{{ row.adgroupName }}</span>
        </template>
      </el-table-column>
      <el-table-column label="当前竞价" width="120" align="center">
        <template #default="{ row }">
          <span>{{ currencyIcon }}{{ row.currentBid.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="调整后" width="150" align="center">
        <template #default="{ row }">
          <el-input
            v-model="row.newBid"
            size="small"
            type="number"
            inputmode="decimal"
            style="width: 100px"
            @change="validateBid(row)"
          >
            <template #prefix>
              <span class="bid-icon">{{ currencyIcon }}</span>
            </template>
          </el-input>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" link size="small" @click="removeRow($index)">x</el-button>
        </template>
      </el-table-column>
    </el-table>
    <template #footer>
      <el-button @click="onClose">取消</el-button>
      <el-button type="primary" :loading="isConfirming" @click="onConfirm">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 批量调整竞价对话框组件。
 * 用于在三个投放面板（定位组、关键词、商品）中批量修改竞价。
 */
import { ref, watch } from "vue";
import { ArrowDown } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

defineOptions({ name: "BatchBidAdjustDialog" });

/** 表格行数据（含 newBid 渲染字段）。 */
interface BidTableRow {
  id: string | number;
  targetingText: string;
  campaignName: string;
  adgroupName: string;
  currentBid: number;
  newBid: number;
}

/** 批量设置模式。 */
type BatchSetMode = "fixed" | "increase" | "decrease" | "multiply";

const props = defineProps<{
  modelValue: boolean;
  items: Array<{
    id: string | number;
    targetingText: string;
    campaignName: string;
    adgroupName: string;
    currentBid: number;
    newBid?: number;
  }>;
  currencyIcon?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "confirm", items: Array<{ id: string | number; bid: number }>): void;
}>();

const isVisible = ref(props.modelValue);
const tableData = ref<BidTableRow[]>([]);
const isConfirming = ref(false);

const batchSetMode = ref<BatchSetMode | null>(null);
const batchSetValue = ref("");

watch(
  () => props.modelValue,
  (val) => {
    isVisible.value = val;
    if (val && props.items.length > 0) {
      tableData.value = props.items.map((item) => ({
        ...item,
        newBid: item.newBid ?? item.currentBid,
      }));
    }
  }
);

watch(isVisible, (val) => {
  emit("update:modelValue", val);
});

/**
 * 处理批量设置命令。
 *
 * @param command - 批量设置模式。
 */
function handleBatchSetCommand(command: string): void {
  batchSetMode.value = command as BatchSetMode;
  batchSetValue.value = "";
}

/** 应用批量设置到所有行。 */
function applyBatchSet(): void {
  const value = parseFloat(batchSetValue.value);
  if (!value || isNaN(value)) {
    ElMessage.warning("请输入有效的数值");
    return;
  }

  tableData.value.forEach((row) => {
    switch (batchSetMode.value) {
      case "fixed":
        row.newBid = value;
        break;
      case "increase":
        row.newBid = row.currentBid + value;
        break;
      case "decrease":
        row.newBid = Math.max(0, row.currentBid - value);
        break;
      case "multiply":
        row.newBid = row.currentBid * value;
        break;
    }
    row.newBid = Math.round(row.newBid * 100) / 100;
  });

  ElMessage.success(`已批量设置 ${tableData.value.length} 条记录的竞价`);
}

/**
 * 验证单个行的竞价输入。
 *
 * @param row - 表格行数据。
 */
function validateBid(row: BidTableRow): void {
  const val = parseFloat(String(row.newBid));
  if (!val || isNaN(val) || val <= 0) {
    row.newBid = row.currentBid;
    ElMessage.warning("竞价必须大于0");
    return;
  }
  row.newBid = Math.round(val * 100) / 100;
}

/**
 * 从表格中移除某一行。
 *
 * @param index - 行索引。
 */
function removeRow(index: number): void {
  tableData.value.splice(index, 1);
}

/** 确认批量调整竞价。 */
function onConfirm(): void {
  if (tableData.value.length === 0) {
    ElMessage.warning("没有要调整的竞价项");
    return;
  }

  for (const row of tableData.value) {
    const val = parseFloat(String(row.newBid));
    if (!val || isNaN(val) || val <= 0) {
      ElMessage.error(`第 ${tableData.value.indexOf(row) + 1} 行的竞价无效`);
      return;
    }
  }

  isConfirming.value = true;
  const result = tableData.value.map((row) => ({
    id: row.id,
    bid: Math.round(parseFloat(String(row.newBid)) * 100) / 100,
  }));

  emit("confirm", result);
  isConfirming.value = false;
  isVisible.value = false;
}

/** 关闭对话框。 */
function onClose(): void {
  isVisible.value = false;
  batchSetMode.value = null;
  batchSetValue.value = "";
}
</script>

<style scoped lang="scss">
.batch-bid-header {
  display: flex;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.targeting-text {
  font-weight: 500;
  color: var(--el-color-primary);
}
</style>
