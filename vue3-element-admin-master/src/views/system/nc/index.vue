<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true" label-suffix=":">
        <el-form-item label="群组" prop="ncGroupId">
          <el-select
            v-model="queryParams.ncGroupId"
            clearable
            placeholder="全部群组"
            style="width: 200px"
          >
            <el-option
              v-for="opt in groupOptions"
              :key="opt.id"
              :label="`${opt.deptName} - ${opt.name}`"
              :value="opt.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="状态" prop="status">
          <el-select
            v-model="queryParams.status"
            clearable
            placeholder="全部"
            style="width: 100px"
          >
            <el-option :value="true" label="生效" />
            <el-option :value="false" label="停用" />
          </el-select>
        </el-form-item>

        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button
            v-hasPerm="['nc:rule:add']"
            type="success"
            icon="plus"
            @click="handleOpenDialog()"
          >
            新增规则
          </el-button>
        </div>
      </div>

      <el-table
        ref="dataTableRef"
        v-loading="loading"
        :data="pageData"
        highlight-current-row
        class="data-table__content"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column label="群组" prop="ncGroupName" min-width="160" />
        <el-table-column label="子路径" prop="ncPath" min-width="220" />
        <el-table-column label="权限位" prop="permissionBits" width="90" align="center" />
        <el-table-column label="权限标签" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="label in row.permLabels"
              :key="label"
              type="info"
              size="small"
              style="margin-right: 4px"
            >
              {{ label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? "生效" : "停用" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" prop="updateTime" width="170" align="center" />
        <el-table-column label="操作" width="150" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-hasPerm="['nc:rule:edit']"
              type="primary"
              size="small"
              link
              icon="edit"
              @click="handleOpenDialog(row)"
            >
              编辑
            </el-button>
            <el-button
              v-hasPerm="['nc:rule:delete']"
              type="danger"
              size="small"
              link
              icon="delete"
              @click="handleDelete(row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.page"
        v-model:limit="queryParams.pageSize"
        @pagination="loadPage"
      />
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <nc-rule-dialog
      v-model="dialogVisible"
      :rule-data="currentRule"
      :group-options="groupOptions"
      @saved="handleQuery"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * NC 文件访问规则管理页：展示并管理各部门的子路径 ACL 权限规则。
 * 所属板块：nc。
 */
import type { NcFileRuleVO, NcFileRulePageQuery, NcGroupOption } from "@/api/nc/fileRule";

import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import {
  getNcFileRulePage,
  getNcGroupOptions,
  deleteNcFileRule,
} from "@/api/nc/fileRule";
import NcRuleDialog from "./components/RuleDialog.vue";

const loading = ref(false);
const total = ref(0);
const pageData = ref<NcFileRuleVO[]>([]);
const groupOptions = ref<NcGroupOption[]>([]);
const dialogVisible = ref(false);
const currentRule = ref<NcFileRuleVO | null>(null);

const queryParams = ref<NcFileRulePageQuery>({
  page: 1,
  pageSize: 20,
});

const queryFormRef = ref();

/** 加载群组下拉选项 */
async function loadGroupOptions(): Promise<void> {
  try {
    groupOptions.value = await getNcGroupOptions();
  } catch {
    ElMessage.error("加载群组选项失败");
  }
}

/** 加载分页数据 */
async function loadPage(): Promise<void> {
  if (loading.value) return;
  loading.value = true;
  try {
    const res = await getNcFileRulePage(queryParams.value);
    pageData.value = res.list;
    total.value = res.total;
  } catch {
    ElMessage.error("加载规则列表失败");
  } finally {
    loading.value = false;
  }
}

/** 查询按钮：重置到第一页后刷新 */
function handleQuery(): void {
  queryParams.value.page = 1;
  loadPage();
}

/** 重置查询条件 */
function handleResetQuery(): void {
  queryFormRef.value?.resetFields();
  queryParams.value = { page: 1, pageSize: 20 };
  loadPage();
}

/** 打开新增/编辑弹窗 */
function handleOpenDialog(rule: NcFileRuleVO | null = null): void {
  currentRule.value = rule;
  dialogVisible.value = true;
}

/** 删除指定规则 */
async function handleDelete(id: number): Promise<void> {
  await ElMessageBox.confirm(
    "确认删除该规则？删除后对应 ACL 将自动撤销。",
    "删除确认",
    { type: "warning" }
  );
  try {
    await deleteNcFileRule(id);
    ElMessage.success("删除成功");
    loadPage();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(() => {
  loadGroupOptions();
  loadPage();
});
</script>

<style scoped lang="scss">
.data-table {
  margin-top: 16px;
}
</style>
