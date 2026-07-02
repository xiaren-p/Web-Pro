/**
 * 天气 API：仪表盘实况查询。
 */
import request from "@/utils/request";
import type { WeatherLive } from "./types";

/**
 * 获取指定城市的实时天气。
 *
 * 城市参数可选，不传时由后端读取系统默认城市（佛山南海区）。
 *
 * @param {string} [city] - 城市 adcode，可选
 * @returns {Promise<WeatherLive>} 高德实时天气数据
 */
export function getWeatherLive(city?: string): Promise<WeatherLive> {
  return request({
    url: "/common/weather/live",
    method: "get",
    params: city ? { city } : undefined,
  });
}
