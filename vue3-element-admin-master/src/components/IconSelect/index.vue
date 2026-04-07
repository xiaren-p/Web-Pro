<template>
  <div ref="iconSelectRef" :style="{ width: props.width }">
    <el-popover :visible="popoverVisible" :width="props.width" placement="bottom-end">
      <template #reference>
        <div @click="popoverVisible = !popoverVisible">
          <slot>
            <el-input v-model="selectedIcon" readonly placeholder="点击选择图标" class="reference">
              <template #prepend>
                <!-- 根据图标类型展示 -->
                <el-icon v-if="isElementIcon">
                  <component :is="selectedIcon.replace('el-icon-', '')" />
                </el-icon>
                <template v-else-if="isTablerIcon">
                  <div :class="`i-tabler:${selectedIcon.replace('tabler:', '')}`" />
                </template>
                <template v-else>
                  <div :class="`i-svg:${selectedIcon}`" />
                </template>
              </template>
              <template #suffix>
                <!-- 清空按钮 -->
                <el-icon
                  v-if="selectedIcon"
                  style="margin-right: 8px"
                  @click.stop="clearSelectedIcon"
                >
                  <CircleClose />
                </el-icon>

                <el-icon
                  :style="{
                    transform: popoverVisible ? 'rotate(180deg)' : 'rotate(0)',
                    transition: 'transform .5s',
                  }"
                >
                  <ArrowDown @click.stop="togglePopover" />
                </el-icon>
              </template>
            </el-input>
          </slot>
        </div>
      </template>

      <!-- 图标选择弹窗 -->
      <div ref="popoverContentRef">
        <el-input v-model="filterText" placeholder="搜索图标" clearable @input="filterIcons" />
        <el-tabs v-model="activeTab" @tab-click="handleTabClick">
          <el-tab-pane label="SVG 图标" name="svg">
            <el-scrollbar height="300px">
              <ul class="icon-grid">
                <li
                  v-for="icon in filteredSvgIcons"
                  :key="'svg-' + icon"
                  class="icon-grid-item"
                  @click="selectIcon(icon)"
                >
                  <el-tooltip :content="icon" placement="bottom" effect="light">
                    <div :class="`i-svg:${icon}`" />
                  </el-tooltip>
                </li>
              </ul>
            </el-scrollbar>
          </el-tab-pane>
          <el-tab-pane label="Tabler 图标" name="tabler">
            <el-scrollbar height="300px">
              <ul class="icon-grid">
                <li
                  v-for="icon in filteredTablerIcons"
                  :key="'tabler-' + icon"
                  class="icon-grid-item"
                  @click="selectIcon('tabler:' + icon)"
                >
                  <el-tooltip :content="icon" placement="bottom" effect="light">
                    <div :class="`i-tabler:${icon}`" />
                  </el-tooltip>
                </li>
              </ul>
            </el-scrollbar>
          </el-tab-pane>
          <el-tab-pane label="Element 图标" name="element">
            <el-scrollbar height="300px">
              <ul class="icon-grid">
                <li
                  v-for="icon in filteredElementIcons"
                  :key="icon"
                  class="icon-grid-item"
                  @click="selectIcon(icon)"
                >
                  <el-icon>
                    <component :is="icon" />
                  </el-icon>
                </li>
              </ul>
            </el-scrollbar>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
// 仅保留电商相关 Tabler 图标，避免一次性加载整个图标包导致卡顿
const TABLER_ECOMMERCE_ICONS = [
  "shopping-cart",
  "shopping-bag",
  "basket",
  "truck",
  "package",
  "barcode",
  "receipt",
  "credit-card",
  "wallet",
  "cash",
  "tag",
  "tags",
  "building-store",
  "chart-bar",
  "chart-line",
  "chart-pie",
  "box",
];

const props = defineProps({
  modelValue: {
    type: String,
    default: "",
  },
  width: {
    type: String,
    default: "500px",
  },
});

const emit = defineEmits(["update:modelValue"]);

const iconSelectRef = ref();
const popoverContentRef = ref();
const popoverVisible = ref(false);
const activeTab = ref("svg");

const svgIcons = ref<string[]>([]);
const elementIcons = ref<string[]>(Object.keys(ElementPlusIconsVue));
const tablerIcons = ref<string[]>(TABLER_ECOMMERCE_ICONS);
const selectedIcon = defineModel("modelValue", {
  type: String,
  required: true,
  default: "",
});

const filterText = ref("");
const filteredSvgIcons = ref<string[]>([]);
const filteredElementIcons = ref<string[]>(elementIcons.value);
const filteredTablerIcons = ref<string[]>(tablerIcons.value);
const isElementIcon = computed(() => {
  return selectedIcon.value && selectedIcon.value.startsWith("el-icon");
});
const isTablerIcon = computed(() => {
  return selectedIcon.value && selectedIcon.value.startsWith("tabler:");
});

function loadIcons() {
  const icons = import.meta.glob("../../assets/icons/*.svg");
  for (const path in icons) {
    const iconName = path.replace(/.*\/(.*)\.svg$/, "$1");
    svgIcons.value.push(iconName);
  }
  filteredSvgIcons.value = svgIcons.value;
}

function handleTabClick(tabPane: any) {
  activeTab.value = tabPane.props.name;
  filterIcons();
}

function filterIcons() {
  if (activeTab.value === "svg") {
    filteredSvgIcons.value = filterText.value
      ? svgIcons.value.filter((icon) => icon.toLowerCase().includes(filterText.value.toLowerCase()))
      : svgIcons.value;
  } else if (activeTab.value === "tabler") {
    filteredTablerIcons.value = filterText.value
      ? tablerIcons.value.filter((icon) =>
          icon.toLowerCase().includes(filterText.value.toLowerCase())
        )
      : tablerIcons.value;
  } else {
    filteredElementIcons.value = filterText.value
      ? elementIcons.value.filter((icon) =>
          icon.toLowerCase().includes(filterText.value.toLowerCase())
        )
      : elementIcons.value;
  }
}

function selectIcon(icon: string) {
  const iconName =
    activeTab.value === "element" ? "el-icon-" + icon : activeTab.value === "tabler" ? icon : icon;
  emit("update:modelValue", iconName);
  popoverVisible.value = false;
}

function togglePopover() {
  popoverVisible.value = !popoverVisible.value;
}

onClickOutside(iconSelectRef, () => (popoverVisible.value = false), {
  ignore: [popoverContentRef],
});

/**
 * 清空已选图标
 */
function clearSelectedIcon() {
  selectedIcon.value = "";
}

onMounted(() => {
  loadIcons();
  if (selectedIcon.value) {
    if (elementIcons.value.includes(selectedIcon.value.replace("el-icon-", ""))) {
      activeTab.value = "element";
    } else if (selectedIcon.value.startsWith("tabler:")) {
      activeTab.value = "tabler";
    } else {
      activeTab.value = "svg";
    }
  }
});
</script>

<style scoped lang="scss">
.reference :deep(.el-input__wrapper),
.reference :deep(.el-input__inner) {
  cursor: pointer;
}

.icon-grid {
  display: flex;
  flex-wrap: wrap;
}

.icon-grid-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  margin: 4px;
  cursor: pointer;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  transition: all 0.3s;
}

.icon-grid-item:hover {
  border-color: #4080ff;
  transform: scale(1.2);
}
</style>
