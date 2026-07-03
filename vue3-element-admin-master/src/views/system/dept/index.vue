<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="关键字" prop="keywords">
          <el-input
            v-model="queryParams.keywords"
            placeholder="部门名称"
            @keyup.enter="handleQuery"
          />
        </el-form-item>

        <el-form-item label="部门状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 100px">
            <el-option :value="1" label="正常" />
            <el-option :value="0" label="禁用" />
          </el-select>
        </el-form-item>

        <el-form-item class="search-buttons">
          <el-button class="filter-item" type="primary" icon="search" @click="handleQuery">
            搜索
          </el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button v-if="isCompanyAdmin" type="success" icon="plus" @click="handleOpenDialog()">
            新增
          </el-button>
          <el-button
            v-if="isCompanyAdmin"
            type="danger"
            :disabled="selectIds.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
        </div>
      </div>

      <el-table
        v-loading="loading"
        :data="deptList"
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="isCompanyAdmin" type="selection" width="55" align="center" />
        <el-table-column prop="name" label="部门名称" min-width="200" />
        <el-table-column prop="code" label="部门编号" width="200" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.status == 1" type="success">正常</el-tag>
            <el-tag v-else type="info">禁用</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="sort" label="排序" width="100" />

        <el-table-column label="操作" fixed="right" align="left" width="200">
          <template #default="scope">
            <el-button
              v-if="
                isCompanyAdmin ||
                (isDeptAdmin &&
                  (String(scope.row.id) === myDeptIdStr ||
                    myDeptDescendantIds.has(String(scope.row.id))))
              "
              type="primary"
              link
              size="small"
              icon="plus"
              @click.stop="handleOpenDialog(scope.row.id, undefined)"
            >
              新增
            </el-button>
            <el-button
              v-if="
                isCompanyAdmin ||
                (isDeptAdmin &&
                  (String(scope.row.id) === myDeptIdStr ||
                    myDeptDescendantIds.has(String(scope.row.id))))
              "
              type="primary"
              link
              size="small"
              icon="edit"
              @click.stop="handleOpenDialog(scope.row.parentId, scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-if="
                isCompanyAdmin || (isDeptAdmin && myDeptDescendantIds.has(String(scope.row.id)))
              "
              type="danger"
              link
              size="small"
              icon="delete"
              @click.stop="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <DeptFormDialog ref="deptFormDialogRef" @success="handleQuery" />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

import { useUserStore } from "@/store/modules/user-store";
import { DeptAPI, type DeptVO, type DeptQuery } from "@/api/dept";
import DeptFormDialog from "./components/DeptFormDialog.vue";

defineOptions({
  name: "Dept",
  inheritAttrs: false,
});

const queryFormRef = ref();
const deptFormDialogRef = ref();
const userStore = useUserStore();

/** Query form ref. */
const isCompanyAdmin = computed(() => userStore.userInfo.roles?.includes("ROOT") ?? false);

/** Whether current user is department admin. */
const isDeptAdmin = computed(() => userStore.userInfo.roles?.includes("dept_admin") ?? false);

/** Current user department ID. */
const myDeptId = computed(() => userStore.userInfo.deptId ?? null);

/** Current user department ID as string (aligned with DeptVO.id type). */
const myDeptIdStr = computed<string | null>(() =>
  myDeptId.value != null ? String(myDeptId.value) : null
);

/**
 * Recursively collect all descendant IDs in the node tree.
 *
 * @param children - Current level child node list.
 * @param result - Collection result set.
 */
function addAllDescendants(children: DeptVO[] | undefined, result: Set<string>): void {
  children?.forEach((c) => {
    result.add(String(c.id));
    addAllDescendants(c.children, result);
  });
}

/**
 * Find target node in tree and recursively collect all descendant IDs (excluding self).
 *
 * @param nodes - Current level node list.
 * @param targetId - Target parent node ID.
 * @param result - Collection result set.
 * @returns Whether target node was found.
 */
function collectDescendantIds(nodes: DeptVO[], targetId: string, result: Set<string>): boolean {
  for (const node of nodes) {
    if (String(node.id) === targetId) {
      addAllDescendants(node.children, result);
      return true;
    }
    if (node.children && collectDescendantIds(node.children, targetId, result)) return true;
  }
  return false;
}

/** All descendant department IDs of current user department (excluding self). */
const myDeptDescendantIds = computed<Set<string>>(() => {
  const result = new Set<string>();
  if (!isDeptAdmin.value || !myDeptIdStr.value || !deptList.value) return result;
  collectDescendantIds(deptList.value, myDeptIdStr.value, result);
  return result;
});

const loading = ref(false);
const selectIds = ref<string[]>([]);
const queryParams = reactive<DeptQuery>({ pageNum: 1, pageSize: 10 });
const deptList = ref<DeptVO[]>();

/** Query department list. */
function handleQuery() {
  loading.value = true;
  DeptAPI.getList(queryParams).then((data) => {
    deptList.value = data;
    loading.value = false;
  });
}

/** Reset query and re-search. */
function handleResetQuery() {
  queryFormRef.value.resetFields();
  handleQuery();
}

/** Table selection change handler. */
function handleSelectionChange(selection: DeptVO[]) {
  selectIds.value = selection.map((item) => String(item.id));
}

/**
 * Open department form dialog.
 *
 * @param parentId - Parent department ID (for creating child).
 * @param deptId - Department ID (for editing).
 */
function handleOpenDialog(parentId?: string, deptId?: string) {
  deptFormDialogRef.value.open(parentId, deptId);
}

/** Delete department (single or batch). */
function handleDelete(deptId?: string) {
  const deptIds = [deptId || selectIds.value].join(",");

  if (!deptIds) {
    ElMessage.warning("请勾选删除项");
    return;
  }

  ElMessageBox.confirm(
    `<div style="font-size:14px;line-height:1.7;color:#303133">
      <p style="margin:0 0 12px;font-weight:600;font-size:15px">确认删除所选部门？此操作不可撤销。</p>
      <div style="border-top:1px solid #ebeef5;margin-bottom:12px"></div>
      <p style="margin:0 0 8px;font-weight:600;color:#606266">Nextcloud 同步影响</p>
      <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px">
        <div style="display:flex;align-items:flex-start;gap:8px">
          <span style="color:#f56c6c;font-size:15px;flex-shrink:0;margin-top:1px">x</span>
          <span>部门对应的 NC 群组将被<b>立即删除</b></span>
        </div>
        <div style="display:flex;align-items:flex-start;gap:8px">
          <span style="color:#f56c6c;font-size:15px;flex-shrink:0;margin-top:1px">x</span>
          <span>所有成员将<b>即刻失去</b>部门文件夹的访问权限</span>
        </div>
        <div style="display:flex;align-items:flex-start;gap:8px">
          <span style="color:#67c23a;font-size:15px;flex-shrink:0;margin-top:1px">OK</span>
          <span>部门文件夹及文件<b>不会被删除</b>，保留为孤立状态</span>
        </div>
      </div>
      <div style="background:#fffbe6;border:1px solid #ffe58f;border-radius:6px;padding:10px 12px;color:#8a6d00;font-size:13px;line-height:1.6">
        * 建议删除前先在 Nextcloud 中备份或迁移文件夹内的数据
      </div>
    </div>`,
    "删除部门警告",
    {
      confirmButtonText: "我已知晓，确认删除",
      cancelButtonText: "取消",
      type: "warning",
      dangerouslyUseHTMLString: true,
      confirmButtonClass: "el-button--danger",
    }
  ).then(
    () => {
      loading.value = true;
      DeptAPI.deleteByIds(deptIds)
        .then(() => {
          ElMessage.success("删除成功");
          handleResetQuery();
        })
        .finally(() => (loading.value = false));
    },
    () => {
      ElMessage.info("已取消删除");
    }
  );
}

onMounted(() => {
  handleQuery();
});
</script>
