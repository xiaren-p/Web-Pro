<template>
  <div class="team-report-container app-container">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="8" :xs="24">
        <el-card
          shadow="hover"
          body-style="display: flex; align-items: center; padding: 20px;"
          class="cursor-pointer"
          @click="handleStatsClick('total', '应提交人员列表')"
        >
          <el-icon :size="48" color="#409eff" class="mr-4"><User /></el-icon>
          <div>
            <div class="text-[24px] font-bold text-[#303133]">{{ teamStats.total }}</div>
            <div class="text-[14px] text-[#909399] mt-1">应提交人数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8" :xs="24">
        <el-card
          shadow="hover"
          body-style="display: flex; align-items: center; padding: 20px;"
          class="cursor-pointer"
          @click="handleStatsClick('submitted', '实提交人员列表')"
        >
          <el-icon :size="48" color="#67C23A" class="mr-4"><Check /></el-icon>
          <div>
            <div class="text-[24px] font-bold text-[#67C23A]">{{ teamStats.submitted }}</div>
            <div class="text-[14px] text-[#909399] mt-1">实提交人数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8" :xs="24">
        <el-card
          shadow="hover"
          body-style="display: flex; align-items: center; padding: 20px;"
          class="cursor-pointer"
          @click="handleStatsClick('missing', '未提交人员列表')"
        >
          <el-icon :size="48" color="#F56C6C" class="mr-4"><Warning /></el-icon>
          <div>
            <div class="text-[24px] font-bold text-[#F56C6C]">{{ teamStats.missing }}</div>
            <div class="text-[14px] text-[#909399] mt-1">未提交人数</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 搜索区域 -->
    <div class="search-container bg-white px-4 pt-4 pb-0 mb-4 rounded shadow-sm">
      <el-form :inline="true" :model="queryParams" class="filter-form">
        <el-form-item label="类型">
          <el-select
            v-model="queryParams.type"
            placeholder="报表类型"
            style="width: 120px"
            @change="handleTypeChange"
          >
            <el-option label="日报" value="daily" />
            <el-option label="周报" value="weekly" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期">
          <el-date-picker
            v-model="queryParams.date"
            type="date"
            placeholder="汇报日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :clearable="false"
            style="width: 200px"
            @change="handleQuery"
          />
        </el-form-item>
        <el-form-item label="部门">
          <el-select
            v-model="queryParams.dept_id"
            placeholder="请选择部门"
            style="width: 200px"
            clearable
            filterable
            @change="handleQuery"
          >
            <el-option
              v-for="item in deptOptions"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="handleQuery">查询</el-button>
          <el-button :icon="Refresh" @click="resetQuery">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 团队列表表格: 显示已提交的汇报 -->
    <el-card shadow="never" class="table-container">
      <el-table
        v-loading="loading"
        :data="reportList"
        style="width: 100%"
        highlight-current-row
        border
      >
        <el-table-column label="提交人" width="180">
          <template #default="{ row }">
            <div class="flex items-center">
              <el-avatar :size="32" :src="row.avatar" class="mr-2 bg-blue-500">
                {{ (row.nickname || row.username || "?").charAt(0) }}
              </el-avatar>
              <div>
                <div class="font-medium text-gray-700">{{ row.nickname || row.username }}</div>
                <div class="text-xs text-gray-400">{{ row.department || "未知部门" }}</div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.type === 'daily' ? 'primary' : 'success'" effect="light">
              {{ row.type_display || (row.type === "daily" ? "日报" : "周报") }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="content" label="工作内容" min-width="200" show-overflow-tooltip />

        <el-table-column prop="plan" label="下阶段计划" min-width="200" show-overflow-tooltip />

        <el-table-column prop="work_hours" label="工时" width="80" align="center" />
        <el-table-column prop="progress" label="进度" width="80" align="center">
          <template #default="{ row }">{{ row.progress }}%</template>
        </el-table-column>

        <el-table-column prop="created_at" label="提交时间" width="160" align="center">
          <template #default="{ row }">
            {{ row.created_at_display || formatTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" :icon="View" @click="handleViewDetail(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <ReportDrawer v-model:visible="drawerVisible" mode="read" :data="drawerData" />

    <el-dialog
      v-model="detailDialogVisible"
      :title="detailDialogTitle"
      width="600px"
      append-to-body
    >
      <el-table v-loading="detailLoading" :data="detailUserList" height="400">
        <el-table-column label="姓名" width="180" align="center">
          <template #default="{ row }">
            <div class="flex items-center justify-center">
              <el-avatar :size="30" :src="row.avatar" class="mr-2 bg-blue-500">
                {{ (row.nickname || row.username || "?").charAt(0) }}
              </el-avatar>
              <span>{{ row.nickname || row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column property="department" label="部门" align="center" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { User, Check, Warning, Search, Refresh, View } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import ReportDrawer from "@/views/WorkReport/components/ReportDrawer.vue";
import {
  getWorkReportList,
  getTeamStats,
  getTeamStatsDetails,
  type WorkReportVO,
  type WorkReportQuery,
  type TeamStatsVO,
} from "@/api/workReport";
import { DeptAPI } from "@/api/dept";

const loading = ref(false);
const detailLoading = ref(false);
const reportList = ref<WorkReportVO[]>([]);
const total = ref(0);
const deptOptions = ref<{ label: string; value: any }[]>([]);

// Details Dialog
const detailDialogVisible = ref(false);
const detailDialogTitle = ref("");
const detailUserList = ref<any[]>([]);

const todayStr = dayjs().format("YYYY-MM-DD");

const getDepts = async () => {
  try {
    const res = await DeptAPI.getOptions();
    deptOptions.value = res;
  } catch (e) {
    console.error(e);
  }
};

const queryParams = reactive<WorkReportQuery>({
  pageNum: 1,
  pageSize: 15,
  scope: "team",
  date: todayStr,
  dept_id: undefined,
  type: "daily",
});

// 处理类型变化，自动调整日期
const handleTypeChange = (val: string) => {
  if (val === "daily") {
    queryParams.date = dayjs().format("YYYY-MM-DD");
  } else if (val === "weekly") {
    let d = dayjs();
    // 如果不是周五，往前找最近的一个周五
    if (d.day() !== 5) {
      // 如果今天是周六(6)，减1天就是周五
      // 如果今天是周四(4)，一直减直到周五
      // 简单的逻辑：一直减直到 day() === 5
      while (d.day() !== 5) {
        d = d.subtract(1, "day");
      }
    }
    queryParams.date = d.format("YYYY-MM-DD");
  }
  handleQuery();
};

const handleStatsClick = async (status: string, title: string) => {
  detailDialogVisible.value = true;
  detailDialogTitle.value = title;
  detailLoading.value = true;
  detailUserList.value = [];

  // Get filter params
  const statsDate = queryParams.date || todayStr;
  const statsDept = queryParams.dept_id;
  const statsType = queryParams.type;

  try {
    const res = await getTeamStatsDetails(statsDate, statsDept, statsType, status);
    detailUserList.value = res || [];
  } catch (e: any) {
    console.error("获取详情列表失败", e);
    detailUserList.value = [];
  } finally {
    detailLoading.value = false;
  }
};

const teamStats = reactive<TeamStatsVO>({
  total: 0,
  submitted: 0,
  missing: 0,
});

const drawerVisible = ref(false);
const drawerData = ref<Partial<WorkReportVO>>({});

const formatTime = (time: string) => {
  if (!time) return "";
  return dayjs(time).format("YYYY-MM-DD HH:mm");
};

const loadData = async () => {
  loading.value = true;
  try {
    // 1. Get List
    // Filter out empty params
    const params: any = { ...queryParams };
    if (!params.date) delete params.date;
    if (!params.dept_id) delete params.dept_id;
    // Map report_date for list filter (used by WorkReportViewSet filterset_fields)
    // If we have a date selected, we must send it as report_date if we want to filter the list by day.
    if (queryParams.date) {
      params.report_date = queryParams.date;
    }

    const res: any = await getWorkReportList(params);
    if (res.results) {
      reportList.value = res.results;
      total.value = res.count;
    } else if (res.data) {
      reportList.value = res.data;
      total.value = res.total;
    } else {
      reportList.value = res as any;
      total.value = 0;
    }

    // 2. Get Stats (always use current date filter or today if empty)
    const statsDate = queryParams.date || todayStr;
    const statsDept = queryParams.dept_id;
    const statsType = queryParams.type;
    const statsRes = await getTeamStats(statsDate, statsDept, statsType);
    if (statsRes) {
      teamStats.total = statsRes.total || 0;
      teamStats.submitted = statsRes.submitted || 0;
      teamStats.missing = statsRes.missing || 0;
    }
  } catch (error) {
    console.error("获取团队日报失败", error);
    reportList.value = [];
  } finally {
    loading.value = false;
  }
};

const handleQuery = () => {
  queryParams.pageNum = 1;
  loadData();
};

const resetQuery = () => {
  queryParams.date = todayStr;
  queryParams.dept_id = undefined;
  queryParams.type = "daily";
  handleQuery();
};

const handleViewDetail = (row: WorkReportVO) => {
  drawerData.value = { ...row };
  drawerVisible.value = true;
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
  getDepts();
  loadData();
});
</script>

<style scoped>
.app-container {
  padding: 20px;
}
</style>
