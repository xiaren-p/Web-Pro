<template>
  <div>
    <div class="search-container">
      <el-row :gutter="12" style="align-items: center">
        <el-col :span="12">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="关键字" prop="keywords">
              <el-input
                v-model="queryParams.keywords"
                placeholder="用户名"
                @keyup.enter="handleQuery"
              />
            </el-form-item>
            <el-form-item class="search-buttons">
              <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
              <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
            </el-form-item>
          </el-form>
        </el-col>
      </el-row>
    </div>

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button
            v-hasPerm="['pc:conf:add']"
            type="success"
            icon="plus"
            @click="handleOpenDialog()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="['pc:conf:delete']"
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
        :data="list"
        row-key="id"
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="username" label="用户名" min-width="200" />
        <el-table-column prop="password" label="密码" width="200">
          <template #default="{ row }">
            <span>{{ row.password }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status" type="success">正常</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="order_num" label="排序" width="100" />

        <el-table-column label="操作" fixed="right" align="left" width="240">
          <template #default="scope">
            <el-button
              v-hasPerm="['pc:conf:edit']"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="handleOpenDialog(undefined, scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['pc:conf:delete']"
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

    <SellerFormDialog ref="formDialogRef" @success="handleQuery" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { SellerAPI } from "@/backend";
import { ElMessage, ElMessageBox } from "element-plus";
import SellerFormDialog from "./components/SellerFormDialog.vue";

const queryFormRef = ref();
const formDialogRef = ref();
const loading = ref(false);
const selectIds = ref<number[]>([]);
const total = ref(0);
const queryParams = reactive<any>({ pageNum: 1, pageSize: 10, keywords: "" });
const list = ref<any[]>([]);

function fetchData() {
  loading.value = true;
  list.value = [];
  const params = {
    pageNum: queryParams.pageNum,
    pageSize: queryParams.pageSize,
    keywords: queryParams.keywords,
  };
  SellerAPI.getList(params)
    .then((data: any) => {
      if (Array.isArray(data)) {
        list.value = data;
        total.value = data.length;
      } else if (data && typeof data === "object") {
        list.value = data.list || data;
        total.value =
          data.total || (Array.isArray(data.list) ? data.list.length : list.value.length);
      } else {
        list.value = [];
        total.value = 0;
      }
    })
    .finally(() => (loading.value = false));
}

function handleResetQuery() {
  queryFormRef.value.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

function handleSelectionChange(selection: any) {
  selectIds.value = selection.map((item: any) => item.id);
}

function handleOpenDialog(parentId?: string | number, id?: string | number) {
  formDialogRef.value.open(id);
}

function handleDelete(id?: number) {
  const ids = id ? String(id) : selectIds.value.join(",");
  if (!ids) {
    ElMessage.warning("请勾选删除项");
    return;
  }
  ElMessageBox.confirm("确认删除已选中的数据项?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => {
      loading.value = true;
      SellerAPI.deleteByIds(ids)
        .then(() => {
          ElMessage.success("删除成功");
          handleResetQuery();
        })
        .finally(() => (loading.value = false));
    })
    .catch(() => {
      ElMessage.info("已取消删除");
    });
}

function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.data-table__toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.data-table__toolbar--actions {
  display: flex;
  gap: 8px;
}
</style>
