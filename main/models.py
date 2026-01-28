from django.db import models


class Reading(models.Model):
    timestamp = models.DateTimeField(primary_key=True)
    temperature = models.FloatField()
    humidity = models.FloatField()

    class Meta:
        db_table = "readings"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp}: {self.temperature}°C, {self.humidity}%"