from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings
import os

from .models import Reading

def home(request):
    # sort filenames by time
    pictures = sorted(os.listdir(settings.SPIDER_PICTURES_DIR), reverse=True)

    if pictures:
        recent_picture = pictures[0]
        recent_picture_url = f"/pictures/{recent_picture}"
    else:
        recent_picture_url = None

    # get most recent rh and temperature from database
    recent_reading = Reading.objects.first()

    return render(request, "main.html", {
        "recent_rh": f"{recent_reading.humidity}%" if recent_reading else "None",
        "recent_temperature": f"{recent_reading.temperature}°C" if recent_reading else "None",
        "recent_picture": recent_picture_url
    })

