<template>
  <el-dropdown trigger="click" @command="handleLanguageChange">
    <div class="i-svg:language" :class="size" />
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="item in langOptions"
          :key="item.value"
          :disabled="appStore.language === item.value"
          :command="item.value"
        >
          {{ item.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
/**
 * 语言切换组件。
 */
import { useAppStore } from "@/store/modules/app-store";
import { LanguageEnum } from "@/enums/settings/locale-enum";

defineProps<{ size?: string }>();

const appStore = useAppStore();

const langOptions = [
  { value: LanguageEnum.ZH_CN, label: "中文" },
  { value: LanguageEnum.EN, label: "English" },
];

function handleLanguageChange(lang: string) {
  appStore.changeLanguage(lang as LanguageEnum);
}
</script>
