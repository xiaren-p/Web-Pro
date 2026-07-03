/**
 * 通用图片上传 API：复用 /users/upload-image 端点，支持缩略图参数。
 */
import request from "@/utils/request";

/** 图片上传返回结果。 */
export interface ImageUploadResult {
  url: string;
  name?: string;
  width?: number;
  height?: number;
  size?: number;
  thumbs?: Record<string, string>;
}

const UPLOAD_BASE_URL = "/users";

export const UploadAPI = {
  /**
   * 上传图片文件。
   *
   * @param file - 图片文件。
   * @param thumbs - 缩略图尺寸数组。
   * @returns 上传结果（含 URL）。
   */
  uploadImage(file: File, thumbs?: Array<number | string>) {
    const form = new FormData();
    form.append("file", file);
    const params: Record<string, string> = {};
    if (thumbs && thumbs.length) params.thumbs = thumbs.join(",");
    return request<any, ImageUploadResult>({
      url: `${UPLOAD_BASE_URL}/upload-image`, method: "post", data: form, params,
    });
  },
};
