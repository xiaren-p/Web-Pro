/**
 * 角色 API：分页查询、增删改、菜单授权。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface RolePageQuery extends PageQuery {
  keywords?: string;
}

export interface RolePageVO {
  id: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
}

export interface RoleForm {
  id?: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
  dataScope?: number;
}

const ROLE_BASE_URL = "/roles";

export const RoleAPI = {
  getPage(params: RolePageQuery) {
    return request<any, PageResult<RolePageVO[]>>({
      url: `${ROLE_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getOptions() {
    return request<any, any[]>({ url: `${ROLE_BASE_URL}/options`, method: "get" });
  },
  getFormData(id: string) {
    return request<any, RoleForm>({ url: `${ROLE_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: RoleForm) {
    return request({ url: `${ROLE_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: RoleForm) {
    return request({ url: `${ROLE_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${ROLE_BASE_URL}/${ids}`, method: "delete" });
  },
  getMenuIds(roleId: string) {
    return request<any, string[]>({ url: `${ROLE_BASE_URL}/${roleId}/menuIds`, method: "get" });
  },
  saveMenus(roleId: string, menuIds: Array<string | number>) {
    return request({ url: `${ROLE_BASE_URL}/${roleId}/menus`, method: "put", data: menuIds });
  },
  getRoleMenuIds(roleId: string) {
    return this.getMenuIds(roleId);
  },
  updateRoleMenus(roleId: string, menuIds: Array<string | number>) {
    return this.saveMenus(roleId, menuIds);
  },
};
