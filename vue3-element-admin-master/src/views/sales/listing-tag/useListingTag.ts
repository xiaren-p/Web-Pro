import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { ListingTagAPI, type ListingTagVO, type ListingTagQuery } from "@/api/sales/listing-tag";
import { defaultColumns, tagStatusOptions } from "@/views/sales/listing-tag/constants";

const STORAGE_KEY = "SALES_LISTING_TAG_COLUMNS";

export function useListingTag() {
  const loading = ref(false);
  const tableData = ref<ListingTagVO[]>([]);
  const pageNum = ref(1);
  const pageSize = ref(20);
  const total = ref(0);
  const typeOptions = ref<string[]>([]);

  // 查询参数
  const queryParams = reactive<ListingTagQuery>({
    pageNum: 1,
    pageSize: 20,
    tagName: "",
    type: "",
    status: "",
    createByName: "",
  });

  // 列配置
  const initColumns = () => {
    const cached = localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        return JSON.parse(cached);
      } catch {
        return JSON.parse(JSON.stringify(defaultColumns));
      }
    }
    return JSON.parse(JSON.stringify(defaultColumns));
  };
  const columns = ref(initColumns());
  const tableColumns = computed(() => columns.value.filter((c: any) => c.visible));

  // 状态和类型映射
  const getStatusTag = (status: string) => {
    const option = tagStatusOptions.find(
      (o: { label: string; value: string }) => o.value === status
    );
    return option?.label || status;
  };

  const getStatusType = (status: string) => {
    switch (status) {
      case "normal":
        return "success";
      case "creating":
      case "modifying":
        return "warning";
      case "deleted":
        return "danger";
      default:
        return "info";
    }
  };

  // 查询列表
  const handleQuery = async () => {
    loading.value = true;
    try {
      const res = await ListingTagAPI.getPage({
        ...queryParams,
        pageNum: pageNum.value,
        pageSize: pageSize.value,
      });
      tableData.value = res.data || [];
      total.value = res.total || 0;
    } catch {
      ElMessage.error("查询失败");
    } finally {
      loading.value = false;
    }
  };

  // 加载类型选项
  const loadTypeOptions = async () => {
    try {
      const res = await ListingTagAPI.getTypeOptions();
      typeOptions.value = res || [];
    } catch {
      typeOptions.value = [];
    }
  };

  // 刷新查询和类型选项
  const handleQueryAndRefresh = async () => {
    await handleQuery();
    await loadTypeOptions();
  };

  // 搜索
  const handleSearch = (params: any) => {
    Object.assign(queryParams, params);
    pageNum.value = 1;
    handleQuery();
    loadTypeOptions();
  };

  // 重置
  const handleReset = (params: any) => {
    Object.assign(queryParams, params);
    pageNum.value = 1;
    handleQuery();
  };

  // 删除
  const handleDelete = async (row: ListingTagVO) => {
    try {
      await ElMessageBox.confirm(`确定要删除标签「${row.tagName}」吗？`, "提示", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      });
      await ListingTagAPI.delete(row.id);
      ElMessage.success("删除成功");
      handleQuery();
      loadTypeOptions();
    } catch {
      // 取消删除或删除失败
    }
  };

  // 批量删除
  const selectedRows = ref<ListingTagVO[]>([]);
  const handleBatchDelete = async () => {
    if (selectedRows.value.length === 0) {
      ElMessage.warning("请先选择要删除的标签");
      return;
    }
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedRows.value.length} 个标签吗？`,
        "提示",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      );
      await ListingTagAPI.batchDelete(selectedRows.value.map((r) => r.id));
      ElMessage.success("批量删除成功");
      selectedRows.value = [];
      handleQuery();
      loadTypeOptions();
    } catch {
      // 取消删除或删除失败
    }
  };

  // 分页
  const handleSizeChange = (size: number) => {
    pageSize.value = size;
    pageNum.value = 1;
    handleQuery();
  };

  const handleCurrentChange = (page: number) => {
    pageNum.value = page;
    handleQuery();
  };

  // 列配置
  const columnConfigVisible = ref(false);
  const handleConfigSave = (newColumns: any[]) => {
    columns.value = newColumns;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(newColumns));
    ElMessage.success("配置已保存");
  };
  const handleConfigReset = () => {
    columns.value = JSON.parse(JSON.stringify(defaultColumns));
    localStorage.removeItem(STORAGE_KEY);
    ElMessage.success("已恢复默认配置");
  };

  onMounted(() => {
    handleQuery();
    loadTypeOptions();
  });

  return {
    loading,
    tableData,
    pageNum,
    pageSize,
    total,
    columns,
    tableColumns,
    selectedRows,
    columnConfigVisible,
    typeOptions,
    getStatusTag,
    getStatusType,
    handleQuery,
    handleQueryAndRefresh,
    handleSearch,
    handleReset,
    handleDelete,
    handleBatchDelete,
    handleSizeChange,
    handleCurrentChange,
    handleConfigSave,
    handleConfigReset,
  };
}
