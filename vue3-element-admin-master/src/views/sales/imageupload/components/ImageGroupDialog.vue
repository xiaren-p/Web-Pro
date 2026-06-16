<template>
  <el-dialog v-model="visible" :title="title" width="500px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="图片组" prop="imageGroup">
        <el-input v-model="formData.imageGroup" placeholder="请输入图片组名称" />
      </el-form-item>
      <el-form-item label="Cloud 路径" prop="cloudPath">
        <el-input v-model="formData.cloudPath" placeholder="请输入 Cloud 路径" />
      </el-form-item>
    </el-form>
    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取 消</el-button>
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ImageUploadAPI, type ImageUploadForm } from "@/api/imageUpload";
import { ElMessage } from "element-plus"; // Import ElMessage explicitly if auto-import isn't working for logic, but usually it is. But better safe.

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const formRef = ref();

const formData = reactive<ImageUploadForm>({
  id: undefined,
  imageGroup: "",
  cloudPath: "",
});

const rules = {
  imageGroup: [{ required: true, message: "请输入图片组名称", trigger: "blur" }],
  // cloudPath 可以为空，故不设置 required 校验
};

function handleClose() {
  visible.value = false;
  formRef.value?.resetFields();
}

function open(row?: any) {
  visible.value = true;
  if (row && row.id) {
    title.value = "修改图片组";
    formData.id = row.id;
    formData.imageGroup = row.imageGroup;
    formData.cloudPath = row.cloudPath;
  } else {
    title.value = "新增图片组";
    formData.id = undefined;
    formData.imageGroup = "";
    formData.cloudPath = "";
  }
}

function handleSubmit() {
  formRef.value.validate((valid: boolean) => {
    if (valid) {
      const api = formData.id
        ? ImageUploadAPI.update(formData.id, formData)
        : ImageUploadAPI.create(formData);
      api.then(() => {
        ElMessage.success(formData.id ? "修改成功" : "新增成功");
        handleClose();
        emit("success");
      });
    }
  });
}

defineExpose({ open });
</script>
