/**
 * 销售-Listing 标签管理 API：分页查询、新增、编辑、删除、状态切换。
 */
import request from "@/utils/request";
import type { PageQuery } from "@/api/common/page";

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

export interface ListingTagQuery extends PageQuery {
  tagName?: string;
  type?: string;
  status?: string;
  createByName?: string;
  "type[]"?: string[];
  "status[]"?: string[];
}

export interface ListingTagForm {
  id?: number;
  tagName: string;
  type: string;
  color: string;
}

const LISTING_TAG_BASE_URL = "/sales/listing/tags";

export const ListingTagAPI = {
  getPage(params: ListingTagQuery) {
    return request<any, { total: number; data: ListingTagVO[] }>({
      url: LISTING_TAG_BASE_URL,
      method: "get",
      params,
    });
  },
  getDetail(id: number) {
    return request<ListingTagVO>({
      url: `${LISTING_TAG_BASE_URL}/${id}`,
      method: "get",
    });
  },
  create(data: ListingTagForm) {
    return request<any>({
      url: LISTING_TAG_BASE_URL,
      method: "post",
      data,
    });
  },
  update(id: number, data: ListingTagForm) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/${id}`,
      method: "put",
      data,
    });
  },
  delete(id: number) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/${id}`,
      method: "delete",
    });
  },
  batchDelete(ids: number[]) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/batch-delete`,
      method: "post",
      data: { ids },
    });
  },
  updateStatus(id: number, status: string) {
    return request<any>({
      url: `${LISTING_TAG_BASE_URL}/${id}/status`,
      method: "put",
      data: { status },
    });
  },
  getTypeOptions() {
    return request<any, string[]>({
      url: `${LISTING_TAG_BASE_URL}/type-options`,
      method: "get",
    });
  },
};
