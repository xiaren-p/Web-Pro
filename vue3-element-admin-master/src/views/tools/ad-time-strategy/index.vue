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
          <el-select v-model="listQuery.type" placeholder="全部类型" style="width: 140px" clearable>
            <el-option label="SP策略" value="SP" />
            <el-option label="SB策略" value="SB" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select
            v-model="listQuery.status"
            placeholder="全部有效状态"
            style="width: 140px"
            clearable
          >
            <el-option label="有效" value="active" />
            <el-option label="无效" value="inactive" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-select
            v-model="listQuery.creator"
            placeholder="创建人"
            style="width: 140px"
            clearable
          >
            <el-option label="当前账号" value="self" />
            <el-option label="系统" value="system" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="listQuery.templateName"
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
        <BiddingStrategyForm ref="formRef" />
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
        <el-table-column prop="templateName" label="模板名称" sortable min-width="160" />
        <el-table-column prop="type" label="类型" sortable min-width="110" />
        <el-table-column prop="status" label="有效状态" min-width="100" />
        <el-table-column prop="creator" label="创建人" sortable min-width="110" />
        <el-table-column prop="createTime" label="创建时间" sortable min-width="160" />
        <el-table-column prop="effectiveShop" label="生效店铺" sortable min-width="120" />
        <el-table-column label="操作" min-width="110">
          <template #header>
            操作
            <el-tooltip content="模板的基本操作" placement="top">
              <el-icon class="question-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </template>
          <template #default>
            <el-button link type="primary" size="small">编辑</el-button>
          </template>
        </el-table-column>
        <el-table-column label="执行日志" min-width="100">
          <template #default>
            <el-button link type="primary" size="small">查看</el-button>
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
        <el-button type="primary" :disabled="!hasSelection">启用</el-button>
        <el-button :disabled="!hasSelection">暂停</el-button>
        <el-button :disabled="!hasSelection">删除</el-button>
      </div>
      <div class="pager-wrapper">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[25, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          :total="0"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import { ArrowDown, QuestionFilled } from "@element-plus/icons-vue";
import type { ElTable } from "element-plus";
import BiddingStrategyForm from "./BiddingStrategyForm.vue";

defineOptions({
  name: "AdTimeStrategy",
});

const listQuery = reactive({
  type: "",
  status: "",
  creator: "",
  templateName: "",
});

const page = ref(1);
const pageSize = ref(25);

// 表格相关
const tableRef = ref<InstanceType<typeof ElTable>>();
const tableData = ref<any[]>([]);
const selectedRows = ref<any[]>([]);

const hasSelection = computed(() => selectedRows.value.length > 0);
const selectAll = ref(false);

const formRef = ref();

function handleSearch() {
  // 触发搜索逻辑
  console.log("Searching...", listQuery);
}

function resetSearch() {
  listQuery.type = "";
  listQuery.status = "";
  listQuery.creator = "";
  listQuery.templateName = "";
}

function handleAddTemplate(cmd: string) {
  // 触发新增分时模板
  if (cmd === "bidding") {
    openBiddingStrategyForm();
  } else {
    console.log("Add template:", cmd);
  }
}

function handleSelectionChange(val: any[]) {
  selectedRows.value = val;
  // 同步底部全选按钮状态
  if (val.length > 0 && val.length === tableData.value.length) {
    selectAll.value = true;
  } else {
    selectAll.value = false;
  }
}

function toggleSelectAll() {
  // 底部「全选」复选框勾选或取消时，联动表格内容全选状态
  if (tableRef.value) {
    tableRef.value.toggleAllSelection();
  }
}

function openBiddingStrategyForm() {
  formRef.value?.open();
}
</script>

<style scoped lang="scss" src="./index.scss"></style>
