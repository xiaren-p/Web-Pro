<template>
  <el-card shadow="never" class="mt-2">
    <div class="flex flex-wrap">
      <!-- 左侧问候语区域 -->
      <div class="flex-1 flex items-start">
        <img
          class="w80px h80px rounded-full"
          :src="userStore.userInfo.avatar + '?imageView2/1/w/80/h/80'"
        />
        <div class="ml-5">
          <p>{{ greetings }}</p>
          <p class="text-sm text-gray">{{ weatherText }}</p>
        </div>
      </div>

      <!-- 右侧图标区域 - PC端 -->
      <div class="hidden sm:block">
        <div class="flex items-end space-x-6">
          <!-- 仓库 -->
          <div>
            <div class="font-bold color-#ff9a2e text-sm flex items-center">
              <el-icon class="mr-2px"><Folder /></el-icon>
              仓库
            </div>
            <div class="mt-3 whitespace-nowrap">
              <el-link href="" target="_blank">
                <div class="i-svg:gitee text-lg color-#F76560" />
              </el-link>
              <el-divider direction="vertical" />
              <el-link href="" target="_blank">
                <div class="i-svg:github text-lg color-#4080FF" />
              </el-link>
            </div>
          </div>

          <!-- 文档 -->
          <div>
            <div class="font-bold color-#4080ff text-sm flex items-center">
              <el-icon class="mr-2px"><Document /></el-icon>
              文档
            </div>
            <div class="mt-3 whitespace-nowrap">
              <el-link href="" target="_blank">
                <div class="i-svg:juejin text-lg" />
              </el-link>
            </div>
          </div>

          <!-- 视频 -->
          <div>
            <div class="font-bold color-#f76560 text-sm flex items-center">
              <el-icon class="mr-2px"><VideoCamera /></el-icon>
              视频
            </div>
            <div class="mt-3 whitespace-nowrap">
              <el-link href="" target="_blank">
                <div class="i-svg:bilibili text-lg" />
              </el-link>
            </div>
          </div>
        </div>
      </div>

      <!-- 移动端图标区域 -->
      <div class="w-full sm:hidden mt-3">
        <div class="flex justify-end space-x-4 overflow-x-auto">
          <!-- 仓库图标 -->
          <el-link href="" target="_blank">
            <div class="i-svg:gitee text-lg color-#F76560" />
          </el-link>
          <el-link href="" target="_blank">
            <div class="i-svg:github text-lg color-#4080FF" />
          </el-link>

          <!-- 文档图标 -->
          <el-link href="" target="_blank">
            <div class="i-svg:juejin text-lg" />
          </el-link>

          <!-- 视频图标 -->
          <el-link href="" target="_blank">
            <div class="i-svg:bilibili text-lg" />
          </el-link>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { useUserStore } from "@/store/modules/user-store";
import { WeatherAPI } from "@/backend";
import { Folder, Document, VideoCamera } from "@element-plus/icons-vue";

const userStore = useUserStore();

// 当前时间（用于计算问候语）
const currentDate = new Date();

// 问候语
const greetings = computed(() => {
  const hours = currentDate.getHours();
  const nickname = userStore.userInfo.nickname;
  if (hours >= 6 && hours < 8) {
    return "晨起披衣出草堂，轩窗已自喜微凉🌅！";
  } else if (hours >= 8 && hours < 12) {
    return `上午好，${nickname}！`;
  } else if (hours >= 12 && hours < 18) {
    return `下午好，${nickname}！`;
  } else if (hours >= 18 && hours < 24) {
    return `晚上好，${nickname}！`;
  } else {
    return "偷偷向银河要了一把碎星，只等你闭上眼睛撒入你的梦中，晚安🌛！";
  }
});

// 天气信息
const weatherText = ref("正在获取天气...");

const fetchWeather = async () => {
  try {
    const w = await WeatherAPI.getLive();
    if (w && w.weather) {
      weatherText.value = `${w.city} ${w.weather}，气温${w.temperature}℃，${w.winddirection}风${w.windpower}级`;
    }
  } catch (e) {
    weatherText.value = "天气获取失败";
    console.error("Weather fetch failed", e);
  }
};

onMounted(() => {
  fetchWeather();
});
</script>
