/**
 * 刊登管理 - 商品类型 Schema API。
 *
 * 后端路由：GET /api/v1/sales/product-type-schema
 * 后端已预处理 properties / properties_zh，返回 fields / fieldsZh / requiredFields / defaultFields。
 */
import request from "@/utils/request";
import type { ProductTypeSchemaVO, ProductTypeSchemaQuery } from "./types";

export type { ProductTypeSchemaVO, ProductTypeSchemaQuery, SchemaFieldDef } from "./types";

export const ListingPublishAPI = {
  /**
   * 获取商品类型 JSON Schema（后端已解析）。
   *
   * @param params - 查询参数（marketplaceId + productTypeOrigin）。
   * @returns 解析后的 Schema 数据，含 fields / fieldsZh / requiredFields / defaultFields。
   */
  getProductTypeSchema(params: ProductTypeSchemaQuery) {
    return request<ProductTypeSchemaVO, any>({
      url: "/sales/product-type-schema",
      method: "get",
      params,
    });
  },
};
