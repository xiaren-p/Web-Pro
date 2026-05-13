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
          <el-button
            v-hasPerm="['sys:dept:add']"
            type="success"
            icon="plus"
            @click="handleOpenDialog()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="['sys:dept:delete']"
            type="danger"
            :disabled="selectIds.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="deptList"
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
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
              v-hasPerm="['sys:dept:add']"
              type="primary"
              link
              size="small"
              icon="plus"
              @click.stop="handleOpenDialog(scope.row.id, undefined)"
            >
              新增
            </el-button>
            <el-button
              v-hasPerm="['sys:dept:edit']"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="handleOpenDialog(scope.row.parentId, scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['sys:dept:delete']"
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
import { DeptAPI, type DeptVO, type DeptQuery } from "@/api/dept";
import DeptFormDialog from "./components/DeptFormDialog.vue";

defineOptions({
  name: "Dept",
  inheritAttrs: false,
});

const queryFormRef = ref();
const deptFormDialogRef = ref();

const loading = ref(false);
const selectIds = ref<number[]>([]);
const queryParams = reactive<DeptQuery>({ pageNum: 1, pageSize: 10 });

const deptList = ref<DeptVO[]>();

// 查询部门
function handleQuery() {
  loading.value = true;
  DeptAPI.getList(queryParams).then((data) => {
    deptList.value = data;
    loading.value = false;
  });
}

// 重置查询
function handleResetQuery() {
  queryFormRef.value.resetFields();
  handleQuery();
}

// 处理选中项变化
function handleSelectionChange(selection: any) {
  selectIds.value = selection.map((item: any) => item.id);
}

/**
 * 打开部门弹窗
 *
 * @param parentId 父部门ID
 * @param deptId 部门ID
 */
function handleOpenDialog(parentId?: string, deptId?: string) {
  deptFormDialogRef.value.open(parentId, deptId);
}

// 删除部门
function handleDelete(deptId?: number) {
  const deptIds = [deptId || selectIds.value].join(",");

  if (!deptIds) {
    ElMessage.warning("请勾选删除项");
    return;
  }

  ElMessageBox.confirm("确认删除已选中的数据项?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(
    () => {
      loading.value = true;
      DeptAPI.deleteByIds(deptIds)
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
