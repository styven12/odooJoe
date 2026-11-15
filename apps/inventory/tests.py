from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from apps.crm.models import Partner
from .models import Product,StockMovement

class InventoryPurchasingFlowTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='stock-admin',email='stock@example.test',password='test-password')
  self.company=Company.objects.create(name='Stock Test',code='STOCKTEST')
  CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  ERPModule.objects.create(slug='inventory',name='Stocks',is_enabled=True)
  ERPModule.objects.create(slug='purchasing',name='Achats',is_enabled=True)
  self.product=Product.objects.create(company=self.company,sku='ITEM-1',name='Article test',unit='unité')
  self.supplier=Partner.objects.create(company=self.company,name='Fournisseur test',partner_type=Partner.PartnerType.SUPPLIER)
  self.client.force_login(self.user)
  session=self.client.session; session['active_company_id']=self.company.pk; session.save()
 def test_stock_receipt_and_issue_and_prevent_negative_balance(self):
  response=self.client.post(reverse('inventory:move_stock'),{'product':self.product.pk,'kind':'IN','quantity':'12','reference':'INITIAL'})
  self.assertEqual(response.status_code,302)
  self.assertEqual(self.product.on_hand,Decimal('12'))
  self.client.post(reverse('inventory:move_stock'),{'product':self.product.pk,'kind':'OUT','quantity':'13','reference':'OVERDRAW'})
  self.assertEqual(self.product.movements.count(),1)
  self.client.post(reverse('inventory:move_stock'),{'product':self.product.pk,'kind':'OUT','quantity':'5','reference':'DELIVERY'})
  self.assertEqual(self.product.on_hand,Decimal('7'))
 def test_purchase_receipt_adds_stock_once(self):
  response=self.client.post(reverse('purchasing:create_order'),{'supplier':self.supplier.pk,'product':self.product.pk,'quantity':'4','unit_cost':'2500','notes':''})
  self.assertEqual(response.status_code,302)
  from apps.purchasing.models import PurchaseOrder
  order=PurchaseOrder.objects.get(company=self.company)
  self.client.post(reverse('purchasing:action',args=[order.pk,'order']))
  self.client.post(reverse('purchasing:action',args=[order.pk,'receive']))
  self.client.post(reverse('purchasing:action',args=[order.pk,'receive']))
  order.refresh_from_db()
  self.assertEqual(order.status,PurchaseOrder.Status.RECEIVED)
  self.assertEqual(self.product.on_hand,Decimal('4'))
  self.assertEqual(self.product.movements.count(),1)
 def test_cross_company_product_is_not_visible_or_movable(self):
  other=Company.objects.create(name='Autre',code='OTHERSTOCK')
  foreign=Product.objects.create(company=other,sku='SECRET',name='Privé')
  self.client.post(reverse('inventory:move_stock'),{'product':foreign.pk,'kind':'IN','quantity':'1'})
  self.assertFalse(StockMovement.objects.filter(product=foreign).exists())
  self.assertNotContains(self.client.get(reverse('inventory:stock')),'SECRET')
