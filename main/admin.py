from django.contrib import admin
from main.models import dataset, data, model, prediction
# Register your models here.
admin.site.register(dataset)
admin.site.register(data)
admin.site.register(model)
admin.site.register(prediction)