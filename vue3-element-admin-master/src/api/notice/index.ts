/**
 * 通知公告 API：发布、撤回、阅读、个人列表、导出。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export type NoticePageQuery = PageQuery & {
  title?: string;
  publishStatus?: number;
  isRead?: number;
};

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
  getPage(params: any) {
    return request<any, PageResult<NoticePageVO[]>>({
      url: `${NOTICE_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, any>({ url: `${NOTICE_BASE_URL}/${id}/form`, method: "get" });
  },
  publish(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/publish`, method: "post" });
  },
  revoke(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/revoke`, method: "post" });
  },
  getDetail(id: string) {
    return request<any, NoticeDetailVO>({ url: `${NOTICE_BASE_URL}/${id}/detail`, method: "get" });
  },
  read(id: string) {
    return request({ url: `${NOTICE_BASE_URL}/${id}/read`, method: "post" });
  },
  readAll() {
    return request({ url: `${NOTICE_BASE_URL}/read-all`, method: "post" });
  },
  getMyPage(params: any) {
    return request<any, PageResult<NoticePageVO[]>>({
      url: `${NOTICE_BASE_URL}/my-page`,
      method: "get",
      params,
    });
  },
  getMyNoticePage(params: any) {
    return this.getMyPage(params);
  },
  exportData(params: any) {
    return request({
      url: `${NOTICE_BASE_URL}/export`,
      method: "get",
      params,
      responseType: "blob",
    });
  },
  create(data: any) {
    return request({ url: `${NOTICE_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: any) {
    return request({ url: `${NOTICE_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${NOTICE_BASE_URL}/${ids}`, method: "delete" });
  },
};
