from django.db import models

class Crop(models.Model):
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class Market(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Price(models.Model):
    crop = models.ForeignKey(Crop, on_delete=models.CASCADE)
    market = models.ForeignKey(Market, on_delete=models.CASCADE)
    price = models.FloatField()
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.crop} - {self.market} - {self.price}"