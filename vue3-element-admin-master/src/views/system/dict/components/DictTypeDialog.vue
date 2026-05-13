<template>
  <el-dialog v-model="visible" :title="title" width="500px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
      <el-form-item label="字典名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入字典名称" />
      </el-form-item>

      <el-form-item label="字典编码" prop="dictCode">
        <el-input v-model="formData.dictCode" placeholder="请输入字典编码" />
      </el-form-item>

      <el-form-item label="状态">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">启用</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="formData.remark" type="textarea" placeholder="请输入备注" />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" :loading="loading" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleClose">取 消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { DictAPI, type DictForm } from "@/api/dict";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const loading = ref(false);
const formRef = ref();

const formData = reactive<DictForm>({});

const rules = computed(() => {
  const rules: Partial<Record<string, any>> = {
    name: [{ required: true, message: "请输入字典名称", trigger: "blur" }],
    dictCode: [{ required: true, message: "请输入字典编码", trigger: "blur" }],
  };
  return rules;
});

/**
 * 打开弹窗
 *
 * @param id 字典ID
 */
function open(id?: string) {
  visible.value = true;
  if (id) {
    title.value = "修改字典";
    DictAPI.getFormData(id).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    title.value = "新增字典";
    formData.id = undefined;
    formData.name = undefined;
    formData.dictCode = undefined;
    formData.status = 1;
    formData.remark = undefined;
  }
}

// 提交字典表单
function handleSubmit() {
  formRef.value.validate((isValid: boolean) => {
    if (isValid) {
      loading.value = true;
      const id = formData.id;
      if (id) {
        DictAPI.update(id, formData)
          .then(() => {
            ElMessage.success("修改成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        DictAPI.create(formData)
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

// 关闭字典弹窗
function handleClose() {
  visible.value = false;
  formRef.value.resetFields();
  formRef.value.clearValidate();
}

defineExpose({ open });
</script>
