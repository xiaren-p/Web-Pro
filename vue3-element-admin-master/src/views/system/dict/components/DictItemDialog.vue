<template>
  <el-dialog v-model="visible" :title="title" width="600px" @close="handleClose">
    <el-form ref="formRef" :model="formData" :rules="rules" label-width="100px">
      <el-form-item label="字典项标签" prop="label">
        <el-input v-model="formData.label" placeholder="请输入字典标签" />
      </el-form-item>
      <el-form-item label="字典项值" prop="value">
        <el-input v-model="formData.value" placeholder="请输入字典值" />
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="formData.status">
          <el-radio :value="1">启用</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="排序">
        <el-input-number v-model="formData.sort" controls-position="right" />
      </el-form-item>
      <el-form-item>
        <template #label>
          <div class="flex-y-center">
            标签类型
            <el-tooltip>
              <template #content>回显样式，为空时则显示 '文本'</template>
              <el-icon class="ml-1 cursor-pointer">
                <QuestionFilled />
              </el-icon>
            </el-tooltip>
          </div>
        </template>
        <el-select
          v-model="formData.tagType"
          placeholder="请选择标签类型"
          clearable
          @clear="formData.tagType = ''"
        >
          <template #label="{ value }">
            <el-tag v-if="value" :type="value">
              {{ formData.label ? formData.label : "字典标签" }}
            </el-tag>
          </template>
          <!-- <el-option label="默认文本" value="" /> -->
          <el-option v-for="type in tagType" :key="type" :label="type" :value="type">
            <div flex-y-center gap-10px>
              <el-tag :type="type">{{ formData.label ?? "字典标签" }}</el-tag>
              <span>{{ type }}</span>
            </div>
          </el-option>
        </el-select>
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
import type { TagProps } from "element-plus";
import { DictAPI, type DictItemForm, type DictItemPageVO } from "@/api/dict";

const emit = defineEmits(["success"]);

const visible = ref(false);
const title = ref("");
const loading = ref(false);
const formRef = ref();

const dictCode = ref("");

const formData = reactive<DictItemForm>({});

// 标签类型
const tagType: TagProps["type"][] = ["primary", "success", "info", "warning", "danger"];

const rules = computed(() => {
  const rules: Partial<Record<string, any>> = {
    value: [{ required: true, message: "请输入字典值", trigger: "blur" }],
    label: [{ required: true, message: "请输入字典标签", trigger: "blur" }],
  };

  return rules;
});

/**
 * 打开弹窗
 *
 * @param code 字典编码
 * @param row 字典项数据
 */
function open(code: string, row?: DictItemPageVO) {
  visible.value = true;
  dictCode.value = code;
  title.value = row ? "编辑字典项" : "新增字典项";

  if (row?.id) {
    DictAPI.getDictItemFormData(code, row.id).then((data) => {
      Object.assign(formData, data);
    });
  } else {
    formData.id = undefined;
    formData.sort = 1;
    formData.status = 1;
    formData.tagType = "";
    formData.label = undefined;
    formData.value = undefined;
  }
}

// 提交表单
function handleSubmit() {
  formRef.value.validate((isValid: boolean) => {
    if (isValid) {
      loading.value = true;
      const id = formData.id;

      formData.dictCode = dictCode.value;
      if (id) {
        DictAPI.updateDictItem(dictCode.value, id, formData)
          .then(() => {
            ElMessage.success("修改成功");
            emit("success");
            handleClose();
          })
          .finally(() => (loading.value = false));
      } else {
        DictAPI.createDictItem(dictCode.value, formData)
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
  formRef.value.resetFields();
  formRef.value.clearValidate();
}

defineExpose({ open });
</script>
