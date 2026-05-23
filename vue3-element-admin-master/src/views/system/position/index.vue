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
          <el-button
            v-if="isCompanyAdmin"
            type="success"
            icon="plus"
            @click="handleOpenDialog()"
          >
            新增
          </el-button>
          <el-button
            v-if="isCompanyAdmin"
            type="danger"
            :disabled="ids.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
        </div>
      </div>

      <el-table
        ref="dataTableRef"
        v-loading="loading"
        :data="positionList"
        highlight-current-row
        border
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" :selectable="(row: PositionPageVO) => !row.isBuiltin" />
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
              @click="handleOpenPermDrawer(scope.row)"
            >
              分配权限
            </el-button>
            <el-button
              v-if="isCompanyAdmin"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="handleOpenDialog(scope.row.id)"
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

    <!-- 岗位表单弹窗 -->
    <position-dialog ref="positionDialogRef" @success="handleResetQuery" />

    <!-- 分配权限抽屉 -->
    <position-perm-drawer ref="positionPermDrawerRef" @success="handleResetQuery" />
  </div>
</template>

<script setup lang="ts">
/**
 * 岗位管理列表页：展示所有岗位、支持增删改及菜单权限分配。
 * 所属板块：system。
 */
import { computed } from 'vue';

import { useUserStore } from '@/store/modules/user-store';
import { PositionAPI, type PositionPageVO, type PositionPageQuery } from "@/api/position";
import PositionDialog from "./components/PositionDialog.vue";
import PositionPermDrawer from "./components/PositionPermDrawer.vue";

defineOptions({
  name: "Position",
  inheritAttrs: false,
});

const queryFormRef = ref();
const positionDialogRef = ref();
const positionPermDrawerRef = ref();

const loading = ref(false);
const ids = ref<string[]>([]);
const total = ref(0);

const queryParams = reactive<PositionPageQuery>({
  pageNum: 1,
  pageSize: 10,
});

const userStore = useUserStore();

/** 是否为公司管理员（含超管） */
const isCompanyAdmin = computed(() => userStore.userInfo.roles?.includes('ROOT') ?? false);

/** 是否为部门管理员 */
const isDeptAdmin = computed(() => userStore.userInfo.roles?.includes('dept_admin') ?? false);

/** 岗位表格数据 */
const positionList = ref<PositionPageVO[]>();

/** 获取分页数据 */
function fetchData() {
  loading.value = true;
  PositionAPI.getPage(queryParams)
    .then((data) => {
      positionList.value = data.list;
      total.value = data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

/** 查询（重置页码后获取数据） */
function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

/** 重置查询 */
function handleResetQuery() {
  queryFormRef.value.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

/** 行复选框选中 */
function handleSelectionChange(selection: PositionPageVO[]) {
  ids.value = selection.filter((item) => !item.isBuiltin).map((item) => item.id);
}

/** 打开岗位表单弹窗 */
function handleOpenDialog(positionId?: string) {
  positionDialogRef.value.open(positionId);
}

/** 打开岗位权限分配抽屉 */
function handleOpenPermDrawer(row: PositionPageVO) {
  positionPermDrawerRef.value.open(row);
}

/** 删除岗位 */
function handleDelete(positionId?: string) {
  const positionIds = positionId ? positionId : ids.value.join(",");
  if (!positionIds) {
    ElMessage.warning("请勾选需要删除的非内置岗位");
    return;
  }

  ElMessageBox.confirm("确认删除已选中的数据项？", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(() => {
    loading.value = true;
    PositionAPI.deleteByIds(positionIds)
      .then(() => {
        ElMessage.success("删除成功");
        handleResetQuery();
      })
      .finally(() => {
        loading.value = false;
      });
  });
}

onMounted(fetchData);
</script>
