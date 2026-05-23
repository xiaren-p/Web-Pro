<template>
  <el-container class="nc-folder-perm">
    <!-- ===== 左侧：文件夹树 ===== -->
    <el-aside width="300px" class="folder-aside">
      <div class="aside-title">
        <el-icon><FolderOpened /></el-icon>
        文件夹目录
      </div>
      <el-scrollbar class="aside-scroll">
        <el-tree
          ref="treeRef"
          :props="treeProps"
          :load="loadNode"
          node-key="key"
          lazy
          highlight-current
          :expand-on-click-node="false"
          @node-click="handleNodeClick"
        >
          <template #default="{ data }">
            <span class="node-label">
              <el-icon><Folder /></el-icon>
              {{ data.name }}
              <el-icon v-if="data.hasRule" class="lock-icon"><Lock /></el-icon>
            </span>
          </template>
        </el-tree>
      </el-scrollbar>
    </el-aside>

    <!-- ===== 右侧：权限面板 ===== -->
    <el-main class="perm-panel">
      <!-- 未选中状态 -->
      <div v-if="!activeNode" class="empty-hint">
        <el-empty description="点击左侧文件夹查看权限配置" :image-size="80" />
      </div>

      <!-- 根节点正在加载 ncPath -->
      <div v-else-if="!activeNode.ncPath" class="empty-hint">
        <el-empty description="正在加载目录信息…" :image-size="80" />
      </div>

      <!-- 已选中具体路径 -->
      <template v-else>
        <!-- 路径面包屑 + 操作按钮 -->
        <div class="perm-header">
          <el-breadcrumb separator="/" class="path-breadcrumb">
            <el-breadcrumb-item v-for="(seg, i) in pathSegments" :key="i">
              {{ seg }}
            </el-breadcrumb-item>
          </el-breadcrumb>
          <div class="header-btns">
            <el-button size="small" @click="openMkdir">新建子目录</el-button>
            <el-button size="small" type="primary" @click="openAddRule">+ 添加规则</el-button>
          </div>
        </div>

        <!-- 规则表格 -->
        <el-table v-loading="rulesLoading" :data="rules" border size="small">
          <el-table-column label="用户" min-width="200">
            <template #default="{ row }: { row: FolderRuleVO }">
              <span class="user-cell">
                <span class="user-name">{{ row.username }}</span>
                <span v-if="row.userNickname !== row.username" class="user-nick">
                  {{ row.userNickname }}
                </span>
                <el-tag v-if="row.deptName" type="info" size="small" class="dept-tag">
                  {{ row.deptName }}
                </el-tag>
              </span>
            </template>
          </el-table-column>
          <el-table-column label="权限" min-width="160">
            <template #default="{ row }: { row: FolderRuleVO }">
              <el-tag v-for="lbl in row.permLabels" :key="lbl" size="small" class="mr-1">
                {{ lbl }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="80" align="center">
            <template #default="{ row }: { row: FolderRuleVO }">
              <el-tag :type="row.status ? 'success' : 'info'" size="small">
                {{ row.status ? "生效" : "停用" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }: { row: FolderRuleVO }">
              <el-button link type="primary" size="small" @click="openEditRule(row)">
                编辑
              </el-button>
              <el-button link type="danger" size="small" @click="handleDeleteRule(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div v-if="!rulesLoading && rules.length === 0" class="no-rules">
          该目录暂无 ACL 规则，点击「添加规则」配置访问权限
        </div>
      </template>
    </el-main>

    <!-- ===== 规则编辑弹窗 ===== -->
    <el-dialog
      v-model="ruleDialog.visible"
      :title="ruleDialog.ruleId ? '编辑权限规则' : '添加权限规则'"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form :model="ruleForm" label-width="80px">
        <!-- 用户选择器（仅新增时可选；编辑时展示只读信息） -->
        <el-form-item label="目标用户">
          <template v-if="ruleDialog.ruleId">
            <span class="readonly-user">
              {{ ruleForm.selectedUserLabel || "—" }}
            </span>
          </template>
          <template v-else>
            <!-- 搜索输入 -->
            <el-input
              v-model="userSearchQuery"
              placeholder="搜索用户名/昵称"
              clearable
              prefix-icon="Search"
              size="small"
              style="margin-bottom: 6px"
            />
            <!-- 部门-用户树 -->
            <div class="user-tree-wrap">
              <el-tree
                ref="userTreeRef"
                :data="userTreeData"
                :props="userTreeProps"
                :filter-node-method="filterUserNode"
                node-key="nodeKey"
                highlight-current
                :expand-on-click-node="false"
                default-expand-all
                @node-click="handleUserNodeClick"
              >
                <template #default="{ data: nodeData }: { data: UserTreeNode }">
                  <span v-if="nodeData.type === 'dept'" class="tree-dept-node">
                    <el-icon><OfficeBuilding /></el-icon>
                    {{ nodeData.name }}
                  </span>
                  <span
                    v-else
                    :class="['tree-user-node', { selected: ruleForm.userId === nodeData.id }]"
                  >
                    <el-icon><User /></el-icon>
                    {{ nodeData.nickname }}
                    <span class="tree-user-un">@{{ nodeData.username }}</span>
                  </span>
                </template>
              </el-tree>
              <div v-if="userTreeLoading" class="tree-loading">加载中…</div>
              <div v-else-if="!userTreeData.length" class="tree-empty">暂无已同步 NC 的用户</div>
            </div>
            <div v-if="ruleForm.userId" class="selected-user-tip">
              已选：{{ ruleForm.selectedUserLabel }}
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
        <el-button type="primary" :loading="ruleDialog.loading" @click="submitRule">确定</el-button>
      </template>
    </el-dialog>

    <!-- ===== 新建子目录弹窗 ===== -->
    <el-dialog
      v-model="mkdirDialog.visible"
      title="新建子目录"
      width="420px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px">
        <el-form-item label="父目录">
          <span class="text-sm text-gray-500">{{ activeNode?.ncPath || "/" }}</span>
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
  </el-container>
</template>

<script setup lang="ts">
/**
 * NC 文件夹权限配置页面：左侧文件夹树 + 右侧 ACL 规则管理面板。
 * 所属板块：nc / 文件权限管理。
 */
import type { FolderRuleVO, UserTreeDept, UserTreeUser } from "@/api/nc/folderTree";

import { computed, nextTick, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Folder, FolderOpened, Lock, OfficeBuilding, User } from "@element-plus/icons-vue";

import {
  createFolder,
  deleteFolderRule,
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
      // 自动展开并选中第一个根节点
      if (roots.length > 0) {
        nextTick(() => {
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

function handleUserNodeClick(data: UserTreeNode): void {
  if (data.type !== "user") return;
  const u = data as UserTreeUser & { nodeKey: string };
  ruleForm.userId = u.id;
  ruleForm.selectedUserLabel = `${u.nickname}（${u.username}）`;
}

// ─── 规则弹窗 ─────────────────────────────────────────────────────────────────

const ruleDialog = reactive({
  visible: false,
  loading: false,
  ruleId: null as number | null,
});
const ruleForm = reactive({
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
  if (!ruleForm.userId || !activeNode.value?.ncPath || ruleDialog.loading) return;
  ruleDialog.loading = true;
  try {
    await setFolderRule({
      userId: ruleForm.userId,
      ncPath: activeNode.value.ncPath,
      permissionBits: computePermBits(),
      status: ruleForm.status,
    });
    ruleDialog.visible = false;
    await loadRules(activeNode.value.ncPath);
    ElMessage.success("规则已保存，ACL 同步任务已入队");
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
    ElMessage.success("文件夹已创建，请重新展开父目录查看");
  } catch {
    ElMessage.error("创建失败");
  } finally {
    mkdirDialog.loading = false;
  }
}
</script>

<style scoped lang="scss">
.nc-folder-perm {
  height: calc(100vh - 120px);
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  overflow: hidden;
}

.folder-aside {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color);
  overflow: hidden;
}

.aside-title {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 16px;
  font-weight: 600;
  font-size: 14px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-fill-color-light);
  flex-shrink: 0;
}

.aside-scroll {
  flex: 1;

  :deep(.el-scrollbar__wrap) {
    overflow-x: hidden;
  }

  :deep(.el-tree) {
    padding: 8px 0;
  }
}

.node-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.lock-icon {
  color: var(--el-color-warning);
  font-size: 12px;
}

.perm-panel {
  padding: 16px;
  overflow-y: auto;
}

.empty-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.perm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.path-breadcrumb {
  font-size: 14px;
}

.header-btns {
  display: flex;
  gap: 8px;
}

.no-rules {
  margin-top: 12px;
  padding: 16px;
  text-align: center;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  background: var(--el-fill-color-lighter);
  border-radius: 4px;
}

// 规则表格 - 用户列
.user-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.user-name {
  font-weight: 500;
  font-size: 13px;
}

.user-nick {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.dept-tag {
  font-size: 11px;
}

// 规则弹窗 - 用户树
.user-tree-wrap {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  padding: 4px 0;
  max-height: 240px;
  overflow-y: auto;
  width: 100%;

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
  color: var(--el-color-primary);
}

.readonly-user {
  font-size: 13px;
  color: var(--el-text-color-regular);
}
</style>
