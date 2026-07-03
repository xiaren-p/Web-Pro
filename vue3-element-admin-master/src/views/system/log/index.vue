<template>
  <div class="app-container">
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item prop="keywords" label="关键字">
          <el-input
            v-model="queryParams.keywords"
            placeholder="日志内容"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item prop="createTime" label="操作时间">
          <el-date-picker
            v-model="queryParams.createTime"
            :editable="false"
            type="daterange"
            range-separator="~"
            start-placeholder="开始时间"
            end-placeholder="截止时间"
            value-format="YYYY-MM-DD"
            style="width: 200px"
          />
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
    <el-card shadow="hover" class="data-table">
      <el-table
        v-loading="isLoading"
        :data="pageData"
        highlight-current-row
        border
        class="data-table__content"
      >
        <el-table-column label="操作时间" prop="createTime" width="180" />
        <el-table-column label="操作人" prop="operator" width="120" />
        <el-table-column label="日志模块" prop="module" width="100" />
        <el-table-column label="日志内容" prop="content" min-width="200" />
        <el-table-column label="IP 地址" prop="ip" width="150" />
        <el-table-column label="地区" prop="region" width="150" />
        <el-table-column label="浏览器" prop="browser" width="150" />
        <el-table-column label="终端系统" prop="os" width="200" show-overflow-tooltip />
        <el-table-column label="执行时间(ms)" prop="executionTime" width="150" />
      </el-table>
      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="fetchData"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * 操作日志列表页。
 */
import { useLogList } from "./composables/useLogList";
defineOptions({ name: "Log", inheritAttrs: false });
const queryFormRef = ref();
const { isLoading, total, queryParams, pageData, fetchData, handleQuery } = useLogList();
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  queryParams.createTime = undefined;
  fetchData();
}
onMounted(() => {
  handleQuery();
});
</script>
