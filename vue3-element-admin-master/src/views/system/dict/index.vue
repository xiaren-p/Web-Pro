<template>
  <div class="app-container">
    <!-- 搜索区域 -->
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
          <el-button
            v-hasPerm="['sys:dict:add']"
            type="success"
            icon="plus"
            @click="handleAddClick()"
          >
            新增
          </el-button>
          <el-button
            v-hasPerm="['sys:dict:delete']"
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
              @click.stop="handleOpenDictData(scope.row)"
            >
              <template #icon>
                <Collection />
              </template>
              字典数据
            </el-button>

            <el-button
              v-hasPerm="['sys:dict:edit']"
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="handleEditClick(scope.row.id)"
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
import { DictAPI, type DictPageQuery, type DictPageVO } from "@/api/dict";
import DictTypeDialog from "./components/DictTypeDialog.vue";
import router from "@/router";

defineOptions({
  name: "Dict",
  inheritAttrs: false,
});

const queryFormRef = ref();
const dictTypeDialogRef = ref();

const loading = ref(false);
const ids = ref<string[]>([]);
const total = ref(0);

const queryParams = reactive<DictPageQuery>({
  pageNum: 1,
  pageSize: 10,
});

const tableData = ref<DictPageVO[]>();

/** Get paginated data. */
function fetchData() {
  loading.value = true;
  DictAPI.getPage(queryParams)
    .then((data) => {
      tableData.value = data.list;
      total.value = data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

/** Query (reset page and fetch). */
function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

/** Reset query. */
function handleResetQuery() {
  queryFormRef.value.resetFields();
  queryParams.pageNum = 1;
  fetchData();
}

/** Selection change handler. */
function handleSelectionChange(selection: DictPageVO[]) {
  ids.value = selection.map((item) => String(item.id));
}

/** Open create dialog. */
function handleAddClick() {
  dictTypeDialogRef.value.open();
}

/**
 * Edit dict.
 *
 * @param id - Dict ID.
 */
function handleEditClick(id: string) {
  dictTypeDialogRef.value.open(id);
}

/**
 * Delete dict (single or batch).
 *
 * @param id - Single dict ID; if omitted, deletes selected rows.
 */
function handleDelete(id?: string) {
  const dictIds = [id || ids.value].join(",");
  if (!dictIds) {
    ElMessage.warning("请勾选删除项");
    return;
  }
  ElMessageBox.confirm("确认删除已选中的数据项?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(
    () => {
      DictAPI.deleteByIds(dictIds).then(() => {
        ElMessage.success("删除成功");
        handleResetQuery();
      });
    },
    () => {
      ElMessage.info("已取消删除");
    }
  );
}

/** Navigate to dict data management page. */
function handleOpenDictData(row: DictPageVO) {
  router.push({
    path: "/system/dict-item",
    query: { dictCode: row.dictCode, title: "【" + row.name + "】字典数据", status: row.status },
  });
}

onMounted(() => {
  handleQuery();
});
</script>
