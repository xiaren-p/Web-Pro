<template>
  <div class="app-container">
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="字典名称/编码"
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
          <el-button v-hasPerm="['sys:dict:add']" type="success" icon="plus" @click="openDialog()">
            新增
          </el-button>
          <el-button
            v-hasPerm="['sys:dict:delete']"
            type="danger"
            :disabled="selectedIds.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
        </div>
      </div>
      <el-table
        v-loading="isLoading"
        highlight-current-row
        :data="tableData"
        border
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="字典名称" prop="name" />
        <el-table-column label="字典编码" prop="dictCode" />
        <el-table-column label="状态" prop="status">
          <template #default="scope">
            <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
              {{ scope.row.status_text || (scope.row.status === 1 ? "启用" : "禁用") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column fixed="right" label="操作" align="center" width="220">
          <template #default="scope">
            <el-button
              type="primary"
              link
              size="small"
              :disabled="scope.row.status !== 1"
              @click.stop="openDictData(scope.row)"
            >
              <template #icon><Collection /></template>
              字典数据
            </el-button>
            <el-button
              v-hasPerm="['sys:dict:edit']"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="editDialog(scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['sys:dict:delete']"
              type="danger"
              link
              size="small"
              icon="delete"
              @click.stop="handleDelete(scope.row.id)"
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
    <DictTypeDialog ref="dictTypeDialogRef" @success="handleQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 字典管理列表页。
 */
import { useDictList } from "./composables/useDictList";
import type { DictPageVO } from "@/api/dict";
import DictTypeDialog from "./components/DictTypeDialog.vue";
import router from "@/router";

defineOptions({ name: "Dict", inheritAttrs: false });

const queryFormRef = ref();
const dictTypeDialogRef = ref();
const {
  isLoading,
  selectedIds,
  total,
  queryParams,
  tableData,
  fetchData,
  handleQuery,
  handleSelectionChange,
  handleDelete: deleteAction,
} = useDictList();

function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}
function handleDelete(id?: string) {
  deleteAction(id, () => queryFormRef.value?.resetFields());
}
function openDialog() {
  dictTypeDialogRef.value.open();
}
function editDialog(id: string) {
  dictTypeDialogRef.value.open(id);
}
function openDictData(row: DictPageVO) {
  router.push({
    path: "/system/dict-item",
    query: { dictCode: row.dictCode, title: "[" + row.name + "]字典数据", status: row.status },
  });
}
onMounted(() => {
  handleQuery();
});
</script>
