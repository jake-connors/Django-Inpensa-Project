from django.urls import path, re_path
from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$',views.login, name = 'login'),
    ##url(r'^login/$',views.log, name = 'login'),
    url(r'^register/$', views.register, name='register'),
    url(r'^forgot/$', views.forgot, name='forgot'),
    url(r'^dash/$', views.dash, name='dash'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^sets$', views.set_list, name = 'set_list'),
    url(r'^upload/$', views.upload_db, name='upload_db'),
    url(r'^test/$', views.test, name='test'),
    url(r'^view/$', views.view, name='view'),
    url(r'^predict/$', views.predict, name='predict'),
    url(r'^models/$', views.models, name='models'),
    url(r'^cmodel/$', views.cmodel, name='cmodel'),
    url(r'^delete_dataset/$', views.delete_dataset, name='delete_dataset'),
    url(r'^delete_model/$', views.delete_model, name='delete_models'),
    url(r'^add_data/$', views.add_data, name='add_data'),
    url(r'^edit_data/$', views.edit_data, name='edit_data'),
    url(r'^delete_data/$', views.delete_data, name='delete_data'),
    url(r'^edit/$', views.edit, name='edit'),
    url(r'^ajax/edit_single_data/$', views.edit_single_data),
    url(r'^ajax/edit_whole_data/$', views.edit_whole_data),
    url(r'^ajax/delete_row/$', views.delete_row),
    url(r'^ajax/get_data/$', views.get_data),
    url(r'^ajax/add_row/$', views.add_row),
    url(r'^ajax/data_list/$', views.dataList),

    
]
