/**
 * 菜单管理列表页业务逻辑 composable。
 */

import { ref, reactive } from "vue";
import { MenuAPI, type MenuQuery, type MenuVO } from "@/api/menu";

export function useMenuList() {
  const isLoading = ref(false);
  const queryParams = reactive<MenuQuery>({});
  const menuTableData = ref<MenuVO[]>([]);
  const selectedMenuId = ref<string | undefined>();

  function handleQuery() {
    isLoading.value = true;
    MenuAPI.getTree(queryParams)
      .then((data) => {
        menuTableData.value = data;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  function handleRowClick(row: MenuVO) {
    selectedMenuId.value = row.id;
  }

  function handleDelete(menuId: string) {
    if (!menuId) {
      ElMessage.warning("请勾选删除项");
      return;
    }
    ElMessageBox.confirm("确认删除已选中的数据项?", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(
      () => {
        isLoading.value = true;
        MenuAPI.deleteById(menuId)
          .then(() => {
            ElMessage.success("删除成功");
            handleQuery();
          })
          .finally(() => {
            isLoading.value = false;
          });
      },
      () => {
        ElMessage.info("已取消删除");
      }
    );
  }

  return {
    isLoading,
    queryParams,
    menuTableData,
    selectedMenuId,
    handleQuery,
    handleRowClick,
    handleDelete,
  };
}
