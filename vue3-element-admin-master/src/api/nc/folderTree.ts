/**
 * NC 文件夹树管理 API 模块：文件夹浏览、新建目录、权限规则分配。
 * 所属板块：nc。
 */
import request from "@/utils/request";

/** NC DEPT_ADMIN 群组选项（左侧面板数据源） */
export interface NcGroupItem {
  /** NcGroup 主键 */
  id: number;
  /** NC 群组 code（如 tech_admin） */
  code: string;
  /** NC 群组显示名称 */
  name: string;
  /** 所属部门名称 */
  deptName: string;
}

/** 文件夹节点上绑定的权限规则简报 */
export interface FolderRuleVO {
  /** NcFileAccessRule 主键 */
  id: number;
  ncGroupId: number;
  ncGroupCode: string;
  ncGroupName: string;
  /** NC 群组类型，如 DEPT / DEPT_ADMIN */
  ncGroupType: string;
  ncPath: string;
  permissionBits: number;
  /** 权限标签列表，如 ["READ", "WRITE"] */
  permLabels: string[];
  isGroupFolder: boolean;
  status: boolean;
  createTime: string | null;
  updateTime: string | null;
}

/** 单个文件夹节点（el-tree 懒加载数据单元） */
export interface FolderItem {
  /** 文件夹显示名称 */
  name: string;
  /**
   * 完整 NC 路径（含挂载点），用于 NcFileAccessRule.nc_path。
   * 示例：技术部/机密文档
   */
  ncPath: string;
  /** 当前节点已存在的权限规则，无则为 null */
  rule: FolderRuleVO | null;
}

/** 文件夹列表接口响应结构 */
export interface FolderListResult {
  /** Group Folder 挂载点名称 */
  mountPoint: string;
  /** 当前浏览路径（相对于挂载点根，空串=根目录） */
  currentPath: string;
  /** 完整 NC 路径（= mountPoint/currentPath） */
  fullNcPath: string;
  /** 当前路径自身的权限规则 */
  currentRule: FolderRuleVO | null;
  /** 直属子文件夹列表 */
  items: FolderItem[];
}

/** 文件夹列表查询参数 */
export interface FolderListQuery {
  /** NcGroup ID（必须是 DEPT_ADMIN 类型） */
  groupId: number;
  /** 相对于挂载点根的子路径；空串=根目录 */
  path: string;
}

/** 新建文件夹请求体 */
export interface MkdirForm {
  /** NcGroup ID */
  groupId: number;
  /** 父路径（相对于挂载点根）；空串=在挂载点根下创建 */
  parentPath: string;
  /** 新文件夹名称（不能含 '/'） */
  folderName: string;
}

/** 新建文件夹响应 */
export interface MkdirResult {
  message: string;
  /** 新目录的完整 nc_path */
  ncPath: string;
}

/** 所有 NC 群组选项（添加规则弹窗群组选择器数据源） */
export interface NcGroupOption {
  /** NcGroup 主键 */
  id: number;
  /** NC 群组 code */
  code: string;
  /** NC 群组显示名称 */
  name: string;
  /** 群组类型：DEPT / DEPT_ADMIN */
  groupType: string;
  /** 所属部门名称 */
  deptName: string;
}

/** 设置权限规则请求体 */
export interface SetRuleForm {
  /** NcGroup ID */
  groupId: number;
  /** 完整 NC 路径（含挂载点），如 "技术部/机密文档" */
  ncPath: string;
  /** 权限位（1~31） */
  permissionBits: number;
  /** 是否生效，默认 true */
  status?: boolean;
}

/**
 * 获取所有 DEPT_ADMIN NC 群组列表（左侧面板数据源）。
 *
 * @returns {Promise<NcGroupItem[]>} 群组列表
 */
export function fetchNcGroupList(): Promise<NcGroupItem[]> {
  return request.get("/nc/folder-tree/groups");
}

/**
 * 列出指定群组目录下的直属子文件夹（懒加载节点数据源）。
 *
 * @param {FolderListQuery} params 查询参数
 * @returns {Promise<FolderListResult>} 文件夹列表与当前层级信息
 */
export function fetchFolderList(
  params: FolderListQuery
): Promise<FolderListResult> {
  return request.get("/nc/folder-tree/list", { params });
}

/**
 * 在指定路径下创建新文件夹（幂等：已存在时静默通过）。
 *
 * @param {MkdirForm} data 新建文件夹请求体
 * @returns {Promise<MkdirResult>} 创建结果，含新目录的 ncPath
 */
export function createFolder(data: MkdirForm): Promise<MkdirResult> {
  return request.post("/nc/folder-tree/mkdir", data);
}

/**
 * 为指定路径设置或更新 NC ACL 权限规则（upsert）。
 *
 * @param {SetRuleForm} data 权限规则表单
 * @returns {Promise<FolderRuleVO>} 更新/新建后的规则数据
 */
export function setFolderRule(data: SetRuleForm): Promise<FolderRuleVO> {
  return request.post("/nc/folder-tree/set-rule", data);
}

/**
 * 删除指定 NC 权限规则并入队撤销 ACL 同步。
 *
 * @param {number} id NcFileAccessRule 主键
 * @returns {Promise<void>}
 */
export function deleteFolderRule(id: number): Promise<void> {
  return request.delete(`/nc/folder-tree/rule/${id}`);
}

/**
 * 查询指定 NC 路径上所有群组的 ACL 规则（跨群组聚合）。
 *
 * @param {string} ncPath 完整路径（含挂载点），如 "销售部/报表"
 * @returns {Promise<FolderRuleVO[]>} 规则列表
 */
export function fetchPathRules(ncPath: string): Promise<FolderRuleVO[]> {
  return request.get("/nc/folder-tree/path-rules", { params: { ncPath } });
}

/**
 * 获取所有 NC 群组列表（添加规则弹窗群组选择器数据源）。
 *
 * @returns {Promise<NcGroupOption[]>} 群组列表
 */
export function fetchAllNcGroups(): Promise<NcGroupOption[]> {
  return request.get("/nc/folder-tree/all-groups");
}
