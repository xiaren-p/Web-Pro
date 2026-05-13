/**
 * 销售-商品 Listing API：分页查询、批量打标签 / 分类。
 */
import request from "@/utils/request";
import type { ListingItemVO } from "@/api/sales/listing.types";

export type { ListingItemVO };

export const SalesProductListingAPI = {
  getPage(params: any) {
    return request<{ total: number; data: ListingItemVO[] }, any>({
      url: "/sales/product/listing",
      method: "get",
      params,
    });
  },
  upsertLabels(data: { asin: string; tags: string[] } | { asin: string; tags: string[] }[]) {
    return request<any>({
      url: "/sales/product/listing/labels/upsert",
      method: "post",
      data,
    });
  },
  upsertAssort(data: { asin: string; assort: string } | { asin: string; assort: string }[]) {
    return request<any>({
      url: "/sales/product/listing/assort/upsert",
      method: "post",
      data,
    });
  },
  upsertRemark(data: { listing_id: string; remark: string }) {
    return request<any>({
      url: "/sales/product/listing/remark/upsert",
      method: "post",
      data,
    });
  },
};
