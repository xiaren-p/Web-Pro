<!-- 系统配置 -->
<template>
  <div class="app-container">
    <!-- 搜索区域 -->
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
            @click="handleOpenDialog()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="['sys:config:refresh']"
            color="#626aef"
            icon="RefreshLeft"
            @click="handleRefreshCache"
          >
            刷新缓存
          </el-button>
        </div>
      </div>

      <el-table
        ref="dataTableRef"
        v-loading="loading"
        :data="pageData"
        highlight-current-row
        class="data-table__content"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column key="configName" label="配置名称" prop="configName" min-width="100" />
        <el-table-column key="configKey" label="配置键" prop="configKey" min-width="100" />
        <el-table-column key="configValue" label="配置值" prop="configValue" min-width="100" />
        <el-table-column key="remark" label="描述" prop="remark" min-width="100" />
        <el-table-column fixed="right" label="操作" width="220">
          <template #default="scope">
            <el-button
              v-hasPerm="['sys:config:update']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="handleOpenDialog(scope.row.id)"
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
import { ConfigAPI, type ConfigPageQuery, type ConfigPageVO } from "@/api/config";
import { useDebounceFn } from "@vueuse/core";
import ConfigDialog from "./components/ConfigDialog.vue";

defineOptions({
  name: "Config",
  inheritAttrs: false,
});

const queryFormRef = ref();
const configDialogRef = ref();

const loading = ref(false);
const selectIds = ref<number[]>([]);
const total = ref(0);

const queryParams = reactive<ConfigPageQuery>({
  pageNum: 1,
  pageSize: 10,
  keywords: "",
});

// 系统配置表格数据
const pageData = ref<ConfigPageVO[]>([]);

// 获取数据
function fetchData() {
  loading.value = true;
  ConfigAPI.getPage(queryParams)
    .then((data) => {
      pageData.value = data.list;
      total.value = data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

// 查询（重置页码后获取数据）
function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

// 重置查询
function handleResetQuery() {
  queryFormRef.value.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

// 行复选框选中项变化
function handleSelectionChange(selection: any) {
  selectIds.value = selection.map((item: any) => item.id);
}

// 打开系统配置弹窗
function handleOpenDialog(id?: string) {
  configDialogRef.value.open(id);
}

// 刷新缓存(防抖)
const handleRefreshCache = useDebounceFn(() => {
  ConfigAPI.refreshCache().then(() => {
    ElMessage.success("刷新成功");
  });
}, 1000);

// 删除系统配置
function handleDelete(id: string) {
  ElMessageBox.confirm("确认删除该项配置?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(() => {
    loading.value = true;
    ConfigAPI.deleteById(id)
      .then(() => {
        ElMessage.success("删除成功");
        handleResetQuery();
      })
      .finally(() => (loading.value = false));
  });
}

onMounted(() => {
  handleQuery();
});
</script>
