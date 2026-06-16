<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑标签' : '新增标签'"
    width="480px"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-form ref="formRef" :model="formData" :rules="formRules" label-width="90px">
      <el-form-item label="标签名称" prop="tagName">
        <el-input
          v-model="formData.tagName"
          placeholder="请输入标签名称"
          maxlength="100"
          show-word-limit
        />
      </el-form-item>
      <el-form-item label="标签类型" prop="type">
        <el-select v-model="formData.type" placeholder="请选择标签类型" style="width: 100%">
          <el-option
            v-for="item in tagTypeOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="标签颜色" prop="color">
        <div class="color-picker-wrapper">
          <el-color-picker v-model="formData.color" show-alpha />
          <div class="preset-colors">
            <span
              v-for="color in presetColors"
              :key="color.value"
              class="preset-color"
              :class="{ active: formData.color === color.value }"
              :style="{ backgroundColor: color.value }"
              @click="formData.color = color.value"
            />
          </div>
        </div>
      </el-form-item>
    </el-form>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="emit('update:visible', false)">取消</el-button>
        <el-button type="primary" :loading="saveLoading" @click="handleSave">保存</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
/**
 * Listing 标签编辑/新增对话框组件。
 */
import { reactive, ref, computed, watch } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { tagTypeOptions, presetColors } from "../constants";
import { ListingTagAPI, type ListingTagForm, type ListingTagVO } from "@/api/sales/listing-tag";

const props = defineProps<{
  visible: boolean;
  row?: ListingTagVO | null;
}>();

const emit = defineEmits(["update:visible", "success"]);

const formRef = ref<FormInstance>();
const saveLoading = ref(false);

const isEdit = computed(() => !!props.row?.id);

const formData = reactive<ListingTagForm>({
  tagName: "",
  type: "",
  color: "#409eff",
});

const formRules: FormRules<ListingTagForm> = {
  tagName: [
    { required: true, message: "请输入标签名称", trigger: "blur" },
    { min: 1, max: 100, message: "标签名称长度在 1 到 100 个字符", trigger: "blur" },
  ],
  type: [{ required: true, message: "请选择标签类型", trigger: "change" }],
  color: [{ required: true, message: "请选择标签颜色", trigger: "change" }],
};

watch(
  () => props.visible,
  (val) => {
    if (val) {
      initForm();
    }
  }
);

function initForm() {
  if (props.row) {
    formData.tagName = props.row.tagName || "";
    formData.type = props.row.type || "";
    formData.color = props.row.color || "#409eff";
  } else {
    formData.tagName = "";
    formData.type = "";
    formData.color = "#409eff";
  }
  formRef.value?.clearValidate();
}

async function handleSave() {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (!valid) return;
    saveLoading.value = true;
    try {
      if (isEdit.value && props.row) {
        await ListingTagAPI.update(props.row.id, { ...formData });
        ElMessage.success("更新成功");
      } else {
        await ListingTagAPI.create({ ...formData });
        ElMessage.success("创建成功");
      }
      emit("update:visible", false);
      emit("success");
    } catch {
      ElMessage.error(isEdit.value ? "更新失败" : "创建失败");
    } finally {
      saveLoading.value = false;
    }
  });
}
</script>

<style scoped lang="scss">
.color-picker-wrapper {
  display: flex;
  gap: 16px;
  align-items: center;

  .preset-colors {
    display: flex;
    gap: 8px;
  }

  .preset-color {
    width: 28px;
    height: 28px;
    cursor: pointer;
    border-radius: 4px;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.1);
    transition: all 0.2s;

    &:hover {
      transform: scale(1.1);
    }

    &.active {
      box-shadow: 0 0 0 2px #409eff;
    }
  }
}
</style>
