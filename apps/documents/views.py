from pathlib import Path
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required,permission_required
from django.core.exceptions import ValidationError
from django.http import FileResponse,Http404
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_GET
from apps.core.models import ERPModule
from apps.core.guards import require_active_company
from .models import DocumentRecord
class DocumentForm(forms.ModelForm):
 class Meta:
  model=DocumentRecord;fields=('title','category','file')
  labels={'title':'Titre','category':'Catégorie','file':'Fichier'}
def enabled(request):
 if not ERPModule.objects.filter(slug='documents',is_enabled=True).exists():raise Http404('Module désactivé')
 # Sans société active : les GET affichent des listes vides ; les POST sont
 # redirigés avec un message par @require_active_company.
@login_required
@require_active_company
@permission_required('documents.view_documentrecord',raise_exception=True)
def library(request):
 enabled(request)
 if request.method=='POST':
  if not request.user.has_perm('documents.add_documentrecord'):raise Http404
  form=DocumentForm(request.POST,request.FILES)
  if form.is_valid():
   document=form.save(commit=False);document.company=request.company;document.uploaded_by=request.user;document.original_name=Path(document.file.name).name;document.size_bytes=document.file.size
   document.save();messages.success(request,'Document ajouté à la bibliothèque.');return redirect('documents:library')
 else:form=DocumentForm()
 return render(request,'documents/library.html',{'documents':DocumentRecord.objects.filter(company=request.company).select_related('uploaded_by'),'form':form})
@login_required
@require_GET
@permission_required('documents.view_documentrecord',raise_exception=True)
def download(request,document_id):
 enabled(request);document=get_object_or_404(DocumentRecord,pk=document_id,company=request.company)
 try:return FileResponse(document.file.open('rb'),as_attachment=True,filename=Path(document.original_name).name)
 except (FileNotFoundError,OSError,ValueError):
  # Le disque Render est éphémère : après un redéploiement, la fiche existe
  # encore mais le fichier a disparu. On renvoie un message clair au lieu
  # d'une page 404 brute, et l'utilisateur peut retéléverser le document.
  messages.error(request,'Le fichier n\'est plus disponible sur le stockage (disque éphémère après redéploiement). Vous pouvez retéléverser ce document depuis la bibliothèque.')
  return redirect('documents:library')
