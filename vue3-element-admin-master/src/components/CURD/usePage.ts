import { ref } from "vue";
import type { IObject, PageContentInstance, PageModalInstance, PageSearchInstance } from "./types";

/**
 * CURD 页面编排 Composable。
 *
 * 统一管理搜索表单、数据表格、新增/编辑弹窗的引用与交互流程，
 * 供系统管理类页面（User/Dept/Menu/Position 等）复用标准 CRUD 操作。
 *
 * @returns 搜索/表格/弹窗的响应式引用与控制方法。
 */
function usePage() {
  const searchRef = ref<PageSearchInstance>();
  const contentRef = ref<PageContentInstance>();
  const addModalRef = ref<PageModalInstance>();
  const editModalRef = ref<PageModalInstance>();

  /** 搜索按钮点击：触发数据表格重新加载。 */
  function handleQueryClick(queryParams: IObject) {
    const filterParams = contentRef.value?.getFilterParams();
    contentRef.value?.fetchPageData({ ...queryParams, ...filterParams }, true);
  }
  /** 重置按钮点击：重置搜索条件并重新加载数据。 */
  function handleResetClick(queryParams: IObject) {
    const filterParams = contentRef.value?.getFilterParams();
    contentRef.value?.fetchPageData({ ...queryParams, ...filterParams }, true);
  }
  /** 新增按钮点击：打开新增弹窗。 */
  function handleAddClick(RefImpl?: Ref<PageModalInstance>) {
    if (RefImpl) {
      RefImpl?.value.setModalVisible();
      RefImpl?.value.handleDisabled(false);
    } else {
      addModalRef.value?.setModalVisible();
      addModalRef.value?.handleDisabled(false);
    }
  }
  /**
   * 编辑按钮点击：打开编辑弹窗并回填表单数据。
   *
   * @param row - 当前行数据。
   * @param callback - 可选，获取表单回填数据的异步回调，用于 API 获取详情。
   * @param RefImpl - 可选，外部传入的弹窗实例 ref（用于非默认弹窗场景）。
   */
  async function handleEditClick(
    row: IObject,
    callback?: (result?: IObject) => IObject,
    RefImpl?: Ref<PageModalInstance>
  ) {
    if (RefImpl) {
      RefImpl.value?.setModalVisible();
      RefImpl.value?.handleDisabled(false);
      const from = await (callback?.(row) ?? Promise.resolve(row));
      RefImpl.value?.setFormData(from ? from : row);
    } else {
      editModalRef.value?.setModalVisible();
      editModalRef.value?.handleDisabled(false);
      const from = await (callback?.(row) ?? Promise.resolve(row));
      editModalRef.value?.setFormData(from ? from : row);
    }
  }
  // 查看
  async function handleViewClick(
    row: IObject,
    callback?: (result?: IObject) => IObject,
    RefImpl?: Ref<PageModalInstance>
  ) {
    if (RefImpl) {
      RefImpl.value?.setModalVisible();
      RefImpl.value?.handleDisabled(true);
      const from = await (callback?.(row) ?? Promise.resolve(row));
      RefImpl.value?.setFormData(from ? from : row);
    } else {
      editModalRef.value?.setModalVisible();
      editModalRef.value?.handleDisabled(true);
      const from = await (callback?.(row) ?? Promise.resolve(row));
      editModalRef.value?.setFormData(from ? from : row);
    }
  }
  // 表单提交
  function handleSubmitClick() {
    //根据检索条件刷新列表数据
    const queryParams = searchRef.value?.getQueryParams();
    contentRef.value?.fetchPageData(queryParams, true);
  }
  // 导出
  function handleExportClick() {
    // 根据检索条件导出数据
    const queryParams = searchRef.value?.getQueryParams();
    contentRef.value?.exportPageData(queryParams);
  }
  // 搜索显隐
  function handleSearchClick() {
    searchRef.value?.toggleVisible();
  }
  // 涮选数据
  function handleFilterChange(filterParams: IObject) {
    const queryParams = searchRef.value?.getQueryParams();
    contentRef.value?.fetchPageData({ ...queryParams, ...filterParams }, true);
  }

  return {
    searchRef,
    contentRef,
    addModalRef,
    editModalRef,
    handleQueryClick,
    handleResetClick,
    handleAddClick,
    handleEditClick,
    handleViewClick,
    handleSubmitClick,
    handleExportClick,
    handleSearchClick,
    handleFilterChange,
  };
}

export default usePage;
