<template>
  <div class="nc-perm-page">
    <!-- ===== 左侧：文件夹树 ===== -->
    <div class="nc-sidebar" :style="{ width: sidebarWidth + 'px' }">
      <div class="sidebar-header">
        <el-icon class="sidebar-icon"><FolderOpened /></el-icon>
        <span class="sidebar-title">文件夹目录</span>
      </div>
      <el-scrollbar class="sidebar-scroll">
        <el-tree
          ref="treeRef"
          :props="treeProps"
          :load="loadNode"
          node-key="key"
          lazy
          highlight-current
          :expand-on-click-node="false"
          class="nc-tree"
          @node-click="handleNodeClick"
        >
          <template #default="{ data }">
            <span class="tree-node-label">
              <el-icon class="node-folder-icon"><Folder /></el-icon>
              <span class="node-name">{{ data.name }}</span>
              <el-icon v-if="data.hasRule" class="node-lock-icon"><Lock /></el-icon>
            </span>
          </template>
        </el-tree>
      </el-scrollbar>
    </div>

    <!-- ===== 拖拽分隔条 ===== -->
    <div class="nc-resize-handle" @mousedown="handleResizeStart" />

    <!-- ===== 右侧：权限面板 ===== -->
    <div class="nc-main">
      <!-- 未选中 -->
      <div v-if="!activeNode" class="main-empty">
        <el-empty description="点击左侧文件夹查看权限配置" :image-size="80" />
      </div>

      <!-- 根节点加载中 -->
      <div v-else-if="!activeNode.ncPath" class="main-empty">
        <el-empty description="正在加载目录信息…" :image-size="60" />
      </div>

      <!-- 已选中具体路径 -->
      <template v-else>
        <!-- 顶部 header -->
        <div class="main-header">
          <div class="path-info">
            <div class="path-label">当前路径</div>
            <div class="path-crumbs">
              <template v-for="(seg, i) in pathSegments" :key="i">
                <span v-if="i > 0" class="crumb-sep">/</span>
                <span class="crumb-item" :class="{ 'crumb-last': i === pathSegments.length - 1 }">
                  {{ seg }}
                </span>
              </template>
            </div>
          </div>
          <div class="header-actions">
            <el-button :icon="Refresh" @click="handleRefresh">刷新</el-button>
            <el-button v-hasPerm="['nc:folder:mkdir']" :icon="FolderAdd" @click="openMkdir">
              新建子目录
            </el-button>
            <el-button
              v-if="activeNode && !activeNode.isRoot"
              v-hasPerm="['nc:folder:rmdir']"
              type="danger"
              :icon="Delete"
              @click="handleDeleteFolder"
            >
              删除此目录
            </el-button>
            <el-button
              v-hasPerm="['nc:folder:setperm']"
              type="primary"
              :icon="Plus"
              @click="openAddRule"
            >
              添加规则
            </el-button>
          </div>
        </div>

        <!-- 规则表格 -->
        <el-table
          v-loading="rulesLoading"
          :data="rules"
          class="perm-table"
          :header-cell-style="{
            background: '#f5f7fa',
            color: '#606266',
            fontWeight: '600',
            fontSize: '13px',
          }"
        >
          <el-table-column label="用户" min-width="200">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="user-cell">
                <div
                  class="user-avatar"
                  :style="
                    !isRealAvatarUrl(row.avatarUrl) ? { background: avatarColor(row.username) } : {}
                  "
                >
                  <img
                    v-if="isRealAvatarUrl(row.avatarUrl)"
                    :src="resolveRuleAvatar(row.avatarUrl)"
                    class="user-avatar-img"
                    alt=""
                  />
                  <span v-else>{{ row.username.charAt(0).toUpperCase() }}</span>
                </div>
                <div class="user-info">
                  <div class="user-main">
                    <span class="user-name">{{ row.username }}</span>
                    <span v-if="row.userNickname !== row.username" class="user-nick">
                      {{ row.userNickname }}
                    </span>
                  </div>
                  <div v-if="row.deptName" class="dept-chip">
                    {{ row.deptName }}
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="权限" width="400">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="perm-badges">
                <span
                  v-for="lbl in row.permLabels"
                  :key="lbl"
                  class="perm-badge"
                  :class="`perm-badge--${lbl.toLowerCase()}`"
                >
                  {{ lbl }}
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="120" align="center">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="status-wrap">
                <span
                  class="status-dot"
                  :class="row.status ? 'status-dot--on' : 'status-dot--off'"
                />
                <span class="status-text">{{ row.status ? "生效" : "停用" }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="180" align="center">
            <template #default="{ row }: { row: FolderRuleVO }">
              <el-button
                v-hasPerm="['nc:folder:setperm']"
                link
                type="primary"
                size="small"
                @click="openEditRule(row)"
              >
                编辑
              </el-button>
              <el-button
                v-hasPerm="['nc:folder:delete']"
                link
                type="danger"
                size="small"
                @click="handleDeleteRule(row)"
              >
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="!rulesLoading && rules.length === 0" class="no-rules-hint">
          <el-icon><InfoFilled /></el-icon>
          该目录暂无 ACL 规则，点击「添加规则」开始配置访问权限
        </div>
      </template>
    </div>

    <!-- ===== 规则编辑弹窗 ===== -->
    <el-dialog
      v-model="ruleDialog.visible"
      :title="ruleDialog.ruleId ? '编辑权限规则' : '添加权限规则'"
      width="520px"
      :close-on-click-modal="false"
    >
      <el-form :model="ruleForm" label-width="80px" class="rule-form">
        <!-- 用户选择器（仅新增时可选；编辑时展示只读信息） -->
        <el-form-item label="目标用户">
          <template v-if="ruleDialog.ruleId">
            <span class="readonly-user">{{ ruleForm.selectedUserLabel || "—" }}</span>
          </template>
          <template v-else>
            <el-input
              v-model="userSearchQuery"
              placeholder="搜索用户名 / 昵称"
              clearable
              prefix-icon="Search"
              size="small"
              style="margin-bottom: 8px"
            />
            <div class="user-tree-wrap">
              <el-tree
                ref="userTreeRef"
                :data="userTreeData"
                :props="userTreeProps"
                :filter-node-method="filterUserNode"
                node-key="nodeKey"
                show-checkbox
                :expand-on-click-node="false"
                default-expand-all
                @check="handleUserTreeCheck"
              >
                <template #default="{ data: nodeData }: { data: UserTreeNode }">
                  <span v-if="nodeData.type === 'dept'" class="tree-dept-node">
                    <el-icon><OfficeBuilding /></el-icon>
                    {{ nodeData.name }}
                  </span>
                  <span v-else class="tree-user-node">
                    <el-icon><User /></el-icon>
                    {{ nodeData.nickname }}
                    <span class="tree-user-un">@{{ nodeData.username }}</span>
                  </span>
                </template>
              </el-tree>
              <div v-if="userTreeLoading" class="tree-loading">加载中…</div>
              <div v-else-if="!userTreeData.length" class="tree-empty">暂无已同步 NC 的用户</div>
            </div>
            <div class="selected-user-tip" :class="{ active: ruleForm.userIds.length > 0 }">
              <template v-if="ruleForm.userIds.length">
                已勾选
                <strong>{{ ruleForm.userIds.length }}</strong>
                个用户
              </template>
              <template v-else>请勾选用户，或勾选部门节点自动选中该部门所有成员</template>
            </div>
          </template>
        </el-form-item>

        <el-form-item label="权限预设">
          <el-radio-group v-model="ruleForm.preset" @change="applyPreset">
            <el-radio-button value="read">只读</el-radio-button>
            <el-radio-button value="write">读写</el-radio-button>
            <el-radio-button value="full">全权</el-radio-button>
            <el-radio-button value="custom">自定义</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="ruleForm.preset === 'custom'" label="权限位">
          <el-checkbox-group v-model="ruleForm.permBits">
            <el-checkbox :value="1">读取(R)</el-checkbox>
            <el-checkbox :value="2">写入(W)</el-checkbox>
            <el-checkbox :value="4">创建(C)</el-checkbox>
            <el-checkbox :value="8">删除(D)</el-checkbox>
            <el-checkbox :value="16">共享(S)</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="ruleForm.status" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="ruleDialog.loading"
          :disabled="!ruleDialog.ruleId && ruleForm.userIds.length === 0"
          @click="submitRule"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 新建子目录弹窗 ===== -->
    <el-dialog
      v-model="mkdirDialog.visible"
      title="新建子目录"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px" class="rule-form">
        <el-form-item label="父目录">
          <div class="mkdir-parent-path">
            <el-icon><Folder /></el-icon>
            {{ activeNode?.ncPath || "/" }}
          </div>
        </el-form-item>
        <el-form-item label="文件夹名">
          <el-input
            v-model="mkdirForm.name"
            placeholder="输入文件夹名（不含 /）"
            @keyup.enter="submitMkdir"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mkdirDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="mkdirDialog.loading"
          :disabled="!mkdirForm.name.trim()"
          @click="submitMkdir"
        >
          创建
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 删除子目录确认弹窗 ===== -->
    <el-dialog
      v-model="rmdirDialog.visible"
      title="删除子目录"
      width="480px"
      :close-on-click-modal="false"
    >
      <div class="rmdir-body">
        <!-- 危险提示横幅 -->
        <div class="rmdir-danger-banner">
          <el-icon class="rmdir-danger-icon"><Delete /></el-icon>
          <span>此操作将把文件夹移入 NC 回收站，30 天内可通过 NC 管理后台恢复</span>
        </div>

        <!-- 目标路径 -->
        <div class="rmdir-info-row">
          <span class="rmdir-label">目标路径</span>
          <span class="rmdir-path">{{ activeNode?.ncPath }}</span>
        </div>

        <!-- 受影响规则（预检加载中时显示 skeleton） -->
        <div class="rmdir-info-row" style="align-items: flex-start">
          <span class="rmdir-label">影响规则</span>
          <div v-if="rmdirDialog.previewLoading" class="rmdir-preview-loading">
            <el-icon class="is-loading">
              <svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32zm0 640a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V736a32 32 0 0 1 32-32zm448-192a32 32 0 0 1-32 32H736a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zM288 512a32 32 0 0 1-32 32H64a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zm411.44-235.26a32 32 0 0 1 0 45.26L563.18 458.26a32 32 0 1 1-45.26-45.26l136.26-136.26a32 32 0 0 1 45.26 0zm-355.62 355.62a32 32 0 0 1 0 45.26L207.56 813.88a32 32 0 1 1-45.26-45.26l136.26-136.26a32 32 0 0 1 45.26 0zm355.62 0a32 32 0 0 1 45.26 0l136.26 136.26a32 32 0 1 1-45.26 45.26L699.44 677.62a32 32 0 0 1 0-45.26zm-355.62-355.62a32 32 0 0 1 45.26 0L525.44 412.74a32 32 0 1 1-45.26 45.26L343.92 321.74a32 32 0 0 1 0-45.26z"
                />
              </svg>
            </el-icon>
            正在检查影响范围…
          </div>
          <div v-else-if="rmdirDialog.preview" class="rmdir-preview-content">
            <span v-if="rmdirDialog.preview.ruleCount === 0" class="rmdir-no-rules">
              无关联权限规则
            </span>
            <template v-else>
              <span class="rmdir-rule-count">
                共
                <strong>{{ rmdirDialog.preview.ruleCount }}</strong>
                条规则将被清除，影响用户：
              </span>
              <div class="rmdir-user-tags">
                <el-tag
                  v-for="u in rmdirDialog.preview.affectedUsers"
                  :key="u"
                  size="small"
                  type="warning"
                  effect="light"
                >
                  {{ u }}
                </el-tag>
              </div>
            </template>
          </div>
        </div>

        <!-- 二次确认输入 -->
        <div class="rmdir-confirm-row">
          <span class="rmdir-label">确认操作</span>
          <div class="rmdir-confirm-input-wrap">
            <el-input
              v-model="rmdirDialog.confirmText"
              placeholder="请输入目录名称以确认删除"
              size="small"
            />
            <div class="rmdir-confirm-hint">
              请输入
              <strong>{{ activeNode?.name }}</strong>
              以启用删除按钮
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="rmdirDialog.visible = false">取消</el-button>
        <el-button
          type="danger"
          :loading="rmdirDialog.loading"
          :disabled="rmdirDialog.previewLoading || rmdirDialog.confirmText !== activeNode?.name"
          @click="submitDeleteFolder"
        >
          确认删除
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * NC 文件夹权限配置页面：左侧文件夹树 + 右侧 ACL 规则管理面板。
 * 所属板块：nc / 文件权限管理。
 */
import type {
  FolderDeletePreview,
  FolderRuleVO,
  UserTreeDept,
  UserTreeUser,
} from "@/api/nc/folderTree";

import { computed, nextTick, onBeforeUnmount, reactive, ref, shallowRef, watch } from "vue";
import { resolveAvatarSrc } from "@/utils/avatarPresets";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Delete,
  Folder,
  FolderAdd,
  FolderOpened,
  InfoFilled,
  Lock,
  OfficeBuilding,
  Plus,
  Refresh,
  User,
} from "@element-plus/icons-vue";

import {
  batchSetFolderRules,
  createFolder,
  deleteFolder,
  deleteFolderRule,
  fetchFolderDeletePreview,
  fetchFolderList,
  fetchNcGroupList,
  fetchPathRules,
  fetchUserTree,
  setFolderRule,
} from "@/api/nc/folderTree";

// ─── 类型 ────────────────────────────────────────────────────────────────────

interface FolderTreeNode {
  key: string;
  name: string;
  ncPath: string;
  groupId: number;
  isRoot: boolean;
  hasRule: boolean;
}

/** 用于 el-tree 渲染的联合节点类型（部门或用户） */
type UserTreeNode =
  | (UserTreeDept & { nodeKey: string; children: UserTreeNode[] })
  | (UserTreeUser & { nodeKey: string });

// ─── 头像颜色（根据用户名 hash 稳定取色）────────────────────────────────────────

/**
 * 根据用户名哈希值返回固定的头像背景颜色。
 *
 * @param {string} name - 用户名
 * @returns {string} CSS 颜色字符串
 */
/**
 * 判断 avatarUrl 是否为真实可展示的图片地址（非 preset 占位符）。
 *
 * @param {string | undefined} url - 后端返回的 avatarUrl 字段。
 * @returns {boolean} 是否可直接用 img src 展示。
 */
function isRealAvatarUrl(url: string | undefined): boolean {
  if (!url) return false;
  return url.startsWith("http://") || url.startsWith("https://") || url.startsWith("preset:");
}

/**
 * 解析规则头像：preset 转为 SVG data URI，普通 URL 原样返回。
 *
 * @param {string | undefined} url - 后端返回的 avatarUrl 字段。
 * @returns {string} 可直接用于 img src 的地址。
 */
function resolveRuleAvatar(url: string | undefined): string {
  return resolveAvatarSrc(url ?? "");
}

function avatarColor(name: string): string {
  const palette = ["#1677ff", "#52c41a", "#fa8c16", "#722ed1", "#13c2c2", "#eb2f96", "#2f54eb"];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

// ─── 左侧宽度拖拽 ────────────────────────────────────────────────────────────────

const SIDEBAR_MIN = 160;
const SIDEBAR_MAX = 480;
const sidebarWidth = ref(220);

let _dragStartX = 0;
let _dragStartWidth = 0;

function handleResizeMove(e: MouseEvent): void {
  const delta = e.clientX - _dragStartX;
  sidebarWidth.value = Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, _dragStartWidth + delta));
}

function handleResizeEnd(): void {
  document.removeEventListener("mousemove", handleResizeMove);
  document.removeEventListener("mouseup", handleResizeEnd);
  document.body.style.cursor = "";
  document.body.style.userSelect = "";
}

function handleResizeStart(e: MouseEvent): void {
  _dragStartX = e.clientX;
  _dragStartWidth = sidebarWidth.value;
  document.body.style.cursor = "col-resize";
  document.body.style.userSelect = "none";
  document.addEventListener("mousemove", handleResizeMove);
  document.addEventListener("mouseup", handleResizeEnd);
}

onBeforeUnmount(() => {
  handleResizeEnd();
});

// ─── 文件夹树 ─────────────────────────────────────────────────────────────────

const treeRef = ref();
const treeProps = { label: "name" };

// TODO(类型): el-tree LoadFunction 的 node 参数类型与自定义 data 不兼容，使用 any 过渡
async function loadNode(node: any, resolve: (data: FolderTreeNode[]) => void): Promise<void> {
  if (node.level === 0) {
    try {
      const groups = await fetchNcGroupList();
      const roots = groups.map((g) => ({
        key: `root-${g.id}`,
        name: g.deptName,
        ncPath: "",
        groupId: g.id,
        isRoot: true,
        hasRule: false,
      }));
      resolve(roots);
      // 自动展开并选中第一个根节点，设置 activeNode 使展开后自动加载规则
      if (roots.length > 0) {
        nextTick(() => {
          activeNode.value = roots[0];
          treeRef.value?.setCurrentKey(roots[0].key);
          // 同步存储 elNode，确保自动选中的根节点也能触发 mkdir/rmdir 后的刷新
          const rootElNode = treeRef.value?.getNode(roots[0].key);
          activeElNode.value = rootElNode ?? null;
          rootElNode?.expand();
        });
      }
    } catch {
      resolve([]);
    }
    return;
  }

  const data = node.data as FolderTreeNode;
  const relPath = data.isRoot
    ? ""
    : (() => {
        const idx = data.ncPath.indexOf("/");
        return idx >= 0 ? data.ncPath.substring(idx + 1) : "";
      })();

  try {
    const result = await fetchFolderList({ groupId: data.groupId, path: relPath });
    if (data.isRoot) {
      // 回填根节点的实际 ncPath（Group Folder 挂载点名）
      data.ncPath = result.fullNcPath;
      data.key = result.fullNcPath;
      // 若该根节点正被用户选中（点击后触发展开），立即加载其规则
      if (activeNode.value?.groupId === data.groupId) {
        loadRules(data.ncPath);
      }
    }
    resolve(
      result.items.map((item) => ({
        key: item.ncPath,
        name: item.name,
        ncPath: item.ncPath,
        groupId: data.groupId,
        isRoot: false,
        hasRule: !!item.rule,
      }))
    );
  } catch {
    resolve([]);
  }
}

// ─── 节点选择 ─────────────────────────────────────────────────────────────────

const activeNode = ref<FolderTreeNode | null>(null);
/**
 * 当前激活的 el-tree Node 对象，用于直接操作节点（不经 key 查找）。
 * 使用 shallowRef 避免 Vue 深代理包装 el-tree 内部 Node，防止 expand/loadData 行为异常。
 */
const activeElNode = shallowRef<any>(null);

function handleNodeClick(data: FolderTreeNode, elNode: any): void {
  activeNode.value = data;
  activeElNode.value = elNode;
  rules.value = [];
  if (data.ncPath) {
    loadRules(data.ncPath);
  } else if (data.isRoot) {
    // 根节点尚未展开：直接用已捕获的 elNode 展开，避免通过 key 查找（key 会被 loadNode 修改）
    elNode?.expand();
  }
}

// ─── 右侧规则面板 ─────────────────────────────────────────────────────────────

const rules = ref<FolderRuleVO[]>([]);
const rulesLoading = ref(false);
const pathSegments = computed(() => activeNode.value?.ncPath.split("/") ?? []);

async function loadRules(ncPath: string): Promise<void> {
  rulesLoading.value = true;
  try {
    rules.value = await fetchPathRules(ncPath);
  } finally {
    rulesLoading.value = false;
  }
}

/**
 * 刷新当前选中节点：强制重载其子节点并重新拉取权限规则。
 */
async function handleRefresh(): Promise<void> {
  const node = activeNode.value;
  if (!node) return;
  // 刷新规则表格
  if (node.ncPath) {
    loadRules(node.ncPath);
  }
  // 刷新树节点子列表
  const treeNode = activeElNode.value;
  if (treeNode) {
    treeNode.loaded = false;
    treeNode.expanded = false;
    await nextTick();
    treeNode.expand();
  }
}

// ─── 用户树（规则弹窗数据源） ─────────────────────────────────────────────────

const userTreeRef = ref();
const userTreeData = ref<UserTreeNode[]>([]);
const userTreeLoading = ref(false);
const userSearchQuery = ref("");
const userTreeProps = { label: "name", children: "children" };

/** 将后端返回的 UserTreeDept[] 适配为 el-tree 节点格式 */
function buildUserTreeNodes(depts: UserTreeDept[]): UserTreeNode[] {
  return depts.map((dept) => ({
    ...dept,
    nodeKey: `dept-${dept.id ?? "none"}`,
    children: dept.children.map((u) => ({
      ...u,
      nodeKey: `user-${u.id}`,
    })) as UserTreeNode[],
  })) as UserTreeNode[];
}

async function loadUserTree(): Promise<void> {
  if (userTreeData.value.length) return;
  userTreeLoading.value = true;
  try {
    const raw = await fetchUserTree();
    userTreeData.value = buildUserTreeNodes(raw);
  } finally {
    userTreeLoading.value = false;
  }
}

/** el-tree filter-node-method：搜索用户名或昵称，同时保留部门父节点 */
// TODO(类型): FilterNodeMethodFunction 的 data 参数为 TreeNodeData（any-like），使用断言处理
function filterUserNode(query: string, data: unknown): boolean {
  if (!query) return true;
  const node = data as UserTreeNode;
  if (node.type === "dept") return true; // 部门节点始终显示
  const u = node as UserTreeUser & { nodeKey: string };
  const q = query.toLowerCase();
  return u.username.toLowerCase().includes(q) || u.nickname.toLowerCase().includes(q);
}

// 搜索词变化时触发 el-tree 过滤
watch(userSearchQuery, (val) => {
  userTreeRef.value?.filter(val);
});

// TODO(类型): el-tree @check 的 checkedInfo 参数类型为 CheckedInfo（含 TreeNodeData），使用 any 过渡
function handleUserTreeCheck(_data: unknown, state: { checkedNodes: unknown[] }): void {
  const users = (state.checkedNodes as UserTreeNode[]).filter(
    (n) => n.type === "user"
  ) as (UserTreeUser & {
    nodeKey: string;
  })[];
  ruleForm.userIds = users.map((u) => u.id);
}

// ─── 规则弹窗 ─────────────────────────────────────────────────────────────────

const ruleDialog = reactive({
  visible: false,
  loading: false,
  ruleId: null as number | null,
});
const ruleForm = reactive({
  /** 添加模式：多选用户 ID 列表 */
  userIds: [] as number[],
  /** 编辑模式：单个用户 ID */
  userId: null as number | null,
  selectedUserLabel: "",
  preset: "read" as "read" | "write" | "full" | "custom",
  permBits: [1] as number[],
  status: true,
});

const PRESET_BITS: Record<string, number[]> = {
  read: [1],
  write: [1, 4, 8, 16],
  full: [1, 2, 4, 8, 16],
};

function applyPreset(val: string | number | boolean | undefined): void {
  const key = String(val);
  if (key !== "custom") ruleForm.permBits = [...(PRESET_BITS[key] ?? ruleForm.permBits)];
}

function computePermBits(): number {
  return ruleForm.permBits.reduce((acc, b) => acc | b, 0);
}

async function openAddRule(): Promise<void> {
  ruleDialog.ruleId = null;
  ruleForm.userIds = [];
  ruleForm.userId = null;
  ruleForm.selectedUserLabel = "";
  ruleForm.preset = "read";
  ruleForm.permBits = [1];
  ruleForm.status = true;
  userSearchQuery.value = "";
  userTreeData.value = []; // 强制重新加载，确保数据最新
  ruleDialog.visible = true;
  await loadUserTree();
}

function openEditRule(row: FolderRuleVO): void {
  ruleDialog.ruleId = row.id;
  ruleForm.userId = row.userId;
  ruleForm.selectedUserLabel = `${row.userNickname}（${row.username}）`;
  ruleForm.preset = "custom";
  ruleForm.permBits = [1, 2, 4, 8, 16].filter((b) => (row.permissionBits & b) !== 0);
  ruleForm.status = row.status;
  ruleDialog.visible = true;
}

async function submitRule(): Promise<void> {
  if (!activeNode.value?.ncPath || ruleDialog.loading) return;
  // 前置校验
  if (ruleDialog.ruleId && !ruleForm.userId) return;
  if (!ruleDialog.ruleId && !ruleForm.userIds.length) {
    ElMessage.warning("请至少劾选一个用户");
    return;
  }
  ruleDialog.loading = true;
  try {
    if (ruleDialog.ruleId) {
      // 编辑模式：单用户更新
      await setFolderRule({
        groupId: activeNode.value.groupId,
        userId: ruleForm.userId!,
        ncPath: activeNode.value.ncPath,
        permissionBits: computePermBits(),
        status: ruleForm.status,
      });
      ElMessage.success("规则已保存，ACL 同步任务已入队");
    } else {
      // 添加模式：批量多用户
      const result = await batchSetFolderRules({
        groupId: activeNode.value.groupId,
        userIds: [...ruleForm.userIds],
        ncPath: activeNode.value.ncPath,
        permissionBits: computePermBits(),
        status: ruleForm.status,
      });
      ElMessage.success(
        `已处理 ${result.created + result.updated} 条规则（新建 ${result.created}，更新 ${result.updated}）`
      );
    }
    ruleDialog.visible = false;
    await loadRules(activeNode.value.ncPath);
  } catch {
    ElMessage.error("保存失败");
  } finally {
    ruleDialog.loading = false;
  }
}

async function handleDeleteRule(row: FolderRuleVO): Promise<void> {
  await ElMessageBox.confirm(
    `删除用户 ${row.userNickname}（${row.username}）在此路径的权限规则？`,
    "确认删除",
    { type: "warning" }
  );
  try {
    await deleteFolderRule(row.id, activeNode.value!.groupId);
    await loadRules(activeNode.value!.ncPath);
    ElMessage.success("规则已删除");
  } catch {
    ElMessage.error("删除失败");
  }
}

// ─── 删除文件夹弹窗 ───────────────────────────────────────────────────────────

const rmdirDialog = reactive({
  visible: false,
  loading: false,
  previewLoading: false,
  confirmText: "",
  preview: null as FolderDeletePreview | null,
});

/**
 * 点击「删除此目录」：打开确认弹窗并预检受影响范围。
 */
async function handleDeleteFolder(): Promise<void> {
  if (!activeNode.value || activeNode.value.isRoot) return;
  rmdirDialog.confirmText = "";
  rmdirDialog.preview = null;
  rmdirDialog.visible = true;
  rmdirDialog.previewLoading = true;
  try {
    rmdirDialog.preview = await fetchFolderDeletePreview(
      activeNode.value.groupId,
      activeNode.value.ncPath
    );
  } catch {
    ElMessage.error("预检失败，请稍后重试");
    rmdirDialog.visible = false;
  } finally {
    rmdirDialog.previewLoading = false;
  }
}

/**
 * 确认删除：清理 DB 规则并将文件夹移入 NC 回收站，完成后刷新父节点。
 */
async function submitDeleteFolder(): Promise<void> {
  if (!activeNode.value || rmdirDialog.loading) return;
  if (rmdirDialog.confirmText !== activeNode.value.name) return;

  const targetNode = activeNode.value;
  rmdirDialog.loading = true;
  try {
    const result = await deleteFolder({
      groupId: targetNode.groupId,
      ncPath: targetNode.ncPath,
    });
    rmdirDialog.visible = false;
    ElMessage.success(
      `目录「${targetNode.name}」已移入 NC 回收站` +
        (result.deletedRules > 0 ? `，同步清除 ${result.deletedRules} 条权限规则` : "")
    );

    // 通过已存储的 el-tree Node 的 parent 属性找父节点，无需 key 查找
    const currentElNode = activeElNode.value;
    const parentElNode = currentElNode?.parent;
    if (parentElNode && parentElNode.level > 0) {
      parentElNode.loaded = false;
      parentElNode.expanded = false;
      await nextTick();
      parentElNode.expand();
    }

    // 清空右侧面板
    activeNode.value = null;
    rules.value = [];
  } catch {
    ElMessage.error("删除失败，请重试");
  } finally {
    rmdirDialog.loading = false;
  }
}

// ─── 新建目录弹窗 ─────────────────────────────────────────────────────────────

const mkdirDialog = reactive({ visible: false, loading: false });
const mkdirForm = reactive({ name: "" });

function openMkdir(): void {
  mkdirForm.name = "";
  mkdirDialog.visible = true;
}

async function submitMkdir(): Promise<void> {
  if (!mkdirForm.name.trim() || !activeNode.value || mkdirDialog.loading) return;
  const node = activeNode.value;
  const slashIdx = node.ncPath.indexOf("/");
  const parentPath = slashIdx >= 0 ? node.ncPath.substring(slashIdx + 1) : "";
  mkdirDialog.loading = true;
  try {
    await createFolder({ groupId: node.groupId, parentPath, folderName: mkdirForm.name.trim() });
    mkdirDialog.visible = false;
    ElMessage.success("文件夹已创建");
    // 直接使用已存储的 el-tree Node 对象（不经过 key 查找，避免根节点 key 被修改导致查不到）
    const treeNode = activeElNode.value;
    if (treeNode) {
      treeNode.loaded = false;
      treeNode.expanded = false;
      await nextTick();
      treeNode.expand();
    }
  } catch {
    ElMessage.error("创建失败");
  } finally {
    mkdirDialog.loading = false;
  }
}
</script>

<style scoped lang="scss">
// ─── 整体布局 ──────────────────────────────────────────────────────────────────

.nc-perm-page {
  display: flex;
  height: calc(100vh - 120px);
  overflow: hidden;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
}

// ─── 左侧侧边栏 ────────────────────────────────────────────────────────────────

.nc-resize-handle {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
  transition: background 0.15s;

  &::after {
    position: absolute;
    inset: 0 -2px;
    content: "";
  }

  &:hover {
    background: var(--el-color-primary-light-5);
  }
}

.nc-sidebar {
  display: flex;
  flex-shrink: 0;
  flex-direction: column;
  overflow: hidden;
  background: #f3f3f3;
  border-right: 1px solid #e0e0e0;
}

.sidebar-header {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
  padding: 14px 16px;
  background: #f3f3f3;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-icon {
  font-size: 16px;
  color: var(--el-color-primary);
}

.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
}

.sidebar-scroll {
  flex: 1;

  :deep(.el-scrollbar__wrap) {
    overflow-x: hidden;
  }
}

// 文件夹树样式
.nc-tree {
  padding: 4px 0;
  background: transparent;

  :deep(.el-tree-node__content) {
    height: 34px;
    padding-right: 6px;
    margin: 1px 6px;
    border-radius: 4px;

    &:hover {
      background: rgba(0, 0, 0, 0.05);
    }
  }

  :deep(.el-tree-node.is-current > .el-tree-node__content) {
    font-weight: 500;
    color: #003d6b;
    background: #cce4f7;
  }
}

.tree-node-label {
  display: flex;
  gap: 6px;
  align-items: center;
  min-width: 0;
  font-size: 13px;

  .node-folder-icon {
    flex-shrink: 0;
    font-size: 15px;
    color: #e0a020;
  }

  .node-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-lock-icon {
    flex-shrink: 0;
    font-size: 12px;
    color: #999;
  }
}

// ─── 右侧主面板 ────────────────────────────────────────────────────────────────

.nc-main {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.main-empty {
  display: flex;
  flex: 1;
  align-items: center;
  justify-content: center;
}

// 顶部 header
.main-header {
  display: flex;
  flex-shrink: 0;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px 12px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.path-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.path-label {
  font-size: 11px;
  font-weight: 500;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.path-crumbs {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: center;
}

.crumb-item {
  font-size: 14px;
  font-weight: 400;
  color: #888;

  &.crumb-last {
    font-weight: 600;
    color: #1a1a1a;
  }
}

.crumb-sep {
  margin: 0 3px;
  color: #ccc;
}

.header-actions {
  display: flex;
  flex-shrink: 0;
  gap: 8px;
  align-items: center;
}

// ─── 表格 ──────────────────────────────────────────────────────────────────────

.perm-table {
  flex: 1;
  overflow-x: hidden;
  overflow-y: auto;

  :deep(.el-table__cell) {
    padding: 6px 0; // 压缩行高
  }

  :deep(.el-table__row:hover > td) {
    background: #f7f7f7 !important;
  }

  :deep(.el-table__inner-wrapper::before) {
    display: none;
  }

  // 无数据时撑高空块，使"暂无数据"居中显示
  :deep(.el-table__empty-block) {
    min-height: 300px;
  }
}

// 用户单元格
.user-cell {
  display: flex;
  gap: 10px;
  align-items: center;
}

.user-avatar {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  overflow: hidden;
  font-size: 12px;
  font-weight: 600;
  color: #fff;
  background: #e1e1e1; // 由 :style 动态覆盖为 avatarColor
  border-radius: 50%;
}

.user-avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.user-main {
  display: flex;
  gap: 6px;
  align-items: center;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
}

.user-nick {
  font-size: 12px;
  color: #888;
}

.dept-chip {
  display: inline-block;
  padding: 1px 6px;
  font-size: 11px;
  color: #666;
  white-space: nowrap;
  background: #f0f0f0;
  border: 1px solid #e0e0e0;
  border-radius: 3px;
}

// 权限徽章 - Win11 极简风格：统一浅灰底 + 轻着色文字
.perm-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.perm-badge {
  display: inline-block;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 500;
  color: #555;
  letter-spacing: 0.3px;
  white-space: nowrap;
  background: #f4f4f4;
  border: 1px solid #e2e2e2;
  border-radius: 3px;
}

// 状态指示
.status-wrap {
  display: flex;
  gap: 5px;
  align-items: center;
  justify-content: center;
}

.status-dot {
  flex-shrink: 0;
  width: 6px;
  height: 6px;
  border-radius: 50%;

  &--on {
    background: #38a169;
  }

  &--off {
    background: #bbb;
  }
}

.status-text {
  font-size: 12px;
  color: #666;
}

// 无规则提示
.no-rules-hint {
  display: flex;
  gap: 7px;
  align-items: center;
  padding: 12px 16px;
  margin: 0 20px 16px;
  font-size: 13px;
  color: #888;
  background: #fafafa;
  border: 1px dashed #ddd;
  border-radius: 4px;

  .el-icon {
    flex-shrink: 0;
    color: #bbb;
  }
}

// ─── 弹窗表单 ──────────────────────────────────────────────────────────────────

.rule-form {
  :deep(.el-form-item__label) {
    font-size: 13px;
  }
}

.mkdir-parent-path {
  display: flex;
  gap: 6px;
  align-items: center;
  width: 100%;
  padding: 6px 10px;
  font-size: 13px;
  color: #666;
  word-break: break-all;
  background: #f4f4f4;
  border: 1px solid #e5e5e5;
  border-radius: 4px;
}

// 规则弹窗 - 用户树
.user-tree-wrap {
  width: 100%;
  max-height: 240px;
  padding: 4px 0;
  overflow-y: auto;
  background: #fafafa;
  border: 1px solid #e5e5e5;
  border-radius: 4px;

  :deep(.el-tree-node__content) {
    height: 30px;
  }
}

.tree-dept-node {
  display: flex;
  gap: 4px;
  align-items: center;
  font-size: 13px;
  font-weight: 500;
  color: #666;
  cursor: default;
}

.tree-user-node {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 0 4px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 3px;

  &.selected {
    font-weight: 500;
    color: var(--el-color-primary);
  }
}

.tree-user-un {
  font-size: 11px;
  color: #aaa;
}

.tree-loading,
.tree-empty {
  padding: 16px;
  font-size: 12px;
  color: #aaa;
  text-align: center;
}

.selected-user-tip {
  margin-top: 6px;
  font-size: 12px;
  color: #aaa;

  &.active {
    font-weight: 500;
    color: var(--el-color-primary);
  }
}

.readonly-user {
  font-size: 13px;
  color: #666;
}

// ─── 删除目录弹窗 ──────────────────────────────────────────────────────────────

.rmdir-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rmdir-danger-banner {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 10px 14px;
  font-size: 13px;
  line-height: 1.6;
  color: #c0392b;
  background: #fff5f5;
  border: 1px solid #fecdcd;
  border-radius: 4px;

  .rmdir-danger-icon {
    flex-shrink: 0;
    margin-top: 2px;
    font-size: 16px;
    color: #c0392b;
  }
}

.rmdir-info-row {
  display: flex;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}

.rmdir-label {
  flex-shrink: 0;
  min-width: 56px;
  font-size: 12px;
  font-weight: 500;
  color: #888;
}

.rmdir-path {
  padding: 3px 8px;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 12px;
  color: #1a1a1a;
  word-break: break-all;
  background: #f4f4f4;
  border: 1px solid #e5e5e5;
  border-radius: 3px;
}

.rmdir-preview-loading {
  display: flex;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  color: #aaa;
}

.rmdir-preview-content {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rmdir-no-rules {
  font-size: 12px;
  color: #aaa;
}

.rmdir-rule-count {
  font-size: 13px;
  color: #555;

  strong {
    font-weight: 600;
    color: #d46b08;
  }
}

.rmdir-user-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.rmdir-confirm-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding-top: 12px;
  border-top: 1px solid #efefef;
}

.rmdir-confirm-input-wrap {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}

.rmdir-confirm-hint {
  font-size: 11px;
  color: #aaa;

  strong {
    font-family: "Consolas", "Courier New", monospace;
    color: #333;
  }
}
</style>
