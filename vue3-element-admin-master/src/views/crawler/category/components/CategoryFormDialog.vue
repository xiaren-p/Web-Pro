<template>
  <el-dialog v-model="visible" :title="title" width="600px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="120px">
      <el-form-item label="类目名" prop="name">
        <el-input v-model="formData.name" placeholder="请输入类目名" />
      </el-form-item>
      <el-form-item label="类目ID" prop="category_id">
        <el-input v-model="formData.category_id" placeholder="请输入类目ID" />
      </el-form-item>
      <el-form-item label="类目站点" prop="site">
        <el-input v-model="formData.site" placeholder="请输入站点" />
      </el-form-item>
      <el-form-item label="类目归类" prop="category_type">
        <el-input v-model="formData.category_type" placeholder="请输入归类" />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">正常</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleClose">取 消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from "vue";
import { CategoryAPI, type CategoryForm } from "@/api/crawler/category";
import { ElMessage } from "element-plus";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const formRef = ref();
const loading = ref(false);

const formData = reactive<CategoryForm>({
  id: undefined,
  name: "",
  category_id: "",
  site: "",
  category_type: "",
  status: 1,
});

const rules = computed(() => ({
  name: [{ required: true, message: "类目名不能为空", trigger: "blur" }],
  category_id: [{ required: true, message: "类目ID不能为空", trigger: "blur" }],
}));

function open(id?: string) {
  visible.value = true;
  if (id) {
    title.value = "修改类目";
    CategoryAPI.getFormData(id).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    title.value = "新增类目";
    Object.assign(formData, {
      id: undefined,
      name: "",
      category_id: "",
      site: "",
      category_type: "",
      status: 1,
    });
  }
}

function handleClose() {
  visible.value = false;
  formRef.value?.resetFields();
  formRef.value?.clearValidate();
}

function handleSubmit() {
  formRef.value.validate((isValid: boolean) => {
    if (isValid) {
      loading.value = true;
      const id = (formData as any).id;
      if (id) {
        CategoryAPI.update(String(id), formData)
          .then(() => {
            ElMessage.success("修改成功");
            handleClose();
            emit("success");
          })
          .finally(() => (loading.value = false));
      } else {
        CategoryAPI.create(formData)
          .then(() => {
            ElMessage.success("新增成功");
            handleClose();
            emit("success");
          })
          .finally(() => (loading.value = false));
      }
    }
  });
}

defineExpose({ open });
</script>
