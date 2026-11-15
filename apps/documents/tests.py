import tempfile
from pathlib import Path
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase,override_settings
from django.urls import reverse
from apps.companies.models import Company,CompanyMembership
from apps.core.models import ERPModule
from .models import DocumentRecord
class DocumentLibraryTests(TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2]);self.addCleanup(self.tmp.cleanup);self.settings=override_settings(MEDIA_ROOT=self.tmp.name);self.settings.enable();self.addCleanup(self.settings.disable)
  self.user=get_user_model().objects.create_superuser(username='doc-admin',email='doc@example.test',password='test-password');self.company=Company.objects.create(name='Docs',code='DOCSTEST');CompanyMembership.objects.create(company=self.company,user=self.user,role=CompanyMembership.Role.OWNER);ERPModule.objects.create(slug='documents',name='Documents',is_enabled=True);self.client.force_login(self.user);session=self.client.session;session['active_company_id']=self.company.pk;session.save()
 def test_upload_and_download_company_document(self):
  upload=SimpleUploadedFile('guide.txt',b'Guide interne',content_type='text/plain')
  response=self.client.post(reverse('documents:library'),{'title':'Guide','category':'Procédures','file':upload})
  self.assertEqual(response.status_code,302);doc=DocumentRecord.objects.get(company=self.company);self.assertEqual(doc.original_name,'guide.txt')
  download=self.client.get(reverse('documents:download',args=[doc.pk]));self.assertEqual(download.status_code,200);self.assertEqual(b''.join(download.streaming_content),b'Guide interne')
 def test_another_company_cannot_download_document(self):
  other=Company.objects.create(name='Autre',code='OTHERDOC');upload=SimpleUploadedFile('private.txt',b'Private',content_type='text/plain');doc=DocumentRecord.objects.create(company=other,title='Private',file=upload,original_name='private.txt',size_bytes=7,uploaded_by=self.user)
  self.assertEqual(self.client.get(reverse('documents:download',args=[doc.pk])).status_code,404)
