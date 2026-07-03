/**
 * 字典 API：字典类型与字典项的分页、表单、选项接口。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 字典类型分页查询参数。 */
export interface DictPageQuery extends PageQuery {
  keywords?: string;
}

/** 字典类型分页列表项。 */
export interface DictPageVO {
  id: string;
  name?: string;
  dictCode?: string;
  status?: number;
  remark?: string;
}

/** 字典类型表单。 */
export interface DictForm {
  id?: string;
  name?: string;
  dictCode?: string;
  status?: number;
  remark?: string;
}

/** 字典项分页查询参数。 */
export interface DictItemPageQuery extends PageQuery {
  keywords?: string;
}

/** 字典项分页列表项。 */
export interface DictItemPageVO {
  id: string;
  label?: string;
  value?: string;
  status?: number;
  sort?: number;
  tagType?: string;
}

/** 字典项表单。 */
export interface DictItemForm {
  id?: string;
  dictCode?: string;
  label?: string;
  value?: string;
  status?: number;
  sort?: number;
  tagType?: string;
}

/** 字典项下拉选项。 */
export interface DictItemOption {
  label: string;
  value: string | number;
  colorType?: string;
  cssClass?: string;
  tagType?: string;
}

const DICT_BASE_URL = "/dicts";

export const DictAPI = {
  /**
   * 分页查询字典类型。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: DictPageQuery) {
    return request<any, PageResult<DictPageVO[]>>({
      url: `${DICT_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  /**
   * 获取全部字典类型列表。
   *
   * @returns 字典类型列表。
   */
  getList() {
    return request<any, DictPageVO[]>({ url: `${DICT_BASE_URL}`, method: "get" });
  },
  /**
   * 获取字典类型编辑表单。
   *
   * @param id - 字典ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, DictForm>({ url: `${DICT_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建字典类型。
   *
   * @param data - 表单数据。
   */
  create(data: DictForm) {
    return request({ url: `${DICT_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新字典类型。
   *
   * @param id - 字典ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: DictForm) {
    return request({ url: `${DICT_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除字典类型。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${DICT_BASE_URL}/${ids}`, method: "delete" });
  },
  /**
   * 分页查询字典项。
   *
   * @param dictCode - 字典编码。
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getItemPage(dictCode: string, params: DictItemPageQuery) {
    return request<any, PageResult<DictItemPageVO[]>>({
      url: `${DICT_BASE_URL}/${dictCode}/items/page`,
      method: "get",
      params,
    });
  },
  /**
   * 获取字典项编辑表单。
   *
   * @param dictCode - 字典编码。
   * @param itemId - 字典项ID。
   * @returns 表单数据。
   */
  getItemForm(dictCode: string, itemId: string) {
    return request<any, DictItemForm>({
      url: `${DICT_BASE_URL}/${dictCode}/items/${itemId}/form`,
      method: "get",
    });
  },
  /**
   * 创建字典项。
   *
   * @param dictCode - 字典编码。
   * @param data - 表单数据。
   */
  createItem(dictCode: string, data: DictItemForm) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items`, method: "post", data });
  },
  /**
   * 更新字典项。
   *
   * @param dictCode - 字典编码。
   * @param itemId - 字典项ID。
   * @param data - 更新的数据。
   */
  updateItem(dictCode: string, itemId: string, data: DictItemForm) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items/${itemId}`, method: "put", data });
  },
  /**
   * 批量删除字典项。
   *
   * @param dictCode - 字典编码。
   * @param ids - 逗号分隔的ID列表。
   */
  deleteItems(dictCode: string, ids: string) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items/${ids}`, method: "delete" });
  },
  /**
   * 获取字典项下拉选项。
   *
   * @param dictCode - 字典编码。
   * @returns 选项列表。
   */
  getItemOptions(dictCode: string) {
    return request<any, DictItemOption[]>({
      url: `${DICT_BASE_URL}/${dictCode}/items/options`,
      method: "get",
    });
  },
  /** @deprecated 使用 getItemPage 替代。 */
  getDictItemPage(dictCode: string, params: DictItemPageQuery) {
    return DictAPI.getItemPage(dictCode, params);
  },
  /** @deprecated 使用 getItemForm 替代。 */
  getDictItemFormData(dictCode: string, itemId: string) {
    return DictAPI.getItemForm(dictCode, itemId);
  },
  /** @deprecated 使用 updateItem 替代。 */
  updateDictItem(dictCode: string, itemId: string, data: DictItemForm) {
    return DictAPI.updateItem(dictCode, itemId, data);
  },
  /** @deprecated 使用 createItem 替代。 */
  createDictItem(dictCode: string, data: DictItemForm) {
    return DictAPI.createItem(dictCode, data);
  },
  /** @deprecated 使用 deleteItems 替代。 */
  deleteDictItems(dictCode: string, ids: string) {
    return DictAPI.deleteItems(dictCode, ids);
  },
};
