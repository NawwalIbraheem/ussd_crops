from django.contrib import admin
from .models import Crop, CropType, Grade, Market, Price

admin.site.register(Crop)
admin.site.register(CropType)
admin.site.register(Grade)
admin.site.register(Market)
admin.site.register(Price)