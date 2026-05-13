/**
 * 天气 API：仪表盘实况查询。
 */
import request from "@/utils/request";

export const WeatherAPI = {
  getLive() {
    return request<any, any>({
      url: "/weather/live",
      method: "get",
    });
  },
};
