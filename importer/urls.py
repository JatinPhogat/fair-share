from django.urls import path
from .views import ImportUploadView, ImportSessionDetailView, ImportRowResolveView, ImportCommitView

urlpatterns = [
    path("upload/", ImportUploadView.as_view(), name="import-upload"),
    path("<int:pk>/", ImportSessionDetailView.as_view(), name="import-detail"),
    path("<int:session_pk>/rows/<int:row_pk>/", ImportRowResolveView.as_view(), name="import-row-resolve"),
    path("<int:pk>/commit/", ImportCommitView.as_view(), name="import-commit"),
]
