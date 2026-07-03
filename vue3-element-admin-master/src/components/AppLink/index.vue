<template>
  <component :is="linkType" v-bind="linkProps(to)">
    <slot />
  </component>
</template>

<script setup lang="ts">
defineOptions({
  name: "AppLink",
  inheritAttrs: false,
});

import { isExternal } from "@/utils/index";
import type { RouteLocationRaw } from "vue-router";

/** 智能链接组件：自动判断外部链接（<a>）还是路由跳转（<router-link>）。 */
const props = defineProps<{
  to: RouteLocationRaw & { path?: string };
}>();

const isExternalLink = computed(() => {
  return isExternal(props.to.path || "");
});

const linkType = computed(() => (isExternalLink.value ? "a" : "router-link"));

const linkProps = (to: any) => {
  if (isExternalLink.value) {
    return {
      href: to.path,
      target: "_blank",
      rel: "noopener noreferrer",
    };
  }
  return { to };
};
</script>
