/**
 * 部门 API：列表/树形/下拉/表单维护。
 */
import request from "@/utils/request";
import type { PageQuery } from "@/api/common/page";

/** 部门查询参数。 */
export interface DeptQuery extends PageQuery {
  keywords?: string;
  status?: number;
}

/** 部门 VO（含子部门树）。 */
export interface DeptVO {
  id: string;
  parentId?: string;
  name?: string;
  code?: string;
  status?: number;
  sort?: number;
  children?: DeptVO[];
}

/** 部门表单数据。 */
export interface DeptForm {
  id?: string;
  parentId?: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
}

/** 部门下拉选项。 */
export interface DeptOption {
  value: string;
  label: string;
}

const DEPT_BASE_URL = "/depts";

export const DeptAPI = {
  /**
   * 获取部门列表（支持关键字/状态筛选）。
   *
   * @param params - 查询参数。
   * @returns 部门树列表。
   */
  getList(params: DeptQuery) {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}`, method: "get", params });
  },
  /**
   * 获取部门下拉选项。
   *
   * @returns 部门选项列表。
   */
  getOptions() {
    return request<any, DeptOption[]>({ url: `${DEPT_BASE_URL}/options`, method: "get" });
  },
  /**
   * 获取部门树形结构。
   *
   * @returns 部门树。
   */
  getTree() {
    return request<any, DeptVO[]>({ url: `${DEPT_BASE_URL}/tree`, method: "get" });
  },
  /**
   * 获取部门编辑表单数据。
   *
   * @param id - 部门ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, DeptForm>({ url: `${DEPT_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建部门。
   *
   * @param data - 部门表单数据。
   */
  create(data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新部门。
   *
   * @param id - 部门ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: DeptForm) {
    return request({ url: `${DEPT_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除部门（逗号分隔ID）。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${DEPT_BASE_URL}/${ids}`, method: "delete" });
  },
};
