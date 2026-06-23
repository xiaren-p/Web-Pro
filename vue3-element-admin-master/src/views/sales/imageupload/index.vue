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
          <el-button type="danger" icon="delete" :disabled="multiple" @click="handleBatchDelete">
            批量删除
          </el-button>
          <el-dropdown
            split-button
            type="primary"
            icon="refresh"
            :disabled="multiple"
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
        v-loading="loading"
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

    <!-- Dialogs -->
    <ImageGroupDialog ref="imageGroupDialogRef" @success="handleQuery" />
    <LogDetailDialog ref="logDetailDialogRef" />
    <SyncQueueDialog ref="syncQueueDialogRef" />
  </div>
</template>

<script setup lang="ts">
import { Picture as IconPicture, ArrowDown } from "@element-plus/icons-vue";
import type { UploadProps, UploadRequestOptions } from "element-plus";
import { ImageUploadAPI } from "@/api/imageUpload";
import ImageGroupDialog from "./components/ImageGroupDialog.vue";
import LogDetailDialog from "./components/LogDetailDialog.vue";
import SyncQueueDialog from "./components/SyncQueueDialog.vue";

defineOptions({
  name: "ImageUpload",
});

const queryFormRef = ref();
const loading = ref(false);
const ids = ref<string[]>([]);
const multiple = ref(true);
const total = ref(0);

const queryParams = reactive({
  pageNum: 1,
  pageSize: 20,
  imageGroup: "",
  status: undefined as string | undefined,
});

const tableData = ref<any[]>([]);

// Dialog Refs
const imageGroupDialogRef = ref();
const logDetailDialogRef = ref();
const syncQueueDialogRef = ref();

// 查询
function handleQuery() {
  loading.value = true;
  ImageUploadAPI.getPage(queryParams)
    .then((data) => {
      tableData.value = data.list;
      total.value = data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

function handleResetQuery() {
  queryFormRef.value.resetFields();
  handleQuery();
}

function handleSizeChange(size: number) {
  queryParams.pageSize = size;
  handleQuery();
}
function handleCurrentChange(page: number) {
  queryParams.pageNum = page;
  handleQuery();
}

function handleAdd() {
  imageGroupDialogRef.value.open();
}

function handleEdit(row: any) {
  imageGroupDialogRef.value.open(row);
}

function handleDelete(row: any) {
  ElMessageBox.confirm("确认删除该图片组吗?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(() => {
    ImageUploadAPI.deleteByIds(row.id).then(() => {
      ElMessage.success("删除成功");
      handleQuery();
    });
  });
}

/** 单行同步命令处理：breakpoint=断点同步，resync=重新同步。 */
function handleSyncCommand(cmd: string, row: any) {
  const forceResync = cmd === "resync";
  const label = forceResync ? "重新同步" : "断点同步";
  loading.value = true;
  ImageUploadAPI.sync(row.id, forceResync)
    .then(() => {
      ElMessage.success(`${label}成功`);
      handleQuery();
    })
    .finally(() => {
      loading.value = false;
    });
}

function handleSelectionChange(selection: any[]) {
  ids.value = selection.map((item) => item.id);
  multiple.value = !selection.length;
}

function handleBatchDelete() {
  ElMessageBox.confirm("确认删除选中的数据项?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(() => {
    ImageUploadAPI.deleteByIds(ids.value.join(",")).then(() => {
      ElMessage.success("删除成功");
      handleQuery();
    });
  });
}

/** 批量同步：forceResync=true 全部同步，false 仅同步未成功项。 */
function handleBatchSync(forceResync: boolean) {
  const label = forceResync ? "重新同步" : "断点同步";
  ElMessageBox.confirm(`确认${label}选中的 ${ids.value.length} 条数据项?`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(() => {
    loading.value = true;
    ImageUploadAPI.batchSync(ids.value, forceResync)
      .then((res: any) => {
        const successCount = res.filter((r: any) => r.success).length;
        const failCount = res.length - successCount;
        if (failCount === 0) {
          ElMessage.success(`${label}成功 ${successCount} 条`);
        } else {
          ElMessage.warning(`${label}完成: 成功 ${successCount} 条, 失败 ${failCount} 条`);
        }
        handleQuery();
      })
      .finally(() => {
        loading.value = false;
      });
  });
}

function handleOpenQueue() {
  syncQueueDialogRef.value.open();
}

const beforeImport: UploadProps["beforeUpload"] = (rawFile) => {
  const isCSV = rawFile.name.toLowerCase().endsWith(".csv");
  if (!isCSV) {
    ElMessage.error("只能上传 CSV 格式的文件!");
    return false;
  }
  return true;
};

const handleImport = (options: UploadRequestOptions) => {
  const { file } = options;
  loading.value = true;
  return ImageUploadAPI.importCsv(file as File)
    .then((res: any) => {
      // 后端返回 snake_case 格式: { created, updated, failed, failed_items, success_ids }
      const r = res as any;
      const c = r.created || 0;
      const u = r.updated || 0;
      const f = r.failed || 0;
      const fItems = r.failed_items || [];
      const sIds = r.success_ids || [];

      let msg = `<p><strong>导入结果汇总：</strong></p>`;
      if (c > 0) msg += `<p>✅ 新增: ${c} 条</p>`;
      if (u > 0) msg += `<p>🔄 更新: ${u} 条</p>`;

      // 仅当有失败记录时才显示失败部分
      if (f > 0) {
        msg += `<p style="color:#F56C6C">❌ 失败: ${f} 条</p>`;
        msg += `<div style="max-height:150px;overflow-y:auto;background:#fef0f0;padding:5px;border-radius:4px;margin:5px 0;">`;
        fItems.forEach((item: string) => {
          msg += `<div style="color:#F56C6C;font-size:12px">${item}</div>`;
        });
        msg += `</div>`;
      }

      if (c === 0 && u === 0 && f === 0) {
        ElMessage.warning("未导入任何有效数据");
        handleQuery();
        return;
      }

      // 弹窗提示，并询问同步方式
      msg += `<p style="margin-top:15px">请选择同步方式：</p>`;
      msg += `<div style="margin:10px 0">`;
      msg += `<label style="display:block;margin:5px 0;cursor:pointer"><input type="radio" name="syncMode" value="breakpoint" checked style="margin-right:8px">断点同步（仅同步未成功项）</label>`;
      msg += `<label style="display:block;margin:5px 0;cursor:pointer"><input type="radio" name="syncMode" value="resync" style="margin-right:8px">重新同步（全部重新同步）</label>`;
      msg += `</div>`;

      ElMessageBox.confirm(msg, "导入完成", {
        distinguishCancelAndClose: true,
        confirmButtonText: "立即同步",
        cancelButtonText: "稍后处理",
        dangerouslyUseHTMLString: true,
        type: f > 0 ? "warning" : "success",
        draggable: true,
      })
        .then(() => {
          // 读取用户选择的同步方式
          const selectedRadio = document.querySelector(
            'input[name="syncMode"]:checked'
          ) as HTMLInputElement;
          const forceResync = selectedRadio?.value === "resync";
          const syncLabel = forceResync ? "重新同步" : "断点同步";

          if (sIds.length > 0) {
            loading.value = true;
            ImageUploadAPI.batchSync(sIds, forceResync)
              .then((syncRes: any) => {
                const successCount = syncRes.filter((r: any) => r.success).length;
                const failCount = syncRes.length - successCount;
                if (failCount === 0) {
                  ElMessage.success(`${syncLabel}成功 ${successCount} 条`);
                } else {
                  ElMessage.warning(
                    `${syncLabel}完成: 成功 ${successCount} 条, 失败 ${failCount} 条`
                  );
                }
                handleQuery();
              })
              .finally(() => {
                loading.value = false;
              });
          } else {
            ElMessage.info("没有可同步的数据");
            handleQuery();
          }
        })
        .catch(() => {
          // 用户点击"稍后处理"或关闭弹窗
          handleQuery();
        });
    })
    .catch((err) => {
      console.error("Import error", err);
      ElMessage.error(err.message || err.msg || "导入失败");
    })
    .finally(() => {
      loading.value = false;
    });
};

function handleDownload() {
  const downloadData = (data: any[]) => {
    if (!data || data.length === 0) {
      ElMessage.warning("暂无数据可下载");
      return;
    }

    // CSV Header
    let csvContent = "图片组,状态,Cloud 路径,日志\n";

    data.forEach((row) => {
      const logLastLine = row.log ? row.log.split("\n").pop() : "";
      // 处理可能包含逗号的字段，用引号包裹
      const escape = (val: any) => `"${String(val || "").replace(/"/g, '""')}"`;

      csvContent += `${escape(row.imageGroup)},${escape(row.status)},${escape(row.cloudPath)},${escape(logLastLine)}\n`;
    });

    // 添加 BOM (\uFEFF) 以解决 Excel 打开乱码问题
    const blob = new Blob(["\uFEFF" + csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "image_uploads.csv");
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (ids.value.length > 0) {
    // 下载选中
    const selectedRows = tableData.value.filter((row) => ids.value.includes(row.id));
    downloadData(selectedRows);
  } else {
    ElMessageBox.confirm("当前没选择数据，是否下载全部数据?", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info",
    }).then(() => {
      // 下载全部（当前页或所有页，这里演示下载当前页数据，实际应调用后端导出接口）
      // 由于没有后端导出接口，这里仅下载当前页数据作为演示
      // 如果需要下载所有数据，通常需要后端支持 export 接口
      downloadData(tableData.value);
    });
  }
}

function showLogDetail(log: string) {
  if (!log) return;
  logDetailDialogRef.value.open(log);
}

onMounted(() => {
  handleQuery();
});
</script>

<style scoped lang="scss">
/* 页面整体 flex 布局：搜索区域固定高度，表格区域占满剩余空间 */
.image-upload-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

/* 表格卡片区域弹性填充 */
.data-table {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;

  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
    overflow: hidden;
    padding: 16px;
  }
}

/* 工具栏不缩不滚 */
.data-table__toolbar {
  flex-shrink: 0;
  margin-bottom: 12px;
}

/* 分页栏不缩不滚 */
.pagination-container {
  flex-shrink: 0;
  display: flex;
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
  color: #909399;
  background: #f5f7fa;
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
