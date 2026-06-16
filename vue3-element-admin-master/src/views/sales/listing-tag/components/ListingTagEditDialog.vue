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
        <el-select
          v-model="formData.type"
          placeholder="请选择标签类型"
          filterable
          allow-create
          style="width: 100%"
        >
          <el-option v-for="item in typeOptions" :key="item" :label="item" :value="item" />
        </el-select>
      </el-form-item>
      <el-form-item label="标签颜色" prop="color">
        <div class="color-picker-wrapper">
          <div class="color-input-row">
            <el-color-picker v-model="formData.color" show-alpha />
            <el-input
              v-model="formData.color"
              placeholder="输入颜色值"
              class="color-input"
              @input="handleColorInput"
            />
          </div>
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
      <el-form-item v-if="isEdit" label="创建人">
        <el-input :model-value="currentRow?.createByName || '-'" disabled />
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
import { reactive, ref, computed, watch, nextTick } from "vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
import { presetColors } from "@/views/sales/listing-tag/constants";
import { ListingTagAPI, type ListingTagForm, type ListingTagVO } from "@/api/sales/listing-tag";

const props = defineProps<{
  visible: boolean;
  row?: ListingTagVO | null;
  typeOptions: string[];
}>();

const emit = defineEmits(["update:visible", "success"]);

const formRef = ref<FormInstance>();
const saveLoading = ref(false);
const currentRow = ref<ListingTagVO | null>(null);

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

const initForm = () => {
  if (props.row) {
    currentRow.value = props.row;
    formData.tagName = props.row.tagName || "";
    formData.type = props.row.type || "";
    formData.color = props.row.color || "#409eff";
  } else {
    currentRow.value = null;
    formData.tagName = "";
    formData.type = "";
    formData.color = "#409eff";
  }
  nextTick(() => {
    formRef.value?.clearValidate();
  });
};

const handleColorInput = (val: string) => {
  // 颜色选择器双向绑定即可，这里只做格式化校验
  if (val && !/^#[0-9a-fA-F]{3,8}$/.test(val)) {
    // 简单校验，不合法时保持当前值，在 UI 上通过 el-color-picker 修正就行
  }
};

const handleSave = async () => {
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
};
</script>

<style scoped lang="scss">
.color-picker-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
}

.color-input-row {
  display: flex;
  gap: 12px;
  align-items: center;
}

.color-input {
  flex: 1;
}

.preset-colors {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.preset-color {
  position: relative;
  width: 32px;
  height: 32px;
  cursor: pointer;
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--border-base);
  transition: all var(--transition-fast);

  &:hover {
    box-shadow: 0 4px 12px var(--shadow-sm);
    transform: scale(1.1);
  }

  &.active {
    box-shadow: 0 0 0 2px var(--color-primary-500);

    &::after {
      position: absolute;
      top: 50%;
      left: 50%;
      width: 12px;
      height: 12px;
      content: "";
      background-color: var(--surface-base);
      border-radius: 50%;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
      transform: translate(-50%, -50%);
    }
  }
}
</style>
