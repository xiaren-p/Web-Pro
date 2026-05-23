<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑 NC 规则' : '新增 NC 规则'"
    width="520px"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="90px"
    >
      <el-form-item label="群组" prop="ncGroupId">
        <el-select
          v-model="form.ncGroupId"
          placeholder="请选择部门管理员群组"
          style="width: 100%"
          filterable
        >
          <el-option
            v-for="opt in groupOptions"
            :key="opt.id"
            :label="`${opt.deptName} - ${opt.name}`"
            :value="opt.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="子路径" prop="ncPath">
        <el-input
          v-model="form.ncPath"
          placeholder="如：技术部/机密文档（首尾斜杠自动去除）"
          clearable
        />
      </el-form-item>

      <el-form-item label="权限位" prop="permissionBits">
        <el-input-number
          v-model="form.permissionBits"
          :min="1"
          :max="31"
          controls-position="right"
          style="width: 140px"
        />
        <span class="perm-hint">READ=1 WRITE=2 CREATE=4 DELETE=8 SHARE=16（相加组合）</span>
      </el-form-item>

      <el-form-item label="是否生效" prop="status">
        <el-switch v-model="form.status" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取 消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确 认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * NC 规则新增/编辑弹窗：接受群组选项与当前规则数据，提交后通知父组件刷新。
 * 所属板块：nc。
 */
import type { FormInstance, FormRules } from "element-plus";
import type { NcFileRuleVO, NcFileRuleForm, NcGroupOption } from "@/api/nc/fileRule";

import { ref, watch } from "vue";
import { ElMessage } from "element-plus";

import { createNcFileRule, updateNcFileRule } from "@/api/nc/fileRule";

defineProps<{
  groupOptions: NcGroupOption[];
}>();

const emit = defineEmits<{
  (e: "saved"): void;
}>();

const visible = defineModel<boolean>({ required: true });

/** 当前正在编辑的规则，null 表示新增 */
const ruleData = defineModel<NcFileRuleVO | null>("ruleData");

const isEdit = ref(false);
const submitting = ref(false);
const formRef = ref<FormInstance>();

const defaultForm = (): NcFileRuleForm => ({
  ncGroupId: 0,
  ncPath: "",
  permissionBits: 1,
  isGroupFolder: true,
  status: true,
});

const form = ref<NcFileRuleForm>(defaultForm());

const rules: FormRules = {
  ncGroupId: [{ required: true, message: "请选择群组", trigger: "change" }],
  ncPath: [
    { required: true, message: "请输入子路径", trigger: "blur" },
    { max: 500, message: "路径最长 500 字符", trigger: "blur" },
  ],
  permissionBits: [
    { required: true, message: "请输入权限位", trigger: "blur" },
    {
      validator: (_rule: unknown, value: number, callback: (e?: Error) => void) => {
        if (!Number.isInteger(value) || value < 1 || value > 31) {
          callback(new Error("权限位须为 1-31 之间的整数"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

watch(ruleData, (rule) => {
  if (rule) {
    isEdit.value = true;
    form.value = {
      ncGroupId: rule.ncGroupId,
      ncPath: rule.ncPath,
      permissionBits: rule.permissionBits,
      isGroupFolder: rule.isGroupFolder,
      status: rule.status,
    };
  } else {
    isEdit.value = false;
    form.value = defaultForm();
  }
});

/** 提交表单（新增 or 更新） */
async function handleSubmit(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  if (submitting.value) return;

  submitting.value = true;
  try {
    if (isEdit.value && ruleData.value) {
      await updateNcFileRule(ruleData.value.id, form.value);
      ElMessage.success("更新成功");
    } else {
      await createNcFileRule(form.value);
      ElMessage.success("新增成功");
    }
    emit("saved");
    handleClose();
  } catch {
    ElMessage.error(isEdit.value ? "更新失败" : "新增失败");
  } finally {
    submitting.value = false;
  }
}

/** 关闭弹窗并重置表单 */
function handleClose(): void {
  formRef.value?.resetFields();
  form.value = defaultForm();
  visible.value = false;
}
</script>

<style scoped lang="scss">
.perm-hint {
  margin-left: 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
