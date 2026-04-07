<template>
  <el-dialog
    v-model="dialog.visible"
    :title="dialog.title"
    width="500px"
    @close="handleCloseDialog"
  >
    <el-form ref="roleFormRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="角色名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入角色名称" />
      </el-form-item>

      <el-form-item label="角色编码" prop="code">
        <el-input v-model="formData.code" placeholder="请输入角色编码" />
      </el-form-item>

      <el-form-item label="数据权限" prop="dataScope">
        <el-select v-model="formData.dataScope">
          <el-option :key="1" label="全部数据" :value="1" />
          <el-option :key="2" label="部门及子部门数据" :value="2" />
          <el-option :key="3" label="本部门数据" :value="3" />
          <el-option :key="4" label="本人数据" :value="4" />
        </el-select>
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">正常</el-radio>
          <el-radio :value="0">停用</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="排序" prop="sort">
        <el-input-number
          v-model="formData.sort"
          controls-position="right"
          :min="0"
          style="width: 100px"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleCloseDialog">取 消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { RoleAPI, type RoleForm } from "@/backend";

const emit = defineEmits(["success"]);

const roleFormRef = ref();
const loading = ref(false);

const dialog = reactive({
  title: "",
  visible: false,
});

const formData = reactive<RoleForm>({
  sort: 1,
  status: 1,
});

const rules = reactive({
  name: [{ required: true, message: "请输入角色名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入角色编码", trigger: "blur" }],
  dataScope: [{ required: true, message: "请选择数据权限", trigger: "blur" }],
  status: [{ required: true, message: "请选择状态", trigger: "blur" }],
});

function open(roleId?: string) {
  dialog.visible = true;
  if (roleId) {
    dialog.title = "修改角色";
    RoleAPI.getFormData(roleId).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    dialog.title = "新增角色";
  }
}

function handleSubmit() {
  roleFormRef.value.validate((valid: any) => {
    if (valid) {
      loading.value = true;
      const roleId = formData.id;
      if (roleId) {
        RoleAPI.update(roleId, formData)
          .then(() => {
            ElMessage.success("修改成功");
            handleCloseDialog();
            emit("success");
          })
          .finally(() => (loading.value = false));
      } else {
        RoleAPI.create(formData)
          .then(() => {
            ElMessage.success("新增成功");
            handleCloseDialog();
            emit("success");
          })
          .finally(() => (loading.value = false));
      }
    }
  });
}

function handleCloseDialog() {
  dialog.visible = false;

  roleFormRef.value.resetFields();
  roleFormRef.value.clearValidate();

  formData.id = undefined;
  formData.sort = 1;
  formData.status = 1;
}

defineExpose({
  open,
});
</script>
