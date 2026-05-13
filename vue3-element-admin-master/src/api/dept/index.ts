/**
 * 部门 API：列表/树形/下拉/表单维护。
 */
import request from "@/utils/request";
import type { PageQuery } from "@/api/common/page";

export interface DeptQuery extends PageQuery {
  keywords?: string;
  status?: number;
}

export interface DeptVO {
  id: string;
  parentId?: string;
  name?: string;
  code?: string;
  status?: number;
  sort?: number;
  children?: DeptVO[];
}

export interface DeptForm {
  id?: string;
  parentId?: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
}

const DEPT_BASE_URL = "/depts";

export const DeptAPI = {
  getList(params: DeptQuery) {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}`, method: "get", params });
  },
  getOptions() {
    return request<any, any[]>({ url: `${DEPT_BASE_URL}/options`, method: "get" });
  },
  getTree() {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}/tree`, method: "get" });
  },
  getFormData(id: string) {
    return request<any, DeptForm>({ url: `${DEPT_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${DEPT_BASE_URL}/${ids}`, method: "delete" });
  },
};
