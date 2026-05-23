<template>
  <div class="nc-folder-tree">
    <!-- 左侧：DEPT_ADMIN 群组列表 -->
    <div class="nc-folder-tree__sidebar">
      <div class="sidebar__header">
        <el-icon><Lock /></el-icon>
        NC 权限组
      </div>
      <div v-if="groupLoading" class="sidebar__loading">
        <el-skeleton :rows="5" animated />
      </div>
      <el-scrollbar v-else class="sidebar__scroll">
        <div
          v-for="group in groupList"
          :key="group.id"
          :class="['group-item', { 'is-active': selectedGroup?.id === group.id }]"
          @click="handleSelectGroup(group)"
        >
          <div class="group-item__dept">{{ group.deptName }}</div>
          <div class="group-item__name">{{ group.name }}</div>
        </div>
        <div v-if="groupList.length === 0" class="sidebar__empty">暂无 DEPT_ADMIN 群组</div>
      </el-scrollbar>
    </div>

    <!-- 右侧：文件夹树 -->
    <div class="nc-folder-tree__main">
      <div v-if="!selectedGroup" class="main__placeholder">
        <el-empty description="请在左侧选择权限组" :image-size="120" />
      </div>

      <template v-else>
        <div class="main__header">
          <div class="header__info">
            <el-icon class="header__icon"><FolderOpened /></el-icon>
            <span class="header__dept">{{ selectedGroup.deptName }}</span>
            <el-divider direction="vertical" />
            <el-tag type="info" size="small">{{ selectedGroup.name }}</el-tag>
          </div>
          <div class="header__tip">点击文件夹节点的展开箭头可加载子目录</div>
        </div>

        <el-scrollbar class="main__scroll">
          <el-tree
            :key="treeKey"
            ref="treeRef"
            :props="treeProps"
            :load="loadNode"
            node-key="ncPath"
            lazy
            :expand-on-click-node="false"
            :default-expand-all="false"
            class="nc-tree"
          >
            <template #default="{ data }: { data: FolderItem }">
              <div class="tree-node">
                <el-icon class="tree-node__icon"><Folder /></el-icon>
                <span class="tree-node__name">{{ data.name }}</span>
                <el-tag
                  v-if="data.rule"
                  :type="data.rule.status ? 'success' : 'warning'"
                  size="small"
                  class="tree-node__tag"
                >
                  {{ permBitsLabel(data.rule.permissionBits) }}
                </el-tag>
                <div class="tree-node__actions" @click.stop>
                  <el-button size="small" type="primary" link @click="handleSetRule(data)">
                    {{ data.rule ? "改权限" : "设权限" }}
                  </el-button>
                  <el-button size="small" link @click="handleMkdir(data)">新建子目录</el-button>
                  <el-button
                    v-if="data.rule"
                    size="small"
                    type="danger"
                    link
                    @click="handleDeleteRule(data)"
                  >
                    清除
                  </el-button>
                </div>
              </div>
            </template>
          </el-tree>
        </el-scrollbar>
      </template>
    </div>

    <!-- 设置权限对话框 -->
    <el-dialog
      v-model="ruleDialog.visible"
      title="设置目录权限"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form label-width="90px" class="rule-form">
        <el-form-item label="目录路径">
          <span class="form-text">{{ ruleDialog.ncPath }}</span>
        </el-form-item>
        <el-form-item label="权限选择">
          <div class="perm-presets">
            <el-button
              size="small"
              :type="computedPermBits === 1 ? 'primary' : 'default'"
              @click="ruleForm.permBits = [1]"
            >
              只读
            </el-button>
            <el-button
              size="small"
              :type="computedPermBits === 31 ? 'primary' : 'default'"
              @click="ruleForm.permBits = [1, 2, 4, 8, 16]"
            >
              完全控制
            </el-button>
          </div>
          <el-checkbox-group v-model="ruleForm.permBits" class="perm-checkboxes">
            <el-checkbox :value="1">读取 READ</el-checkbox>
            <el-checkbox :value="2">写入 WRITE</el-checkbox>
            <el-checkbox :value="4">创建 CREATE</el-checkbox>
            <el-checkbox :value="8">删除 DELETE</el-checkbox>
            <el-checkbox :value="16">分享 SHARE</el-checkbox>
          </el-checkbox-group>
          <div v-if="computedPermBits > 0" class="perm-preview">权限位：{{ computedPermBits }}</div>
        </el-form-item>
        <el-form-item label="是否生效">
          <el-switch v-model="ruleForm.status" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="ruleDialog.loading"
          :disabled="computedPermBits === 0"
          @click="submitSetRule"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 新建子目录对话框 -->
    <el-dialog
      v-model="mkdirDialog.visible"
      title="新建子目录"
      width="440px"
      :close-on-click-modal="false"
    >
      <el-form label-width="80px" class="mkdir-form">
        <el-form-item label="父目录">
          <span class="form-text">
            {{ mkdirDialog.parentPath ? `/${mkdirDialog.parentPath}` : "/ (根目录)" }}
          </span>
        </el-form-item>
        <el-form-item label="文件夹名">
          <el-input
            ref="folderNameInputRef"
            v-model="mkdirForm.folderName"
            placeholder="输入新文件夹名称"
            :maxlength="64"
            show-word-limit
            @keyup.enter="submitMkdir"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="mkdirDialog.visible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="mkdirDialog.loading"
          :disabled="!mkdirForm.folderName.trim()"
          @click="submitMkdir"
        >
          创建
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * NC 文件夹权限配置页面。
 * 以 DEPT_ADMIN 群组为基础，懒加载浏览 NC Group Folder 文件树，
 * 支持在任意目录层级创建子文件夹与分配 ACL 权限规则。
 * 所属板块：nc。
 */
import type { FolderItem, FolderRuleVO, NcGroupItem } from "@/api/nc/folderTree";

import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Folder, FolderOpened, Lock } from "@element-plus/icons-vue";

import {
  createFolder,
  deleteFolderRule,
  fetchFolderList,
  fetchNcGroupList,
  setFolderRule,
} from "@/api/nc/folderTree";

// ── 群组列表 ──────────────────────────────────────────────────────────
const groupList = ref<NcGroupItem[]>([]);
const groupLoading = ref(false);
const selectedGroup = ref<NcGroupItem | null>(null);

/**
 * 加载所有 DEPT_ADMIN 群组列表。
 */
async function loadGroupList(): Promise<void> {
  if (groupLoading.value) return;
  groupLoading.value = true;
  try {
    groupList.value = await fetchNcGroupList();
  } catch {
    ElMessage.error("加载群组列表失败");
  } finally {
    groupLoading.value = false;
  }
}

/**
 * 点击左侧群组，切换选中并重置文件树。
 *
 * @param {NcGroupItem} group 被点击的群组
 */
function handleSelectGroup(group: NcGroupItem): void {
  if (selectedGroup.value?.id === group.id) return;
  selectedGroup.value = group;
  // 通过更新 treeKey 强制销毁并重建 el-tree，触发全新懒加载
  treeKey.value = group.id;
}

// ── 文件夹树 ──────────────────────────────────────────────────────────
const treeRef = ref();
const treeKey = ref(0);

const treeProps = {
  label: "name",
  children: "children",
  isLeaf: () => false,
};

/**
 * el-tree 懒加载回调，拉取指定节点下的直属子目录。
 *
 * @param {{ level: number; data: Record<string, unknown> }} node el-tree 内部节点对象
 * @param {Function} resolve 数据注入回调
 *
 * 参数类型使用 Record<string, unknown> 而非 FolderItem：
 * LoadFunction 的 node.data 实际类型为 TreeNodeData = Record<string, any>，
 * 若写成 FolderItem 会违反函数参数逆变规则导致 TS2322，
 * 因此在函数体内通过类型断言获取具体字段。
 */
async function loadNode(
  node: { level: number; data: Record<string, unknown> },
  resolve: (items: FolderItem[]) => void
): Promise<void> {
  if (!selectedGroup.value) {
    resolve([]);
    return;
  }

  // level===0 为虚根节点，path 传空串加载 Group Folder 根目录
  let path = "";
  if (node.level > 0) {
    // node.data 运行时为 FolderItem，通过断言取 ncPath
    // ncPath = "mountPoint/a/b" → path = "a/b"（去掉挂载点前缀）
    const ncPath = (node.data as unknown as FolderItem).ncPath;
    const slashIdx = ncPath.indexOf("/");
    path = slashIdx >= 0 ? ncPath.substring(slashIdx + 1) : "";
  }

  try {
    const result = await fetchFolderList({
      groupId: selectedGroup.value.id,
      path,
    });
    resolve(result.items);
  } catch {
    ElMessage.error("加载文件夹失败");
    resolve([]);
  }
}

// ── 权限标签辅助函数 ──────────────────────────────────────────────────

/**
 * 将权限位转换为简短显示标签。
 *
 * @param {number} bits 权限位（1~31）
 * @returns {string} 简短标签，如 "只读"、"完全"、"R+W+C"
 */
function permBitsLabel(bits: number): string {
  if (bits === 1) return "只读";
  if (bits === 31) return "完全";
  const parts: string[] = [];
  if (bits & 1) parts.push("R");
  if (bits & 2) parts.push("W");
  if (bits & 4) parts.push("C");
  if (bits & 8) parts.push("D");
  if (bits & 16) parts.push("S");
  return parts.join("+") || String(bits);
}

/**
 * 将权限位分解为独立的位数组（供 el-checkbox-group 绑定）。
 *
 * @param {number} bits 权限位
 * @returns {number[]} 已选中的位值列表
 */
function decomposeBits(bits: number): number[] {
  const result: number[] = [];
  [1, 2, 4, 8, 16].forEach((b) => {
    if (bits & b) result.push(b);
  });
  return result;
}

// ── 设置权限对话框 ────────────────────────────────────────────────────
const ruleDialog = reactive({
  visible: false,
  loading: false,
  ncPath: "",
  existingRuleId: null as number | null,
});

const ruleForm = reactive({
  permBits: [1] as number[],
  status: true,
});

const computedPermBits = computed<number>(() =>
  ruleForm.permBits.reduce((acc, bit) => acc | bit, 0)
);

/**
 * 打开设置权限对话框。
 *
 * @param {FolderItem} data 当前节点数据
 */
function handleSetRule(data: FolderItem): void {
  ruleDialog.ncPath = data.ncPath;
  ruleDialog.existingRuleId = data.rule?.id ?? null;
  ruleForm.permBits = data.rule ? decomposeBits(data.rule.permissionBits) : [1];
  ruleForm.status = data.rule?.status ?? true;
  ruleDialog.visible = true;
}

/**
 * 提交设置权限（upsert）。
 */
async function submitSetRule(): Promise<void> {
  if (!selectedGroup.value || ruleDialog.loading) return;
  if (computedPermBits.value === 0) {
    ElMessage.warning("请至少选择一个权限");
    return;
  }
  ruleDialog.loading = true;
  try {
    const updatedRule = await setFolderRule({
      groupId: selectedGroup.value.id,
      ncPath: ruleDialog.ncPath,
      permissionBits: computedPermBits.value,
      status: ruleForm.status,
    });
    ElMessage.success("权限规则已保存，ACL 同步任务已入队");
    ruleDialog.visible = false;
    // 原地更新树节点的 rule 数据，无需全量刷新
    _updateNodeRule(ruleDialog.ncPath, updatedRule);
  } catch {
    ElMessage.error("保存权限规则失败");
  } finally {
    ruleDialog.loading = false;
  }
}

// ── 新建子目录对话框 ──────────────────────────────────────────────────
const mkdirDialog = reactive({
  visible: false,
  loading: false,
  parentNcPath: "",
  parentPath: "",
});

const mkdirForm = reactive({ folderName: "" });
const folderNameInputRef = ref();

/**
 * 打开新建子目录对话框。
 *
 * @param {FolderItem} data 父节点数据
 */
function handleMkdir(data: FolderItem): void {
  mkdirDialog.parentNcPath = data.ncPath;
  // parentPath = ncPath 去掉挂载点前缀
  const slashIdx = data.ncPath.indexOf("/");
  mkdirDialog.parentPath = slashIdx >= 0 ? data.ncPath.substring(slashIdx + 1) : "";
  mkdirForm.folderName = "";
  mkdirDialog.visible = true;
  nextTick(() => folderNameInputRef.value?.focus());
}

/**
 * 提交新建子目录。
 */
async function submitMkdir(): Promise<void> {
  if (!selectedGroup.value || mkdirDialog.loading) return;
  const name = mkdirForm.folderName.trim();
  if (!name) {
    ElMessage.warning("文件夹名称不能为空");
    return;
  }
  mkdirDialog.loading = true;
  try {
    await createFolder({
      groupId: selectedGroup.value.id,
      parentPath: mkdirDialog.parentPath,
      folderName: name,
    });
    ElMessage.success(`文件夹 "${name}" 创建成功`);
    mkdirDialog.visible = false;
    // 标记父节点为未加载，展开时会重新拉取子列表
    _reloadNode(mkdirDialog.parentNcPath);
  } catch {
    ElMessage.error("创建文件夹失败");
  } finally {
    mkdirDialog.loading = false;
  }
}

// ── 删除权限规则 ──────────────────────────────────────────────────────

/**
 * 弹出确认后删除节点上的权限规则。
 *
 * @param {FolderItem} data 当前节点数据
 */
async function handleDeleteRule(data: FolderItem): Promise<void> {
  if (!data.rule) return;
  try {
    await ElMessageBox.confirm(
      `确定要清除 "${data.ncPath}" 的权限规则吗？NC ACL 将被撤销。`,
      "清除权限规则",
      { type: "warning", confirmButtonText: "确定清除", cancelButtonText: "取消" }
    );
  } catch {
    return;
  }
  try {
    await deleteFolderRule(data.rule.id);
    ElMessage.success("权限规则已清除，ACL 撤销任务已入队");
    _updateNodeRule(data.ncPath, null);
  } catch {
    ElMessage.error("清除权限规则失败");
  }
}

// ── 树节点原地更新辅助 ────────────────────────────────────────────────

/**
 * 原地更新 el-tree 中指定节点的 rule 字段，无需全量刷新。
 *
 * @param {string} ncPath 节点 ncPath（节点 key）
 * @param {FolderRuleVO | null} rule 新规则数据，null 表示清除
 */
function _updateNodeRule(ncPath: string, rule: FolderRuleVO | null): void {
  const node = treeRef.value?.getNode(ncPath);
  if (node?.data) {
    node.data.rule = rule;
  }
}

/**
 * 将指定树节点标记为未加载，触发下次展开时重新拉取子列表。
 *
 * @param {string} ncPath 父节点的 ncPath（节点 key）
 */
function _reloadNode(ncPath: string): void {
  const node = treeRef.value?.getNode(ncPath);
  if (node) {
    node.loaded = false;
    node.childNodes = [];
    node.expanded = false;
  }
}

// ── 生命周期 ──────────────────────────────────────────────────────────
onMounted(loadGroupList);
</script>

<style scoped lang="scss">
.nc-folder-tree {
  display: flex;
  height: calc(100vh - 120px);
  min-height: 500px;
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
}

// ── 左侧群组列表 ────────────────────────────────────────────────────
.nc-folder-tree__sidebar {
  width: 220px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--el-border-color-light);
  background: var(--el-fill-color-extra-light);
}

.sidebar__header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  border-bottom: 1px solid var(--el-border-color-light);
  flex-shrink: 0;
}

.sidebar__loading {
  padding: 16px;
}

.sidebar__scroll {
  flex: 1;
  overflow: hidden;
}

.sidebar__empty {
  padding: 24px 16px;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  text-align: center;
}

.group-item {
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid var(--el-border-color-extra-light);

  &:hover {
    background: var(--el-fill-color-light);
  }

  &.is-active {
    background: var(--el-color-primary-light-9);
    border-right: 2px solid var(--el-color-primary);
  }
}

.group-item__dept {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-bottom: 2px;
}

.group-item__name {
  font-size: 13px;
  color: var(--el-text-color-primary);
  font-weight: 500;
}

// ── 右侧主区域 ──────────────────────────────────────────────────────
.nc-folder-tree__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main__placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.main__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  border-bottom: 1px solid var(--el-border-color-light);
  flex-shrink: 0;
}

.header__info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header__icon {
  color: var(--el-color-warning);
  font-size: 18px;
}

.header__dept {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header__tip {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.main__scroll {
  flex: 1;
  overflow: hidden;

  :deep(.el-scrollbar__wrap) {
    padding: 12px;
  }
}

// ── 树节点 ──────────────────────────────────────────────────────────
.nc-tree {
  :deep(.el-tree-node__content) {
    height: auto;
    min-height: 36px;
    padding: 4px 0;
  }
}

.tree-node {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  padding-right: 8px;
}

.tree-node__icon {
  flex-shrink: 0;
  color: var(--el-color-warning);
}

.tree-node__name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}

.tree-node__tag {
  flex-shrink: 0;
}

.tree-node__actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.15s;

  .el-tree-node__content:hover & {
    opacity: 1;
  }
}

// ── 对话框内容 ──────────────────────────────────────────────────────
.form-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-family: monospace;
  word-break: break-all;
}

.perm-presets {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}

.perm-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.perm-preview {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
