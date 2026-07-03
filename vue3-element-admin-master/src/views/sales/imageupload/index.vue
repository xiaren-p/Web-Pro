<template>
  <div class="app-container image-upload-page">
    <!-- 搜索区域 -->
    <div class="search-container">
      <el-form ref="queryFormRef" :model="queryParams" :inline="true">
        <el-form-item label="图片组" prop="imageGroup">
          <el-input
            v-model="queryParams.imageGroup"
            placeholder="请输入图片组名称"
            clearable
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="queryParams.status" placeholder="全部" clearable style="width: 120px">
            <el-option label="正常" value="normal" />
            <el-option label="警告" value="warning" />
            <el-option label="错误" value="error" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" icon="search" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleResetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <el-card shadow="hover" class="data-table flex-1">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button type="primary" icon="plus" @click="handleAdd">新增</el-button>
          <el-button
            type="danger"
            icon="delete"
            :disabled="isBatchDisabled"
            @click="handleBatchDelete"
          >
            批量删除
          </el-button>
          <el-dropdown
            split-button
            type="primary"
            icon="refresh"
            :disabled="isBatchDisabled"
            style="margin-right: 12px"
            @click="handleBatchSync(false)"
          >
            批量同步
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="handleBatchSync(false)">
                  断点同步（仅失败）
                </el-dropdown-item>
                <el-dropdown-item @click="handleBatchSync(true)">重新同步（全部）</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <el-button type="info" icon="list" @click="handleOpenQueue">同步队列</el-button>
          <el-upload
            action="#"
            :show-file-list="false"
            accept=".csv"
            :before-upload="beforeImport"
            :http-request="handleImport"
            style="display: inline-block; margin: 0 12px"
          >
            <el-button type="warning" icon="upload">上传</el-button>
          </el-upload>
          <el-button type="success" icon="download" @click="handleDownload">下载</el-button>
        </div>
      </div>

      <el-table
        v-loading="isLoading"
        :data="tableData"
        border
        height="100%"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="图片" width="100" align="center">
          <template #default="scope">
            <el-image
              style="width: 40px; height: 40px"
              :src="scope.row.imageUrl"
              :preview-src-list="[scope.row.imageUrl]"
              fit="cover"
              preview-teleported
            >
              <template #error>
                <div class="image-slot">
                  <el-icon><IconPicture /></el-icon>
                </div>
              </template>
            </el-image>
          </template>
        </el-table-column>
        <el-table-column label="图片组" prop="imageGroup" min-width="100" />
        <el-table-column label="状态" prop="status" width="100" align="center">
          <template #default="scope">
            <el-tag v-if="scope.row.status === 'normal'" type="success">正常</el-tag>
            <el-tag v-else-if="scope.row.status === 'warning'" type="warning">警告</el-tag>
            <el-tag v-else-if="scope.row.status === 'error'" type="danger">错误</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column
          label="Cloud 路径"
          prop="cloudPath"
          min-width="200"
          show-overflow-tooltip
        />
        <el-table-column label="日志" prop="log" min-width="200">
          <template #default="scope">
            <div v-if="scope.row.log" class="log-cell" @click="showLogDetail(scope.row.log)">
              {{ scope.row.log.split("\n").pop() }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right" align="center">
          <template #default="scope">
            <el-button type="primary" link icon="edit" size="small" @click="handleEdit(scope.row)">
              编辑
            </el-button>
            <el-button
              type="danger"
              link
              icon="delete"
              size="small"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
            <el-dropdown
              trigger="click"
              @command="(cmd: string) => handleSyncCommand(cmd, scope.row)"
            >
              <el-button type="success" link icon="refresh" size="small">
                同步
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="breakpoint">断点同步</el-dropdown-item>
                  <el-dropdown-item command="resync">重新同步</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          :current-page="queryParams.pageNum"
          :page-size="queryParams.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <ImageGroupDialog ref="imageGroupDialogRef" @success="handleQuery" />
    <LogDetailDialog ref="logDetailDialogRef" />
    <SyncQueueDialog ref="syncQueueDialogRef" />
  </div>
</template>

<script setup lang="ts">
/**
 * 图片上传管理列表页。
 *
 * @description 薄编排层：组合 useImageUploadList composable 与子组件。
 *              搜索/分页/删除/同步/导入/导出逻辑全部在 composable 中。
 */
import { Picture as IconPicture, ArrowDown } from "@element-plus/icons-vue";
import type { ImageUploadVO } from "@/api/imageUpload";
import { useImageUploadList } from "./composables/useImageUploadList";
import ImageGroupDialog from "./components/ImageGroupDialog.vue";
import LogDetailDialog from "./components/LogDetailDialog.vue";
import SyncQueueDialog from "./components/SyncQueueDialog.vue";

defineOptions({
  name: "ImageUpload",
});

const queryFormRef = ref();
const imageGroupDialogRef = ref();
const logDetailDialogRef = ref();
const syncQueueDialogRef = ref();

const {
  isLoading,
  isBatchDisabled,
  total,
  queryParams,
  tableData,
  handleQuery,
  resetAndQuery,
  handleSizeChange,
  handleCurrentChange,
  handleSelectionChange,
  handleDelete,
  handleBatchDelete,
  handleSyncCommand,
  handleBatchSync,
  handleDownload,
  beforeImport,
  handleImport,
} = useImageUploadList();

/** 重置查询条件并重新查询。 */
function handleResetQuery() {
  queryFormRef.value.resetFields();
  resetAndQuery();
}

/** 打开新增弹窗。 */
function handleAdd() {
  imageGroupDialogRef.value.open();
}

/** 打开编辑弹窗。 */
function handleEdit(row: ImageUploadVO) {
  imageGroupDialogRef.value.open(row);
}

/** 打开日志详情弹窗。 */
function showLogDetail(log: string) {
  if (!log) return;
  logDetailDialogRef.value.open(log);
}

/** 打开同步队列弹窗。 */
function handleOpenQueue() {
  syncQueueDialogRef.value.open();
}

onMounted(() => {
  handleQuery();
});
</script>

<style scoped lang="scss">
.image-upload-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.data-table {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;

  :deep(.el-card__body) {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-height: 0;
    padding: 16px;
    overflow: hidden;
  }
}

.data-table__toolbar {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.pagination-container {
  display: flex;
  flex-shrink: 0;
  justify-content: flex-end;
  padding-top: 12px;
}

.image-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  font-size: 20px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-light);
}

.log-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--el-color-primary);
  white-space: nowrap;
  cursor: pointer;
}

.log-cell:hover {
  text-decoration: underline;
}
</style>
