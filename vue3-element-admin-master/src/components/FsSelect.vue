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
      popper-class="fs-select-popper"
      @change="onChange"
      @visible-change="onVisibleChange"
    >
      <template v-if="remote || filterable" #header>
        <div class="fs-select-popper__header" @click.stop>
          <el-input
            v-model="searchKeyword"
            placeholder="输入关键字进行搜索..."
            size="small"
            clearable
            @input="handleHeaderSearch"
          />
        </div>
      </template>

      <el-option
        v-if="multiple && showSelectAll"
        :key="ALL_OPTION"
        :label="selectAllLabel"
        :value="ALL_OPTION"
        class="fs-select-popper__all-option"
      >
        <el-checkbox
          :model-value="isAllSelected"
          :indeterminate="isIndeterminate"
          @click.stop.prevent="toggleAll"
        />
        <span class="fs-select-popper__label">{{ selectAllLabel }}</span>
      </el-option>

      <el-option
        v-for="option in filteredOptions"
        :key="option.value"
        :label="option.label || option.title || option.value"
        :value="option.value"
        :class="{ 'fs-select-popper__check-option': multiple }"
      >
        <template #default>
          <el-checkbox
            v-if="multiple"
            :model-value="isChecked(option.value)"
            class="fs-select-popper__check"
          />
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
 * 判断传入值是否在当前多选列表中。
 *
 * @param {any} val - 待判断的选项值
 * @returns {boolean} 若已选中返回 true
 */
function isChecked(val: any): boolean {
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  return vals.includes(val);
}

/**
 * 是否全选：所有选项值都在已选列表中。
 */
const isAllSelected = computed((): boolean => {
  if (!props.multiple) return false;
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  const all = props.options.map((o: any) => o.value);
  return all.length > 0 && all.every((v) => vals.includes(v));
});

/**
 * 是否半选：至少选中一项但非全选。
 */
const isIndeterminate = computed((): boolean => {
  if (!props.multiple) return false;
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  const all = props.options.map((o: any) => o.value);
  return vals.length > 0 && vals.length < all.length;
});

/**
 * 全选/取消全选切换。
 */
function toggleAll(): void {
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  const all = props.options.map((o: any) => o.value);
  if (all.every((v) => vals.includes(v))) {
    internalValue.value = [];
  } else {
    internalValue.value = [...all];
  }
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

<style lang="scss">
/**
 * FsSelect 下拉面板全局样式
 * 必须用不带 scoped 的 <style> 块，因为 el-select 的下拉面板 teleport 到 body 下。
 */
.fs-select-popper {
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-popover) !important;

  .el-select-dropdown__header {
    padding: 8px 8px 4px;
  }

  // 搜索框
  &__header {
    padding: 8px 8px 4px;
  }

  // 全选行
  &__all-option {
    border-bottom: 1px solid var(--border-subtle);
    font-weight: var(--font-weight-medium);
  }

  // 复选框
  &__check {
    margin-right: 8px;
    pointer-events: none; // 点击由 el-option 处理
  }

  // 选项内 label 文本
  &__label {
    margin-left: 8px;
  }

  .el-select-dropdown__item {
    display: flex;
    align-items: center;
    padding: 8px 12px;
    transition: background-color var(--transition-fast);

    &.is-hovering {
      background-color: var(--surface-hover) !important;
    }

    &.is-selected {
      font-weight: var(--font-weight-normal);
      color: var(--text-primary);
      background-color: var(--surface-base);
    }
  }

  // 复选框样式覆盖
  .el-checkbox {
    height: auto;
    margin-right: 0;
    line-height: 1;

    .el-checkbox__inner {
      width: 16px;
      height: 16px;
      border-radius: var(--radius-sm);
      border-color: var(--border-strong);
      background-color: var(--surface-base);
      transition: all var(--transition-fast);

      &:hover {
        border-color: var(--color-primary-400);
      }
    }

    &.is-checked .el-checkbox__inner {
      background-color: var(--color-primary-500);
      border-color: var(--color-primary-500);
      &::after {
        border-width: 2px;
        height: 8px;
        left: 5px;
        top: 1px;
        width: 4px;
      }
    }

    &.is-indeterminate .el-checkbox__inner {
      background-color: var(--color-primary-500);
      border-color: var(--color-primary-500);
      &::before {
        height: 2px;
        left: 3px;
        right: 3px;
        top: 6px;
      }
    }

    .el-checkbox__label {
      display: none;
    }
  }
}
</style>
