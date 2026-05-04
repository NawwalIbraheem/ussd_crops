from django.contrib import admin
from .models import Crop, Market, Price

admin.site.register(Crop)
admin.site.register(Market)
admin.site.register(Price)