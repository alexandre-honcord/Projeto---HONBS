from django.urls import path
from honbs import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.base_view, name='base_view'),
    path('main/', views.main, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('ldap-login/', views.ldap_login, name='ldap_login'),
    path('home/', views.home, name='home_view'),
    path('resumo/', views.resumo, name='resume'),
    path('doador/', views.donator, name='donator'),
    path('doacoes/', views.donations, name='donations'),
    path('fracionamento/', views.fractionation, name='fractionation'),
    path('alertas/', views.alertas, name='alerts'),
    path('qualidade/', views.qualidade, name='quality'),
    path('transfusao/', views.transfusion, name='transfusion'),
    path('estoque/', views.stock, name='stock'),
    path('estoque-lista/', views.stock_list, name='stock_list'),
    path('captacao/', views.capture, name='capture'),
    path('dash/', views.dash, name='dash'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
