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
    path('relatorios/', views.reports, name='reports'),
    path('donator/<int:codigo>/', views.donator, name='donator'),
    path('doacoes/', views.donations, name='donations'),
    path('fracionamento/', views.fractionation, name='fractionation'),
    path('hemocomponentes/<int:codigo>/', views.prodHemocomponente, name='prodHemo'),
    path('lote/<int:sequencia>/', views.batch, name='batch'),
    path('alertas/', views.alertas, name='alerts'),
    path('qualidade/', views.qualidade, name='quality'),
    path('transfusao/', views.transfusion, name='transfusion'),
    path('infotransfusao/', views.infoTransfusion, name='infoTransfusion'),
    path('estoque/', views.stock, name='stock'),
    path('detalhe-estoque/', views.stock_list, name='stock_list'),
    path('captacao/', views.capture, name='capture'),
    path('dash/', views.dash, name='dash'),

    path('cadastros/', views.registrations, name='registrations'),
    path('edit-stock/<int:hemocomponente_id>/', views.edit_stock, name='edit_stock'),
    path('delete-stock/<int:hemocomponente_id>/', views.delete_stock, name='delete_stock'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
