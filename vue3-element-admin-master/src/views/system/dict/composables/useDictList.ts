/**
 * 字典管理列表页业务逻辑 composable。
 */

import { ref, reactive } from "vue";
import { DictAPI, type DictPageQuery, type DictPageVO } from "@/api/dict";

export function useDictList() {
  const isLoading = ref(false);
  const selectedIds = ref<string[]>([]);
  const total = ref(0);
  const queryParams = reactive<DictPageQuery>({ pageNum: 1, pageSize: 10 });
  const tableData = ref<DictPageVO[]>();

  function fetchData() {
    isLoading.value = true;
    DictAPI.getPage(queryParams)
      .then((data) => {
        tableData.value = data.list;
        total.value = data.total;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  function handleQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  function handleSelectionChange(selection: DictPageVO[]) {
    selectedIds.value = selection.map((item) => String(item.id));
  }

  function handleDelete(id?: string, onBeforeRefresh?: () => void) {
    const dictIds = id || selectedIds.value.join(",");
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
          onBeforeRefresh?.();
          queryParams.pageNum = 1;
          fetchData();
        });
      },
      () => {
        ElMessage.info("已取消删除");
      }
    );
  }

  return {
    isLoading,
    selectedIds,
    total,
    queryParams,
    tableData,
    fetchData,
    handleQuery,
    handleSelectionChange,
    handleDelete,
  };
}
