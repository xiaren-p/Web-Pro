<template>
  <el-dialog v-model="visible" :title="title" width="600px" @closed="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="80px">
      <el-form-item label="上级部门" prop="parentId">
        <el-tree-select
          v-model="formData.parentId"
          placeholder="选择上级部门"
          :data="deptOptions"
          filterable
          check-strictly
          :render-after-expand="false"
        />
      </el-form-item>
      <el-form-item label="部门名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入部门名称" />
      </el-form-item>
      <el-form-item label="部门编号" prop="code">
        <el-input v-model="formData.code" placeholder="请输入部门编号" />
      </el-form-item>
      <el-form-item label="显示排序" prop="sort">
        <el-input-number
          v-model="formData.sort"
          controls-position="right"
          style="width: 100px"
          :min="0"
        />
      </el-form-item>
      <el-form-item label="部门状态">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">正常</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
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
import { DeptAPI, type DeptForm } from "@/backend";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const loading = ref(false);
const formRef = ref();

const deptOptions = ref<OptionType[]>([]);
const formData = reactive<DeptForm>({
  status: 1,
  parentId: "0",
  sort: 1,
});

const rules = reactive({
  parentId: [{ required: true, message: "上级部门不能为空", trigger: "change" }],
  name: [{ required: true, message: "部门名称不能为空", trigger: "blur" }],
  code: [{ required: true, message: "部门编号不能为空", trigger: "blur" }],
  sort: [{ required: true, message: "显示排序不能为空", trigger: "blur" }],
});

/**
 * 打开部门弹窗
 *
 * @param parentId 父部门ID
 * @param deptId 部门ID
 */
async function open(parentId?: string, deptId?: string) {
  visible.value = true;
  // 加载部门下拉数据
  const data = await DeptAPI.getOptions();
  deptOptions.value = [
    {
      value: "0",
      label: "顶级部门",
      children: data,
    },
  ];

  if (deptId) {
    title.value = "修改部门";
    DeptAPI.getFormData(deptId).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    title.value = "新增部门";
    formData.id = undefined;
    formData.parentId = parentId || "0";
    formData.status = 1;
    formData.sort = 1;
    formData.name = undefined;
    formData.code = undefined;
  }
}

// 提交部门表单
function handleSubmit() {
  formRef.value.validate((valid: any) => {
    if (valid) {
      loading.value = true;
      const deptId = formData.id;
      if (deptId) {
        DeptAPI.update(deptId, formData)
          .then(() => {
            ElMessage.success("修改成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        DeptAPI.create(formData)
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

// 关闭弹窗
function handleClose() {
  visible.value = false;
  formRef.value?.resetFields();
  formRef.value?.clearValidate();
}

defineExpose({ open });
</script>
