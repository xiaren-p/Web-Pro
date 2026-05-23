/**
 * NC 文件访问规则 API 模块：子路径 ACL 管控的增删改查接口封装。
 * 所属板块：nc。
 */
import request from "@/utils/request";

/** NC 文件访问规则列表查询参数 */
export interface NcFileRulePageQuery {
  /** 页码（从 1 开始） */
  page: number;
  /** 每页条数（最大 100） */
  pageSize: number;
  /** 按群组 ID 筛选 */
  ncGroupId?: number;
  /** 是否生效筛选 */
  status?: boolean;
}

/** NC 文件访问规则列表项 VO（后端只读序列化输出） */
export interface NcFileRuleVO {
  id: number;
  ncGroupId: number;
  ncGroupCode: string;
  ncGroupName: string;
  ncGroupType: string;
  ncPath: string;
  permissionBits: number;
  /** 权限标签列表，例如 ["READ", "WRITE"] */
  permLabels: string[];
  isGroupFolder: boolean;
  status: boolean;
  createTime: string | null;
  updateTime: string | null;
}

/** NC 文件访问规则分页结果 */
export interface NcFileRulePageResult {
  total: number;
  list: NcFileRuleVO[];
}

/** NC 文件访问规则群组下拉选项 */
export interface NcGroupOption {
  id: number;
  code: string;
  name: string;
  deptName: string;
}

/** NC 文件访问规则新建/编辑表单 */
export interface NcFileRuleForm {
  /** 目标 NcGroup ID（DEPT_ADMIN 群组） */
  ncGroupId: number;
  /** 子路径，首尾斜杠自动去除，例如：技术部/机密文档 */
  ncPath: string;
  /** 权限位（1-31） */
  permissionBits: number;
  /** 是否 Group Folder，默认 true */
  isGroupFolder?: boolean;
  /** 是否生效，默认 true */
  status?: boolean;
}

/**
 * 分页查询 NC 文件访问规则列表。
 *
 * @param {NcFileRulePageQuery} params - 分页与筛选参数。
 * @returns {Promise<NcFileRulePageResult>} 分页结果。
 */
export function getNcFileRulePage(params: NcFileRulePageQuery): Promise<NcFileRulePageResult> {
  return request.get("/nc/rules/page", { params });
}

/**
 * 获取可选的 DEPT_ADMIN NC 群组下拉列表。
 *
 * @returns {Promise<NcGroupOption[]>} 群组选项列表。
 */
export function getNcGroupOptions(): Promise<NcGroupOption[]> {
  return request.get("/nc/rules/group-options");
}

/**
 * 新建 NC 文件访问规则。
 *
 * @param {NcFileRuleForm} data - 规则表单数据。
 * @returns {Promise<NcFileRuleVO>} 新建成功的规则数据。
 */
export function createNcFileRule(data: NcFileRuleForm): Promise<NcFileRuleVO> {
  return request.post("/nc/rules/create", data);
}

/**
 * 更新指定 NC 文件访问规则。
 *
 * @param {number} id - 规则 ID。
 * @param {Partial<NcFileRuleForm>} data - 需要更新的字段。
 * @returns {Promise<NcFileRuleVO>} 更新后的规则数据。
 */
export function updateNcFileRule(id: number, data: Partial<NcFileRuleForm>): Promise<NcFileRuleVO> {
  return request.put(`/nc/rules/${id}`, data);
}

/**
 * 删除指定 NC 文件访问规则（删除前后端自动入队撤销 ACL）。
 *
 * @param {number} id - 规则 ID。
 * @returns {Promise<void>}
 */
export function deleteNcFileRule(id: number): Promise<void> {
  return request.delete(`/nc/rules/${id}`);
}
