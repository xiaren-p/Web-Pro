<template>
  <el-drawer
    v-model="visibleModel"
    :title="title"
    size="600px"
    direction="rtl"
    custom-class="report-drawer"
    @close="handleClose"
  >
    <div v-if="mode === 'read'" class="detail-mode">
      <!-- 阅读模式 -->
      <div class="detail-header">
        <div class="user-info">
          <el-avatar :size="40" :src="currentDetail.avatar">
            {{ (currentDetail.nickname || currentDetail.username || "我")?.charAt(0) }}
          </el-avatar>
          <div class="ml-3">
            <div class="font-bold">
              {{ currentDetail.nickname || currentDetail.username || "我" }}
            </div>
            <div class="text-xs text-gray-500">
              {{ currentDetail.report_date }}
              {{ currentDetail.type === "weekly" ? "周报" : "日报" }}
            </div>
          </div>
        </div>
        <el-tag type="success">已提交</el-tag>
      </div>

      <div class="detail-section">
        <h4>今日工作内容 (Today's Work)</h4>
        <div class="content-box">{{ currentDetail.content }}</div>
      </div>

      <div class="detail-section">
        <h4>明日计划 (Plan)</h4>
        <div class="content-box">{{ currentDetail.plan || "无" }}</div>
      </div>

      <div class="detail-section">
        <h4>遇到问题 (Issues)</h4>
        <div class="content-box">{{ currentDetail.issues || "无" }}</div>
      </div>

      <div class="detail-meta">
        <span>工时: {{ currentDetail.work_hours }}h</span>
        <span class="ml-4">进度: {{ currentDetail.progress }}%</span>
      </div>
    </div>

    <div v-else class="edit-mode">
      <!-- 编辑模式 -->
      <el-form :model="form" label-position="top">
        <el-form-item label="汇报类型">
          <el-radio-group v-model="form.type">
            <el-radio-button label="daily" value="daily">日报</el-radio-button>
            <el-radio-button label="weekly" value="weekly">周报</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="今日工作内容 (必填)">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="6"
            placeholder="1. 完成了...&#10;2. 修复了..."
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="工时 (小时)">
              <el-input-number v-model="form.work_hours" :min="0" :max="24" :step="0.5" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="进度 (%)">
              <el-slider v-model="form.progress" :step="10" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="明日计划">
          <el-input v-model="form.plan" type="textarea" :rows="3" placeholder="计划..." />
        </el-form-item>

        <el-form-item label="需要协调/遇到问题">
          <el-input v-model="form.issues" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <template v-if="mode !== 'read'">
          <el-button @click="handleCancel">取消</el-button>
          <el-button type="primary" @click="submitReport">提交</el-button>
        </template>
        <template v-else>
          <el-button @click="handleCancel">关闭</el-button>
        </template>
      </div>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from "vue";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: "read" }, // 'read' | 'write' | 'edit'
  data: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["update:visible", "submit"]);

const visibleModel = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
});

const title = computed(() => {
  if (props.mode === "write") return "写日报";
  if (props.mode === "edit") return "编辑日报";
  return "日报详情";
});

const currentDetail = ref<any>({});

const form = reactive({
  type: "daily",
  content: "",
  plan: "",
  issues: "",
  work_hours: 8,
  progress: 0,
});

watch(
  () => props.visible,
  (val) => {
    if (val) {
      if (props.mode === "read") {
        currentDetail.value = { ...props.data };
      } else if (props.mode === "edit") {
        // 回填
        form.content = props.data.content;
        form.plan = props.data.plan;
        form.issues = props.data.issues;
        form.work_hours = props.data.work_hours;
        form.progress = props.data.progress;
        form.type = props.data.type || "daily";
      } else {
        // 重置
        form.content = "";
        form.plan = "";
        form.issues = "";
        form.work_hours = 8;
        form.progress = 0;
        form.type = "daily";
      }
    }
  }
);

const handleClose = () => {
  emit("update:visible", false);
};

const handleCancel = () => {
  visibleModel.value = false;
};

const submitReport = () => {
  if (!form.content) {
    ElMessage.warning("请填写今日工作内容");
    return;
  }

  const reportData = {
    ...form,
    report_date: dayjs().format("YYYY-MM-DD"),
  };

  emit("submit", reportData);
};
</script>

<style scoped lang="scss">
/* 详情页样式 */
.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 16px;
  margin-bottom: 24px;
  border-bottom: 1px solid #ebeef5;

  .user-info {
    display: flex;
    align-items: center;
  }
}

.detail-section {
  margin-bottom: 24px;

  h4 {
    margin: 0 0 8px;
    font-size: 14px;
    color: #606266;
  }

  .content-box {
    padding: 12px;
    font-size: 14px;
    line-height: 1.6;
    color: #303133;
    white-space: pre-wrap;
    background-color: #f9fafc;
    border-radius: 4px;
  }
}

.detail-meta {
  padding-top: 16px;
  margin-top: 30px;
  font-size: 13px;
  color: #909399;
  text-align: right;
  border-top: 1px dashed #ebeef5;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  width: 100%;
}

.text-gray-500 {
  color: #909399;
}
.text-xs {
  font-size: 12px;
}
.font-bold {
  font-weight: 600;
}
.ml-3 {
  margin-left: 12px;
}
.ml-4 {
  margin-left: 16px;
}
</style>
