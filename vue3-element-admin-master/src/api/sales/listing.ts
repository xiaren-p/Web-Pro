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
  upsertLabels(
    data:
      | {
          id: number;
          asin: string;
          tags: { globalTagId: string; tagName: string; color: string }[];
        }
      | {
          id: number;
          asin: string;
          tags: { globalTagId: string; tagName: string; color: string }[];
        }[]
  ) {
    return request<any>({
      url: "/sales/product/listing/labels/upsert",
      method: "post",
      data,
    });
  },
  upsertAssort(
    data:
      | { id: number; asin: string; assort: string }
      | { id: number; asin: string; assort: string }[]
  ) {
    return request<any>({
      url: "/sales/product/listing/assort/upsert",
      method: "post",
      data,
    });
  },
  upsertRemark(data: { listing_id: number; remark: string }) {
    return request<any>({
      url: "/sales/product/listing/remark/upsert",
      method: "post",
      data,
    });
  },
};
