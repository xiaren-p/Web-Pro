/**
 * 共享分页类型：所有 *PageQuery 与 PageResult<T> 在此定义。
 */

export interface PageQuery {
  pageNum: number;
  pageSize: number;
}

export interface PageResult<T> {
  total: number;
  list: T;
}
