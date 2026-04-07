<template>
  <div class="app-container">
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

    <el-card shadow="hover" class="data-table">
      <div class="data-table__toolbar">
        <div class="data-table__toolbar--actions">
          <el-button type="primary" icon="plus" @click="handleAdd">新增</el-button>
          <el-button type="danger" icon="delete" :disabled="multiple" @click="handleBatchDelete">
            批量删除
          </el-button>
          <el-button type="primary" icon="refresh" :disabled="multiple" @click="handleBatchSync">
            批量同步
          </el-button>
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
        <el-table-column label="操作" width="250" fixed="right" align="center">
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
            <el-button
              type="success"
              link
              icon="refresh"
              size="small"
              @click="handleUpload(scope.row)"
            >
              {{ !scope.row.status ? "同步" : "重新同步" }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex-x-end mt-3">
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
import { Picture as IconPicture } from "@element-plus/icons-vue";
import type { UploadProps, UploadRequestOptions } from "element-plus";
import { ImageUploadAPI } from "@/backend";
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

function handleUpload(row: any) {
  const action = !row.status ? "同步" : "重新同步";
  loading.value = true;
  ImageUploadAPI.sync(row.id)
    .then(() => {
      ElMessage.success(`${action}成功`);
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

function handleBatchSync() {
  ElMessageBox.confirm(`确认同步选中的 ${ids.value.length} 条数据项?`, "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "info",
  }).then(() => {
    loading.value = true;
    ImageUploadAPI.batchSync(ids.value)
      .then((res: any) => {
        // 简单统计成功失败
        const successCount = res.filter((r: any) => r.success).length;
        const failCount = res.length - successCount;
        if (failCount === 0) {
          ElMessage.success(`批量同步成功 ${successCount} 条`);
        } else {
          ElMessage.warning(`批量同步完成: 成功 ${successCount} 条, 失败 ${failCount} 条`);
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

      // 弹窗提示，并询问是否立即同步
      msg += `<p style="margin-top:15px">是否立即对成功的 <strong>${sIds.length}</strong> 条数据执行同步操作？</p>`;

      ElMessageBox.confirm(msg, "导入完成", {
        distinguishCancelAndClose: true,
        confirmButtonText: "立即同步",
        cancelButtonText: "稍后处理",
        dangerouslyUseHTMLString: true,
        type: f > 0 ? "warning" : "success",
        draggable: true,
      })
        .then(() => {
          // 用户点击“立即同步”
          if (sIds.length > 0) {
            loading.value = true;
            ImageUploadAPI.batchSync(sIds)
              .then((syncRes: any) => {
                // 简单统计同步结果
                const successCount = syncRes.filter((r: any) => r.success).length;
                const failCount = syncRes.length - successCount;
                if (failCount === 0) {
                  ElMessage.success(`同步成功 ${successCount} 条`);
                } else {
                  ElMessage.warning(`同步完成: 成功 ${successCount} 条, 失败 ${failCount} 条`);
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
          // 用户点击“稍后处理”或关闭弹窗
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

<style scoped>
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
