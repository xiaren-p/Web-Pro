/**
 * 刊登管理 - API 模块（商品类型 Schema + Amazon 分类 + 店铺 + 市场 + 模板 CRUD）。
 *
 * 后端路由前缀：/api/v1/sales/publication/...
 */
import request from "@/utils/request";
import type {
  ProductTypeSchemaVO,
  ProductTypeSchemaQuery,
  AmazonCategoryVO,
  CategorySearchType,
  ShopOptionVO,
  MarketplaceVO,
  PublishTemplateDetailVO,
  PublishTemplateForm,
  PublishTemplatePageQuery,
  PublishTemplatePageResult,
} from "./types";

export type {
  ProductTypeSchemaVO,
  ProductTypeSchemaQuery,
  SchemaFieldDef,
  AmazonCategoryVO,
  CategorySearchType,
  ShopOptionVO,
  MarketplaceVO,
  PublishTemplateListVO,
  PublishTemplateDetailVO,
  PublishTemplateForm,
  PublishTemplatePageQuery,
  PublishTemplatePageResult,
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
      url: "/sales/publication/product-type-schema",
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
      url: "/sales/publication/root-categories",
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
      url: "/sales/publication/category-children",
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
      url: "/sales/publication/category-search",
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

  // ── Amazon 市场列表 ──

  /**
   * 获取全部 Amazon 市场列表（从 LxMarketplace）。
   *
   * @returns 市场数组，每项含 marketplaceId / country / code / region。
   */
  getMarketplaces() {
    return request<MarketplaceVO[], any>({
      url: "/sales/publication/marketplaces",
      method: "get",
    });
  },

  // ── 刊登模板 CRUD ──

  /**
   * 分页查询模板列表（不含 data_json）。
   *
   * @param params - 分页查询参数（pageNum / pageSize / keyword）。
   * @returns 分页结果，含 total 和 list。
   */
  getTemplatePage(params: PublishTemplatePageQuery) {
    return request<PublishTemplatePageResult, any>({
      url: "/sales/publication/templates/page",
      method: "get",
      params,
    });
  },

  /**
   * 获取模板详情（含 dataJson），用于编辑表单回填。
   *
   * @param id - 模板主键 ID。
   * @returns 模板详情，含 dataJson 字段。
   */
  getTemplateForm(id: string) {
    return request<PublishTemplateDetailVO, any>({
      url: `/sales/publication/templates/${id}/form`,
      method: "get",
    });
  },

  /**
   * 新增模板。
   *
   * @param data - 模板表单数据（amazonData 映射到 data_json）。
   * @returns 创建后的模板详情。
   */
  createTemplate(data: PublishTemplateForm) {
    return request<PublishTemplateDetailVO, any>({
      url: "/sales/publication/templates",
      method: "post",
      data,
    });
  },

  /**
   * 编辑模板。
   *
   * @param id - 模板主键 ID。
   * @param data - 模板表单数据。
   * @returns 更新后的模板详情。
   */
  updateTemplate(id: string, data: PublishTemplateForm) {
    return request<PublishTemplateDetailVO, any>({
      url: `/sales/publication/templates/${id}`,
      method: "put",
      data,
    });
  },

  /**
   * 软删除模板。
   *
   * @param id - 模板主键 ID。
   * @returns 删除结果。
   */
  deleteTemplate(id: string) {
    return request<{ deletedCount: number }, any>({
      url: `/sales/publication/templates/${id}`,
      method: "delete",
    });
  },
};
