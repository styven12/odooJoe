from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from apps.crm.models import Partner
from apps.inventory.models import Product,StockMovement
from .models import RetailProduct,POSReceipt,POSSession,WebOrder
class RetailTests(TestCase):
 def setUp(self):
  self.user=get_user_model().objects.create_superuser(username='retail-admin',email='retail@example.test',password='test-password');self.company=Company.objects.create(name='Retail Test',code='RETAILTEST');CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER)
  for slug in ('pos','ecommerce'):ERPModule.objects.create(slug=slug,name=slug,is_enabled=True)
  self.product=Product.objects.create(company=self.company,sku='RETAIL-1',name='Produit test');RetailProduct.objects.create(company=self.company,product=self.product,price=Decimal('2000'),online=True);self.customer=Partner.objects.create(company=self.company,name='Client test',partner_type=Partner.PartnerType.CUSTOMER);StockMovement.objects.create(company=self.company,product=self.product,kind='IN',quantity=Decimal('10'),created_by=self.user)
  self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_pos_session_receipt_stock_and_cash_closing(self):
  self.client.post(reverse('retail:pos'),{'action':'open','opening_cash':'1000'});session=POSSession.objects.get(state=POSSession.State.OPEN)
  response=self.client.post(reverse('retail:pos'),{'action':'sale','product':self.product.pk,'quantity':'2','payment_method':'CASH','payment_reference':'','customer_name':''})
  self.assertEqual(response.status_code,302);self.assertEqual(POSReceipt.objects.get().total,Decimal('4000'));self.assertEqual(self.product.on_hand,Decimal('8'));self.assertEqual(session.expected_cash,Decimal('5000'))
  self.client.post(reverse('retail:pos'),{'action':'close','closing_cash':'5000'});session.refresh_from_db();self.assertEqual(session.state,POSSession.State.CLOSED);self.assertEqual(session.closing_cash,Decimal('5000'))
 def test_web_order_confirmation_deducts_stock_once(self):
  listing=RetailProduct.objects.get(product=self.product)
  response=self.client.post(reverse('retail:webshop'),{'action':'order','listing':listing.pk,'customer':self.customer.pk,'quantity':'3'})
  self.assertEqual(response.status_code,302);order=WebOrder.objects.get();self.assertEqual(order.total,Decimal('6000'))
  self.client.post(reverse('retail:confirm_web_order',args=[order.pk]));order.refresh_from_db();self.assertEqual(order.state,WebOrder.State.CONFIRMED);self.assertEqual(self.product.on_hand,Decimal('7'))
