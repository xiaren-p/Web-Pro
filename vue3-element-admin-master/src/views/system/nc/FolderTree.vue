<template>
  <div class="nc-perm-page">
    <!-- ===== 左侧：文件夹树 ===== -->
    <div class="nc-sidebar">
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
            <el-button v-hasPerm="['nc:folder:setperm']" type="primary" :icon="Plus" @click="openAddRule">
              添加规则
            </el-button>
          </div>
        </div>

        <!-- 规则表格 -->
        <el-table
          v-loading="rulesLoading"
          :data="rules"
          class="perm-table"
          :header-cell-style="{ background: '#f5f7fa', color: '#606266', fontWeight: '600', fontSize: '13px' }"
        >
          <el-table-column label="用户" min-width="220">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="user-cell">
                <div class="user-avatar" :style="{ background: avatarColor(row.username) }">
                  {{ row.username.charAt(0).toUpperCase() }}
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

          <el-table-column label="权限" min-width="240">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="perm-badges">
                <span
                  v-for="lbl in row.permLabels"
                  :key="lbl"
                  class="perm-badge"
                  :class="`perm-badge--${lbl.toLowerCase()}`"
                >{{ lbl }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }: { row: FolderRuleVO }">
              <div class="status-wrap">
                <span class="status-dot" :class="row.status ? 'status-dot--on' : 'status-dot--off'" />
                <span class="status-text">{{ row.status ? "生效" : "停用" }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }: { row: FolderRuleVO }">
              <el-button v-hasPerm="['nc:folder:setperm']" link type="primary" size="small" @click="openEditRule(row)">
                编辑
              </el-button>
              <el-button v-hasPerm="['nc:folder:delete']" link type="danger" size="small" @click="handleDeleteRule(row)">
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
                已勾选 <strong>{{ ruleForm.userIds.length }}</strong> 个用户
              </template>
              <template v-else>
                请勾选用户，或勾选部门节点自动选中该部门所有成员
              </template>
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
        >确定</el-button>
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
        <div class="rmdir-info-row" style="align-items: flex-start;">
          <span class="rmdir-label">影响规则</span>
          <div v-if="rmdirDialog.previewLoading" class="rmdir-preview-loading">
            <el-icon class="is-loading"><svg viewBox="0 0 1024 1024" xmlns="http://www.w3.org/2000/svg"><path d="M512 64a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V96a32 32 0 0 1 32-32zm0 640a32 32 0 0 1 32 32v192a32 32 0 0 1-64 0V736a32 32 0 0 1 32-32zm448-192a32 32 0 0 1-32 32H736a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zM288 512a32 32 0 0 1-32 32H64a32 32 0 1 1 0-64h192a32 32 0 0 1 32 32zm411.44-235.26a32 32 0 0 1 0 45.26L563.18 458.26a32 32 0 1 1-45.26-45.26l136.26-136.26a32 32 0 0 1 45.26 0zm-355.62 355.62a32 32 0 0 1 0 45.26L207.56 813.88a32 32 0 1 1-45.26-45.26l136.26-136.26a32 32 0 0 1 45.26 0zm355.62 0a32 32 0 0 1 45.26 0l136.26 136.26a32 32 0 1 1-45.26 45.26L699.44 677.62a32 32 0 0 1 0-45.26zm-355.62-355.62a32 32 0 0 1 45.26 0L525.44 412.74a32 32 0 1 1-45.26 45.26L343.92 321.74a32 32 0 0 1 0-45.26z"/></svg></el-icon>
            正在检查影响范围…
          </div>
          <div v-else-if="rmdirDialog.preview" class="rmdir-preview-content">
            <span v-if="rmdirDialog.preview.ruleCount === 0" class="rmdir-no-rules">
              无关联权限规则
            </span>
            <template v-else>
              <span class="rmdir-rule-count">
                共 <strong>{{ rmdirDialog.preview.ruleCount }}</strong> 条规则将被清除，影响用户：
              </span>
              <div class="rmdir-user-tags">
                <el-tag
                  v-for="u in rmdirDialog.preview.affectedUsers"
                  :key="u"
                  size="small"
                  type="warning"
                  effect="light"
                >{{ u }}</el-tag>
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
              请输入 <strong>{{ activeNode?.name }}</strong> 以启用删除按钮
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
import type { FolderDeletePreview, FolderRuleVO, UserTreeDept, UserTreeUser } from "@/api/nc/folderTree";

import { computed, nextTick, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Folder, FolderAdd, FolderOpened, InfoFilled, Lock, OfficeBuilding, Plus, User, Delete } from "@element-plus/icons-vue";

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
function avatarColor(name: string): string {
  const palette = ['#1677ff', '#52c41a', '#fa8c16', '#722ed1', '#13c2c2', '#eb2f96', '#2f54eb'];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return palette[Math.abs(hash) % palette.length];
}

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
          treeRef.value?.getNode(roots[0].key)?.expand();
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

function handleNodeClick(data: FolderTreeNode): void {
  activeNode.value = data;
  rules.value = [];
  if (data.ncPath) {
    loadRules(data.ncPath);
  } else if (data.isRoot) {
    // 根节点尚未展开：自动触发展开，loadNode 完成后会回调 loadRules
    treeRef.value?.getNode(data.key)?.expand();
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
function handleUserTreeCheck(
  _data: unknown,
  state: { checkedNodes: unknown[] },
): void {
  const users = (state.checkedNodes as UserTreeNode[]).filter((n) => n.type === "user") as (UserTreeUser & {
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
        `已处理 ${result.created + result.updated} 条规则（新建 ${result.created}，更新 ${result.updated}）`,
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
    await deleteFolderRule(row.id);
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
      activeNode.value.ncPath,
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
        (result.deletedRules > 0 ? `，同步清除 ${result.deletedRules} 条权限规则` : ""),
    );

    // 刷新父节点：找到父节点并强制重新懒加载
    const parentPath = targetNode.ncPath.includes("/")
      ? targetNode.ncPath.substring(0, targetNode.ncPath.lastIndexOf("/"))
      : targetNode.ncPath;
    const parentNode = treeRef.value?.getNode(parentPath);
    if (parentNode) {
      parentNode.loaded = false;
      parentNode.expanded = false;
      await nextTick();
      parentNode.expand();
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
    // 自动刷新：强制重载当前树节点的子目录列表
    const treeNode = treeRef.value?.getNode(node.key);
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
  background: #fff;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

// ─── 左侧侧边栏 ────────────────────────────────────────────────────────────────

.nc-sidebar {
  width: 240px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-lighter);
  background: #fafbfc;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 18px;
  background: #fff;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
}

.sidebar-icon {
  color: var(--el-color-primary);
  font-size: 17px;
}

.sidebar-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.sidebar-scroll {
  flex: 1;

  :deep(.el-scrollbar__wrap) {
    overflow-x: hidden;
  }
}

// 文件夹树样式
.nc-tree {
  background: transparent;
  padding: 6px 0;

  :deep(.el-tree-node__content) {
    height: 38px;
    border-radius: 6px;
    margin: 1px 8px;
    padding-right: 8px;

    &:hover {
      background: rgba(64, 158, 255, 0.08);
    }
  }

  :deep(.el-tree-node.is-current > .el-tree-node__content) {
    background: rgba(64, 158, 255, 0.12);
    color: var(--el-color-primary);
    font-weight: 500;
  }
}

.tree-node-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  min-width: 0;

  .node-folder-icon {
    color: #faad14;
    font-size: 15px;
    flex-shrink: 0;
  }

  .node-name {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .node-lock-icon {
    color: var(--el-color-primary);
    font-size: 12px;
    flex-shrink: 0;
    opacity: 0.7;
  }
}

// ─── 右侧主面板 ────────────────────────────────────────────────────────────────

.nc-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.main-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

// 顶部 header
.main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-shrink: 0;
  gap: 16px;
}

.path-info {
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
}

.path-label {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
  text-transform: uppercase;
  letter-spacing: 0.6px;
  font-weight: 500;
}

.path-crumbs {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 2px;
}

.crumb-item {
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-secondary);

  &.crumb-last {
    color: var(--el-text-color-primary);
    font-weight: 600;
  }
}

.crumb-sep {
  margin: 0 4px;
  color: var(--el-text-color-placeholder);
  font-weight: 400;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-shrink: 0;
}

// ─── 表格 ──────────────────────────────────────────────────────────────────────

.perm-table {
  flex: 1;
  padding: 0 24px 16px;
  overflow: auto;

  :deep(.el-table__row:hover > td) {
    background: #f5f9ff !important;
  }

  :deep(.el-table__inner-wrapper::before) {
    display: none; // 去掉底部分隔线
  }
}

// 用户单元格
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  flex-shrink: 0;
  letter-spacing: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.user-main {
  display: flex;
  align-items: center;
  gap: 6px;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.user-nick {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dept-chip {
  display: inline-block;
  padding: 0 6px;
  height: 18px;
  line-height: 18px;
  font-size: 11px;
  border-radius: 3px;
  background: #f0f5ff;
  border: 1px solid #adc6ff;
  color: #2f54eb;
  white-space: nowrap;
}

// 权限徽章
.perm-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.perm-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
  white-space: nowrap;

  &--read {
    background: #e6f4ff;
    color: #1677ff;
  }

  &--write {
    background: #fff7e6;
    color: #d46b08;
  }

  &--create {
    background: #f6ffed;
    color: #389e0d;
  }

  &--delete {
    background: #fff1f0;
    color: #cf1322;
  }

  &--share {
    background: #f9f0ff;
    color: #531dab;
  }
}

// 状态指示
.status-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;

  &--on {
    background: #52c41a;
    box-shadow: 0 0 0 2px rgba(82, 196, 26, 0.2);
  }

  &--off {
    background: #bfbfbf;
  }
}

.status-text {
  font-size: 12px;
  color: var(--el-text-color-regular);
}

// 无规则提示
.no-rules-hint {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0 24px 16px;
  padding: 14px 18px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px dashed var(--el-border-color);
  font-size: 13px;
  color: var(--el-text-color-secondary);

  .el-icon {
    color: var(--el-text-color-placeholder);
    flex-shrink: 0;
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
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  padding: 6px 10px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
  width: 100%;
  word-break: break-all;
}

// 规则弹窗 - 用户树
.user-tree-wrap {
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  padding: 4px 0;
  max-height: 240px;
  overflow-y: auto;
  width: 100%;
  background: #fafafa;

  :deep(.el-tree-node__content) {
    height: 30px;
  }
}

.tree-dept-node {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  cursor: default;
}

.tree-user-node {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  cursor: pointer;
  padding: 0 4px;
  border-radius: 3px;

  &.selected {
    color: var(--el-color-primary);
    font-weight: 500;
  }
}

.tree-user-un {
  font-size: 11px;
  color: var(--el-text-color-placeholder);
}

.tree-loading,
.tree-empty {
  text-align: center;
  padding: 16px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.selected-user-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);

  &.active {
    color: var(--el-color-primary);
    font-weight: 500;
  }
}

.readonly-user {
  font-size: 13px;
  color: var(--el-text-color-regular);
}

// ─── 删除目录弹窗 ──────────────────────────────────────────────────────────────

.rmdir-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rmdir-danger-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: #fff2f0;
  border: 1px solid #ffccc7;
  border-radius: 6px;
  font-size: 13px;
  color: #cf1322;
  line-height: 1.6;

  .rmdir-danger-icon {
    font-size: 18px;
    flex-shrink: 0;
    margin-top: 1px;
    color: #cf1322;
  }
}

.rmdir-info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
}

.rmdir-label {
  min-width: 56px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
  font-weight: 500;
  flex-shrink: 0;
}

.rmdir-path {
  font-family: monospace;
  font-size: 13px;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-lighter);
  padding: 3px 8px;
  border-radius: 4px;
  word-break: break-all;
}

.rmdir-preview-loading {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.rmdir-preview-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rmdir-no-rules {
  color: var(--el-text-color-placeholder);
  font-size: 12px;
}

.rmdir-rule-count {
  font-size: 13px;
  color: var(--el-text-color-regular);

  strong {
    color: #d46b08;
    font-weight: 600;
  }
}

.rmdir-user-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.rmdir-confirm-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding-top: 4px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.rmdir-confirm-input-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rmdir-confirm-hint {
  font-size: 11px;
  color: var(--el-text-color-placeholder);

  strong {
    color: var(--el-text-color-primary);
    font-family: monospace;
  }
}
</style>
