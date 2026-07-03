<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item prop="keywords" label="关键字">
          <el-input
            v-model="queryParams.keywords"
            placeholder="岗位名称/编码"
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
          <el-button v-if="isCompanyAdmin" type="success" icon="plus" @click="openDialog()">
            新增
          </el-button>
          <el-button
            v-if="isCompanyAdmin"
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
        ref="dataTableRef"
        v-loading="isLoading"
        :data="positionList"
        highlight-current-row
        border
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column
          type="selection"
          width="55"
          align="center"
          :selectable="(row: PositionPageVO) => !row.isBuiltin"
        />
        <el-table-column label="岗位名称" prop="name" min-width="120" />
        <el-table-column label="岗位编码" prop="code" width="160" />
        <el-table-column label="所属部门" prop="deptName" width="140" show-overflow-tooltip />
        <el-table-column label="状态" align="center" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 1" type="success">正常</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="排序" align="center" width="80" prop="sort" />
        <el-table-column fixed="right" label="操作" width="220">
          <template #default="scope">
            <el-button
              v-if="(isCompanyAdmin || isDeptAdmin) && !scope.row.isBuiltin"
              type="primary"
              size="small"
              link
              icon="position"
              @click="openPermDrawer(scope.row)"
            >
              分配权限
            </el-button>
            <el-button
              v-if="isCompanyAdmin"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="openDialog(scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-if="isCompanyAdmin && !scope.row.isBuiltin"
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
    <PositionDialog ref="positionDialogRef" @success="handleResetQuery" />
    <PositionPermDrawer ref="positionPermDrawerRef" @success="handleResetQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 岗位管理列表页。
 *
 * @description 薄编排层：组合 usePositionList composable 与 PositionDialog/PermDrawer。
 *              查询/分页/删除/权限判断全部在 composable 中。
 */
import { usePositionList } from "./composables/usePositionList";
import type { PositionPageVO } from "@/api/position";
import PositionDialog from "./components/PositionDialog.vue";
import PositionPermDrawer from "./components/PositionPermDrawer.vue";

defineOptions({ name: "Position", inheritAttrs: false });
const queryFormRef = ref();
const positionDialogRef = ref();
const positionPermDrawerRef = ref();
const {
  isCompanyAdmin,
  isDeptAdmin,
  isLoading,
  selectedIds,
  total,
  queryParams,
  positionList,
  fetchData,
  handleQuery,
  handleSelectionChange,
  handleDelete: deleteAction,
} = usePositionList();

/** 重置查询条件并重新查询。 */
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

/** 删除岗位（单个或批量）。 */
function handleDelete(positionId?: string) {
  deleteAction(positionId, () => queryFormRef.value?.resetFields());
}

/** 打开岗位表单弹窗。 */
function openDialog(positionId?: string) {
  positionDialogRef.value.open(positionId);
}

/** 打开权限分配抽屉。 */
function openPermDrawer(row: PositionPageVO) {
  positionPermDrawerRef.value.open(row);
}

onMounted(fetchData);
</script>
