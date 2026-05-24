<!-- 用户管理 -->
<template>
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
                :disabled="selectIds.length === 0"
                @click="handleDelete()"
              >
                删除
              </el-button>
            </div>
          </div>

          <el-table
            v-loading="loading"
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
                  v-hasPerm="'sys:user:reset-password'"
                  v-show="canWriteUser(scope.row)"
                  type="primary"
                  icon="RefreshLeft"
                  size="small"
                  link
                  @click="hancleResetPassword(scope.row)"
                >
                  重置密码
                </el-button>
                <el-button
                  v-hasPerm="'sys:user:edit'"
                  v-show="canWriteUser(scope.row)"
                  type="primary"
                  icon="edit"
                  link
                  size="small"
                  @click="handleOpenDialog(scope.row.id)"
                >
                  编辑
                </el-button>
                <el-button
                  v-hasPerm="'sys:user:delete'"
                  v-show="canWriteUser(scope.row)"
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
import { UserAPI, type UserPageQuery, type UserPageVO } from "@/api/user";
import { useUserStore } from "@/store";

import DeptTree from "./components/DeptTree.vue";
import UserFormDrawer from "./components/UserFormDrawer.vue";

const userStore = useUserStore();

/**
 * 判断当前登录用户是否有权限对目标用户执行写操作（编辑、删除、重置密码）。
 * - COMPANY_ADMIN（1）或未知级别：全权访问。
 * - DEPT_ADMIN（2）：仅允许操作与自身 deptId 相同的用户；后端负责子部门授权。
 * - MEMBER（3）：无写权。
 *
 * @param {UserPageVO} row - 目标用户行数据。
 * @returns {boolean} 是否允许对该用户执行写操作。
 */
function canWriteUser(row: UserPageVO): boolean {
  const { adminLevel, deptId } = userStore.userInfo;
  // COMPANY_ADMIN 或超管：全权
  if (!adminLevel || adminLevel === 1) return true;
  // MEMBER：无写权
  if (adminLevel === 3) return false;
  // DEPT_ADMIN：仅允许操作本部门用户，后端负责子部门授权检查
  return !!deptId && row.deptId === deptId;
}
defineOptions({
  name: "User",
  inheritAttrs: false,
});

const queryFormRef = ref();
const userFormDrawerRef = ref();

const queryParams = reactive<UserPageQuery>({
  pageNum: 1,
  pageSize: 10,
});

const pageData = ref<UserPageVO[]>();
const total = ref(0);
const loading = ref(false);

// 选中的用户ID
const selectIds = ref<number[]>([]);

// 获取数据
async function fetchData() {
  loading.value = true;
  try {
    const data = await UserAPI.getPage(queryParams);
    pageData.value = data.list;
    total.value = data.total;
  } finally {
    loading.value = false;
  }
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
  queryParams.deptId = undefined;
  queryParams.createTime = undefined;
  fetchData();
}

// 选中项发生变化
function handleSelectionChange(selection: any[]) {
  selectIds.value = selection.map((item) => item.id);
}

// 重置密码
function hancleResetPassword(row: UserPageVO) {
  ElMessageBox.prompt("请输入用户【" + row.username + "】的新密码", "重置密码", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
  }).then(
    ({ value }) => {
      if (!value || value.length < 6) {
        ElMessage.warning("密码至少需要6位字符，请重新输入");
        return false;
      }
      UserAPI.resetPassword(row.id, value)
        .then(() => {
          ElMessage.success("密码重置成功，新密码是：" + value);
        })
        .catch(() => {
          ElMessage.error("重置密码失败，请稍后重试");
        });
    },
    () => {
      ElMessage.info("已取消重置密码");
    }
  );
}

/**
 * 打开弹窗
 *
 * @param id 用户ID
 */
function handleOpenDialog(id?: string) {
  userFormDrawerRef.value.open(id);
}

/**
 * 检查是否删除当前登录用户
 * @param singleId 单个删除的用户ID
 * @param selectedIds 批量删除的用户ID数组
 * @param currentUserInfo 当前用户信息
 * @returns 是否包含当前用户
 */
function isDeletingCurrentUser(
  singleId?: number,
  selectedIds: number[] = [],
  currentUserInfo?: any
): boolean {
  if (!currentUserInfo?.userId) return false;

  // 单个删除检查
  if (singleId && singleId.toString() === currentUserInfo.userId) {
    return true;
  }

  // 批量删除检查
  if (!singleId && selectedIds.length > 0) {
    return selectedIds.map(String).includes(currentUserInfo.userId);
  }

  return false;
}

/**
 * 删除用户
 *
 * @param id  用户ID
 */
function handleDelete(id?: number) {
  const userIds = [id || selectIds.value].join(",");
  if (!userIds) {
    ElMessage.warning("请勾选删除项");
    return;
  }

  // 安全检查：防止删除当前登录用户
  const currentUserInfo = userStore.userInfo;
  if (isDeletingCurrentUser(id, selectIds.value, currentUserInfo)) {
    ElMessage.error("不能删除当前登录用户");
    return;
  }

  ElMessageBox.confirm("确认删除用户?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(
    () => {
      loading.value = true;
      UserAPI.deleteByIds(userIds)
        .then(() => {
          ElMessage.success("删除成功");
          handleResetQuery();
        })
        .finally(() => (loading.value = false));
    },
    () => {
      ElMessage.info("已取消删除");
    }
  );
}

onMounted(() => {
  handleQuery();
});
</script>
