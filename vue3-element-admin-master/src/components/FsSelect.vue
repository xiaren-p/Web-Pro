<template>
  <div class="fs-select" :style="containerStyle">
    <el-select
      v-model="internalValue"
      :multiple="multiple"
      :filterable="false"
      :remote="remote"
      :remote-method="onRemote"
      :reserve-keyword="reserveKeyword"
      :placeholder="placeholder"
      :clearable="clearable"
      :size="size"
      collapse-tags
      style="width: 100%"
      :remote-show-suffix="true"
      @change="onChange"
      @visible-change="onVisibleChange"
    >
      <template v-if="remote || filterable" #header>
        <div style="padding: 4px 8px">
          <el-input
            v-model="searchKeyword"
            placeholder="输入关键字进行搜索..."
            size="small"
            clearable
            @input="handleHeaderSearch"
            @click.stop
          />
        </div>
      </template>

      <el-option
        v-if="showSelectAll"
        :key="ALL_OPTION"
        :label="selectAllLabel"
        :value="ALL_OPTION"
      />

      <el-option
        v-for="option in filteredOptions"
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
import { ref, watch, computed } from "vue";
import type { PropType } from "vue";

const props = defineProps({
  modelValue: { type: [Array, String, Number], default: () => [] },
  options: { type: Array as PropType<any[]>, default: () => [] },
  multiple: { type: Boolean, default: false },
  filterable: { type: Boolean, default: true },
  remote: { type: Boolean, default: false },
  remoteMethod: { type: Function, default: null },
  reserveKeyword: { type: Boolean, default: true },
  placeholder: { type: String, default: "" },
  clearable: { type: Boolean, default: true },
  showSelectAll: { type: Boolean, default: true },
  selectAllLabel: { type: String, default: "全选" },
  showOnly: { type: Boolean, default: false },
  size: { type: String as PropType<"large" | "default" | "small">, default: "default" },
});

const emit = defineEmits(["update:modelValue", "change", "only"]);

const ALL_OPTION = "__ALL__";

const searchKeyword = ref("");

const filteredOptions = computed(() => {
  if (props.remote || !props.filterable || !searchKeyword.value) {
    return props.options;
  }
  const kw = searchKeyword.value.toLowerCase();
  return props.options.filter((o) => {
    const label = (o.label || o.title || o.value || "").toString().toLowerCase();
    const code = (o.code || "").toString().toLowerCase();
    return label.includes(kw) || code.includes(kw);
  });
});

function handleHeaderSearch() {
  if (props.remote) {
    onRemote(searchKeyword.value);
  }
}

function onVisibleChange(visible: boolean) {
  if (!visible) {
    if (props.remote) {
      searchKeyword.value = "";
      onRemote("");
    } else if (props.filterable) {
      searchKeyword.value = "";
    }
  }
}

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
    const newVal: any = props.multiple ? (Array.isArray(v) ? v.slice() : []) : v;
    // 内容相同时跳过，避免因引用变化触发下游 watch 形成死循环
    const oldVal = internalValue.value;
    if (JSON.stringify(oldVal) === JSON.stringify(newVal)) return;
    internalValue.value = newVal;
  },
  { deep: true }
);

watch(internalValue, (newV, oldV) => {
  // 内容相同时跳过，避免因引用变化形成 emit→接收→emit 死循环
  if (JSON.stringify(oldV) === JSON.stringify(newV)) return;

  // Handle select all
  if (props.multiple && Array.isArray(newV) && newV.includes(ALL_OPTION)) {
    const all = props.options.map((o: any) => o.value);
    const wasAllSelected = oldV && Array.isArray(oldV) && oldV.length === all.length;

    if (wasAllSelected) {
      internalValue.value = [];
      emit("update:modelValue", []);
      emit("change", []);
    } else {
      internalValue.value = all;
      emit("update:modelValue", all);
      emit("change", all);
    }
    return;
  }
  emit("update:modelValue", newV);
  emit("change", newV);
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

/**
 * 计算组件容器宽度：
 * 多选且已选中时，根据“首项文本 + +N”估算最小宽度，
 * 并使用 width=max(100%, Xpx) 让外层容器真正变宽，推动后续筛选项重新排布。
 *
 * @returns {Record<string, string>} 容器样式对象
 */
const containerStyle = computed((): Record<string, string> => {
  if (!props.multiple) return {};
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  if (vals.length === 0) return {};

  const firstVal = vals[0];
  const opt = (props.options as any[]).find((o: any) => o.value === firstVal);
  const label: string = opt ? String(opt.label ?? opt.title ?? firstVal) : String(firstVal);

  // CJK 字符宽约 14px，ASCII 宽约 8px
  const charPx = [...label].reduce(
    (acc, ch) => acc + (/[\u4e00-\u9fff\uff00-\uffef]/.test(ch) ? 14 : 8),
    0
  );
  const countPx = vals.length > 1 ? 42 : 0; // "+N" 徽标宽度
  const total = charPx + countPx + 56; // 56 = 内边距 + 箭头图标 + 安全余量
  return { minWidth: `${total}px` };
});
</script>

<style scoped>
/**
 * Element Plus collapse-tags DOM 结构：
 *   .el-select__tags
 *     span                  ← 可见 tag 的包裹层
 *       .el-tag             ← 第一个选中项
 *     .el-tag               ← +N 计数 badge（直接子节点）
 */

/* 可见第一项：兼容新旧 DOM，去掉底色/边框/关闭按钮，显示纯黑色文字 */
:deep(.el-select__selection .el-select__selected-item:first-child .el-tag),
:deep(.el-select__tags > span .el-tag) {
  padding-right: 2px !important;
  color: var(--text-primary) !important;
  background-color: transparent !important;
  border-color: transparent !important;
}
:deep(.el-select__selection .el-select__selected-item:first-child .el-tag .el-tag__close),
:deep(.el-select__tags > span .el-tag .el-tag__close) {
  display: none !important;
}

/* +N 计数 badge：兼容新旧 DOM */
:deep(.el-select__selection .el-select__selected-item:not(:first-child) .el-tag),
:deep(.el-select__tags > .el-tag) {
  padding: 0 6px !important;
  color: var(--text-secondary) !important;
  background-color: var(--surface-subtle) !important;
  border-color: var(--border-base) !important;
  border-radius: 4px !important;
}

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
  color: var(--text-tertiary);
}
</style>
