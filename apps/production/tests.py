from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from apps.crm.models import Opportunity,Partner
from apps.inventory.models import Product,StockMovement
from apps.sales.models import SalesOrder
from .models import BillOfMaterials,ManufacturingOrder,Shipment
class ProductionShippingTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='ops-admin',email='ops@example.test',password='test-password');self.company=Company.objects.create(name='Operations',code='OPSTEST');CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  for slug in ('manufacturing','shipping'):ERPModule.objects.create(slug=slug,name=slug,is_enabled=True)
  self.raw=Product.objects.create(company=self.company,sku='RAW',name='Matière');self.finished=Product.objects.create(company=self.company,sku='FIN',name='Produit fini');self.customer=Partner.objects.create(company=self.company,name='Client',partner_type=Partner.PartnerType.CUSTOMER);self.opportunity=Opportunity.objects.create(company=self.company,partner=self.customer,name='Commande client')
  self.order=SalesOrder.objects.create(company=self.company,customer=self.customer,opportunity=self.opportunity,amount=Decimal('1000'),state=SalesOrder.State.CONFIRMED)
  self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_manufacturing_consumes_components_and_adds_finished_stock(self):
  StockMovement.objects.create(company=self.company,product=self.raw,kind='IN',quantity=Decimal('10'),created_by=self.user)
  BillOfMaterials.objects.create(company=self.company,product=self.finished,component=self.raw,quantity=Decimal('2'))
  mo=ManufacturingOrder.objects.create(company=self.company,product=self.finished,quantity=Decimal('3'),created_by=self.user)
  self.client.post(reverse('production:mo_action',args=[mo.pk,'start']));self.client.post(reverse('production:mo_action',args=[mo.pk,'complete']))
  mo.refresh_from_db();self.assertEqual(mo.state,ManufacturingOrder.State.DONE);self.assertEqual(self.raw.on_hand,Decimal('4'));self.assertEqual(self.finished.on_hand,Decimal('3'))
 def test_shipping_deducts_stock_only_once_on_dispatch(self):
  StockMovement.objects.create(company=self.company,product=self.finished,kind='IN',quantity=Decimal('5'),created_by=self.user)
  response=self.client.post(reverse('production:shipments'),{'order':self.order.pk,'product':self.finished.pk,'quantity':'2','carrier':'Transport','tracking_reference':'REF-1'})
  self.assertEqual(response.status_code,302);shipment=Shipment.objects.get()
  self.client.post(reverse('production:shipment_action',args=[shipment.pk,'SHIPPED']))
  shipment.refresh_from_db();self.assertEqual(shipment.state,Shipment.State.SHIPPED);self.assertEqual(self.finished.on_hand,Decimal('3'))
