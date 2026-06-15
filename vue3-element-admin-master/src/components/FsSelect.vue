<template>
  <div class="fs-select" :class="{ 'fs-select--fixed': fixed }" :style="containerStyle">
    <el-tooltip v-if="fixed && tagTooltip" :content="tagTooltip" placement="top" :show-after="500">
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
              <span class="fs-option-title" :title="option.title || option.label">
                {{ option.title || option.label }}
              </span>
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
    </el-tooltip>
    <el-select
      v-else
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
            <span class="fs-option-title" :title="option.title || option.label">
              {{ option.title || option.label }}
            </span>
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
  fixed: { type: Boolean, default: false },
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
    const parentAsin = (o.parent || o.parent_asin || "").toString().toLowerCase();
    return label.includes(kw) || code.includes(kw) || parentAsin.includes(kw);
  });
});

/**
 * 当前已选 tag 文本聚合（用于 tooltip 悬浮查看完整内容）。
 */
const tagTooltip = computed((): string => {
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  if (vals.length === 0) return "";
  const labels = vals.map((val) => {
    const option = (props.options as any[]).find((item: any) => item.value === val);
    return String(option?.title ?? option?.label ?? option?.code ?? val);
  });
  return labels.join("，");
});

function handleHeaderSearch() {
  if (props.remote) {
    onRemote(searchKeyword.value);
  }
}

function onRemote(query: string) {
  if (props.remote && typeof props.remoteMethod === "function") {
    props.remoteMethod(query);
  }
}

function onVisibleChange(visible: boolean) {
  if (!visible) {
    if (props.remote || props.filterable) {
      searchKeyword.value = "";
    }
    if (props.remote) {
      onRemote("");
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
    const oldVal = internalValue.value;
    if (JSON.stringify(oldVal) === JSON.stringify(newVal)) return;
    internalValue.value = newVal;
  },
  { deep: true }
);

watch(internalValue, (newV, oldV) => {
  if (JSON.stringify(oldV) === JSON.stringify(newV)) return;

  if (props.multiple && Array.isArray(newV) && newV.includes(ALL_OPTION)) {
    toggleAll();
    return;
  }
  emit("update:modelValue", newV);
  emit("change", newV);
});

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
  const visibleValues = filteredOptions.value.map((o: any) => o.value);
  return visibleValues.length > 0 && visibleValues.every((v) => vals.includes(v));
});

/**
 * 是否半选：当前可见结果中至少选中一项但非全选。
 */
const isIndeterminate = computed((): boolean => {
  if (!props.multiple) return false;
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  const visibleValues = filteredOptions.value.map((o: any) => o.value);
  const selectedVisibleCount = visibleValues.filter((v) => vals.includes(v)).length;
  return selectedVisibleCount > 0 && selectedVisibleCount < visibleValues.length;
});

/**
 * 全选/取消全选切换：只作用于当前搜索过滤后的可见结果。
 */
function toggleAll(): void {
  const vals = Array.isArray(internalValue.value)
    ? (internalValue.value as any[]).filter((v) => v !== ALL_OPTION)
    : [];
  const visibleValues = filteredOptions.value.map((o: any) => o.value);
  if (visibleValues.length === 0) return;

  if (visibleValues.every((v) => vals.includes(v))) {
    internalValue.value = vals.filter((v) => !visibleValues.includes(v));
  } else {
    internalValue.value = Array.from(new Set([...vals, ...visibleValues]));
  }
}

/**
 * 计算组件容器宽度。
 * fixed 模式下不做自适应扩展；否则根据首项文本 + +N 估算最小宽度。
 *
 * @returns {Record<string, string>} 容器样式对象
 */
const containerStyle = computed((): Record<string, string> => {
  if (props.fixed || !props.multiple) return {};
  const vals = Array.isArray(internalValue.value) ? (internalValue.value as any[]) : [];
  if (vals.length === 0) return {};

  const firstVal = vals[0];
  const opt = (props.options as any[]).find((o: any) => o.value === firstVal);
  const label: string = opt ? String(opt.label ?? opt.title ?? firstVal) : String(firstVal);

  const charPx = [...label].reduce(
    (acc, ch) => acc + (/[一-鿿＀-￯]/.test(ch) ? 14 : 8),
    0
  );
  const countPx = vals.length > 1 ? 42 : 0;
  const total = Math.min(charPx + countPx + 56, 180);
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

/* fixed 模式：强制截断显示 */
.fs-select--fixed :deep(.el-select__tags) {
  max-width: 100%;
  overflow: hidden;
}

.fs-option-img {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  margin-right: 8px;
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
