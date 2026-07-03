/**
 * 部门管理列表页业务逻辑 composable。
 *
 * @module useDeptList
 * @description 封装部门树查询、权限判断（公司管理员/部门管理员）、子孙部门收集、删除（含 NC 警告）。
 */

import { ref, reactive, computed } from "vue";
import { useUserStore } from "@/store/modules/user-store";
import { DeptAPI, type DeptVO, type DeptQuery } from "@/api/dept";

export function useDeptList() {
  const userStore = useUserStore();

  /** 是否为公司管理员（含超管）。 */
  const isCompanyAdmin = computed(() => userStore.userInfo.roles?.includes("ROOT") ?? false);

  /** 是否为部门管理员。 */
  const isDeptAdmin = computed(() => userStore.userInfo.roles?.includes("dept_admin") ?? false);

  /** 当前用户所属部门 ID。 */
  const myDeptId = computed(() => userStore.userInfo.deptId ?? null);

  /** 当前用户所属部门 ID（字符串，与 DeptVO.id 类型对齐）。 */
  const myDeptIdStr = computed<string | null>(() =>
    myDeptId.value != null ? String(myDeptId.value) : null
  );

  /**
   * 递归收集节点树中所有子孙 ID。
   *
   * @param children - 当前层子节点列表。
   * @param result - 收集结果集合。
   */
  function addAllDescendants(children: DeptVO[] | undefined, result: Set<string>): void {
    children?.forEach((c) => {
      result.add(String(c.id));
      addAllDescendants(c.children, result);
    });
  }

  /**
   * 在节点树中找到目标节点，递归收集其全部子孙 ID（不含自身）。
   *
   * @param nodes - 当前层节点列表。
   * @param targetId - 目标父节点 ID。
   * @param result - 收集结果集合。
   * @returns 是否已找到目标节点。
   */
  function collectDescendantIds(nodes: DeptVO[], targetId: string, result: Set<string>): boolean {
    for (const node of nodes) {
      if (String(node.id) === targetId) {
        addAllDescendants(node.children, result);
        return true;
      }
      if (node.children && collectDescendantIds(node.children, targetId, result)) return true;
    }
    return false;
  }

  /** 当前用户所属部门的全部子孙部门 ID 集合（不含本级）。 */
  const myDeptDescendantIds = computed<Set<string>>(() => {
    const result = new Set<string>();
    if (!isDeptAdmin.value || !myDeptIdStr.value || !deptList.value) return result;
    collectDescendantIds(deptList.value, myDeptIdStr.value, result);
    return result;
  });

  /** 表格加载状态。 */
  const isLoading = ref(false);

  /** 表格勾选行 ID 集合。 */
  const selectedIds = ref<string[]>([]);

  /** 查询参数。 */
  const queryParams = reactive<DeptQuery>({ pageNum: 1, pageSize: 10 });

  /** 部门树数据。 */
  const deptList = ref<DeptVO[]>();

  /** 查询部门列表。 */
  function handleQuery() {
    isLoading.value = true;
    DeptAPI.getList(queryParams).then((data) => {
      deptList.value = data;
      isLoading.value = false;
    });
  }

  /** 表格选中项变化回调。 */
  function handleSelectionChange(selection: DeptVO[]) {
    selectedIds.value = selection.map((item) => String(item.id));
  }

  /**
   * 删除部门（单个或批量）。
   *
   * @param deptId - 单个部门ID，不传则删除勾选项。
   * @param onBeforeRefresh - 删除成功后刷新前的回调（用于表单重置）。
   */
  function handleDelete(deptId?: string, onBeforeRefresh?: () => void) {
    const deptIds = deptId || selectedIds.value.join(",");

    if (!deptIds) {
      ElMessage.warning("请勾选删除项");
      return;
    }

    ElMessageBox.confirm(
      `<div style="font-size:14px;line-height:1.7;color:#303133">
        <p style="margin:0 0 12px;font-weight:600;font-size:15px">确认删除所选部门？此操作不可撤销。</p>
        <div style="border-top:1px solid #ebeef5;margin-bottom:12px"></div>
        <p style="margin:0 0 8px;font-weight:600;color:#606266">Nextcloud 同步影响</p>
        <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px">
          <div style="display:flex;align-items:flex-start;gap:8px">
            <span style="color:#f56c6c;font-size:15px;flex-shrink:0;margin-top:1px">x</span>
            <span>部门对应的 NC 群组将被<b>立即删除</b></span>
          </div>
          <div style="display:flex;align-items:flex-start;gap:8px">
            <span style="color:#f56c6c;font-size:15px;flex-shrink:0;margin-top:1px">x</span>
            <span>所有成员将<b>即刻失去</b>部门文件夹的访问权限</span>
          </div>
          <div style="display:flex;align-items:flex-start;gap:8px">
            <span style="color:#67c23a;font-size:15px;flex-shrink:0;margin-top:1px">OK</span>
            <span>部门文件夹及文件<b>不会被删除</b>，保留为孤立状态</span>
          </div>
        </div>
        <div style="background:#fffbe6;border:1px solid #ffe58f;border-radius:6px;padding:10px 12px;color:#8a6d00;font-size:13px;line-height:1.6">
          * 建议删除前先在 Nextcloud 中备份或迁移文件夹内的数据
        </div>
      </div>`,
      "删除部门警告",
      {
        confirmButtonText: "我已知晓，确认删除",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: true,
        confirmButtonClass: "el-button--danger",
      }
    ).then(
      () => {
        isLoading.value = true;
        DeptAPI.deleteByIds(deptIds)
          .then(() => {
            ElMessage.success("删除成功");
            onBeforeRefresh?.();
            handleQuery();
          })
          .finally(() => (isLoading.value = false));
      },
      () => {
        ElMessage.info("已取消删除");
      }
    );
  }

  return {
    isCompanyAdmin,
    isDeptAdmin,
    myDeptIdStr,
    myDeptDescendantIds,
    isLoading,
    selectedIds,
    queryParams,
    deptList,
    handleQuery,
    handleSelectionChange,
    handleDelete,
  };
}
