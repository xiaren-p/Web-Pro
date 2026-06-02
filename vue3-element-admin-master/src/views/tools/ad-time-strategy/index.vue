<template>
  <div class="strategy-page">
    <!-- 顶级蓝条与标题 -->
    <div class="page-title-bar">
      <span class="title-text">分时策略</span>
    </div>

    <!-- 搜索与筛选区域 -->
    <div class="filter-panel">
      <el-form :inline="true" :model="listQuery" class="filter-form">
        <el-form-item>
          <el-select
            v-model="listQuery.status"
            placeholder="全部状态"
            style="width: 140px"
            clearable
          >
            <el-option label="开启" :value="1" />
            <el-option label="暂停" :value="0" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="listQuery.keyword"
            placeholder="请输入模板名称"
            style="width: 200px"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">查询</el-button>
          <el-button @click="resetSearch">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 操作按钮行 -->
    <div class="action-panel">
      <div class="action-left">
        <el-dropdown trigger="click" @command="handleAddTemplate">
          <el-button type="primary">
            + 添加模板
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="bidding">分时调竞价策略</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <BiddingStrategyForm ref="formRef" @saved="onFormSaved" />
      </div>
      <div class="action-right">
        <!-- 对应右侧配置列显示图标 -->
        <el-button icon="Reading" plain />
      </div>
    </div>

    <!-- 数据表格 -->
    <div class="table-container">
      <el-table
        ref="tableRef"
        :data="tableData"
        style="width: 100%"
        border
        empty-text="没有匹配结果"
        header-cell-class-name="table-header-gray"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="45" align="center" />
        <el-table-column prop="name" label="模板名称" sortable min-width="160" />
        <el-table-column prop="type" label="类型" min-width="100">
          <template #default="{ row }">
            {{ TYPE_MAP[row.type] || row.type || "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="有效状态" min-width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">
              {{ STATUS_MAP[row.status] || "-" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="creator" label="创建人" sortable min-width="110" />
        <el-table-column prop="weight" label="权重" sortable min-width="80" />
        <el-table-column prop="created_at" label="创建时间" sortable min-width="160" />
        <el-table-column prop="shops" label="生效店铺" min-width="120">
          <template #default="{ row }">
            {{ (row.shops || []).join("、") || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="标签" min-width="120">
          <template #default="{ row }">
            {{ ((row.field_settings || {}).tags || []).join("、") || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="140" fixed="right">
          <template #header>
            操作
            <el-tooltip content="模板的基本操作" placement="top">
              <el-icon class="question-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 底部批量操作及分页 -->
    <div class="pagination-bar">
      <div class="batch-actions">
        <el-checkbox v-model="selectAll" class="chk-all" @change="toggleSelectAll">
          全选
        </el-checkbox>
        <el-button type="primary" :disabled="!hasSelection" @click="handleBatchEnable">
          启用
        </el-button>
        <el-button :disabled="!hasSelection" @click="handleBatchPause">暂停</el-button>
        <el-button :disabled="!hasSelection" @click="handleBatchDelete">删除</el-button>
      </div>
      <div class="pager-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[25, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="fetchList"
          @current-change="fetchList"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 分时调价策略列表页。
 * 所属板块：tools → ad-time-strategy。
 */
import { ref, reactive, computed, onMounted } from "vue";
import { ArrowDown, QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { ElTable } from "element-plus";
import BiddingStrategyForm from "./BiddingStrategyForm.vue";
import { getTimePricingList, deleteTimePricing } from "@/api/ads/index";

defineOptions({
  name: "AdTimeStrategy",
});

const STATUS_MAP: Record<number, string> = { 0: "暂停", 1: "开启" };
const TYPE_MAP: Record<string, string> = { bidding_time: "竞价分时" };

const listQuery = reactive({
  keyword: "",
  status: "" as number | string,
});

const page = ref(1);
const pageSize = ref(25);
const total = ref(0);

// 表格相关
const tableRef = ref<InstanceType<typeof ElTable>>();
const tableData = ref<any[]>([]);
const selectedRows = ref<any[]>([]);

const hasSelection = computed(() => selectedRows.value.length > 0);
const selectAll = ref(false);

const formRef = ref();

/** 加载策略列表 */
async function fetchList(): Promise<void> {
  try {
    const res = await getTimePricingList({
      pageNum: page.value,
      pageSize: pageSize.value,
      keyword: listQuery.keyword || undefined,
      status: listQuery.status !== "" ? listQuery.status : undefined,
    });
    tableData.value = res.list || [];
    total.value = res.total || 0;
  } catch {
    ElMessage.error("加载策略列表失败");
  }
}

function handleSearch(): void {
  page.value = 1;
  fetchList();
}

function resetSearch(): void {
  listQuery.keyword = "";
  listQuery.status = "";
  page.value = 1;
  fetchList();
}

function handleAddTemplate(cmd: string): void {
  if (cmd === "bidding") {
    formRef.value?.open();
  }
}

/** 编辑策略 */
function handleEdit(row: any): void {
  formRef.value?.openForEdit(row.id);
}

/** 删除策略 */
async function handleDelete(row: any): Promise<void> {
  try {
    await ElMessageBox.confirm(`确定删除策略"${row.name}"吗？`, "删除确认", {
      type: "warning",
    });
    await deleteTimePricing([row.id]);
    ElMessage.success("删除成功");
    fetchList();
  } catch {
    // 取消或失败
  }
}

/** 批量删除 */
async function handleBatchDelete(): Promise<void> {
  if (!hasSelection.value) return;
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${selectedRows.value.length} 条策略吗？`,
      "批量删除确认",
      { type: "warning" }
    );
    const ids = selectedRows.value.map((r: any) => r.id);
    await deleteTimePricing(ids);
    ElMessage.success("删除成功");
    fetchList();
  } catch {
    // 取消或失败
  }
}

/** 批量启用（status=1） */
async function handleBatchEnable(): Promise<void> {
  // TODO: 后端可扩展批量状态更新接口
  ElMessage.info("批量启用功能待实现");
}

/** 批量暂停（status=0） */
async function handleBatchPause(): Promise<void> {
  ElMessage.info("批量暂停功能待实现");
}

function handleSelectionChange(val: any[]): void {
  selectedRows.value = val;
  selectAll.value = val.length > 0 && val.length === tableData.value.length;
}

function toggleSelectAll(): void {
  tableRef.value?.toggleAllSelection();
}

/** 表单提交/编辑成功后刷新列表 */
function onFormSaved(): void {
  fetchList();
}

onMounted(() => {
  fetchList();
});
</script>

<style scoped lang="scss" src="./index.scss"></style>
