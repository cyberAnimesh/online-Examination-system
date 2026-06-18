from django.db import models
import uuid
# Create your models here.


class BaseModel(models.Model):
    uid = models.UUIDField(unique=True, editable=False, default=uuid.uuid4,primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(BaseModel):
    name = models.CharField(max_length=255)
    class Meta:
        verbose_name_plural = "Categories"
    def __str__(self):
        return self.name