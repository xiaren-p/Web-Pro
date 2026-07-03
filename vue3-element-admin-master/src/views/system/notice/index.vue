<template>
  <div class="app-container">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true" label-suffix=":">
        <el-form-item label="标题" prop="title">
          <el-input
            v-model="queryParams.title"
            placeholder="标题"
            clearable
            @keyup.enter="handleQuery()"
          />
        </el-form-item>

        <el-form-item label="发布状态" prop="publishStatus">
          <el-select
            v-model="queryParams.publishStatus"
            clearable
            placeholder="全部"
            style="width: 100px"
          >
            <el-option :value="0" label="未发布" />
            <el-option :value="1" label="已发布" />
            <el-option :value="-1" label="已撤回" />
          </el-select>
        </el-form-item>

        <el-form-item class="search-buttons">
          <el-button type="primary" icon="search" @click="handleQuery()">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery()">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button
            v-hasPerm="['sys:notice:add']"
            type="success"
            icon="plus"
            @click="handleOpenDialog()"
          >
            新增通知
          </el-button>
          <el-button
            v-hasPerm="['sys:notice:delete']"
            type="danger"
            :disabled="selectIds.length === 0"
            icon="delete"
            @click="handleDelete()"
          >
            删除
          </el-button>
          <el-button
            v-hasPerm="['sys:notice:query']"
            type="warning"
            icon="download"
            @click="openExportDialog(queryParams.title)"
          >
            导出
          </el-button>
        </div>
      </div>

      <el-table
        ref="dataTableRef"
        v-loading="isLoading"
        :data="pageData"
        highlight-current-row
        class="data-table__content"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column type="index" label="序号" width="60" />
        <el-table-column label="通知标题" prop="title" min-width="200" />
        <el-table-column align="center" label="通知类型" width="150">
          <template #default="scope">
            <DictLabel v-model="scope.row.type" :code="'notice_type'" />
          </template>
        </el-table-column>
        <el-table-column align="center" label="发布人" prop="publisherName" width="150" />
        <el-table-column align="center" label="通知等级" width="100">
          <template #default="scope">
            <DictLabel v-model="scope.row.level" code="notice_level" />
          </template>
        </el-table-column>
        <el-table-column align="center" label="通告目标类型" prop="targetType" min-width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.targetType == 1" type="warning">全体</el-tag>
            <el-tag v-if="scope.row.targetType == 2" type="success">指定</el-tag>
          </template>
        </el-table-column>
        <el-table-column align="center" label="发布状态" min-width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.publishStatus == 0" type="info">未发布</el-tag>
            <el-tag v-if="scope.row.publishStatus == 1" type="success">已发布</el-tag>
            <el-tag v-if="scope.row.publishStatus == -1" type="warning">已撤回</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作时间" width="250">
          <template #default="scope">
            <div class="flex-x-start">
              <span>创建时间：</span>
              <span>{{ scope.row.createTime || "-" }}</span>
            </div>

            <div v-if="scope.row.publishStatus === 1" class="flex-x-start">
              <span>发布时间：</span>
              <span>{{ scope.row.publishTime || "-" }}</span>
            </div>
            <div v-else-if="scope.row.publishStatus === -1" class="flex-x-start">
              <span>撤回时间：</span>
              <span>{{ scope.row.revokeTime || "-" }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column align="center" fixed="right" label="操作" width="150">
          <template #default="scope">
            <el-button type="primary" size="small" link @click="openDetailDialog(scope.row.id)">
              查看
            </el-button>
            <el-button
              v-if="scope.row.publishStatus != 1"
              v-hasPerm="['sys:notice:publish']"
              type="primary"
              size="small"
              link
              @click="handlePublish(scope.row.id)"
            >
              发布
            </el-button>
            <el-button
              v-if="scope.row.publishStatus == 1"
              v-hasPerm="['sys:notice:revoke']"
              type="primary"
              size="small"
              link
              @click="handleRevoke(scope.row.id)"
            >
              撤回
            </el-button>
            <el-button
              v-if="scope.row.publishStatus != 1"
              v-hasPerm="['sys:notice:edit']"
              type="primary"
              size="small"
              link
              @click="handleOpenDialog(scope.row.id)"
            >
              编辑
            </el-button>
            <el-button
              v-if="scope.row.publishStatus != 1"
              v-hasPerm="['sys:notice:delete']"
              type="danger"
              size="small"
              link
              @click="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <pagination
        v-if="total > 0"
        v-model:total="total"
        v-model:page="queryParams.pageNum"
        v-model:limit="queryParams.pageSize"
        @pagination="fetchData()"
      />
    </el-card>

    <!-- 导出通知弹窗 -->
    <el-dialog
      v-model="exportDialogVisible"
      title="导出通知"
      width="500px"
      append-to-body
      @close="closeExportDialog"
    >
      <el-form :model="exportForm" label-width="100px">
        <el-form-item label="通知类型">
          <Dict v-model="exportForm.type" code="notice_type" />
        </el-form-item>
        <el-form-item label="通知等级">
          <Dict v-model="exportForm.level" code="notice_level" />
        </el-form-item>
        <!-- 目标类型已移除：导出仅支持导出自己的通知（非管理员） -->
        <el-form-item label="发布状态">
          <el-select v-model="exportForm.publishStatus" placeholder="全部" clearable>
            <el-option :value="0" label="未发布" />
            <el-option :value="1" label="已发布" />
            <el-option :value="-1" label="已撤回" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="exportForm.title" placeholder="标题关键词" clearable />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" :loading="isExportLoading" @click="handleExport">
            导出
          </el-button>
          <el-button @click="closeExportDialog">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <NoticeDialog ref="noticeDialogRef" @success="handleResetQuery" />
    <NoticeDetailDialog ref="noticeDetailDialogRef" />
  </div>
</template>

<script setup lang="ts">
/**
 * 通知公告管理列表页。
 *
 * @description 薄编排层：组合 useNoticeList composable 与子组件。
 *              搜索/表格/导出/发布/撤回/删除逻辑全部在 composable 中。
 */
import { useNoticeList } from "./composables/useNoticeList";
import NoticeDialog from "./components/NoticeDialog.vue";
import NoticeDetailDialog from "./components/NoticeDetailDialog.vue";

defineOptions({
  name: "Notice",
  inheritAttrs: false,
});

const queryFormRef = ref();
const noticeDialogRef = ref();
const noticeDetailDialogRef = ref();

const {
  isLoading,
  selectIds,
  total,
  queryParams,
  pageData,
  exportDialogVisible,
  exportForm,
  isExportLoading,
  fetchData,
  handleQuery,
  handleSelectionChange,
  handlePublish,
  handleRevoke,
  handleDelete: deleteAction,
  openExportDialog,
  closeExportDialog,
  handleExport,
} = useNoticeList();

/** 重置查询条件并重新查询。 */
function handleResetQuery() {
  queryFormRef.value?.resetFields();
  handleQuery();
}

/**
 * 删除通知（单个或批量）。
 *
 * @param id - 单个通知ID；不传则删除当前勾选项。
 */
function handleDelete(id?: string) {
  deleteAction(id, () => queryFormRef.value?.resetFields());
}

/**
 * 打开通知编辑弹窗。
 *
 * @param id - 通知ID，不传为新增。
 */
function handleOpenDialog(id?: string) {
  noticeDialogRef.value.open(id);
}

/** 打开通知详情弹窗。 */
function openDetailDialog(id: string) {
  noticeDetailDialogRef.value.open(id);
}

onMounted(() => {
  handleQuery();
});
</script>
