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
            @click="handleOpenExportDialog()"
          >
            导出
          </el-button>
        </div>
      </div>

      <el-table
        ref="dataTableRef"
        v-loading="loading"
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
      v-model="exportDialog.visible"
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
          <el-button type="primary" :loading="exportLoading" @click="handleExport">导出</el-button>
          <el-button @click="closeExportDialog">关闭</el-button>
        </div>
      </template>
    </el-dialog>

    <NoticeDialog ref="noticeDialogRef" @success="handleResetQuery" />
    <NoticeDetailDialog ref="noticeDetailDialogRef" />
  </div>
</template>

<script setup lang="ts">
import { NoticeAPI, type NoticePageQuery, type NoticePageVO } from "@/api/notice";
import { useUserStoreHook } from "@/store/modules/user-store";
import NoticeDialog from "./components/NoticeDialog.vue";
import NoticeDetailDialog from "./components/NoticeDetailDialog.vue";

defineOptions({
  name: "Notice",
  inheritAttrs: false,
});

const queryFormRef = ref();
const noticeDialogRef = ref();
const noticeDetailDialogRef = ref();

const loading = ref(false);
const selectIds = ref<number[]>([]);
const total = ref(0);

const queryParams = reactive<NoticePageQuery>({
  pageNum: 1,
  pageSize: 10,
});

// 通知公告表格数据
const pageData = ref<NoticePageVO[]>([]);

// 导出相关
const exportDialog = reactive({
  visible: false,
});

interface ExportForm {
  type?: string;
  level?: string;
  publishStatus?: number;
  title?: string;
}

const exportForm = reactive<ExportForm>({
  type: undefined,
  level: undefined,
  publishStatus: undefined,
  title: undefined,
});
const exportLoading = ref(false);

function handleOpenExportDialog() {
  exportDialog.visible = true;
  // 默认填充筛选条件
  exportForm.type = undefined;
  exportForm.level = undefined;
  exportForm.publishStatus = undefined;
  exportForm.title = queryParams.title;
}

function closeExportDialog() {
  exportDialog.visible = false;
}

async function handleExport() {
  exportLoading.value = true;
  try {
    console.log("[Debug] Start Export, NoticeAPI keys:", Object.keys(NoticeAPI));
    if (typeof (NoticeAPI as any).exportData !== "function") {
      throw new Error("NoticeAPI.exportData is not a function. Check @/api/notice update.");
    }
    // 非管理员仅导出当前用户可见项，后端支持 onlyMine 参数；管理员导出所有匹配项
    const params: any = { ...exportForm };
    if (!isAdminUser()) params.onlyMine = true;
    const response: any = await (NoticeAPI as any).exportData(params);

    console.log("[Debug] Export response:", response);

    // 处理二进制流下载
    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8",
    });
    const a = document.createElement("a");
    const href = window.URL.createObjectURL(blob);
    a.href = href;
    a.download = `通知公告_${new Date().getTime()}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(href);
    ElMessage.success("导出成功");
    closeExportDialog();
  } catch (err: any) {
    console.error("导出异常:", err);
    ElMessage.error("导出失败: " + (err.message || "未知错误"));
  } finally {
    exportLoading.value = false;
  }
}

// 查询通知公告
function handleQuery() {
  queryParams.pageNum = 1;
  fetchData();
}

// 发送请求接口：管理员查看全部，非管理员只查看分配给自己的（使用后端提供的 my-page）
const userStore = useUserStoreHook();

function isAdminUser() {
  try {
    const roles = (userStore.userInfo && userStore.userInfo.roles) || [];
    const perms = (userStore.userInfo && (userStore.userInfo as any).perms) || [];
    const rs = roles.map((r: any) => String(r).toLowerCase());
    if (rs.includes("admin") || rs.includes("role_admin") || rs.includes("administrator"))
      return true;
    if (perms && Array.isArray(perms) && perms.includes("admin")) return true;
  } catch {
    // ignore and treat as non-admin
  }
  return false;
}

// 发送请求接口
function fetchData() {
  loading.value = true;
  NoticeAPI.getPage(queryParams)
    .then((data: any) => {
      pageData.value = data.list;
      total.value = data.total;
    })
    .finally(() => {
      loading.value = false;
    });
}

// 重置查询
function handleResetQuery() {
  queryFormRef.value!.resetFields();
  queryParams.pageNum = 1;
  handleQuery();
}

// 行复选框选中项变化
function handleSelectionChange(selection: any) {
  selectIds.value = selection.map((item: any) => item.id);
}

// 打开通知公告弹窗
function handleOpenDialog(id?: string) {
  noticeDialogRef.value.open(id);
}

// 发布通知公告
function handlePublish(id: string) {
  NoticeAPI.publish(id).then(() => {
    ElMessage.success("发布成功");
    handleQuery();
  });
}

// 撤回通知公告
function handleRevoke(id: string) {
  NoticeAPI.revoke(id).then(() => {
    ElMessage.success("撤回成功");
    handleQuery();
  });
}

// 删除通知公告
function handleDelete(id?: number) {
  const deleteIds = [id || selectIds.value].join(",");
  if (!deleteIds) {
    ElMessage.warning("请勾选删除项");
    return;
  }

  ElMessageBox.confirm("确认删除已选中的数据项?", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(
    () => {
      loading.value = true;
      NoticeAPI.deleteByIds(deleteIds)
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

const openDetailDialog = async (id: string) => {
  noticeDetailDialogRef.value.open(id);
};

onMounted(() => {
  handleQuery();
});
</script>
