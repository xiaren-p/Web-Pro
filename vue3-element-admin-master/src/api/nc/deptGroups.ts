/**
 * NC 部门群组初始化 API 模块：查询部门 NC 双群组状态，并支持补全操作。
 */
import request from "@/utils/request";

/** 单个部门的 NC 群组简要信息 */
export interface NcGroupBrief {
  id: number;
  code: string;
  folderId: number | null;
}

/** 部门 NC 群组初始化状态枚举 */
export type DeptGroupStatus = "ready" | "partial" | "none";

/** 部门 NC 群组状态行 */
export interface DeptGroupRow {
  deptId: number;
  deptName: string;
  deptCode: string;
  /** ready=双群组就绪; partial=部分缺失; none=未初始化 */
  status: DeptGroupStatus;
  deptGroup: NcGroupBrief | null;
  adminGroup: NcGroupBrief | null;
}

/** 批量初始化结果 */
export interface ProvisionAllResult {
  total: number;
  success: number;
  failed: Array<{ deptId: number; deptName: string; error: string }>;
}

/**
 * 查询所有部门的 NC 双群组初始化状态。
 *
 * @returns {Promise<DeptGroupRow[]>} 部门状态列表
 */
export function fetchDeptGroupStatus(): Promise<DeptGroupRow[]> {
  return request
    .get<unknown, { list: DeptGroupRow[] }>("/nc/dept-groups")
    .then((res) => res.list);
}

/**
 * 为指定部门补全 NC 双群组（幂等）。
 *
 * @param {number} deptId - 部门 ID
 * @returns {Promise<DeptGroupRow>} 最新状态行
 */
export function provisionDeptGroup(deptId: number): Promise<DeptGroupRow> {
  return request.post(`/nc/dept-groups/${deptId}/provision`);
}

/**
 * 批量补全所有未初始化的部门 NC 双群组。
 *
 * @returns {Promise<ProvisionAllResult>} 执行结果
 */
export function provisionAllDeptGroups(): Promise<ProvisionAllResult> {
  return request.post("/nc/dept-groups/provision-all");
}
