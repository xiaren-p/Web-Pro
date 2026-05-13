import request from "@/utils/request";

const WORK_REPORT_BASE_URL = "/work-report";

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

export interface WorkReportForm {
  type: string;
  content: string;
  plan?: string;
  issues?: string;
  work_hours?: number;
  progress?: number;
  report_date: string;
}

export interface WorkReportQuery {
  pageNum?: number; // Backend default pagination might use page/size logic but ViewSet uses limit/offset or page_size
  pageSize?: number;
  scope?: "my" | "team";
  date?: string;
  department?: string; // Optional filter for team view (by name)
  dept_id?: number | string; // Optional filter for team view (by ID)
  type?: string;
}

export interface TeamStatsVO {
  total: number;
  submitted: number;
  missing: number;
}

/**
 * 获取工作汇报列表
 */
export function getWorkReportList(params: WorkReportQuery) {
  return request<any, { data: WorkReportVO[]; total: number }>({
    url: WORK_REPORT_BASE_URL,
    method: "get",
    params,
  });
}

/**
 * 获取团队统计
 */
export function getTeamStats(date?: string, dept_id?: number | string, type?: string) {
  return request<any, TeamStatsVO>({
    url: `${WORK_REPORT_BASE_URL}/team/stats`,
    method: "get",
    params: { date, dept_id, type },
  });
}

/**
 * 获取团队统计详情 (人员列表)
 */
export function getTeamStatsDetails(
  date?: string,
  dept_id?: number | string,
  type?: string,
  status?: string
) {
  return request<any, any[]>({
    url: `${WORK_REPORT_BASE_URL}/team/stats/details`,
    method: "get",
    params: { date, dept_id, type, status },
  });
}

/**
 * 获取工作汇报详情
 */
export function getWorkReportDetail(id: number) {
  return request<any, WorkReportVO>({
    url: `${WORK_REPORT_BASE_URL}/${id}`,
    method: "get",
  });
}

/**
 * 新增工作汇报
 */
export function addWorkReport(data: WorkReportForm) {
  return request({
    url: WORK_REPORT_BASE_URL,
    method: "post",
    data,
  });
}

/**
 * 修改工作汇报
 */
export function updateWorkReport(id: number, data: WorkReportForm) {
  return request({
    url: `${WORK_REPORT_BASE_URL}/${id}`,
    method: "put",
    data,
  });
}

/**
 * 删除工作汇报
 */
export function deleteWorkReport(id: number) {
  return request({
    url: `${WORK_REPORT_BASE_URL}/${id}`,
    method: "delete",
  });
}
