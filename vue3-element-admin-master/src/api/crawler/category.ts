/**
 * 数据采集类目 API（CrawlerCategory）：分页 / 文件下载 / 表单维护。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface CategoryPageQuery extends PageQuery {
  keywords?: string;
  site?: string;
}

export interface CategoryVO {
  id?: string;
  name?: string;
  category_id?: string;
  site?: string;
  category_type?: string;
  status?: number;
}

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
  getPage(params: any) {
    return request<any, PageResult<CategoryVO[]>>({
      url: `${CATEGORY_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, CategoryForm>({ url: `${CATEGORY_BASE_URL}/${id}/form`, method: "get" });
  },
  getTimes(id: string) {
    return request<any, { list: { index: number; name: string }[]; all: string[] }>({
      url: `${CATEGORY_BASE_URL}/${id}/times`,
      method: "get",
    });
  },
  checkFile(id: string, time: string) {
    return request<
      any,
      { exists?: boolean; error_msg?: string; viewUrl?: string; downloadUrl?: string }
    >({ url: `${CATEGORY_BASE_URL}/${id}/file/check`, method: "get", params: { time } });
  },
  downloadFile(id: string, time: string) {
    return request<any, Blob>({
      url: `${CATEGORY_BASE_URL}/${id}/file`,
      method: "get",
      params: { time },
      responseType: "blob",
    });
  },
  create(data: CategoryForm) {
    return request({ url: `${CATEGORY_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: CategoryForm) {
    return request({ url: `${CATEGORY_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${CATEGORY_BASE_URL}/${ids}`, method: "delete" });
  },
};
