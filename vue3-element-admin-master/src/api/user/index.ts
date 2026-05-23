/**
 * 用户相关 API：分页查询、增删改、个人中心、头像上传等。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface UserPageQuery extends PageQuery {
  keywords?: string;
  status?: number;
  deptId?: string;
  createTime?: [string, string];
}

export interface UserPageVO {
  id: string;
  username?: string;
  nickname?: string;
  avatar?: string;
  email?: string;
  mobile?: string;
  gender?: number;
  deptName?: string;
  positionName?: string;
  adminLevelLabel?: string;
  status?: number;
  createTime?: Date;
}

export interface UserForm {
  id?: string;
  avatar?: string;
  deptId?: string;
  email?: string;
  gender?: number;
  mobile?: string;
  nickname?: string;
  positionId?: string;
  adminLevel?: number;
  status?: number;
  username?: string;
  password?: string;
}

export interface UserInfo {
  userId?: string;
  username?: string;
  nickname?: string;
  avatar?: string;
  roles: string[];
  perms: string[];
  /** 管理级别：1=公司管理员，2=部门管理员，3=普通成员 */
  adminLevel?: number;
  /** 当前用户所属部门 ID */
  deptId?: number | null;
}

const USER_BASE_URL = "/users";

export const UserAPI = {
  getInfo() {
    return request<any, UserInfo>({ url: `${USER_BASE_URL}/me`, method: "get" });
  },
  getPage(queryParams: UserPageQuery) {
    return request<any, PageResult<UserPageVO[]>>({
      url: `${USER_BASE_URL}/page`,
      method: "get",
      params: queryParams,
    });
  },
  getFormData(userId: string) {
    return request<any, UserForm>({ url: `${USER_BASE_URL}/${userId}/form`, method: "get" });
  },
  create(data: UserForm) {
    return request({ url: `${USER_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: UserForm) {
    return request({ url: `${USER_BASE_URL}/${id}`, method: "put", data });
  },
  resetPassword(id: string, password: string) {
    return request({
      url: `${USER_BASE_URL}/${id}/password/reset`,
      method: "put",
      params: { password },
    });
  },
  deleteByIds(ids: string) {
    return request({ url: `${USER_BASE_URL}/${ids}`, method: "delete" });
  },
  getProfile() {
    return request<any, any>({ url: `${USER_BASE_URL}/profile`, method: "get" });
  },
  updateProfile(data: any) {
    return request({ url: `${USER_BASE_URL}/profile`, method: "put", data });
  },
  changePassword(data: any) {
    return request({ url: `${USER_BASE_URL}/password`, method: "put", data });
  },
  sendMobileCode(mobile: string) {
    return request({ url: `${USER_BASE_URL}/mobile/code`, method: "post", params: { mobile } });
  },
  bindOrChangeMobile(data: any) {
    return request({ url: `${USER_BASE_URL}/mobile`, method: "put", data });
  },
  sendEmailCode(email: string) {
    return request({ url: `${USER_BASE_URL}/email/code`, method: "post", params: { email } });
  },
  bindOrChangeEmail(data: any) {
    return request({ url: `${USER_BASE_URL}/email`, method: "put", data });
  },
  getOptions() {
    return request<any, any[]>({ url: `${USER_BASE_URL}/options`, method: "get" });
  },
  uploadAvatar(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<any, { url: string; name: string }>({
      url: `${USER_BASE_URL}/avatar`,
      method: "post",
      data: form,
    });
  },
};
