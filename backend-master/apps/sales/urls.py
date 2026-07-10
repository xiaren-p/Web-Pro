"""销售域 — URL 路由。

所有路径以 ``api/v1/`` 为前缀（由 ``backend_master/urls.py`` 的 include 提供）。

包含 Listing、标签、图片上传等子模块。
"""
from django.urls import path

from apps.sales.listing.views.listing_view import SalesProductListingViewSet
from apps.sales.listing.views.listing_tag_view import ListingTagViewSet
from apps.sales.listing.views.image_view import ImageUploadViewSet

urlpatterns = [
    # ── 商品 Listing ──
    path("sales/product/listing", SalesProductListingViewSet.as_view({"get": "page"}), name="sales-product-listing"),
    path("sales/product/listing/labels/upsert", SalesProductListingViewSet.as_view({"post": "upsert_labels"}), name="sales-product-listing-labels-upsert"),
    path("sales/product/listing/assort/upsert", SalesProductListingViewSet.as_view({"post": "upsert_assort"}), name="sales-product-listing-assort-upsert"),
    path("sales/product/listing/remark/upsert", SalesProductListingViewSet.as_view({"post": "upsert_remark"}), name="sales-product-listing-remark-upsert"),

    # ── Listing 标签 ──
    path("sales/listing/tags", ListingTagViewSet.as_view({"get": "list", "post": "create"}), name="sales-listing-tags"),
    path("sales/listing/tags/batch-delete", ListingTagViewSet.as_view({"post": "batch_delete"}), name="sales-listing-tags-batch-delete"),
    path("sales/listing/tags/type-options", ListingTagViewSet.as_view({"get": "type_options"}), name="sales-listing-tags-type-options"),
    path("sales/listing/tags/options", ListingTagViewSet.as_view({"get": "tag_options"}), name="sales-listing-tags-options"),
    path("sales/listing/tags/<str:pk>", ListingTagViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}), name="sales-listing-tags-detail"),
    path("sales/listing/tags/<str:pk>/status", ListingTagViewSet.as_view({"put": "update_status"}), name="sales-listing-tags-status"),

    # ── 图片上传 ──
    path("image-uploads/upload_image", ImageUploadViewSet.as_view({"post": "upload_image"}), name="image-upload-upload-image"),
    path("image-uploads/page", ImageUploadViewSet.as_view({"get": "page"}), name="image-upload-page"),
    path("image-uploads/queue", ImageUploadViewSet.as_view({"get": "queue"}), name="image-upload-queue"),
    path("image-uploads/import_csv", ImageUploadViewSet.as_view({"post": "import_csv"}), name="image-upload-import-csv"),
    path("image-uploads/batch_sync", ImageUploadViewSet.as_view({"post": "batch_sync"}), name="image-upload-batch-sync"),
    path("image-uploads/<str:pk>/form", ImageUploadViewSet.as_view({"get": "form"}), name="image-upload-form"),
    path("image-uploads/<str:pk>/sync", ImageUploadViewSet.as_view({"post": "sync"}), name="image-upload-sync"),
    path("image-uploads", ImageUploadViewSet.as_view({"post": "create"}), name="image-upload-create"),
    path("image-uploads/<str:pk>", ImageUploadViewSet.as_view({"put": "update", "delete": "delete_ids"}), name="image-upload-update-delete"),
]
