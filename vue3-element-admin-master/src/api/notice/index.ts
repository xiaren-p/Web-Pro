/**
 * 通知公告 API：发布、撤回、阅读、个人列表、导出。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 通知分页查询参数。 */
export type NoticePageQuery = PageQuery & {
  title?: string;
  publishStatus?: number;
  isRead?: number;
};

/** 通知分页列表项。 */
export interface NoticePageVO {
  id: string;
  title?: string;
  type?: number;
  status?: number;
  creator?: string;
  createTime?: Date;
  publisherName?: string;
  publishTime?: string;
  revokeTime?: string;
  level?: string | number;
  publishStatus?: number;
  targetType?: number;
}

/** 通知表单数据。 */
export interface NoticeForm {
  id?: string;
  title?: string;
  content?: string;
  status?: number;
  type?: number;
  level?: string;
  targetType?: number;
  targetUserIds?: number[];
}

/** 通知详情 VO。 */
export interface NoticeDetailVO {
  id?: string;
  title?: string;
  content?: string;
  publisherName?: string;
  publishTime?: string;
  type?: string;
  level?: string;
  targetType?: number;
  publishStatus?: number;
}

const NOTICE_BASE_URL = "/notices";

export const NoticeAPI = {
  /**
   * 分页查询通知列表。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getPage(params: Record<string, unknown>) {
    return request<any, PageResult<NoticePageVO[]>>({
      url: `${NOTICE_BASE_URL}/page`, method: "get", params,
    });
  },
  /**
   * 获取通知编辑表单数据。
   *
   * @param id - 通知ID。
   * @returns 表单数据。
   */
  getFormData(id: string) {
    return request<any, NoticeForm>({ url: `${NOTICE_BASE_URL}/${id}/form`, method: "get" });
  },
  /**
   * 发布通知。
   *
   * @param id - 通知ID。
   */
  publish(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/publish`, method: "post" });
  },
  /**
   * 撤回通知。
   *
   * @param id - 通知ID。
   */
  revoke(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/revoke`, method: "post" });
  },
  /**
   * 获取通知详情。
   *
   * @param id - 通知ID。
   * @returns 详情数据。
   */
  getDetail(id: string) {
    return request<any, NoticeDetailVO>({ url: `${NOTICE_BASE_URL}/${id}/detail`, method: "get" });
  },
  /**
   * 标记通知为已读。
   *
   * @param id - 通知ID。
   */
  read(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/read`, method: "post" });
  },
  /** 标记全部通知为已读。 */
  readAll() {
    return request({ url: `${NOTICE_BASE_URL}/read-all`, method: "post" });
  },
  /**
   * 获取当前用户的通知列表。
   *
   * @param params - 查询参数。
   * @returns 分页结果。
   */
  getMyPage(params: Record<string, unknown>) {
    return request<any, PageResult<NoticePageVO[]>>({
      url: `${NOTICE_BASE_URL}/my-page`, method: "get", params,
    });
  },
  /** @deprecated 使用 getMyPage 替代。 */
  getMyNoticePage(params: Record<string, unknown>) {
    return NoticeAPI.getMyPage(params);
  },
  /**
   * 导出通知数据为 xlsx。
   *
   * @param params - 导出筛选条件。
   * @returns Blob 流。
   */
  exportData(params: Record<string, unknown>) {
    return request({ url: `${NOTICE_BASE_URL}/export`, method: "get", params, responseType: "blob" });
  },
  /**
   * 创建通知。
   *
   * @param data - 通知表单数据。
   */
  create(data: NoticeForm) {
    return request({ url: `${NOTICE_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新通知。
   *
   * @param id - 通知ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: NoticeForm) {
    return request({ url: `${NOTICE_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 批量删除通知。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${NOTICE_BASE_URL}/${ids}`, method: "delete" });
  },
};
