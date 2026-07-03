<template>
  <div class="app-container">
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="请输入配置键\配置名称"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button
            v-hasPerm="['sys:config:add']"
            type="success"
            icon="plus"
            @click="openDialog()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="['sys:config:refresh']"
            color="#626aef"
            icon="RefreshLeft"
            @click="refreshCache"
          >
            刷新缓存
          </el-button>
        </div>
      </div>
      <el-table
        ref="dataTableRef"
        v-loading="isLoading"
        :data="pageData"
        highlight-current-row
        class="data-table__content"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column key="configName" label="配置名称" prop="configName" min-width="100" />
        <el-table-column key="configKey" label="配置键" prop="configKey" min-width="100" />
        <el-table-column key="configValue" label="配置值" min-width="100">
          <template #default="scope">
            <span>
              {{ scope.row.configType === "PASSWORD" ? "******" : scope.row.configValue }}
            </span>
          </template>
        </el-table-column>
        <el-table-column key="remark" label="描述" prop="remark" min-width="100" />
        <el-table-column fixed="right" label="操作" width="220">
          <template #default="scope">
            <el-button
              v-hasPerm="['sys:config:update']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="openDialog(scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['sys:config:delete']"
              type="danger"
              size="small"
              link
              icon="delete"
              @click="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="fetchData"
      />
    </el-card>
    <ConfigDialog ref="configDialogRef" @success="handleResetQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 系统配置管理列表页。
 */
import { useConfigList } from "./composables/useConfigList";
import ConfigDialog from "./components/ConfigDialog.vue";

defineOptions({ name: "Config", inheritAttrs: false });
const queryFormRef = ref();
const configDialogRef = ref();
const {
  isLoading,
  total,
  queryParams,
  pageData,
  fetchData,
  handleQuery,
  handleSelectionChange,
  refreshCache,
  handleDelete: deleteAction,
} = useConfigList();
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}
function handleDelete(id: string) {
  deleteAction(id, () => queryFormRef.value?.resetFields());
}
function openDialog(id?: string) {
  configDialogRef.value.open(id);
}
onMounted(() => {
  handleQuery();
});
</script>
