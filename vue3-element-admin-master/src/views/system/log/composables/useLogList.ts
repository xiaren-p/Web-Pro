/**
 * 操作日志列表页业务逻辑 composable。
 */

import { ref, reactive } from "vue";
import { LogAPI, type LogPageQuery, type LogPageVO } from "@/api/log";

export function useLogList() {
  const isLoading = ref(false);
  const total = ref(0);
  const queryParams = reactive<LogPageQuery>({
    pageNum: 1,
    pageSize: 10,
    keywords: "",
    createTime: ["", ""],
  });
  const pageData = ref<LogPageVO[]>();

  function fetchData() {
    isLoading.value = true;
    LogAPI.getPage(queryParams)
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

  return { isLoading, total, queryParams, pageData, fetchData, handleQuery };
}
