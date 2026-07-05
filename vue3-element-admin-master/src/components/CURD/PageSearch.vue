<template>
  <div v-show="isVisible">
    <el-card v-bind="cardAttrs">
      <el-form ref="queryFormRef" :model="queryParams" v-bind="formAttrs" :class="isGrid">
        <template v-for="(item, index) in formItems" :key="item.prop">
          <el-form-item
            v-show="isExpand ? true : index < showNumber"
            :label="item?.label"
            :prop="item.prop"
          >
            <template #label>
              <span class="flex-y-center">
                {{ item?.label || "" }}
                <el-tooltip v-if="item?.tips" v-bind="getTooltipProps(item.tips)">
                  <QuestionFilled class="w-4 h-4 mx-1" />
                </el-tooltip>
                <span v-if="searchConfig.colon" class="ml-0.5">:</span>
              </span>
            </template>
            <slot
              v-if="item.type === 'custom'"
              :name="item.slotName"
              :form-data="queryParams"
              :prop="item.prop"
              :attrs="{ style: { width: '100%' }, ...item.attrs }"
            />
            <el-cascader
              v-else-if="item.type === 'cascader'"
              v-model.trim="queryParams[item.prop]"
              v-bind="{ style: { width: '100%' }, ...item.attrs }"
              v-on="item.events || {}"
            />
            <component
              :is="componentMap.get(item.type)"
              v-else
              v-model.trim="queryParams[item.prop]"
              v-bind="{ style: { width: '100%' }, ...item.attrs }"
              v-on="item.events || {}"
            >
              <template v-if="item.type === 'select'">
                <template v-for="opt in item.options" :key="opt.value">
                  <el-option :label="opt.label" :value="opt.value" />
                </template>
              </template>
            </component>
          </el-form-item>
        </template>
        <el-form-item :class="{ 'col-[auto/-1] justify-self-end': searchConfig?.grid === 'right' }">
          <el-button icon="search" type="primary" @click="handleQuery">搜索</el-button>
          <el-button icon="refresh" @click="handleReset">重置</el-button>
          <template v-if="isExpandable && formItems.length > showNumber">
            <el-link class="ml-3" type="primary" underline="never" @click="isExpand = !isExpand">
              {{ isExpand ? "收起" : "展开" }}
              <component :is="isExpand ? ArrowUp : ArrowDown" class="w-4 h-4 ml-2" />
            </el-link>
          </template>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * CURD 搜索表单组件。支持展开/收缩、多列网格、自定义插槽。
 */
import type { IObject, IForm, ISearchConfig, ISearchComponent } from "./types";
import { ArrowUp, ArrowDown } from "@element-plus/icons-vue";
import { ElInput, ElSelect, ElCascader, ElInputNumber, ElDatePicker, ElTimePicker, ElTimeSelect, ElTreeSelect, ElInputTag } from "element-plus";
import type { FormInstance } from "element-plus";
import InputTag from "@/components/InputTag/index.vue";

const props = defineProps<{ searchConfig: ISearchConfig }>();
const emit = defineEmits<{
  queryClick: [queryParams: IObject];
  resetClick: [queryParams: IObject];
}>();

const componentMap = new Map<ISearchComponent, any>([
  ["input", markRaw(ElInput)],
  ["select", markRaw(ElSelect)],
  ["cascader", markRaw(ElCascader)],
  ["input-number", markRaw(ElInputNumber)],
  ["date-picker", markRaw(ElDatePicker)],
  ["time-picker", markRaw(ElTimePicker)],
  ["time-select", markRaw(ElTimeSelect)],
  ["tree-select", markRaw(ElTreeSelect)],
  ["input-tag", markRaw(ElInputTag)],
  ["custom-tag", markRaw(InputTag)],
]);

const queryFormRef = ref<FormInstance>();
const queryParams = reactive<IObject>({});
const isVisible = ref(true);
const formItems = reactive(props.searchConfig?.formItems ?? []);
const isExpandable = ref(props.searchConfig?.isExpandable ?? true);
const isExpand = ref(false);
const showNumber = computed(() =>
  isExpandable.value ? (props.searchConfig?.showNumber ?? 3) : formItems.length
);
const cardAttrs = computed<IObject>(() => ({
  shadow: "never",
  style: { "margin-bottom": "12px" },
  ...props.searchConfig?.cardAttrs,
}));
const formAttrs = computed<IForm>(() => ({ inline: true, ...props.searchConfig?.form }));
const isGrid = computed(() =>
  props.searchConfig?.grid
    ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 3xl:grid-cols-5 4xl:grid-cols-6 gap-5"
    : "flex flex-wrap gap-x-8 gap-y-4"
);

const getTooltipProps = (tips: string | IObject) =>
  typeof tips === "string" ? { content: tips } : tips;
const handleQuery = () => emit("queryClick", queryParams);
const handleReset = () => {
  queryFormRef.value?.resetFields();
  emit("resetClick", queryParams);
};

onMounted(() => {
  formItems.forEach((item) => {
    if (item?.initFn) item.initFn(item);
    if (["input-tag", "custom-tag", "cascader"].includes(item?.type ?? "")) {
      queryParams[item.prop] = Array.isArray(item.initialValue) ? item.initialValue : [];
    } else if (item.type === "input-number") {
      queryParams[item.prop] = item.initialValue ?? null;
    } else {
      queryParams[item.prop] = item.initialValue ?? "";
    }
  });
});

defineExpose({
  /** 获取当前查询参数。 */
  getQueryParams: () => queryParams,
  /** 切换搜索表单的显示/隐藏。 */
  toggleVisible: () => (isVisible.value = !isVisible.value),
});
</script>

<style lang="scss" scoped>
:deep(.el-input-number .el-input__inner) {
  text-align: left;
}
.el-form-item {
  margin-right: 0;
  margin-bottom: 0;
}
</style>
