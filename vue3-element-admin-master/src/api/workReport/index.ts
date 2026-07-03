/**
 * 工作报告 API：日报/周报的增删改查、团队统计。
 */
import request from "@/utils/request";

const WORK_REPORT_BASE_URL = "/work-report";

/** 工作报告 VO。 */
export interface WorkReportVO {
  id: number;
  user: number;
  username: string;
  nickname: string;
  avatar: string;
  department: string;
  type: string;
  content: string;
  plan: string;
  issues: string;
  work_hours: number;
  progress: number;
  report_date: string;
  created_at: string;
  updated_at: string;
}

/** 工作报告表单。 */
export interface WorkReportForm {
  type: string;
  content: string;
  plan?: string;
  issues?: string;
  work_hours?: number;
  progress?: number;
  report_date: string;
}

/** 工作报告查询参数。 */
export interface WorkReportQuery {
  pageNum?: number;
  pageSize?: number;
  scope?: "my" | "team";
  date?: string;
  department?: string;
  dept_id?: number | string;
  type?: string;
}

/** 团队统计 VO。 */
export interface TeamStatsVO {
  total: number;
  submitted: number;
  missing: number;
}

/** 团队统计详情人员项。 */
export interface TeamStatsDetail {
  user_id: number;
  username: string;
  nickname: string;
  avatar: string;
  department: string;
  status: string;
}

/**
 * 获取工作报告列表。
 *
 * @param params - 查询参数。
 * @returns 分页结果。
 */
export function getWorkReportList(params: WorkReportQuery) {
  return request<any, { data: WorkReportVO[]; total: number }>({
    url: WORK_REPORT_BASE_URL,
    method: "get",
    params,
  });
}

/**
 * 获取团队统计数据。
 *
 * @param date - 日期。
 * @param dept_id - 部门ID。
 * @param type - 报告类型。
 * @returns 团队统计。
 */
export function getTeamStats(date?: string, dept_id?: number | string, type?: string) {
  return request<any, TeamStatsVO>({
    url: `${WORK_REPORT_BASE_URL}/team/stats`,
    method: "get",
    params: { date, dept_id, type },
  });
}

/**
 * 获取团队统计详情（人员列表）。
 *
 * @param date - 日期。
 * @param dept_id - 部门ID。
 * @param type - 报告类型。
 * @param status - 提交状态。
 * @returns 人员列表。
 */
export function getTeamStatsDetails(
  date?: string,
  dept_id?: number | string,
  type?: string,
  status?: string
) {
  return request<any, TeamStatsDetail[]>({
    url: `${WORK_REPORT_BASE_URL}/team/stats/details`,
    method: "get",
    params: { date, dept_id, type, status },
  });
}

/**
 * 获取工作报告详情。
 *
 * @param id - 报告ID。
 * @returns 报告数据。
 */
export function getWorkReportDetail(id: number) {
  return request<any, WorkReportVO>({ url: `${WORK_REPORT_BASE_URL}/${id}`, method: "get" });
}

/**
 * 新增工作报告。
 *
 * @param data - 报告表单。
 */
export function addWorkReport(data: WorkReportForm) {
  return request({ url: WORK_REPORT_BASE_URL, method: "post", data });
}

/**
 * 修改工作报告。
 *
 * @param id - 报告ID。
 * @param data - 更新数据。
 */
export function updateWorkReport(id: number, data: WorkReportForm) {
  return request({ url: `${WORK_REPORT_BASE_URL}/${id}`, method: "put", data });
}

/**
 * 删除工作报告。
 *
 * @param id - 报告ID。
 */
export function deleteWorkReport(id: number) {
  return request({ url: `${WORK_REPORT_BASE_URL}/${id}`, method: "delete" });
}
