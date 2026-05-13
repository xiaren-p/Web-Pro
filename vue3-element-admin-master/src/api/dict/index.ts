/**
 * 字典 API：字典类型与字典项的分页、表单、选项接口。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface DictPageQuery extends PageQuery {
  keywords?: string;
}

export interface DictPageVO {
  id: string;
  name?: string;
  dictCode?: string;
  status?: number;
  remark?: string;
}

export interface DictForm {
  id?: string;
  name?: string;
  dictCode?: string;
  status?: number;
  remark?: string;
}

export interface DictItemPageQuery extends PageQuery {
  keywords?: string;
}

export interface DictItemPageVO {
  id: string;
  label?: string;
  value?: string;
  status?: number;
  sort?: number;
  tagType?: string;
}

export interface DictItemForm {
  id?: string;
  dictCode?: string;
  label?: string;
  value?: string;
  status?: number;
  sort?: number;
  tagType?: string;
}

export interface DictItemOption {
  label: string;
  value: any;
  colorType?: string;
  cssClass?: string;
  tagType?: string;
}

const DICT_BASE_URL = "/dicts";

export const DictAPI = {
  getPage(params: DictPageQuery) {
    return request<any, PageResult<DictPageVO[]>>({
      url: `${DICT_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getList() {
    return request<any, DictPageVO[]>({ url: `${DICT_BASE_URL}`, method: "get" });
  },
  getFormData(id: string) {
    return request<any, DictForm>({ url: `${DICT_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: DictForm) {
    return request({ url: `${DICT_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: DictForm) {
    return request({ url: `${DICT_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${DICT_BASE_URL}/${ids}`, method: "delete" });
  },
  getItemPage(dictCode: string, params: DictItemPageQuery) {
    return request<any, PageResult<DictItemPageVO[]>>({
      url: `${DICT_BASE_URL}/${dictCode}/items/page`,
      method: "get",
      params,
    });
  },
  getItemForm(dictCode: string, itemId: string) {
    return request<any, DictItemForm>({
      url: `${DICT_BASE_URL}/${dictCode}/items/${itemId}/form`,
      method: "get",
    });
  },
  createItem(dictCode: string, data: DictItemForm) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items`, method: "post", data });
  },
  updateItem(dictCode: string, itemId: string, data: DictItemForm) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items/${itemId}`, method: "put", data });
  },
  deleteItems(dictCode: string, ids: string) {
    return request({ url: `${DICT_BASE_URL}/${dictCode}/items/${ids}`, method: "delete" });
  },
  getItemOptions(dictCode: string) {
    return request<any, DictItemOption[]>({
      url: `${DICT_BASE_URL}/${dictCode}/items/options`,
      method: "get",
    });
  },
  getDictItemPage(dictCode: string, params: DictItemPageQuery) {
    return this.getItemPage(dictCode, params);
  },
  getDictItemFormData(dictCode: string, itemId: string) {
    return this.getItemForm(dictCode, itemId);
  },
  updateDictItem(dictCode: string, itemId: string, data: DictItemForm) {
    return this.updateItem(dictCode, itemId, data);
  },
  createDictItem(dictCode: string, data: DictItemForm) {
    return this.createItem(dictCode, data);
  },
  deleteDictItems(dictCode: string, ids: string) {
    return this.deleteItems(dictCode, ids);
  },
};
