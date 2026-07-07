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
          <span class="fs-option-content">
            <el-tooltip
              :content="option.title || option.label"
              :show-after="500"
              placement="top-start"
            >
              <span class="fs-option-title">{{ option.title || option.label }}</span>
            </el-tooltip>
            <small v-if="option.code" class="sku-code">
              {{ option.code }}
              <span v-if="option.value && option.value !== option.code">{{ option.value }}</span>
            </small>
          </span>
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
/**
 * 通用选择器组件（FsSelect）。支持多选/单选、远程搜索、全选、本地过滤、仅筛选。
 */
import { ref, watch, computed } from "vue";

/** 下拉选项。 */
interface SelectOption {
  value: string | number;
  label?: string;
  title?: string;
  code?: string;
  img?: string;
  parent?: string;
  parent_asin?: string;
  [key: string]: unknown;
}

interface Props {
  modelValue?: string | number | (string | number)[];
  options?: SelectOption[];
  multiple?: boolean;
  filterable?: boolean;
  remote?: boolean;
  remoteMethod?: ((query: string) => void) | null;
  reserveKeyword?: boolean;
  placeholder?: string;
  clearable?: boolean;
  showSelectAll?: boolean;
  selectAllLabel?: string;
  showOnly?: boolean;
  size?: "large" | "default" | "small";
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: () => [],
  options: () => [],
  multiple: false,
  filterable: true,
  remote: false,
  remoteMethod: null,
  reserveKeyword: true,
  placeholder: "",
  clearable: true,
  showSelectAll: true,
  selectAllLabel: "全选",
  showOnly: false,
  size: "default",
});

const emit = defineEmits<{
  (e: "update:modelValue", value: string | number | (string | number)[]): void;
  (e: "change", value: string | number | (string | number)[]): void;
  (e: "only", value: string | number): void;
}>();

const ALL_OPTION = "__ALL__";

const searchKeyword = ref("");

const filteredOptions = computed(() => {
  if (props.remote || !props.filterable || !searchKeyword.value) return props.options;
  const kw = searchKeyword.value.toLowerCase();
  return (props.options || []).filter((o) => {
    const label = (o.label || o.title || o.value || "").toString().toLowerCase();
    const code = (o.code || "").toString().toLowerCase();
    const parent = (o.parent || o.parent_asin || "").toString().toLowerCase();
    return label.includes(kw) || code.includes(kw) || parent.includes(kw);
  });
});

function handleHeaderSearch() {
  if (props.remote) onRemote(searchKeyword.value);
}

function onVisibleChange(visible: boolean) {
  if (!visible) {
    if (props.remote) {
      searchKeyword.value = "";
      onRemote("");
    } else if (props.filterable) searchKeyword.value = "";
  }
}

type ValueType = string | number | (string | number)[];

const internalValue = ref<ValueType>(
  props.multiple
    ? Array.isArray(props.modelValue)
      ? props.modelValue.slice()
      : []
    : (props.modelValue ?? "")
);

/** 浅层比较 value 变化，避免 JSON.stringify 开销。 */
function isSameValue(a: ValueType, b: ValueType): boolean {
  if (a === b) return true;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((v, i) => v === b[i]);
  }
  return false;
}

watch(
  () => props.modelValue,
  (v) => {
    const newVal: ValueType = props.multiple ? (Array.isArray(v) ? v.slice() : []) : (v ?? "");
    if (isSameValue(internalValue.value, newVal)) return;
    internalValue.value = newVal;
  },
  { deep: true }
);

watch(internalValue, (newV, oldV) => {
  if (isSameValue(oldV, newV)) return;
  if (props.multiple && Array.isArray(newV) && newV.includes(ALL_OPTION)) {
    toggleAll();
    return;
  }
  emit("update:modelValue", newV);
  emit("change", newV);
});

function onRemote(query: string) {
  if (props.remote && typeof props.remoteMethod === "function") props.remoteMethod(query);
}

function onChange() {
  // no-op, watch handles emit
}

function selectOnly(value: string | number) {
  internalValue.value = props.multiple ? [value] : value;
  emit("only", value);
}

/** 判断传入值是否在当前多选列表中。 */
function isChecked(val: string | number): boolean {
  return Array.isArray(internalValue.value) ? internalValue.value.includes(val) : false;
}

const isAllSelected = computed((): boolean => {
  if (!props.multiple) return false;
  const vals = Array.isArray(internalValue.value) ? internalValue.value : [];
  const visibleValues = filteredOptions.value.map((o) => o.value);
  return visibleValues.length > 0 && visibleValues.every((v) => vals.includes(v));
});

const isIndeterminate = computed((): boolean => {
  if (!props.multiple) return false;
  const vals = Array.isArray(internalValue.value) ? internalValue.value : [];
  const visibleValues = filteredOptions.value.map((o) => o.value);
  const selectedVisibleCount = visibleValues.filter((v) => vals.includes(v)).length;
  return selectedVisibleCount > 0 && selectedVisibleCount < visibleValues.length;
});

function toggleAll(): void {
  const vals = Array.isArray(internalValue.value)
    ? internalValue.value.filter((v) => v !== ALL_OPTION)
    : [];
  const visibleValues = filteredOptions.value.map((o) => o.value);
  if (visibleValues.length === 0) return;
  if (visibleValues.every((v) => vals.includes(v))) {
    internalValue.value = vals.filter((v) => !visibleValues.includes(v));
  } else {
    internalValue.value = Array.from(new Set([...vals, ...visibleValues]));
  }
}

const containerStyle = computed((): Record<string, string> => {
  if (!props.multiple) return {};
  const vals = Array.isArray(internalValue.value) ? internalValue.value : [];
  if (vals.length === 0) return {};
  const firstVal = vals[0];
  const opt = (props.options || []).find((o) => o.value === firstVal);
  const label: string = opt ? String(opt.label ?? opt.title ?? firstVal) : String(firstVal);
  const charPx = [...label].reduce(
    (acc, ch) => acc + (/[\u4e00-\u9fff\uff00-\uffef]/.test(ch) ? 14 : 8),
    0
  );
  const countPx = vals.length > 1 ? 42 : 0;
  const total = charPx + countPx + 56;
  return { minWidth: `${Math.min(total, 260)}px`, maxWidth: "260px" };
});
</script>

<style scoped>
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
:deep(.el-select__selection .el-select__selected-item:not(:first-child) .el-tag),
:deep(.el-select__tags > .el-tag) {
  padding: 0 6px !important;
  color: var(--text-secondary) !important;
  background-color: var(--surface-subtle) !important;
  border-color: var(--border-base) !important;
  border-radius: 4px !important;
}
.fs-option-img {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  margin-right: 8px;
  vertical-align: middle;
  object-fit: cover;
  border-radius: 4px;
}
.fs-option-content {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}
.fs-option-title {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--text-primary);
  white-space: nowrap;
}
.only-btn {
  flex-shrink: 0;
  margin-left: 8px;
}
.sku-code {
  margin-top: 2px;
  margin-left: 0;
  color: var(--text-tertiary);
}
</style>

<style lang="scss">
.fs-select-popper {
  max-width: 480px;
  border-radius: var(--radius-lg) !important;
  box-shadow: var(--shadow-popover) !important;
  .el-select-dropdown__header {
    padding: 8px 8px 4px;
  }
  &__header {
    padding: 8px 8px 4px;
  }
  &__all-option {
    font-weight: var(--font-weight-medium);
    border-bottom: 1px solid var(--border-subtle);
  }
  &__check {
    margin-right: 8px;
    pointer-events: none;
  }
  &__label {
    margin-left: 8px;
  }
  .el-select-dropdown__item {
    display: flex;
    gap: 8px;
    align-items: center;
    height: auto;
    min-height: 48px;
    padding: 8px 12px;
    line-height: 1.35;
    transition: background-color var(--transition-fast);
    &.is-selected::after {
      content: none;
    }
    &.is-hovering {
      background-color: var(--surface-hover) !important;
    }
    &.is-selected {
      font-weight: var(--font-weight-normal);
      color: var(--text-primary);
      background-color: var(--surface-base);
    }
  }
  .el-checkbox {
    flex-shrink: 0;
    height: auto;
    margin-right: 0;
    line-height: 1;
    .el-checkbox__inner {
      width: 16px;
      height: 16px;
      background-color: var(--surface-base);
      border-color: var(--border-strong);
      border-radius: var(--radius-sm);
      transition: all var(--transition-fast);
      &:hover {
        border-color: var(--color-primary-400);
      }
    }
    &.is-checked .el-checkbox__inner {
      background-color: var(--color-primary-500);
      border-color: var(--color-primary-500);
    }
    &.is-indeterminate .el-checkbox__inner {
      background-color: var(--color-primary-500);
      border-color: var(--color-primary-500);
    }
    .el-checkbox__label {
      display: none;
    }
  }
}
</style>
