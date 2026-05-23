/**
 * 菜单相关 API：菜单树 / 路由表 / 表单维护。
 */
import request from "@/utils/request";

export interface Meta {
  alwaysShow?: boolean;
  hidden?: boolean;
  icon?: string;
  keepAlive?: boolean;
  title?: string;
}

export interface RouteVO {
  children?: RouteVO[];
  component?: string;
  meta?: Meta;
  name?: string;
  path?: string;
  redirect?: string;
}

export interface MenuQuery {
  keywords?: string;
}

export interface MenuVO {
  id?: string;
  parentId?: string;
  name?: string;
  type?: number;
  routeName?: string;
  path?: string;
  component?: string;
  perms?: string;
  icon?: string;
  sort?: number;
  visible?: number;
  status?: number;
  children?: MenuVO[];
}

export interface MenuForm {
  id?: string;
  parentId?: string;
  name?: string;
  type?: number;
  routeName?: string;
  path?: string;
  component?: string;
  perms?: string;
  icon?: string;
  sort?: number;
  visible?: number;
  status?: number;
}

const MENU_BASE_URL = "/menus";

/** 过滤 undefined 字段，避免覆盖后端默认值。 */
function mapToBackend(data: MenuForm) {
  const payload: any = {};
  const keys: Array<keyof MenuForm> = [
    "name",
    "parentId",
    "type",
    "routeName",
    "path",
    "component",
    "perms",
    "icon",
    "sort",
    "visible",
    "status",
  ];
  for (const k of keys) {
    if (data[k] !== undefined) payload[k] = data[k];
  }
  return payload;
}

export const MenuAPI = {
  getRoutes() {
    return request<any, RouteVO[]>({ url: `${MENU_BASE_URL}/routes`, method: "get" });
  },
  getList(queryParams: MenuQuery) {
    return request<any, MenuVO[]>({
      url: `${MENU_BASE_URL}`,
      method: "get",
      params: queryParams,
    });
  },
  getTree() {
    return request<any, MenuVO[]>({ url: `${MENU_BASE_URL}/tree`, method: "get" });
  },
  getOptions(onlyParent?: boolean) {
    return request<any, any[]>({
      url: `${MENU_BASE_URL}/options`,
      method: "get",
      params: { onlyParent },
    });
  },

  /**
   * 获取当前登录用户有权分配的菜单选项树（用于岗位权限分配）。
   * 超级管理员返回全量，普通管理员仅返回自身岗位权限范围内的菜单。
   *
   * @returns 菜单选项树数组
   */
  getAssignableOptions() {
    return request<any, any[]>({
      url: `${MENU_BASE_URL}/options`,
      method: "get",
      params: { scope: "assignable" },
    });
  },
  getFormData(id: string) {
    return request<any, MenuForm>({ url: `${MENU_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: MenuForm) {
    return request({ url: `${MENU_BASE_URL}`, method: "post", data: mapToBackend(data) });
  },
  update(id: string, data: MenuForm) {
    return request({ url: `${MENU_BASE_URL}/${id}`, method: "put", data: mapToBackend(data) });
  },
  deleteById(id: string) {
    return request({ url: `${MENU_BASE_URL}/${id}`, method: "delete" });
  },
};
