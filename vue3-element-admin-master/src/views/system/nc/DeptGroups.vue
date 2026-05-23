<template>
  <div class="nc-dept-groups">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <span class="toolbar__title">
          共 <strong>{{ rows.length }}</strong> 个部门，
          未初始化 <strong class="text-danger">{{ noneCount }}</strong> 个，
          不完整 <strong class="text-warning">{{ partialCount }}</strong> 个
        </span>
        <div class="toolbar__actions">
          <el-button :loading="listLoading" @click="loadList">刷新</el-button>
          <el-button
            type="primary"
            :loading="provisionAllLoading"
            :disabled="noneCount === 0"
            @click="handleProvisionAll"
          >一键初始化全部（{{ noneCount }}）</el-button>
        </div>
      </div>
    </el-card>

    <!-- 状态表格 -->
    <el-card shadow="never" class="table-card">
      <el-table v-loading="listLoading" :data="rows" border stripe>
        <el-table-column label="部门名称" prop="deptName" min-width="140" />
        <el-table-column label="部门编码" prop="deptCode" width="130">
          <template #default="{ row }: { row: DeptGroupRow }">
            <el-tag v-if="row.deptCode" type="info" size="small">{{ row.deptCode }}</el-tag>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="DEPT 群组" min-width="160">
          <template #default="{ row }: { row: DeptGroupRow }">
            <span v-if="row.deptGroup">
              <el-tag type="success" size="small">{{ row.deptGroup.code }}</el-tag>
            </span>
            <el-tag v-else type="danger" size="small">未创建</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="DEPT_ADMIN 群组" min-width="180">
          <template #default="{ row }: { row: DeptGroupRow }">
            <span v-if="row.adminGroup">
              <el-tag type="success" size="small">{{ row.adminGroup.code }}</el-tag>
            </span>
            <el-tag v-else type="danger" size="small">未创建</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="Group Folder ID" width="140" align="center">
          <template #default="{ row }: { row: DeptGroupRow }">
            <span v-if="row.deptGroup?.folderId !== null && row.deptGroup?.folderId !== undefined">
              <el-tag type="info" size="small">#{{ row.deptGroup.folderId }}</el-tag>
            </span>
            <span v-else class="text-muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }: { row: DeptGroupRow }">
            <el-tag v-if="row.status === 'ready'" type="success" size="small">就绪</el-tag>
            <el-tag v-else-if="row.status === 'partial'" type="warning" size="small">不完整</el-tag>
            <el-tag v-else type="danger" size="small">未初始化</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center" fixed="right">
          <template #default="{ row }: { row: DeptGroupRow }">
            <el-button
              v-if="row.status !== 'ready'"
              size="small"
              type="primary"
              :loading="provisioningIds.has(row.deptId)"
              @click="handleProvision(row)"
            >初始化</el-button>
            <el-tag v-else type="success" size="small" effect="plain">✓</el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 批量初始化结果对话框 -->
    <el-dialog
      v-model="resultDialog.visible"
      title="批量初始化结果"
      width="520px"
      :close-on-click-modal="false"
    >
      <div class="result-summary">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="待处理">{{ resultDialog.total }}</el-descriptions-item>
          <el-descriptions-item label="成功">
            <span class="text-success">{{ resultDialog.success }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="失败">
            <span class="text-danger">{{ resultDialog.failed.length }}</span>
          </el-descriptions-item>
        </el-descriptions>
      </div>
      <el-table
        v-if="resultDialog.failed.length > 0"
        :data="resultDialog.failed"
        class="mt-3"
        border
        size="small"
      >
        <el-table-column label="部门" prop="deptName" min-width="100" />
        <el-table-column label="错误信息" prop="error" min-width="200" show-overflow-tooltip />
      </el-table>
      <template #footer>
        <el-button type="primary" @click="resultDialog.visible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
/**
 * NC 部门群组初始化页：展示所有部门与 NC 双群组（DEPT + DEPT_ADMIN）的同步状态，
 * 并支持单部门初始化和批量补全。
 * 所属板块：system/nc
 */
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  fetchDeptGroupStatus,
  provisionAllDeptGroups,
  provisionDeptGroup,
  type DeptGroupRow,
} from "@/api/nc/deptGroups";

// ── 列表数据 ─────────────────────────────────────────────────────────────────
const listLoading = ref(false);
const rows = ref<DeptGroupRow[]>([]);

const noneCount = computed(() => rows.value.filter((r) => r.status === "none").length);
const partialCount = computed(() => rows.value.filter((r) => r.status === "partial").length);

async function loadList(): Promise<void> {
  listLoading.value = true;
  try {
    rows.value = await fetchDeptGroupStatus();
  } catch {
    ElMessage.error("加载部门群组状态失败");
  } finally {
    listLoading.value = false;
  }
}

// ── 单部门初始化 ──────────────────────────────────────────────────────────────
const provisioningIds = ref<Set<number>>(new Set());

async function handleProvision(row: DeptGroupRow): Promise<void> {
  provisioningIds.value = new Set([...provisioningIds.value, row.deptId]);
  try {
    const updated = await provisionDeptGroup(row.deptId);
    // 就地更新当前行，避免全量刷新
    const idx = rows.value.findIndex((r) => r.deptId === row.deptId);
    if (idx >= 0) rows.value[idx] = updated;
    ElMessage.success(`${row.deptName} 初始化任务已入队`);
  } catch {
    ElMessage.error(`${row.deptName} 初始化失败`);
  } finally {
    const next = new Set(provisioningIds.value);
    next.delete(row.deptId);
    provisioningIds.value = next;
  }
}

// ── 批量初始化 ────────────────────────────────────────────────────────────────
const provisionAllLoading = ref(false);

const resultDialog = reactive<{
  visible: boolean;
  total: number;
  success: number;
  failed: Array<{ deptId: number; deptName: string; error: string }>;
}>({
  visible: false,
  total: 0,
  success: 0,
  failed: [],
});

async function handleProvisionAll(): Promise<void> {
  await ElMessageBox.confirm(
    `将对 ${noneCount.value} 个未初始化的部门批量入队 NC 群组创建任务，是否继续？`,
    "确认批量初始化",
    { type: "warning" },
  );

  provisionAllLoading.value = true;
  try {
    const res = await provisionAllDeptGroups();
    resultDialog.total = res.total;
    resultDialog.success = res.success;
    resultDialog.failed = res.failed;
    resultDialog.visible = true;
    // 刷新列表
    await loadList();
  } catch {
    ElMessage.error("批量初始化失败");
  } finally {
    provisionAllLoading.value = false;
  }
}

// ── 生命周期 ──────────────────────────────────────────────────────────────────
onMounted(loadList);
</script>

<style scoped lang="scss">
.nc-dept-groups {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toolbar-card {
  :deep(.el-card__body) {
    padding: 12px 16px;
  }
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;

  &__title {
    font-size: 14px;
    color: var(--el-text-color-regular);
  }

  &__actions {
    display: flex;
    gap: 8px;
  }
}

.table-card {
  flex: 1;
}

.result-summary {
  margin-bottom: 8px;
}

.text-success {
  color: var(--el-color-success);
  font-weight: 600;
}

.text-danger {
  color: var(--el-color-danger);
  font-weight: 600;
}

.text-warning {
  color: var(--el-color-warning);
  font-weight: 600;
}

.text-muted {
  color: var(--el-text-color-placeholder);
}
</style>
