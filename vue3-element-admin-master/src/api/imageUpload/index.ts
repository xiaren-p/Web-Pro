/**
 * 商品图片上传管理 API：分页、表单、批量同步、CSV 导入。
 */
import request from "@/utils/request";
import type { PageQuery, PageResult } from "@/api/common/page";

export interface ImageUploadPageQuery extends PageQuery {
  imageGroup?: string;
  status?: string;
}

export interface ImageUploadVO {
  id: string;
  imageGroup?: string;
  status?: string;
  cloudPath?: string;
  log?: string;
  imageUrl?: string;
  createTime?: string;
}

export interface ImageUploadForm {
  id?: string;
  imageGroup?: string;
  cloudPath?: string;
  status?: string;
  log?: string;
  imageUrl?: string;
}

const IMAGE_UPLOAD_BASE_URL = "/image-uploads";

export const ImageUploadAPI = {
  getPage(params: ImageUploadPageQuery) {
    return request<any, PageResult<ImageUploadVO[]>>({
      url: `${IMAGE_UPLOAD_BASE_URL}/page`,
      method: "get",
      params,
    });
  },
  getFormData(id: string) {
    return request<any, ImageUploadForm>({
      url: `${IMAGE_UPLOAD_BASE_URL}/${id}/form`,
      method: "get",
    });
  },
  create(data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}`, method: "post", data });
  },
  update(id: string, data: ImageUploadForm) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}`, method: "put", data });
  },
  deleteByIds(ids: string) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${ids}`, method: "delete" });
  },
  sync(id: string) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/${id}/sync`, method: "post" });
  },
  batchSync(ids: string[]) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/batch_sync`, method: "post", data: { ids } });
  },
  getQueue() {
    return request<any, any[]>({ url: `${IMAGE_UPLOAD_BASE_URL}/queue`, method: "get" });
  },
  importCsv(file: File) {
    const formData = new FormData();
    formData.append("file", file);
    return request({
      url: `${IMAGE_UPLOAD_BASE_URL}/import_csv`,
      method: "post",
      data: formData,
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  batchCreate(data: ImageUploadForm[]) {
    return request({ url: `${IMAGE_UPLOAD_BASE_URL}/batch`, method: "post", data });
  },
};
