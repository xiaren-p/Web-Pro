/**
 * 系统配置 API：分页查询、表单维护、刷新缓存。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 配置分页查询参数。 */
export interface ConfigPageQuery extends PageQuery {
  keywords?: string;
}

/** 配置分页列表项。 */
export interface ConfigPageVO {
  id: string;
  configName?: string;
  configKey?: string;
  configValue?: string;
  configType?: string;
  status?: number;
  remark?: string;
}

/** 配置表单数据。 */
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
  /**
   * 分页查询配置列表。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: ConfigPageQuery) {
    return request<any, PageResult<ConfigPageVO[]>>({
      url: `${CONFIG_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  /**
   * 获取配置编辑表单数据。
   *
   * @param id - 配置ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, ConfigForm>({ url: `${CONFIG_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 创建配置。
   *
   * @param data - 配置数据。
   */
  create(data: ConfigForm) {
    return request({ url: `${CONFIG_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新配置。
   *
   * @param id - 配置ID。
   * @param data - 更新数据。
   */
  update(id: string, data: ConfigForm) {
    return request({ url: `${CONFIG_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除配置。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${CONFIG_BASE_URL}/${ids}`, method: "delete" });
  },
  /** 刷新配置缓存。 */
  refreshCache() {
    return request({ url: `${CONFIG_BASE_URL}/refresh-cache`, method: "post" });
  },
  /**
   * 删除单个配置。
   *
   * @param id - 配置ID。
   */
  deleteById(id: string) {
    return ConfigAPI.deleteByIds(id);
  },
};
