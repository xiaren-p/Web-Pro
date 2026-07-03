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
  deptId?: number | null;
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
  /** 获取当前登录用户信息。 */
  getInfo() {
    return request<any, UserInfo>({ url: `${USER_BASE_URL}/me`, method: "get" });
  },
  /** 分页查询用户列表。 */
  getPage(queryParams: UserPageQuery) {
    return request<any, PageResult<UserPageVO[]>>({
      url: `${USER_BASE_URL}/page`,
      method: "get",
      params: queryParams,
    });
  },
  /** 获取用户编辑表单数据（含部门/岗位信息）。 */
  getFormData(userId: string) {
    return request<any, UserForm>({ url: `${USER_BASE_URL}/${userId}/form`, method: "get" });
  },
  /** 创建用户。 */
  create(data: UserForm) {
    return request({ url: `${USER_BASE_URL}`, method: "post", data });
  },
  /** 更新用户信息。 */
  update(id: string, data: UserForm) {
    return request({ url: `${USER_BASE_URL}/${id}`, method: "put", data });
  },
  /** 重置用户密码为指定值。 */
  resetPassword(id: string, password: string) {
    return request({
      url: `${USER_BASE_URL}/${id}/password/reset`,
      method: "put",
      params: { password },
    });
  },
  /** 批量删除用户（逗号分隔 ID）。 */
  deleteByIds(ids: string) {
    return request({ url: `${USER_BASE_URL}/${ids}`, method: "delete" });
  },
  /** 获取当前用户个人资料。 */
  getProfile() {
    return request<any, any>({ url: `${USER_BASE_URL}/profile`, method: "get" });
  },
  /** 更新当前用户个人资料。 */
  updateProfile(data: any) {
    return request({ url: `${USER_BASE_URL}/profile`, method: "put", data });
  },
  /** 修改当前用户密码。 */
  changePassword(data: any) {
    return request({ url: `${USER_BASE_URL}/password`, method: "put", data });
  },
  /** 发送手机验证码。 */
  sendMobileCode(mobile: string) {
    return request({ url: `${USER_BASE_URL}/mobile/code`, method: "post", params: { mobile } });
  },
  /** 绑定或更换手机号。 */
  bindOrChangeMobile(data: any) {
    return request({ url: `${USER_BASE_URL}/mobile`, method: "put", data });
  },
  /** 发送邮箱验证码。 */
  sendEmailCode(email: string) {
    return request({ url: `${USER_BASE_URL}/email/code`, method: "post", params: { email } });
  },
  /** 绑定或更换邮箱。 */
  bindOrChangeEmail(data: any) {
    return request({ url: `${USER_BASE_URL}/email`, method: "put", data });
  },
  /** 获取用户下拉选项。 */
  getOptions() {
    return request<any, any[]>({ url: `${USER_BASE_URL}/options`, method: "get" });
  },
  /** 上传用户头像（multipart/form-data）。 */
  uploadAvatar(file: File) {
    const form = new FormData();
    form.append("file", file);
    return request<unknown, { url: string }>({
      url: `${USER_BASE_URL}/avatar`,
      method: "post",
      data: form,
    });
  },
};
