/**
 * 岗位管理列表页业务逻辑 composable。
 *
 * @module usePositionList
 * @description 封装岗位分页查询、权限判断、删除（含内置岗位保护）、选中过滤。
 */

import { ref, reactive, computed } from "vue";
import { useUserStore } from "@/store/modules/user-store";
import { PositionAPI, type PositionPageVO, type PositionPageQuery } from "@/api/position";

export function usePositionList() {
  const userStore = useUserStore();

  /** 是否为公司管理员（含超管）。 */
  const isCompanyAdmin = computed(() => userStore.userInfo.roles?.includes("ROOT") ?? false);

  /** 是否为部门管理员。 */
  const isDeptAdmin = computed(() => userStore.userInfo.roles?.includes("dept_admin") ?? false);

  /** 表格加载状态。 */
  const isLoading = ref(false);

  /** 表格勾选行 ID 集合（自动排除内置岗位）。 */
  const selectedIds = ref<string[]>([]);

  /** 表格数据总条数。 */
  const total = ref(0);

  /** 查询参数。 */
  const queryParams = reactive<PositionPageQuery>({ pageNum: 1, pageSize: 10 });

  /** 岗位表格数据。 */
  const positionList = ref<PositionPageVO[]>();

  /** 获取分页数据。 */
  function fetchData() {
    isLoading.value = true;
    PositionAPI.getPage(queryParams)
      .then((data) => {
        positionList.value = data.list;
        total.value = data.total;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  /** 查询（重置页码后获取数据）。 */
  function handleQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  /** 表格选中项变化（自动排除内置岗位）。 */
  function handleSelectionChange(selection: PositionPageVO[]) {
    selectedIds.value = selection.filter((item) => !item.isBuiltin).map((item) => item.id);
  }

  /**
   * 删除岗位（单个或批量）。
   *
   * @param positionId - 单个岗位ID，不传则删除勾选项。
   * @param onBeforeRefresh - 删除成功后刷新前的回调。
   */
  function handleDelete(positionId?: string, onBeforeRefresh?: () => void) {
    const positionIds = positionId ? positionId : selectedIds.value.join(",");
    if (!positionIds) {
      ElMessage.warning("请勾选需要删除的非内置岗位");
      return;
    }

    ElMessageBox.confirm("确认删除已选中的数据项？", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(() => {
      isLoading.value = true;
      PositionAPI.deleteByIds(positionIds)
        .then(() => {
          ElMessage.success("删除成功");
          onBeforeRefresh?.();
          queryParams.pageNum = 1;
          fetchData();
        })
        .finally(() => {
          isLoading.value = false;
        });
    });
  }

  return {
    isCompanyAdmin,
    isDeptAdmin,
    isLoading,
    selectedIds,
    total,
    queryParams,
    positionList,
    fetchData,
    handleQuery,
    handleSelectionChange,
    handleDelete,
  };
}
