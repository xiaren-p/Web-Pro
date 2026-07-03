<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="部门名称"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="部门状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 100px">
            <el-option :value="1" label="正常" />
            <el-option :value="0" label="禁用" />
          </el-select>
        </el-form-item>
        <el-form-item class="search-buttons">
          <el-button class="filter-item" type="primary" icon="search" @click="handleQuery">
            搜索
          </el-button>
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
        v-loading="isLoading"
        :data="deptList"
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="isCompanyAdmin" type="selection" width="55" align="center" />
        <el-table-column prop="name" label="部门名称" min-width="200" />
        <el-table-column prop="code" label="部门编号" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status == 1" type="success">正常</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort" label="排序" width="100" />
        <el-table-column label="操作" fixed="right" align="left" width="200">
          <template #default="scope">
            <el-button
              v-if="
                isCompanyAdmin ||
                (isDeptAdmin &&
                  (String(scope.row.id) === myDeptIdStr ||
                    myDeptDescendantIds.has(String(scope.row.id))))
              "
              type="primary"
              link
              size="small"
              icon="plus"
              @click.stop="openDialog(scope.row.id, undefined)"
            >
              新增
            </el-button>
            <el-button
              v-if="
                isCompanyAdmin ||
                (isDeptAdmin &&
                  (String(scope.row.id) === myDeptIdStr ||
                    myDeptDescendantIds.has(String(scope.row.id))))
              "
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="openDialog(scope.row.parentId, scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-if="
                isCompanyAdmin || (isDeptAdmin && myDeptDescendantIds.has(String(scope.row.id)))
              "
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
    </el-card>
    <DeptFormDialog ref="deptFormDialogRef" @success="handleQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 部门管理列表页。
 *
 * @description 薄编排层：组合 useDeptList composable 与 DeptFormDialog。
 *              部门树查询、权限判断、子孙部门收集、删除逻辑全部在 composable 中。
 */
import { useDeptList } from "./composables/useDeptList";
import DeptFormDialog from "./components/DeptFormDialog.vue";

defineOptions({ name: "Dept", inheritAttrs: false });

const queryFormRef = ref();
const deptFormDialogRef = ref();
const {
  isCompanyAdmin,
  isDeptAdmin,
  myDeptIdStr,
  myDeptDescendantIds,
  isLoading,
  selectedIds,
  queryParams,
  deptList,
  handleQuery,
  handleSelectionChange,
  handleDelete: deleteAction,
} = useDeptList();

/** 重置查询条件并重新查询。 */
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  handleQuery();
}

/** 删除部门（单个或批量）。 */
function handleDelete(deptId?: string) {
  deleteAction(deptId, () => queryFormRef.value?.resetFields());
}

/** 打开部门编辑弹窗。 */
function openDialog(parentId?: string, deptId?: string) {
  deptFormDialogRef.value.open(parentId, deptId);
}

onMounted(() => {
  handleQuery();
});
</script>
