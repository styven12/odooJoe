from django.conf import settings
from django.db import models
class Asset(models.Model):
 class State(models.TextChoices): ACTIVE='ACTIVE','En service'; REPAIR='REPAIR','En maintenance'; RETIRED='RETIRED','Retiré'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='assets')
 reference=models.CharField(max_length=40)
 name=models.CharField(max_length=180)
 category=models.CharField(max_length=100,blank=True)
 serial_number=models.CharField(max_length=100,blank=True)
 location=models.CharField(max_length=160,blank=True)
 purchased_on=models.DateField(null=True,blank=True)
 state=models.CharField(max_length=10,choices=State.choices,default=State.ACTIVE)
 class Meta:
  ordering=['name']
  constraints=[models.UniqueConstraint(fields=['company','reference'],name='service_asset_company_ref_unique')]
 def __str__(self):return f'{self.reference} · {self.name}'
class MaintenanceRequest(models.Model):
 class Priority(models.TextChoices): LOW='LOW','Basse'; NORMAL='NORMAL','Normale'; HIGH='HIGH','Haute'; URGENT='URGENT','Urgente'
 class State(models.TextChoices): OPEN='OPEN','Ouverte'; PLANNED='PLANNED','Planifiée'; IN_PROGRESS='IN_PROGRESS','En cours'; DONE='DONE','Terminée'; CANCELLED='CANCELLED','Annulée'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='maintenance_requests')
 asset=models.ForeignKey(Asset,on_delete=models.PROTECT,related_name='maintenance_requests')
 title=models.CharField(max_length=180)
 description=models.TextField(blank=True)
 priority=models.CharField(max_length=8,choices=Priority.choices,default=Priority.NORMAL)
 state=models.CharField(max_length=12,choices=State.choices,default=State.OPEN)
 scheduled_for=models.DateField(null=True,blank=True)
 assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='maintenance_assignments')
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='maintenance_created')
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:ordering=['state','-priority','scheduled_for']
class HelpdeskTicket(models.Model):
 class Priority(models.TextChoices): LOW='LOW','Basse'; NORMAL='NORMAL','Normale'; HIGH='HIGH','Haute'; URGENT='URGENT','Urgente'
 class State(models.TextChoices): NEW='NEW','Nouveau'; OPEN='OPEN','Ouvert'; WAITING='WAITING','En attente'; RESOLVED='RESOLVED','Résolu'; CLOSED='CLOSED','Fermé'
 company=models.ForeignKey('companies.Company',on_delete=models.PROTECT,related_name='support_tickets')
 number=models.CharField(max_length=24,unique=True,null=True,blank=True)
 title=models.CharField(max_length=180)
 description=models.TextField()
 partner=models.ForeignKey('crm.Partner',on_delete=models.SET_NULL,null=True,blank=True,related_name='support_tickets')
 priority=models.CharField(max_length=8,choices=Priority.choices,default=Priority.NORMAL)
 state=models.CharField(max_length=10,choices=State.choices,default=State.NEW)
 assigned_to=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,blank=True,related_name='support_assignments')
 created_by=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.SET_NULL,null=True,related_name='support_created')
 created_at=models.DateTimeField(auto_now_add=True)
 updated_at=models.DateTimeField(auto_now=True)
 class Meta:ordering=['state','-created_at']
 def save(self,*args,**kwargs):
  creating=self.pk is None;super().save(*args,**kwargs)
  if creating and not self.number:
   self.number=f'TKT-{self.company_id}-{self.pk:06d}';type(self).objects.filter(pk=self.pk).update(number=self.number)
