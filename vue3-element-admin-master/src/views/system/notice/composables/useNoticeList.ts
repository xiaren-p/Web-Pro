/**
 * 通知公告列表页业务逻辑 composable。
 *
 * @module useNoticeList
 * @description 封装查询、删除、发布、撤回、导出等全部业务状态与方法。
 *              视图层仅负责模板编排和模板引用（formRef/dialogRef）的传递。
 */

import { ref, reactive } from "vue";
import { NoticeAPI, type NoticePageQuery, type NoticePageVO } from "@/api/notice";
import { useUserStoreHook } from "@/store/modules/user-store";

export interface ExportForm {
  type?: string;
  level?: string;
  publishStatus?: number;
  title?: string;
}

export function useNoticeList() {
  /** 通知公告表格加载状态。 */
  const isLoading = ref(false);

  /** 表格勾选行 ID 集合。 */
  const selectIds = ref<string[]>([]);

  /** 表格数据总条数。 */
  const total = ref(0);

  /** 查询参数。 */
  const queryParams = reactive<NoticePageQuery>({
    pageNum: 1,
    pageSize: 10,
  });

  /** 表格当前页数据。 */
  const pageData = ref<NoticePageVO[]>([]);

  /** 导出弹窗可见性。 */
  const exportDialogVisible = ref(false);

  /** 导出表单数据。 */
  const exportForm = reactive<ExportForm>({
    type: undefined,
    level: undefined,
    publishStatus: undefined,
    title: undefined,
  });

  /** 导出操作加载状态。 */
  const isExportLoading = ref(false);

  const userStore = useUserStoreHook();

  /**
   * 判断当前用户是否为管理员。
   *
   * @description 管理员可查看全部通知；非管理员仅查看分配给自己的。
   * @returns 是否具有管理员角色或权限。
   */
  function isAdminUser(): boolean {
    try {
      const roles = (userStore.userInfo && userStore.userInfo.roles) || [];
      const perms = (userStore.userInfo && (userStore.userInfo as any).perms) || [];
      const rs = roles.map((r: any) => String(r).toLowerCase());
      if (rs.includes("admin") || rs.includes("role_admin") || rs.includes("administrator"))
        return true;
      if (perms && Array.isArray(perms) && perms.includes("admin")) return true;
    } catch {
      // ignore and treat as non-admin
    }
    return false;
  }

  /**
   * 获取分页列表数据。
   *
   * @description 管理员调 getPage，非管理员由后端根据角色过滤。
   */
  function fetchData() {
    isLoading.value = true;
    NoticeAPI.getPage(queryParams)
      .then((data: any) => {
        pageData.value = data.list;
        total.value = data.total;
      })
      .finally(() => {
        isLoading.value = false;
      });
  }

  /**
   * 查询：重置页码后拉取数据。
   */
  function handleQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  /**
   * 表格选中行变化回调。
   *
   * @param selection - 当前选中的行数据列表。
   */
  function handleSelectionChange(selection: NoticePageVO[]) {
    selectIds.value = selection.map((item) => String(item.id));
  }

  /**
   * 发布通知公告。
   *
   * @param id - 通知ID。
   */
  function handlePublish(id: string) {
    NoticeAPI.publish(id).then(() => {
      ElMessage.success("发布成功");
      handleQuery();
    });
  }

  /**
   * 撤回通知公告。
   *
   * @param id - 通知ID。
   */
  function handleRevoke(id: string) {
    NoticeAPI.revoke(id).then(() => {
      ElMessage.success("撤回成功");
      handleQuery();
    });
  }

  /**
   * 删除通知公告（单个或批量）。
   *
   * @description 确认后删除，成功后重置查询条件并刷新列表。
   * @param id - 单个通知ID；不传则删除当前勾选项。
   * @param onBeforeRefresh - 删除成功后、刷新列表前执行的额外操作（如表单重置）。
   */
  function handleDelete(id?: string, onBeforeRefresh?: () => void) {
    const deleteIds = id || selectIds.value.join(",");
    if (!deleteIds) {
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
        NoticeAPI.deleteByIds(deleteIds)
          .then(() => {
            ElMessage.success("删除成功");
            onBeforeRefresh?.();
            queryParams.pageNum = 1;
            fetchData();
          })
          .finally(() => (isLoading.value = false));
      },
      () => {
        ElMessage.info("已取消删除");
      }
    );
  }

  /**
   * 打开导出数据弹窗并预填表单。
   *
   * @param currentTitle - 当前搜索标题，自动填入导出表单。
   */
  function openExportDialog(currentTitle?: string) {
    exportDialogVisible.value = true;
    exportForm.type = undefined;
    exportForm.level = undefined;
    exportForm.publishStatus = undefined;
    exportForm.title = currentTitle;
  }

  /** 关闭导出弹窗。 */
  function closeExportDialog() {
    exportDialogVisible.value = false;
  }

  /**
   * 执行导出操作。
   *
   * @description 调用后端导出接口，下载 xlsx 文件。
   *              非管理员仅导出当前用户可见项。
   */
  async function handleExport() {
    isExportLoading.value = true;
    try {
      console.log("[Debug] Start Export, NoticeAPI keys:", Object.keys(NoticeAPI));
      if (typeof (NoticeAPI as any).exportData !== "function") {
        throw new Error("NoticeAPI.exportData is not a function. Check @/api/notice update.");
      }
      const params: any = { ...exportForm };
      if (!isAdminUser()) params.onlyMine = true;
      const response: any = await (NoticeAPI as any).exportData(params);

      console.log("[Debug] Export response:", response);

      const blob = new Blob([response.data], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8",
      });
      const a = document.createElement("a");
      const href = window.URL.createObjectURL(blob);
      a.href = href;
      a.download = `通知公告_${new Date().getTime()}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(href);
      ElMessage.success("导出成功");
      closeExportDialog();
    } catch (err: any) {
      console.error("导出异常:", err);
      ElMessage.error("导出失败: " + (err.message || "未知错误"));
    } finally {
      isExportLoading.value = false;
    }
  }

  return {
    isLoading,
    selectIds,
    total,
    queryParams,
    pageData,
    exportDialogVisible,
    exportForm,
    isExportLoading,
    isAdminUser,
    fetchData,
    handleQuery,
    handleSelectionChange,
    handlePublish,
    handleRevoke,
    handleDelete,
    openExportDialog,
    closeExportDialog,
    handleExport,
  };
}
