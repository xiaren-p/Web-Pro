/**
 * 系统配置 API：分页查询、表单维护、刷新缓存。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface ConfigPageQuery extends PageQuery {
  keywords?: string;
}

export interface ConfigPageVO {
  id: string;
  configName?: string;
  configKey?: string;
  configValue?: string;
  configType?: string;
  status?: number;
  remark?: string;
}

export interface ConfigForm {
  id?: string;
  configName?: string;
  configKey?: string;
  configValue?: string;
  configType?: string;
  status?: number;
  remark?: string;
}

const CONFIG_BASE_URL = "/configs";

export const ConfigAPI = {
  getPage(params: ConfigPageQuery) {
    return request<any, PageResult<ConfigPageVO[]>>({
      url: `${CONFIG_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, ConfigForm>({ url: `${CONFIG_BASE_URL}/${id}/form`, method: "get" });
  },
  create(data: ConfigForm) {
    return request({ url: `${CONFIG_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: ConfigForm) {
    return request({ url: `${CONFIG_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${CONFIG_BASE_URL}/${ids}`, method: "delete" });
  },
  refreshCache() {
    return request({ url: `${CONFIG_BASE_URL}/refresh-cache`, method: "post" });
  },
  deleteById(id: string) {
    return this.deleteByIds(id);
  },
};
