<template>
  <el-select
    v-if="type === 'select'"
    v-model="selectedValue"
    :placeholder="placeholder"
    :disabled="disabled"
    clearable
    :style="style"
    @change="handleChange"
  >
    <el-option
      v-for="option in options"
      :key="option.value"
      :label="option.label"
      :value="option.value"
    />
  </el-select>

  <el-radio-group
    v-else-if="type === 'radio'"
    v-model="selectedValue"
    :disabled="disabled"
    :style="style"
    @change="handleChange"
  >
    <el-radio v-for="option in options" :key="option.value" :value="option.value">
      {{ option.label }}
    </el-radio>
  </el-radio-group>

  <el-checkbox-group
    v-else-if="type === 'checkbox'"
    v-model="selectedValue"
    :disabled="disabled"
    :style="style"
    @change="handleChange"
  >
    <el-checkbox v-for="option in options" :key="option.value" :value="option.value">
      {{ option.label }}
    </el-checkbox>
  </el-checkbox-group>
</template>

<script setup lang="ts">
/**
 * 字典组件：根据 dictCode 自动加载字典项，渲染为 select / radio / checkbox。
 */
import { useDictStore } from "@/store";

const dictStore = useDictStore();

interface Props {
  code: string;
  /** v-model 绑定的选中值，支持 string / number / array */
  modelValue?: string | number | (string | number)[];
  type?: "select" | "radio" | "checkbox";
  placeholder?: string;
  disabled?: boolean;
  style?: Record<string, string>;
}

const props = withDefaults(defineProps<Props>(), {
  type: "select",
  placeholder: "请选择",
  disabled: false,
  style: () => ({ width: "300px" }),
});

const emit = defineEmits<{
  (e: "update:modelValue", value: string | number | (string | number)[]): void;
}>();

const options = ref<Array<{ label: string; value: string | number }>>([]);

const selectedValue = ref<string | number | (string | number)[] | undefined>(
  typeof props.modelValue === "string" || typeof props.modelValue === "number"
    ? props.modelValue
    : Array.isArray(props.modelValue)
      ? props.modelValue
      : undefined
);

watch(
  [() => props.modelValue, () => options.value],
  ([newValue, newOptions]) => {
    if (newOptions.length > 0 && newValue !== undefined) {
      if (props.type === "checkbox") {
        selectedValue.value = Array.isArray(newValue) ? newValue : [];
      } else {
        const matchedOption = newOptions.find(
          (option) => String(option.value) === String(newValue)
        );
        selectedValue.value = matchedOption?.value;
      }
    } else {
      selectedValue.value = undefined;
    }
  },
  { immediate: true }
);

/** 选中值变化时同步 v-model。 */
function handleChange(val: string | number | (string | number)[]): void {
  emit("update:modelValue", val);
}

onMounted(async () => {
  await dictStore.loadDictItems(props.code);
  options.value = dictStore.getDictItems(props.code);
});
</script>
