<template>
  <div class="fs-select">
    <el-select
      v-model="internalValue"
      :multiple="multiple"
      :filterable="!remote"
      :remote="remote"
      :remote-method="onRemote"
      :placeholder="placeholder"
      :clearable="clearable"
      collapse-tags
      style="width: 100%"
      @change="onChange"
    >
      <el-option
        v-if="showSelectAll"
        :key="ALL_OPTION"
        :label="selectAllLabel"
        :value="ALL_OPTION"
      />

      <el-option
        v-for="option in options"
        :key="option.value"
        :label="option.label || option.title || option.value"
        :value="option.value"
      >
        <template #default>
          <img v-if="option.img" :src="option.img" class="fs-option-img" />
          <span class="fs-option-title">{{ option.title || option.label }}</span>
          <small v-if="option.code" class="sku-code">{{ option.code }}</small>
          <el-button
            v-if="showOnly"
            class="only-btn"
            type="text"
            size="small"
            @click.stop.prevent="selectOnly(option.value)"
          >
            仅筛选此项
          </el-button>
        </template>
      </el-option>
    </el-select>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import type { PropType } from "vue";

const props = defineProps({
  modelValue: { type: [Array, String, Number], default: () => [] },
  options: { type: Array as PropType<any[]>, default: () => [] },
  multiple: { type: Boolean, default: false },
  remote: { type: Boolean, default: false },
  remoteMethod: { type: Function, default: null },
  placeholder: { type: String, default: "" },
  clearable: { type: Boolean, default: true },
  showSelectAll: { type: Boolean, default: true },
  selectAllLabel: { type: String, default: "全选" },
  showOnly: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "change", "only"]);

const ALL_OPTION = "__ALL__";

const internalValue = ref(
  props.multiple
    ? Array.isArray(props.modelValue)
      ? props.modelValue.slice()
      : []
    : props.modelValue
);

watch(
  () => props.modelValue,
  (v) => {
    internalValue.value = props.multiple ? (Array.isArray(v) ? v.slice() : []) : v;
  },
  { deep: true }
);

watch(internalValue, (v) => {
  // Handle select all
  if (props.multiple && Array.isArray(v) && v.includes(ALL_OPTION)) {
    const all = props.options.map((o: any) => o.value);
    internalValue.value = all;
    emit("update:modelValue", all);
    emit("change", all);
    return;
  }
  emit("update:modelValue", v);
  emit("change", v);
});

function onRemote(query: string) {
  if (props.remote && typeof props.remoteMethod === "function") {
    props.remoteMethod(query);
  }
}

function onChange() {
  // no-op, watch handles emit
}

function selectOnly(value: any) {
  const val = props.multiple ? [value] : value;
  internalValue.value = val as any;
  emit("only", value);
}
</script>

<style scoped>
.fs-option-img {
  width: 36px;
  height: 36px;
  margin-right: 8px;
  vertical-align: middle;
}
.fs-option-title {
  margin-right: 6px;
  vertical-align: middle;
}
.only-btn {
  float: right;
  margin-left: 8px;
}
.sku-code {
  margin-left: 6px;
  color: #999;
}
</style>
