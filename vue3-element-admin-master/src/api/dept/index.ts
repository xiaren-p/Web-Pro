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
  /** 获取部门列表（支持关键字/状态筛选）。 */
  getList(params: DeptQuery) {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}`, method: "get", params });
  },
  /** 获取部门下拉选项。 */
  getOptions() {
    return request<any, any[]>({ url: `${DEPT_BASE_URL}/options`, method: "get" });
  },
  /** 获取部门树形结构。 */
  getTree() {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}/tree`, method: "get" });
  },
  /** 获取部门编辑表单数据。 */
  getFormData(id: string) {
    return request<any, DeptForm>({ url: `${DEPT_BASE_URL}/${id}/form`, method: "get" });
  },
  /** 创建部门。 */
  create(data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}`, method: "post", data });
  },
  /** 更新部门。 */
  update(id: string, data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}/${id}`, method: "put", data });
  },
  /** 批量删除部门（逗号分隔 ID）。 */
  deleteByIds(ids: string) {
    return request({ url: `${DEPT_BASE_URL}/${ids}`, method: "delete" });
  },
};
