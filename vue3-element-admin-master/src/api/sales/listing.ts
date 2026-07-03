/**
 * 销售-商品 Listing API：分页查询、批量打标签 / 分类。
 */
import request from "@/utils/request";
import type { ListingItemVO } from "@/api/sales/listing.types";

export type { ListingItemVO };

export const SalesProductListingAPI = {
  /**
   * 分页查询商品 Listing。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: Record<string, unknown>) {
    return request<{ total: number; data: ListingItemVO[] }, any>({
      url: "/sales/product/listing", method: "get", params,
    });
  },
  /**
   * 批量新增或更新标签。
   *
   * @param data - 标签数据（单条或数组）。
   */
  upsertLabels(
    data:
      | { id: number; asin: string; tags: { globalTagId: string; tagName: string; color: string }[] }
      | { id: number; asin: string; tags: { globalTagId: string; tagName: string; color: string }[] }[]
  ) {
    return request<any>({ url: "/sales/product/listing/labels/upsert", method: "post", data });
  },
  /**
   * 批量新增或更新分类。
   *
   * @param data - 分类数据（单条或数组）。
   */
  upsertAssort(
    data: { id: number; asin: string; assort: string } | { id: number; asin: string; assort: string }[]
  ) {
    return request<any>({ url: "/sales/product/listing/assort/upsert", method: "post", data });
  },
  /**
   * 新增或更新备注。
   *
   * @param data - 备注数据（listing_id + remark）。
   */
  upsertRemark(data: { listing_id: number; remark: string }) {
    return request<any>({ url: "/sales/product/listing/remark/upsert", method: "post", data });
  },
};
