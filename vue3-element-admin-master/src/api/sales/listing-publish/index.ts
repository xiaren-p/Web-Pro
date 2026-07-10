/**
 * 刊登管理 - API 模块（商品类型 Schema + Amazon 分类 + 店铺）。
 *
 * 后端路由前缀：GET /api/v1/sales/...
 */
import request from "@/utils/request";
import type {
  ProductTypeSchemaVO,
  ProductTypeSchemaQuery,
  AmazonCategoryVO,
  CategorySearchType,
  ShopOptionVO,
} from "./types";

export type {
  ProductTypeSchemaVO,
  ProductTypeSchemaQuery,
  SchemaFieldDef,
  AmazonCategoryVO,
  CategorySearchType,
  ShopOptionVO,
} from "./types";

export const ListingPublishAPI = {
  // ── 商品类型 Schema ──

  /**
   * 获取商品类型 JSON Schema（后端已解析）。
   *
   * @param params - 查询参数（marketplaceId + productTypeOrigin）。
   * @returns 解析后的 Schema 数据。
   */
  getProductTypeSchema(params: ProductTypeSchemaQuery) {
    return request<ProductTypeSchemaVO, any>({
      url: "/sales/product-type-schema",
      method: "get",
      params,
    });
  },

  // ── Amazon 分类 ──

  /**
   * 获取根分类列表。
   *
   * @param marketplaceId - Amazon 市场 ID。
   * @returns 根分类数组。
   */
  getRootCategories(marketplaceId: string) {
    return request<AmazonCategoryVO[], any>({
      url: "/sales/root-categories",
      method: "get",
      params: { marketplaceId },
    });
  },

  /**
   * 获取子分类列表。
   *
   * @param marketplaceId - Amazon 市场 ID。
   * @param categoryUniqueId - 父分类唯一 ID。
   * @returns 子分类数组。
   */
  getCategoryChildren(marketplaceId: string, categoryUniqueId: string) {
    return request<AmazonCategoryVO[], any>({
      url: "/sales/category-children",
      method: "get",
      params: { marketplaceId, categoryUniqueId },
    });
  },

  /**
   * 搜索分类。
   *
   * @param marketplaceId - Amazon 市场 ID。
   * @param searchType - 搜索类型。
   * @param keyword - 关键词。
   * @returns 匹配的分类数组。
   */
  searchCategories(marketplaceId: string, searchType: CategorySearchType, keyword: string) {
    return request<AmazonCategoryVO[], any>({
      url: "/sales/category-search",
      method: "get",
      params: { marketplaceId, searchType, keyword },
    });
  },

  // ── 店铺 ──

  /**
   * 获取店铺下拉列表。
   *
   * @returns 已启用且已配置广告的店铺数组。
   */
  getShopOptions() {
    return request<ShopOptionVO[], any>({
      url: "/shops/options",
      method: "get",
    });
  },
};
