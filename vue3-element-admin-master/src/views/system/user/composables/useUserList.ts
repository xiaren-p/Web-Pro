/**
 * 用户管理列表页业务逻辑 composable。
 *
 * @module useUserList
 * @description 封装查询、分页、删除、重置密码、权限判断等全部业务状态与方法。
 *              视图层仅负责模板编排、DeptTree 集成和模板引用（formRef/drawerRef）的传递。
 */

import { ref, reactive } from "vue";
import { UserAPI, type UserPageQuery, type UserPageVO, type UserInfo } from "@/api/user";
import { useUserStore } from "@/store";

export function useUserList() {
  const userStore = useUserStore();

  /** 表格加载状态。 */
  const isLoading = ref(false);

  /** 查询参数。 */
  const queryParams = reactive<UserPageQuery>({
    pageNum: 1,
    pageSize: 10,
  });

  /** 表格当前页数据。 */
  const pageData = ref<UserPageVO[]>();

  /** 表格数据总条数。 */
  const total = ref(0);

  /** 表格勾选行 ID 集合。 */
  const selectedIds = ref<string[]>([]);

  /**
   * 判断当前用户是否有权限对目标用户执行写操作（编辑、删除、重置密码）。
   *
   * @description
   * - COMPANY_ADMIN（1）或未知级别：全权访问。
   * - DEPT_ADMIN（2）：仅允许操作与自身 deptId 相同的用户；后端负责子部门授权。
   * - MEMBER（3）：无写权。
   * @param row - 目标用户行数据。
   * @returns 是否允许对该用户执行写操作。
   */
  function canWriteUser(row: UserPageVO): boolean {
    const { adminLevel, deptId } = userStore.userInfo as UserInfo;
    if (!adminLevel || adminLevel === 1) return true;
    if (adminLevel === 3) return false;
    return !!deptId && row.deptId === deptId;
  }

  /**
   * 获取用户列表分页数据。
   */
  async function fetchData() {
    isLoading.value = true;
    try {
      const data = await UserAPI.getPage(queryParams);
      pageData.value = data.list;
      total.value = data.total;
    } finally {
      isLoading.value = false;
    }
  }

  /**
   * 查询（重置页码后获取数据）。
   */
  function handleQuery() {
    queryParams.pageNum = 1;
    fetchData();
  }

  /**
   * 表格选中项变化回调。
   *
   * @param selection - 当前选中的行数据列表。
   */
  function handleSelectionChange(selection: UserPageVO[]) {
    selectedIds.value = selection.map((item) => item.id);
  }

  /**
   * 重置用户密码。
   *
   * @param row - 目标用户行数据。
   */
  function handleResetPassword(row: UserPageVO) {
    ElMessageBox.prompt("请输入用户【" + row.username + "】的新密码", "重置密码", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
    }).then(
      ({ value }) => {
        if (!value || value.length < 6) {
          ElMessage.warning("密码至少需要6位字符，请重新输入");
          return false;
        }
        UserAPI.resetPassword(row.id, value)
          .then(() => {
            ElMessage.success("密码重置成功，新密码是：" + value);
          })
          .catch(() => {
            ElMessage.error("重置密码失败，请稍后重试");
          });
      },
      () => {
        ElMessage.info("已取消重置密码");
      }
    );
  }

  /**
   * 检查删除操作是否包含当前登录用户。
   *
   * @param singleId - 单个删除的用户ID（不传则为批量删除）。
   * @param currentUserInfo - 当前用户信息。
   * @returns 是否包含当前用户。
   */
  function isDeletingCurrentUser(singleId?: string, currentUserInfo?: UserInfo): boolean {
    if (!currentUserInfo?.userId) return false;
    if (singleId && singleId === currentUserInfo.userId.toString()) return true;
    if (!singleId && selectedIds.value.length > 0) {
      return selectedIds.value.map(String).includes(String(currentUserInfo.userId));
    }
    return false;
  }

  /**
   * 删除用户（单个或批量）。
   *
   * @param id - 用户ID（不传则使用已选中的ID列表）。
   * @param onSuccessRefresh - 删除成功后刷新列表前的回调（用于表单重置等）。
   */
  function handleDelete(id?: string, onSuccessRefresh?: () => void) {
    const userIds = id || selectedIds.value.join(",");
    if (!userIds) {
      ElMessage.warning("请勾选删除项");
      return;
    }

    const currentUserInfo = userStore.userInfo as UserInfo;
    if (isDeletingCurrentUser(id, currentUserInfo)) {
      ElMessage.error("不能删除当前登录用户");
      return;
    }

    ElMessageBox.confirm("确认删除用户?", "警告", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).then(
      () => {
        isLoading.value = true;
        UserAPI.deleteByIds(userIds)
          .then(() => {
            ElMessage.success("删除成功");
            onSuccessRefresh?.();
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

  return {
    isLoading,
    queryParams,
    pageData,
    total,
    selectedIds,
    canWriteUser,
    fetchData,
    handleQuery,
    handleSelectionChange,
    handleResetPassword,
    handleDelete,
  };
}
