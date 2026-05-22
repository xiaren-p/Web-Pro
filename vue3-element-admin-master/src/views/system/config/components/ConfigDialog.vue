<template>
  <el-dialog v-model="visible" :title="title" width="500px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-suffix=":" label-width="100px">
      <el-form-item label="配置名称" prop="configName">
        <el-input v-model="formData.configName" placeholder="请输入配置名称" :maxlength="50" />
      </el-form-item>
      <el-form-item label="配置键" prop="configKey">
        <el-input v-model="formData.configKey" placeholder="请输入配置键" :maxlength="50" />
      </el-form-item>
      <el-form-item label="配置类型" prop="configType">
        <el-select v-model="formData.configType" placeholder="请选择配置类型">
          <el-option value="TEXT" label="文本" />
          <el-option value="PASSWORD" label="密码" />
        </el-select>
      </el-form-item>
      <el-form-item label="配置值" prop="configValue">
        <el-input
          v-model="formData.configValue"
          :type="formData.configType === 'PASSWORD' ? 'password' : 'text'"
          :show-password="formData.configType === 'PASSWORD'"
          placeholder="请输入配置值"
          :maxlength="100"
        />
      </el-form-item>
      <el-form-item label="描述" prop="remark">
        <el-input
          v-model="formData.remark"
          :rows="4"
          :maxlength="100"
          show-word-limit
          type="textarea"
          placeholder="请输入描述"
        />
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
import { ConfigAPI, type ConfigForm } from "@/api/config";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const loading = ref(false);
const formRef = ref();

const formData = reactive<ConfigForm>({
  id: undefined,
  configName: "",
  configKey: "",
  configValue: "",
  configType: "TEXT",
  remark: "",
});

const rules = reactive({
  configName: [{ required: true, message: "请输入系统配置名称", trigger: "blur" }],
  configKey: [{ required: true, message: "请输入系统配置编码", trigger: "blur" }],
  configValue: [{ required: true, message: "请输入系统配置值", trigger: "blur" }],
});

/**
 * 打开系统配置弹窗
 */
function open(id?: string) {
  visible.value = true;
  if (id) {
    title.value = "修改系统配置";
    ConfigAPI.getFormData(id).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    title.value = "新增系统配置";
    formData.id = undefined;
    formData.configName = "";
    formData.configKey = "";
    formData.configValue = "";
    formData.configType = "TEXT";
    formData.remark = "";
  }
}

// 系统配置表单提交
function handleSubmit() {
  formRef.value.validate((valid: any) => {
    if (valid) {
      loading.value = true;
      const id = formData.id;
      if (id) {
        ConfigAPI.update(id, formData)
          .then(() => {
            ElMessage.success("修改成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        ConfigAPI.create(formData)
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

// 关闭系统配置弹窗
function handleClose() {
  visible.value = false;
  formRef.value.resetFields();
  formRef.value.clearValidate();
}

defineExpose({ open });
</script>
