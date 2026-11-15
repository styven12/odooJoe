import uuid
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

def company_document_path(instance,filename):
 suffix=Path(filename).suffix.lower()
 return f'companies/{instance.company_id}/documents/{uuid.uuid4().hex}{suffix}'
def validate_size(file):
 if file.size>10*1024*1024:raise ValidationError('La taille maximale d’un fichier est de 10 Mo.')
class DocumentRecord(models.Model):
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='documents')
 title=models.CharField(max_length=180)
 category=models.CharField(max_length=80,blank=True)
 file=models.FileField(upload_to=company_document_path,validators=[FileExtensionValidator(['pdf','png','jpg','jpeg','docx','xlsx','txt']),validate_size])
 original_name=models.CharField(max_length=255)
 size_bytes=models.PositiveBigIntegerField()
 uploaded_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True)
 uploaded_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['-uploaded_at']
 def __str__(self):return self.title
