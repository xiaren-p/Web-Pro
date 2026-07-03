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

            /** 获取分页数据。 */
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

            /** 查询（重置页码后获取数据）。 */
            function handleQuery() {
              queryParams.pageNum = 1;
              fetchData();
            }

            /** 重置查询。 */
            function handleResetQuery() {
              queryFormRef.value.resetFields();
              queryParams.pageNum = 1;
              fetchData();
            }

            /** 表格行选择回调。 */
            function handleSelectionChange(selection: DictPageVO[]) {
              ids.value = selection.map((item) => String(item.id));
            }

            /** 新增字典。 */
            function handleAddClick() {
              dictTypeDialogRef.value.open();
            }

            /**
             * 编辑字典。
             *
             * @param id - 字典ID。
             */
            function handleEditClick(id: string) {
              dictTypeDialogRef.value.open(id);
            }

            /**
             * 删除字典（单个或批量）。
             *
             * @param id - 单个字典ID，不传则删除勾选项。
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

            /** 跳转到字典数据管理页。 */
            function handleOpenDictData(row: DictPageVO) {
              router.push({
                path: "/system/dict-item",
                query: {
                  dictCode: row.dictCode,
                  title: "【" + row.name + "】字典数据",
                  status: row.status,
                },
              });
            }
            onMounted(() => {
              handleQuery();
            });
          </script>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
