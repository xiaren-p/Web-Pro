/**
 * 菜单相关 API：菜单树 / 路由表 / 表单维护。
 */
import request from "@/utils/request";

/** 路由元信息。 */
export interface Meta {
  alwaysShow?: boolean;
  hidden?: boolean;
  icon?: string;
  keepAlive?: boolean;
  title?: string;
}

/** 前端路由对象。 */
export interface RouteVO {
  children?: RouteVO[];
  component?: string;
  meta?: Meta;
  name?: string;
  path?: string;
  redirect?: string;
}

/** 菜单查询参数。 */
export interface MenuQuery {
  keywords?: string;
}

/** 菜单 VO（含子菜单树）。 */
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

/** 菜单表单数据。 */
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

/** 菜单下拉选项。 */
export interface MenuOption {
  value: string;
  label: string;
  children?: MenuOption[];
}

const MENU_BASE_URL = "/menus";

/** 过滤 undefined 字段，避免覆盖后端默认值。 */
function mapToBackend(data: MenuForm) {
  const payload: Record<string, unknown> = {};
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
  /**
   * 获取当前用户可见的动态路由树。
   *
   * @returns 路由树。
   */
  getRoutes() {
    return request<any, RouteVO[]>({ url: `${MENU_BASE_URL}/routes`, method: "get" });
  },
  /**
   * 获取菜单列表（支持关键字筛选）。
   *
   * @param queryParams - 查询参数。
   * @returns 菜单列表。
   */
  getList(queryParams: MenuQuery) {
    return request<any, MenuVO[]>({ url: `${MENU_BASE_URL}`, method: "get", params: queryParams });
  },
  /**
   * 获取菜单树形结构（支持关键字筛选）。
   *
   * @param params - 查询参数。
   * @returns 菜单树。
   */
  getTree(params?: MenuQuery) {
    return request<any, MenuVO[]>({ url: `${MENU_BASE_URL}/tree`, method: "get", params });
  },
  /**
   * 获取菜单下拉选项（可选仅父级）。
   *
   * @param onlyParent - 是否仅返回父级菜单。
   * @returns 菜单选项列表。
   */
  getOptions(onlyParent?: boolean) {
    return request<any, MenuOption[]>({
      url: `${MENU_BASE_URL}/options`,
      method: "get",
      params: { onlyParent },
    });
  },
  /**
   * 获取当前登录用户有权分配的菜单选项树（用于岗位权限分配）。
   * 超级管理员返回全量，普通管理员仅返回自身岗位权限范围内的菜单。
   *
   * @returns 菜单选项树。
   */
  getAssignableOptions() {
    return request<any, MenuOption[]>({
      url: `${MENU_BASE_URL}/options`,
      method: "get",
      params: { scope: "assignable" },
    });
  },
  /**
   * 获取菜单编辑表单数据。
   *
   * @param id - 菜单ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, MenuForm>({ url: `${MENU_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建菜单。
   *
   * @param data - 菜单表单数据。
   */
  create(data: MenuForm) {
    return request({ url: `${MENU_BASE_URL}`, method: "post", data: mapToBackend(data) });
  },
  /**
   * 更新菜单。
   *
   * @param id - 菜单ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: MenuForm) {
    return request({ url: `${MENU_BASE_URL}/${id}`, method: "put", data: mapToBackend(data) });
  },
  /**
   * 删除单个菜单。
   *
   * @param id - 菜单ID。
   */
  deleteById(id: string) {
    return request({ url: `${MENU_BASE_URL}/${id}`, method: "delete" });
  },
};
