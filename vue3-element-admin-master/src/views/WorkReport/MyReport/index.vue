<template>
  <div class="app-container">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-bold">我的汇报</span>
          <el-button type="primary" :icon="Plus" @click="handleOpenWrite">写日报</el-button>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="myReportList"
        style="width: 100%"
        border
        highlight-current-row
      >
        <el-table-column prop="report_date" label="日期" width="120" sortable align="center">
          <template #default="{ row }">
            <span>{{ row.report_date }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'daily' ? 'primary' : 'success'" effect="light">
              {{ row.type === "daily" ? "日报" : "周报" }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="content" label="工作内容" min-width="200" show-overflow-tooltip />

        <el-table-column prop="plan" label="下阶段计划" min-width="200" show-overflow-tooltip />

        <el-table-column prop="work_hours" label="工时" width="80" align="center">
          <template #default="{ row }">
            <span>{{ row.work_hours }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="提交时间" width="160" align="center">
          <template #default="{ row }">
            <span>{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="handleViewDetail(row)">
              查看
            </el-button>
            <el-button link type="primary" :icon="Edit" @click="handleEditReport(row)">
              编辑
            </el-button>
            <el-button link type="danger" :icon="Delete" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 只要 total > 0 就显示分页 -->
      <div v-if="total > 0" class="flex justify-end mt-4">
        <el-pagination
          v-model:current-page="queryParams.pageNum"
          v-model:page-size="queryParams.pageSize"
          :total="total"
          :page-sizes="[15, 30, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <ReportDrawer
      v-model:visible="drawerVisible"
      :mode="drawerMode"
      :data="drawerData"
      @submit="handleReportSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from "vue";
import { Plus, View, Edit, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import dayjs from "dayjs";

import ReportDrawer from "../components/ReportDrawer.vue";
import {
  getWorkReportList,
  addWorkReport,
  updateWorkReport,
  deleteWorkReport,
} from "@/api/work-report";
import type { WorkReportVO, WorkReportQuery } from "@/api/work-report";

const loading = ref(false);
const myReportList = ref<WorkReportVO[]>([]);
const total = ref(0);

const queryParams = reactive<WorkReportQuery>({
  pageNum: 1,
  pageSize: 15,
  scope: "my", // 只查自己的
});

const drawerVisible = ref(false);
const drawerMode = ref<"read" | "write" | "edit">("read");
const drawerData = ref<Partial<WorkReportVO>>({});

const formatTime = (time: string) => {
  if (!time) return "";
  return dayjs(time).format("YYYY-MM-DD HH:mm");
};

const loadData = async () => {
  loading.value = true;
  try {
    const res: any = await getWorkReportList(queryParams);
    if (res.results) {
      myReportList.value = res.results;
      total.value = res.count;
    } else if (res.data) {
      myReportList.value = res.data;
      total.value = res.total;
    } else {
      // Fallback
      myReportList.value = res as any;
      total.value = 0;
    }
  } catch (error) {
    console.error("获取日报列表失败", error);
    myReportList.value = [];
  } finally {
    loading.value = false;
  }
};

const handleOpenWrite = () => {
  drawerMode.value = "write";
  drawerData.value = {};
  drawerVisible.value = true;
};

const handleEditReport = (row: WorkReportVO) => {
  drawerMode.value = "edit";
  drawerData.value = { ...row };
  drawerVisible.value = true;
};

const handleViewDetail = (row: WorkReportVO) => {
  drawerMode.value = "read";
  drawerData.value = { ...row };
  drawerVisible.value = true;
};

const handleDelete = (row: WorkReportVO) => {
  if (!row.id) return;
  ElMessageBox.confirm("确认要删除这条汇报吗？", "警告", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).then(async () => {
    try {
      await deleteWorkReport(row.id);
      ElMessage.success("删除成功");
      loadData();
    } catch (error) {
      console.error(error);
    }
  });
};

const handleReportSubmit = async (formData: any) => {
  try {
    if (drawerMode.value === "write") {
      await addWorkReport(formData);
      ElMessage.success("添加成功");
    } else if (drawerMode.value === "edit") {
      const id = drawerData.value.id;
      if (id) {
        await updateWorkReport(id, formData);
        ElMessage.success("修改成功");
      }
    }
    drawerVisible.value = false;
    loadData();
  } catch (error) {
    console.error(error);
  }
};

const handleSizeChange = (val: number) => {
  queryParams.pageSize = val;
  loadData();
};

const handleCurrentChange = (val: number) => {
  queryParams.pageNum = val;
  loadData();
};

onMounted(() => {
  loadData();
});
</script>

<style scoped>
.app-container {
  padding: 20px;
}
</style>
