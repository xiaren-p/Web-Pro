<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div v-hasPerm="'pc:category:query'" class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="类目名/类目ID"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>

        <el-form-item label="类目站点" prop="site">
          <el-select
            v-model="queryParams.site"
            placeholder="请选择站点"
            clearable
            style="width: 200px"
          >
            <el-option v-for="s in siteOptions" :key="s" :label="s" :value="s"></el-option>
          </el-select>
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
            v-hasPerm="'pc:category:add'"
            type="success"
            icon="plus"
            @click="handleAddClick()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="'pc:category:delete'"
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
        v-loading="loading"
        highlight-current-row
        :data="tableData"
        border
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="类目名" prop="name" />
        <el-table-column label="类目ID" prop="category_id" />
        <el-table-column label="类目站点" prop="site" />
        <el-table-column label="类目归类" prop="category_type" />
        <el-table-column label="状态" prop="status">
          <template #default="scope">
            <el-tag :type="scope.row.status === 1 ? 'success' : 'info'">
              {{ scope.row.status_text || (scope.row.status === 1 ? "正常" : "禁用") }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column fixed="right" label="操作" align="center" width="260">
          <template #default="scope">
            <el-button
              v-hasPerm="'pc:category:dk'"
              type="info"
              link
              size="small"
              @click.stop="handleViewData(scope.row)"
            >
              数据查看
            </el-button>
            <el-button
              v-hasPerm="'pc:category:edit'"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="handleEditClick(scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="'pc:category:delete'"
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

    <!-- Dialogs -->
    <CategoryFormDialog ref="categoryFormDialogRef" @success="fetchData" />
    <CategoryViewDialog ref="categoryViewDialogRef" />
  </div>
</template>

<script setup lang="ts">
defineOptions({ name: "CrawlerCategory", inheritAttrs: false });

import { ref, reactive, onMounted } from "vue";
import request from "@/utils/request";
import { CategoryAPI, type CategoryPageQuery, type CategoryVO } from "@/api/crawler/category";
import { ElMessage, ElMessageBox } from "element-plus";
import CategoryFormDialog from "./components/CategoryFormDialog.vue";
import CategoryViewDialog from "./components/CategoryViewDialog.vue";

const queryFormRef = ref();
const loading = ref(false);
const ids = ref<number[]>([]);
const total = ref(0);

const queryParams = reactive<CategoryPageQuery>({
  pageNum: 1,
  pageSize: 10,
  keywords: "",
  site: "",
});

const siteOptions = ref<string[]>([]);
const tableData = ref<CategoryVO[]>([]);

const categoryFormDialogRef = ref();
const categoryViewDialogRef = ref();

function fetchData() {
  loading.value = true;
  CategoryAPI.getPage(queryParams)
    .then((data) => {
      if (Array.isArray(data)) {
        tableData.value = data;
        total.value = data.length;
      } else if (data && typeof data === "object") {
        tableData.value = data.list || data;
        total.value =
          data.total || (Array.isArray(data.list) ? data.list.length : tableData.value.length);
      } else {
        tableData.value = [];
        total.value = 0;
      }
    })
    .finally(() => (loading.value = false));
}

async function fetchSites() {
  try {
    const res = await request.get("/crawler/category/sites", {
      headers: { Authorization: "no-auth" },
    });
    if (Array.isArray(res)) {
      siteOptions.value = res;
    }
  } catch (e) {
    console.warn("fetchSites failed", e);
  }
}

function handleQuery() {
  queryParams.pageNum = 1;
  try {
    if (typeof queryParams.keywords === "string") {
      queryParams.keywords = queryParams.keywords.trim();
    }
  } catch {
    // ignore
  }
  fetchData();
}

function handleResetQuery() {
  queryFormRef.value.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

function handleSelectionChange(selection: any) {
  ids.value = selection.map((item: any) => item.id);
}

function handleAddClick() {
  categoryFormDialogRef.value.open();
}

function handleEditClick(id: string) {
  categoryFormDialogRef.value.open(String(id));
}

function handleViewData(row: any) {
  categoryViewDialogRef.value.open(row);
}

function handleDelete(id?: number) {
  const idsStr = id ? String(id) : ids.value.join(",");
  if (!idsStr) {
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
      CategoryAPI.deleteByIds(idsStr)
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

onMounted(() => {
  fetchSites();
  fetchData();
});
</script>

<style scoped>
.app-container {
  padding: 16px;
}
.search-container {
  margin-bottom: 12px;
}
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
