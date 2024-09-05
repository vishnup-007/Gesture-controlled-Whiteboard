from django.db import models

# Create your models here.

class Presentation(models.Model):
    ppt_file = models.FileField(upload_to='presentations/')
