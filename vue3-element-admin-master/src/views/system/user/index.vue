<template>
  <!-- 用户管理 -->
  <div class="app-container">
    <el-row :gutter="20">
      <!-- 部门树 -->
      <el-col :lg="4" :xs="24" class="mb-[12px]">
        <DeptTree v-model="queryParams.deptId" @node-click="handleQuery" />
      </el-col>

      <!-- 用户列表 -->
      <el-col :lg="20" :xs="24">
        <!-- 搜索区域 -->
        <div class="search-container">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true" label-width="auto">
            <el-form-item label="关键字" prop="keywords">
              <el-input
                v-model="queryParams.keywords"
                placeholder="用户名/昵称/手机号"
                clearable
                @keyup.enter="handleQuery"
              />
            </el-form-item>

            <el-form-item label="状态" prop="status">
              <el-select
                v-model="queryParams.status"
                placeholder="全部"
                clearable
                style="width: 100px"
              >
                <el-option label="正常" :value="1" />
                <el-option label="禁用" :value="0" />
              </el-select>
            </el-form-item>

            <el-form-item label="创建时间">
              <el-date-picker
                v-model="queryParams.createTime"
                :editable="false"
                type="daterange"
                range-separator="~"
                start-placeholder="开始时间"
                end-placeholder="截止时间"
                value-format="YYYY-MM-DD"
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
                v-hasPerm="['sys:user:add']"
                type="success"
                icon="plus"
                @click="handleOpenDialog()"
              >
                新增
              </el-button>
              <el-button
                v-hasPerm="'sys:user:delete'"
                type="danger"
                icon="delete"
                :disabled="selectedIds.length === 0"
                @click="handleDelete()"
              >
                删除
              </el-button>
            </div>
          </div>

          <el-table
            v-loading="isLoading"
            :data="pageData"
            border
            stripe
            highlight-current-row
            class="data-table__content"
            @selection-change="handleSelectionChange"
          >
            <el-table-column type="selection" width="50" align="center" />
            <el-table-column label="用户名" prop="username" />
            <el-table-column label="昵称" width="150" align="center" prop="nickname" />
            <el-table-column label="性别" width="100" align="center">
              <template #default="scope">
                <DictLabel v-model="scope.row.gender" code="gender" />
              </template>
            </el-table-column>
            <el-table-column label="部门" width="120" align="center" prop="deptName" />
            <el-table-column label="岗位" width="120" align="center" prop="positionName" />
            <el-table-column label="管理级别" width="100" align="center" prop="adminLevelLabel" />
            <el-table-column label="手机号码" align="center" prop="mobile" width="120" />
            <el-table-column label="邮箱" align="center" prop="email" width="160" />
            <el-table-column label="状态" align="center" prop="status" width="80">
              <template #default="scope">
                <el-tag :type="scope.row.status == 1 ? 'success' : 'info'">
                  {{ scope.row.status_text || (scope.row.status == 1 ? "正常" : "禁用") }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" align="center" prop="createTime" width="150" />
            <el-table-column label="操作" fixed="right" width="220">
              <template #default="scope">
                <el-button
                  v-show="canWriteUser(scope.row)"
                  v-hasPerm="'sys:user:reset-password'"
                  type="primary"
                  icon="RefreshLeft"
                  size="small"
                  link
                  @click="handleResetPassword(scope.row)"
                >
                  重置密码
                </el-button>
                <el-button
                  v-show="canWriteUser(scope.row)"
                  v-hasPerm="'sys:user:edit'"
                  type="primary"
                  icon="edit"
                  link
                  size="small"
                  @click="handleOpenDialog(scope.row.id)"
                >
                  编辑
                </el-button>
                <el-button
                  v-show="canWriteUser(scope.row)"
                  v-hasPerm="'sys:user:delete'"
                  type="danger"
                  icon="delete"
                  link
                  size="small"
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
      </el-col>
    </el-row>

    <!-- 用户表单 -->
    <UserFormDrawer ref="userFormDrawerRef" @success="handleResetQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 用户管理列表页。
 *
 * @description 薄编排层：组合 useUserList composable、DeptTree 侧边栏与 UserFormDrawer。
 *              搜索/分页/删除/重置密码/权限判断逻辑全部在 composable 中。
 */
import { useUserList } from "./composables/useUserList";
import DeptTree from "./components/DeptTree.vue";
import UserFormDrawer from "./components/UserFormDrawer.vue";

defineOptions({
  name: "User",
  inheritAttrs: false,
});

const queryFormRef = ref();
const userFormDrawerRef = ref();

const {
  isLoading,
  queryParams,
  pageData,
  total,
  selectedIds,
  canWriteUser,
  fetchData,
  handleQuery,
  handleSelectionChange,
  handleResetPassword,
  handleDelete: deleteAction,
} = useUserList();

/** 重置查询条件并重新获取数据。 */
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  queryParams.pageNum = 1;
  queryParams.deptId = undefined;
  queryParams.createTime = undefined;
  fetchData();
}

/**
 * 删除用户（单个或批量）。
 *
 * @param id - 用户ID（不传则使用已选中的ID列表）。
 */
function handleDelete(id?: string) {
  deleteAction(id, () => {
    queryFormRef.value?.resetFields();
    queryParams.deptId = undefined;
    queryParams.createTime = undefined;
  });
}

/**
 * 打开用户编辑抽屉。
 *
 * @param id - 用户ID（不传为新增）。
 */
function handleOpenDialog(id?: string) {
  userFormDrawerRef.value.open(id);
}

onMounted(() => {
  handleQuery();
});
</script>
