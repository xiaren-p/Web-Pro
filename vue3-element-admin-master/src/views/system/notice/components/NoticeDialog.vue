<template>
  <el-dialog v-model="visible" :title="title" top="3vh" width="80%" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="通知标题" prop="title">
        <el-input v-model="formData.title" placeholder="通知标题" clearable />
      </el-form-item>

      <el-form-item label="通知类型" prop="type">
        <Dict v-model="formData.type" code="notice_type" />
      </el-form-item>
      <el-form-item label="通知等级" prop="level">
        <Dict v-model="formData.level" code="notice_level" />
      </el-form-item>
      <el-form-item label="目标类型" prop="targetType">
        <el-radio-group v-model="formData.targetType">
          <el-radio :value="1">全体</el-radio>
          <el-radio :value="2">指定</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="formData.targetType == 2" label="指定用户" prop="targetUserIds">
        <el-select v-model="formData.targetUserIds" multiple search placeholder="请选择指定用户">
          <el-option
            v-for="item in userOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="通知内容" prop="content">
        <WangEditor v-model="formData.content" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" :loading="loading" @click="handleSubmit">确定</el-button>
        <el-button @click="handleClose">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { NoticeAPI, type NoticeForm, UserAPI } from "@/backend";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const loading = ref(false);
const formRef = ref();

const userOptions = ref<OptionType[]>([]);
const formData = reactive<NoticeForm>({
  level: "L", // 默认优先级为低
  targetType: 1, // 默认目标类型为全体
});

const rules = reactive({
  title: [{ required: true, message: "请输入通知标题", trigger: "blur" }],
  content: [
    {
      required: true,
      message: "请输入通知内容",
      trigger: "blur",
      validator: (rule: any, value: string, callback: any) => {
        if (!value.replace(/<[^>]+>/g, "").trim()) {
          callback(new Error("请输入通知内容"));
        } else {
          callback();
        }
      },
    },
  ],
  type: [{ required: true, message: "请选择通知类型", trigger: "change" }],
});

/**
 * 打开通知公告弹窗
 * @param id 通知公告ID
 */
function open(id?: string) {
  UserAPI.getOptions().then((data) => {
    userOptions.value = data;
  });

  visible.value = true;
  if (id) {
    title.value = "修改公告";
    NoticeAPI.getFormData(id).then((data) => {
      formData.id = data.id;
      formData.title = data.title;
      formData.content = data.content;
      formData.type = data.type;
      formData.level = data.level || "L";
      formData.targetType = data.targetType || 1;
      formData.targetUserIds = data.targetUserIds || [];
    });
  } else {
    title.value = "新增公告";
    formData.id = undefined;
    formData.title = "";
    formData.content = "";
    formData.type = undefined;
    formData.level = "L";
    formData.targetType = 1;
    formData.targetUserIds = [];
  }
}

// 通知公告表单提交
function handleSubmit() {
  formRef.value.validate((valid: any) => {
    if (valid) {
      loading.value = true;
      const id = formData.id;
      if (id) {
        NoticeAPI.update(id, formData)
          .then(() => {
            ElMessage.success("修改成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        NoticeAPI.create(formData)
          .then(() => {
            ElMessage.success("新增成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      }
    }
  });
}

function handleClose() {
  visible.value = false;
  formRef.value.resetFields();
  formRef.value.clearValidate();
  formData.id = undefined;
  formData.targetType = 1;
}

defineExpose({ open });
</script>
