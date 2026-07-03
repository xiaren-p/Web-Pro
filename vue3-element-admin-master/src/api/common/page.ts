/**
 * 共享分页类型：所有 *PageQuery 与 PageResult<T> 在此定义。
 */

/** 分页查询基础参数。 */
export interface PageQuery {
  pageNum: number;
  pageSize: number;
}

/** 分页查询通用返回结构。 */
export interface PageResult<T> {
  total: number;
  list: T;
}
