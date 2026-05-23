/**
 * 岗位管理 API：分页查询、增删改、菜单授权、下拉选项。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface PositionPageQuery extends PageQuery {
  keywords?: string;
  status?: number;
}

export interface PositionPageVO {
  id: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
  isBuiltin?: boolean;
  deptId?: number | null;
  deptName?: string | null;
}

export interface PositionForm {
  id?: string;
  name?: string;
  code?: string;
  sort?: number;
  status?: number;
  remark?: string;
  deptId?: number | null;
}

const POSITION_BASE_URL = "/positions";

export const PositionAPI = {
  /**
   * 分页查询岗位列表。
   *
   * @param params 查询参数
   * @returns 分页结果
   */
  getPage(params: PositionPageQuery) {
    return request<any, PageResult<PositionPageVO[]>>({
      url: `${POSITION_BASE_URL}/page`,
      method: "get",
      params,
    });
  },

  /**
   * 获取岗位下拉选项（用于用户表单中选择岗位）。
   *
   * @returns 选项数组 { value, label }
   */
  getOptions() {
    return request<any, OptionType[]>({ url: `${POSITION_BASE_URL}/options`, method: "get" });
  },

  /**
   * 获取岗位表单回显数据。
   *
   * @param id 岗位ID
   * @returns 岗位表单对象
   */
  getFormData(id: string) {
    return request<any, PositionForm>({ url: `${POSITION_BASE_URL}/${id}/form`, method: "get" });
  },

  /**
   * 新增岗位。
   *
   * @param data 岗位表单数据
   */
  create(data: PositionForm) {
    return request({ url: `${POSITION_BASE_URL}`, method: "post", data });
  },

  /**
   * 修改岗位。
   *
   * @param id 岗位ID
   * @param data 岗位表单数据
   */
  update(id: string, data: PositionForm) {
    return request({ url: `${POSITION_BASE_URL}/${id}`, method: "put", data });
  },

  /**
   * 批量删除岗位。
   *
   * @param ids 岗位ID，多个以逗号分隔
   */
  deleteByIds(ids: string) {
    return request({ url: `${POSITION_BASE_URL}/${ids}`, method: "delete" });
  },

  /**
   * 获取岗位已关联的菜单ID列表。
   *
   * @param positionId 岗位ID
   * @returns 菜单ID数组
   */
  getMenuIds(positionId: string) {
    return request<any, string[]>({
      url: `${POSITION_BASE_URL}/${positionId}/menuIds`,
      method: "get",
    });
  },

  /**
   * 保存岗位菜单权限。
   *
   * @param positionId 岗位ID
   * @param menuIds 菜单ID数组
   */
  saveMenus(positionId: string, menuIds: Array<string | number>) {
    return request({
      url: `${POSITION_BASE_URL}/${positionId}/menus`,
      method: "put",
      data: { menuIds },
    });
  },
};
