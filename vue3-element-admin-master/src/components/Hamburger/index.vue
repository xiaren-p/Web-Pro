<template>
  <div class="hamburger-wrapper" @click="toggleClick">
    <div :class="['i-svg:collapse', { hamburger: true, 'is-active': isActive }, hamburgerClass]" />
  </div>
</template>

<script setup lang="ts">
/**
 * 汉堡菜单按钮。控制侧边栏折叠/展开。
 */
import { useSettingsStore } from "@/store";
import { ThemeMode, SidebarColor } from "@/enums/settings/theme-enum";
import { LayoutMode } from "@/enums/settings/layout-enum";

defineProps<{ isActive: boolean }>();
const emit = defineEmits<{ (e: "toggleClick"): void }>();

const settingsStore = useSettingsStore();
const layout = computed(() => settingsStore.layout);

const hamburgerClass = computed(() => {
  if (settingsStore.theme === ThemeMode.DARK) return "hamburger--white";
  if (
    layout.value === LayoutMode.MIX &&
    settingsStore.sidebarColorScheme === SidebarColor.CLASSIC_BLUE
  )
    return "hamburger--white";
  return "";
});

function toggleClick() {
  emit("toggleClick");
}
</script>

<style scoped lang="scss">
.hamburger-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 15px;
  cursor: pointer;
  .hamburger {
    vertical-align: middle;
    transform: scaleX(-1);
    transition: transform 0.3s ease;
    &--white {
      color: var(--el-color-white);
    }
    &.is-active {
      transform: scaleX(1);
    }
  }
}
</style>
