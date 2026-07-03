/**
 * 用户相关 API：分页查询、增删改、个人中心、头像上传等。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

/** 用户分页查询参数。 */
export interface UserPageQuery extends PageQuery {
  keywords?: string;
  status?: number;
  deptId?: string;
  createTime?: [string, string];
}

/** 用户分页列表项。 */
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

/** 用户表单数据。 */
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

/** 当前登录用户信息。 */
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

/** 个人资料更新参数。 */
export interface ProfileUpdateData {
  nickname?: string;
  gender?: number;
  avatar?: string;
  mobile?: string;
  email?: string;
}

/** 密码修改参数。 */
export interface PasswordChangeData {
  oldPassword?: string;
  newPassword?: string;
  confirmPassword?: string;
}

/** 手机/邮箱绑定参数。 */
export interface ContactBindData {
  mobile?: string;
  email?: string;
}

/** 用户下拉选项。 */
export interface UserOption {
  value: string;
  label: string;
}

const USER_BASE_URL = "/users";

export const UserAPI = {
  /**
   * 获取当前登录用户信息。
   *
   * @returns 用户信息。
   */
  getInfo() {
    return request<any, UserInfo>({ url: `${USER_BASE_URL}/me`, method: "get" });
  },
  /**
   * 分页查询用户列表。
   *
   * @param queryParams - 查询参数。
   * @returns 分页结果。
   */
  getPage(queryParams: UserPageQuery) {
    return request<any, PageResult<UserPageVO[]>>({
      url: `${USER_BASE_URL}/page`,
      method: "get",
      params: queryParams,
    });
  },
  /**
   * 获取用户编辑表单数据（含部门/岗位信息）。
   *
   * @param userId - 用户ID。
   * @returns 表单数据。
   */
  getFormData(userId: string) {
    return request<any, UserForm>({ url: `${USER_BASE_URL}/${userId}/form`, method: "get" });
  },
  /**
   * 创建用户。
   *
   * @param data - 用户表单数据。
   */
  create(data: UserForm) {
    return request({ url: `${USER_BASE_URL}`, method: "post", data });
  },
  /**
   * 更新用户信息。
   *
   * @param id - 用户ID。
   * @param data - 更新的数据。
   */
  update(id: string, data: UserForm) {
    return request({ url: `${USER_BASE_URL}/${id}`, method: "put", data });
  },
  /**
   * 重置用户密码为指定值。
   *
   * @param id - 用户ID。
   * @param password - 新密码。
   */
  resetPassword(id: string, password: string) {
    return request({
      url: `${USER_BASE_URL}/${id}/password/reset`,
      method: "put",
      params: { password },
    });
  },
  /**
   * 批量删除用户（逗号分隔ID）。
   *
   * @param ids - 逗号分隔的ID列表。
   */
  deleteByIds(ids: string) {
    return request({ url: `${USER_BASE_URL}/${ids}`, method: "delete" });
  },
  /**
   * 获取当前用户个人资料。
   *
   * @returns 个人资料。
   */
  getProfile() {
    return request<any, UserInfo>({ url: `${USER_BASE_URL}/profile`, method: "get" });
  },
  /**
   * 更新当前用户个人资料。
   *
   * @param data - 更新的字段。
   */
  updateProfile(data: ProfileUpdateData) {
    return request({ url: `${USER_BASE_URL}/profile`, method: "put", data });
  },
  /**
   * 修改当前用户密码。
   *
   * @param data - 密码数据（含旧密码、新密码、确认密码）。
   */
  changePassword(data: PasswordChangeData) {
    return request({ url: `${USER_BASE_URL}/password`, method: "put", data });
  },
  /**
   * 发送手机验证码。
   *
   * @param mobile - 手机号码。
   */
  sendMobileCode(mobile: string) {
    return request({ url: `${USER_BASE_URL}/mobile/code`, method: "post", params: { mobile } });
  },
  /**
   * 绑定或更换手机号。
   *
   * @param data - 手机号数据。
   */
  bindOrChangeMobile(data: ContactBindData) {
    return request({ url: `${USER_BASE_URL}/mobile`, method: "put", data });
  },
  /**
   * 发送邮箱验证码。
   *
   * @param email - 邮箱地址。
   */
  sendEmailCode(email: string) {
    return request({ url: `${USER_BASE_URL}/email/code`, method: "post", params: { email } });
  },
  /**
   * 绑定或更换邮箱。
   *
   * @param data - 邮箱数据。
   */
  bindOrChangeEmail(data: ContactBindData) {
    return request({ url: `${USER_BASE_URL}/email`, method: "put", data });
  },
  /**
   * 获取用户下拉选项。
   *
   * @returns 用户选项列表。
   */
  getOptions() {
    return request<any, UserOption[]>({ url: `${USER_BASE_URL}/options`, method: "get" });
  },
  /**
   * 上传用户头像（multipart/form-data）。
   *
   * @param file - 图片文件。
   * @returns 上传结果（含URL）。
   */
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
