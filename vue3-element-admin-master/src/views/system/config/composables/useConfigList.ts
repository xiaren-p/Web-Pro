/**
 * 系统配置管理列表页业务逻辑 composable。
 */

import { ref, reactive } from "vue";
import { useDebounceFn } from "@vueuse/core";
import { ConfigAPI, type ConfigPageQuery, type ConfigPageVO } from "@/api/config";

export function useConfigList() {
  const isLoading = ref(false);
  const selectedIds = ref<string[]>([]);
  const total = ref(0);
  const queryParams = reactive<ConfigPageQuery>({ pageNum: 1, pageSize: 10, keywords: "" });
  const pageData = ref<ConfigPageVO[]>([]);

  function fetchData() {
    isLoading.value = true;
    ConfigAPI.getPage(queryParams)
      .then((data) => {
        pageData.value = data.list;
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

  function handleSelectionChange(selection: ConfigPageVO[]) {
    selectedIds.value = selection.map((item) => String(item.id));
  }

  const refreshCache = useDebounceFn(() => {
    ConfigAPI.refreshCache().then(() => {
      ElMessage.success("刷新成功");
    });
  }, 1000);

  function handleDelete(id: string, onBeforeRefresh?: () => void) {
    ElMessageBox.confirm("确认删除该项配置?", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(() => {
      isLoading.value = true;
      ConfigAPI.deleteById(id)
        .then(() => {
          ElMessage.success("删除成功");
          onBeforeRefresh?.();
          queryParams.pageNum = 1;
          fetchData();
        })
        .finally(() => (isLoading.value = false));
    });
  }

  return {
    isLoading,
    selectedIds,
    total,
    queryParams,
    pageData,
    fetchData,
    handleQuery,
    handleSelectionChange,
    refreshCache,
    handleDelete,
  };
}
