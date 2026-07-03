/**
 * 数据采集类目 API（CrawlerCategory）：分页 / 文件下载 / 表单维护。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 类目分页查询参数。 */
export interface CategoryPageQuery extends PageQuery {
  keywords?: string;
  site?: string;
}

/** 类目 VO。 */
export interface CategoryVO {
  id?: string;
  name?: string;
  category_id?: string;
  site?: string;
  category_type?: string;
  status?: number;
}

/** 类目表单。 */
export interface CategoryForm {
  id?: string;
  name?: string;
  category_id?: string;
  site?: string;
  category_type?: string;
  status?: number;
}

const CATEGORY_BASE_URL = "/crawler/category";

export const CategoryAPI = {
  /**
   * 分页查询类目列表。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: Record<string, unknown>) {
    return request<any, PageResult<CategoryVO[]>>({
      url: `${CATEGORY_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  /**
   * 获取类目编辑表单。
   *
   * @param id - 类目ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, CategoryForm>({ url: `${CATEGORY_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 获取类目采集时段列表。
   *
   * @param id - 类目ID。
   * @returns 时段数据。
   */
  getTimes(id: string) {
    return request<any, { list: { index: number; name: string }[]; all: string[] }>({
      url: `${CATEGORY_BASE_URL}/${id}/times`,
      method: "get",
    });
  },
  /**
   * 检查类目文件是否存在。
   *
   * @param id - 类目ID。
   * @param time - 时段标识。
   * @returns 文件状态。
   */
  checkFile(id: string, time: string) {
    return request<
      any,
      { exists?: boolean; error_msg?: string; viewUrl?: string; downloadUrl?: string }
    >({
      url: `${CATEGORY_BASE_URL}/${id}/file/check`,
      method: "get",
      params: { time },
    });
  },
  /**
   * 下载类目文件。
   *
   * @param id - 类目ID。
   * @param time - 时段标识。
   * @returns Blob 文件流。
   */
  downloadFile(id: string, time: string) {
    return request<any, Blob>({
      url: `${CATEGORY_BASE_URL}/${id}/file`,
      method: "get",
      params: { time },
      responseType: "blob",
    });
  },
  /**
   * 创建类目。
   *
   * @param data - 表单数据。
   */
  create(data: CategoryForm) {
    return request({ url: `${CATEGORY_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新类目。
   *
   * @param id - 类目ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: CategoryForm) {
    return request({ url: `${CATEGORY_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除类目。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${CATEGORY_BASE_URL}/${ids}`, method: "delete" });
  },
};
