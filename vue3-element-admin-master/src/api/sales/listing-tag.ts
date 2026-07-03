/**
 * 销售-Listing 标签管理 API：分页查询、新增、编辑、删除、状态切换。
 */
import request from "@/utils/request";
import type { PageQuery } from "@/api/common/page";

/** 标签 VO。 */
export interface ListingTagVO {
  id: number;
  globalTagId: string;
  tagName: string;
  type: string;
  color: string;
  createByName: string;
  modifyByName: string;
  status: string;
  createTime: string;
  updateTime: string;
}

/** 标签查询参数。 */
export interface ListingTagQuery extends PageQuery {
  tagName?: string;
  type?: string;
  status?: string;
  createByName?: string;
  "type[]"?: string[];
  "status[]"?: string[];
}

/** 标签表单。 */
export interface ListingTagForm {
  id?: number;
  tagName: string;
  type: string;
  color: string;
}

/** 标签下拉选项（精简字段，供选择器使用）。 */
export interface TagOption {
  globalTagId: string;
  tagName: string;
  color: string;
  type: string;
}

const LISTING_TAG_BASE_URL = "/sales/listing/tags";

export const ListingTagAPI = {
  /**
   * 分页查询标签列表。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: ListingTagQuery) {
    return request<any, { total: number; data: ListingTagVO[] }>({
      url: LISTING_TAG_BASE_URL,
      method: "get",
      params,
    });
  },
  /**
   * 获取标签详情。
   *
   * @param id - 标签ID。
   * @returns 标签数据。
   */
  getDetail(id: number) {
    return request<ListingTagVO>({ url: `${LISTING_TAG_BASE_URL}/${id}`, method: "get" });
  },
  /**
   * 创建标签。
   *
   * @param data - 标签表单。
   */
  create(data: ListingTagForm) {
    return request<any>({ url: LISTING_TAG_BASE_URL, method: "post", data });
  },
  /**
   * 更新标签。
   *
   * @param id - 标签ID。
   * @param data - 更新的数据。
   */
  update(id: number, data: ListingTagForm) {
    return request<any>({ url: `${LISTING_TAG_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 删除单个标签。
   *
   * @param id - 标签ID。
   */
  delete(id: number) {
    return request<any>({ url: `${LISTING_TAG_BASE_URL}/${id}`, method: "delete" });
  },
  /**
   * 批量删除标签。
   *
   * @param ids - ID数组。
   */
  batchDelete(ids: number[]) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/batch-delete`,
      method: "post",
      data: { ids },
    });
  },
  /**
   * 更新标签状态。
   *
   * @param id - 标签ID。
   * @param status - 目标状态。
   */
  updateStatus(id: number, status: string) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/${id}/status`,
      method: "put",
      data: { status },
    });
  },
  /**
   * 获取标签类型下拉选项。
   *
   * @returns 类型数组。
   */
  getTypeOptions() {
    return request<any, string[]>({ url: `${LISTING_TAG_BASE_URL}/type-options`, method: "get" });
  },
  /**
   * 获取 status=normal 的全量标签选项（供下拉选择器使用，不分页）。
   *
   * @returns 标签选项数组。
   */
  getOptions() {
    return request<any, TagOption[]>({ url: `${LISTING_TAG_BASE_URL}/options`, method: "get" });
  },
};
