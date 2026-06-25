<template>
  <el-dialog
    v-model="visible"
    title="批量修改广告活动预算"
    width="720px"
    :close-on-click-modal="false"
    @close="onClose"
  >
    <!-- 顶部操作栏 -->
    <div class="batch-budget-header">
      <el-dropdown trigger="click" @command="handleBatchSetCommand">
        <el-button size="small">
          将预算调整为
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

    <!-- 表格 -->
    <el-table
      :data="tableData"
      border
      max-height="400px"
      style="width: 100%; margin-top: 16px"
      row-key="campaignId"
    >
      <el-table-column label="广告活动" min-width="220" align="left">
        <template #default="{ row }">
          <span class="campaign-name">{{ row.name }}</span>
        </template>
      </el-table-column>
      <el-table-column label="店铺" min-width="100" align="center">
        <template #default="{ row }">
          <span>{{ row.profileAlias || row.profileId }}</span>
        </template>
      </el-table-column>
      <el-table-column label="当前预算" width="120" align="center">
        <template #default="{ row }">
          <span>{{ currencyIcon }}{{ row.currentBudget.toFixed(2) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="调整后" width="150" align="center">
        <template #default="{ row }">
          <el-input
            v-model="row.newBudget"
            size="small"
            type="number"
            inputmode="decimal"
            style="width: 100px"
            @change="validateBudget(row)"
          >
            <template #prefix>
              <span class="budget-icon">{{ currencyIcon }}</span>
            </template>
          </el-input>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="60" align="center" fixed="right">
        <template #default="{ $index }">
          <el-button type="danger" link size="small" @click="removeRow($index)">×</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 底部按钮 -->
    <template #footer>
      <el-button @click="onClose">取消</el-button>
      <el-button type="primary" :loading="confirming" @click="onConfirm">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 批量调整广告活动预算对话框组件。
 * 用于广告活动列表页批量修改多个广告活动的每日预算。
 */
import { ref, watch } from "vue";
import { ArrowDown } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

defineOptions({ name: "BatchBudgetDialog" });

/** 批量调整预算对话框接收的单项数据结构 */
export interface BatchBudgetItem {
  /** 广告活动 ID */
  campaignId: string | number;
  /** 店铺 Profile ID */
  profileId: string | number;
  /** 广告活动名称 */
  name: string;
  /** 店铺别名 */
  profileAlias?: string;
  /** 当前每日预算 */
  currentBudget: number;
  /** 调整后的新预算（初始等于 currentBudget） */
  newBudget?: number;
}

const props = withDefaults(
  defineProps<{
    modelValue: boolean;
    items: BatchBudgetItem[];
    currencyIcon?: string;
  }>(),
  {
    currencyIcon: "$",
  }
);

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (
    e: "confirm",
    items: Array<{ campaignId: string | number; profileId: string | number; budget: number }>
  ): void;
}>();

const visible = ref(props.modelValue);
const tableData = ref<any[]>([]);
const confirming = ref(false);

const batchSetMode = ref<"fixed" | "increase" | "decrease" | "multiply" | null>(null);
const batchSetValue = ref("");

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.items.length > 0) {
      tableData.value = props.items.map((item) => ({
        ...item,
        newBudget: item.newBudget ?? item.currentBudget,
      }));
    }
  }
);

watch(visible, (val) => {
  emit("update:modelValue", val);
});

/**
 * 处理批量设置命令：切换当前批量模式。
 *
 * @param {string} command - 批量设置模式
 */
function handleBatchSetCommand(command: string): void {
  batchSetMode.value = command as any;
  batchSetValue.value = "";
}

/**
 * 应用批量设置到所有行的新预算值。
 */
function applyBatchSet(): void {
  const value = parseFloat(batchSetValue.value);
  if (!value || isNaN(value)) {
    ElMessage.warning("请输入有效的数值");
    return;
  }

  tableData.value.forEach((row) => {
    switch (batchSetMode.value) {
      case "fixed":
        row.newBudget = value;
        break;
      case "increase":
        row.newBudget = row.currentBudget + value;
        break;
      case "decrease":
        row.newBudget = Math.max(0.01, row.currentBudget - value);
        break;
      case "multiply":
        row.newBudget = row.currentBudget * value;
        break;
    }
    row.newBudget = Math.round(row.newBudget * 100) / 100;
  });

  ElMessage.success(`已批量设置 ${tableData.value.length} 条记录的预算`);
}

/**
 * 验证单个行的预算输入，确保大于 0。
 *
 * @param {any} row - 行数据
 */
function validateBudget(row: any): void {
  const val = parseFloat(row.newBudget);
  if (!val || isNaN(val) || val <= 0) {
    row.newBudget = row.currentBudget;
    ElMessage.warning("预算必须大于 0");
    return;
  }
  row.newBudget = Math.round(val * 100) / 100;
}

/**
 * 从表格中移除某一行。
 *
 * @param {number} index - 行索引
 */
function removeRow(index: number): void {
  tableData.value.splice(index, 1);
}

/**
 * 确认批量调整预算，校验后 emit 结果。
 */
function onConfirm(): void {
  if (tableData.value.length === 0) {
    ElMessage.warning("没有要调整的预算项");
    return;
  }

  for (const row of tableData.value) {
    const val = parseFloat(row.newBudget);
    if (!val || isNaN(val) || val <= 0) {
      ElMessage.error(`第 ${tableData.value.indexOf(row) + 1} 行的预算无效`);
      return;
    }
  }

  confirming.value = true;
  const result = tableData.value.map((row) => ({
    campaignId: row.campaignId,
    profileId: row.profileId,
    budget: Math.round(parseFloat(row.newBudget) * 100) / 100,
  }));

  emit("confirm", result);
  confirming.value = false;
  visible.value = false;
}

/**
 * 关闭对话框并重置状态。
 */
function onClose(): void {
  visible.value = false;
  batchSetMode.value = null;
  batchSetValue.value = "";
}
</script>

<style scoped lang="scss">
.batch-budget-header {
  display: flex;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.campaign-name {
  font-weight: 500;
  color: var(--el-color-primary);
}

.budget-icon {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary, #64748b);
}
</style>
