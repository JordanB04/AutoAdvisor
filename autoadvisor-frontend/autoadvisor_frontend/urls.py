from django.urls import path, include

urlpatterns = [
    path('ui/', include('ui.urls')),
]
