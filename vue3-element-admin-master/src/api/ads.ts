import request from "@/utils/request";

export function getAdCampaigns(params: any) {
  return request({
    url: "/ads/campaigns",
    method: "get",
    params,
  });
}
