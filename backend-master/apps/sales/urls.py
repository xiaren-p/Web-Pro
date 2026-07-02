"""销售域 — URL 路由。

包含店铺选项、Listing、标签、图片上传等子模块。
"""

from django.urls import path

from apps.sales.views.shop_view import ShopOptionsViewSet
from apps.sales.listing.views.listing_view import SalesProductListingViewSet
from apps.sales.listing.views.listing_tag_view import ListingTagViewSet
from apps.sales.listing.views.image_view import ImageUploadViewSet

urlpatterns = [
    # 店铺下拉
    path("shops/options", ShopOptionsViewSet.as_view({"get": "shops"}), name="shops-options"),
    path("shops/owners", ShopOptionsViewSet.as_view({"get": "owners"}), name="shops-owners"),

    # Listing
    path("sales/product/listing", SalesProductListingViewSet.as_view({"get": "page"}), name="sales-listing-page"),
    path("sales/product/listing/labels/upsert", SalesProductListingViewSet.as_view({"post": "upsert_labels"}), name="sales-listing-upsert-labels"),
    path("sales/product/listing/assort/upsert", SalesProductListingViewSet.as_view({"post": "upsert_assort"}), name="sales-listing-upsert-assort"),
    path("sales/product/listing/remark/upsert", SalesProductListingViewSet.as_view({"post": "upsert_remark"}), name="sales-listing-upsert-remark"),

    # Listing 标签
    path("sales/listing/tags", ListingTagViewSet.as_view({"get": "list", "post": "create"}), name="listing-tags-list"),
    path("sales/listing/tags/batch-delete", ListingTagViewSet.as_view({"post": "batch_delete"}), name="listing-tags-batch-delete"),
    path("sales/listing/tags/type-options", ListingTagViewSet.as_view({"get": "type_options"}), name="listing-tags-type-options"),
    path("sales/listing/tags/options", ListingTagViewSet.as_view({"get": "tag_options"}), name="listing-tags-options"),
    path("sales/listing/tags/<int:pk>", ListingTagViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="listing-tags-detail"),
    path("sales/listing/tags/<int:pk>/status", ListingTagViewSet.as_view({"put": "update_status"}), name="listing-tags-status"),

    # 图片上传
    path("image-uploads/upload_image", ImageUploadViewSet.as_view({"post": "upload_image"}), name="image-upload"),
    path("image-uploads/page", ImageUploadViewSet.as_view({"get": "page"}), name="image-upload-page"),
    path("image-uploads/queue", ImageUploadViewSet.as_view({"get": "queue"}), name="image-upload-queue"),
    path("image-uploads/import_csv", ImageUploadViewSet.as_view({"post": "import_csv"}), name="image-upload-import"),
    path("image-uploads/batch_sync", ImageUploadViewSet.as_view({"post": "batch_sync"}), name="image-upload-batch-sync"),
    path("image-uploads/<int:pk>/form", ImageUploadViewSet.as_view({"get": "form"}), name="image-upload-form"),
    path("image-uploads/<int:pk>/sync", ImageUploadViewSet.as_view({"post": "sync"}), name="image-upload-sync"),
    path("image-uploads", ImageUploadViewSet.as_view({"post": "create"}), name="image-upload-create"),
    path("image-uploads/<int:pk>", ImageUploadViewSet.as_view({"put": "update", "delete": "delete_ids"}), name="image-upload-detail"),
]
