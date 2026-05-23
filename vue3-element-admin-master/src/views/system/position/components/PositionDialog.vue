<template>
  <el-dialog
    v-model="dialog.visible"
    :title="dialog.title"
    width="500px"
    @close="handleCloseDialog"
  >
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="所属部门" prop="deptId">
        <el-select
          v-model="formData.deptId"
          placeholder="请选择所属部门"
          clearable
          style="width: 100%"
        >
          <el-option
            v-for="item in deptOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="岗位名称" prop="name">
        <el-input v-model="formData.name" placeholder="请输入岗位名称" />
      </el-form-item>

      <el-form-item label="岗位编码" prop="code">
        <el-input v-model="formData.code" placeholder="请输入岗位编码（英文、下划线）" />
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
          style="width: 120px"
        />
      </el-form-item>

      <el-form-item label="备注" prop="remark">
        <el-input
          v-model="formData.remark"
          type="textarea"
          :rows="3"
          :maxlength="200"
          show-word-limit
          placeholder="请输入备注"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button type="primary" :loading="loading" @click="handleSubmit">确 定</el-button>
        <el-button @click="handleCloseDialog">取 消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * 岗位新增 / 编辑弹窗：表单包含所属部门、名称、编码、状态、排序、备注。
 * 所属板块：system。
 */
import { DeptAPI } from "@/api/dept";
import { PositionAPI, type PositionForm } from "@/api/position";

const emit = defineEmits(["success"]);

const formRef = ref();
const loading = ref(false);

const deptOptions = ref<OptionType[]>([]);

const dialog = reactive({
  title: "",
  visible: false,
});

const formData = reactive<PositionForm>({
  sort: 1,
  status: 1,
});

const rules = reactive({
  name: [{ required: true, message: "请输入岗位名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入岗位编码", trigger: "blur" }],
  status: [{ required: true, message: "请选择状态", trigger: "blur" }],
});

/**
 * 打开岗位弹窗。
 *
 * @param positionId 岗位ID（编辑时传入，新增时为空）
 */
async function open(positionId?: string) {
  dialog.visible = true;
  deptOptions.value = await DeptAPI.getOptions();
  if (positionId) {
    dialog.title = "修改岗位";
    PositionAPI.getFormData(positionId).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    dialog.title = "新增岗位";
  }
}

/** 提交岗位表单 */
function handleSubmit() {
  formRef.value.validate((valid: boolean) => {
    if (valid) {
      loading.value = true;
      const positionId = formData.id;
      if (positionId) {
        PositionAPI.update(positionId, formData)
          .then(() => {
            ElMessage.success("修改成功");
            handleCloseDialog();
            emit("success");
          })
          .finally(() => (loading.value = false));
      } else {
        PositionAPI.create(formData)
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

/** 关闭弹窗并重置状态 */
function handleCloseDialog() {
  dialog.visible = false;
  formRef.value?.resetFields();
  formRef.value?.clearValidate();
  formData.id = undefined;
  formData.sort = 1;
  formData.status = 1;
  formData.remark = undefined;
  formData.deptId = undefined;
}

defineExpose({ open });
</script>
