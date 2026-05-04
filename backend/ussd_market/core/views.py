from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Price

@csrf_exempt
def ussd_handler(request):
    text = request.POST.get('text', '')

    if text == "":
        response = "CON Welcome to Market System\n"
        response += "1. View Prices\n"
        response += "2. Exit"

    elif text == "1":
        prices = Price.objects.all()[:5]

        response = "END Current Prices:\n"
        for p in prices:
            response += f"{p.crop.name} - {p.price} TZS\n"

    else:
        response = "END Invalid choice"

    return HttpResponse(response)