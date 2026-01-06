from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from logic.mvp import (
    mvp_index,
    init_session,
    verify_age,
    update_profile,
    update_location,
    search_candidates,
    like_user,
    poll_status,
    confirm_match,
    cancel_match,
    block_user,
    report_user,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # MVP landing
    path("", mvp_index, name="mvp_index"),

    # MVP API
    path("api/mvp/init/", init_session, name="mvp_init"),
    path("api/mvp/age/", verify_age, name="mvp_age"),
    path("api/mvp/block/", block_user, name="mvp_block"),
    path("api/mvp/report/", report_user, name="mvp_report"),
    path("api/mvp/profile/", update_profile, name="mvp_profile"),
    path("api/mvp/location/", update_location, name="mvp_location"),
    path("api/mvp/search/", search_candidates, name="mvp_search"),
    path("api/mvp/like/", like_user, name="mvp_like"),
    path("api/mvp/poll/", poll_status, name="mvp_poll"),
    path("api/mvp/confirm/", confirm_match, name="mvp_confirm"),
    path("api/mvp/cancel/", cancel_match, name="mvp_cancel"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Static files are normally served by Django when DEBUG=True.
