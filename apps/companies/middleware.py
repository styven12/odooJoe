from .models import Company, CompanyMembership


class ActiveCompanyMiddleware:
    """Attach the current user's permitted company to each request."""

    session_key = "active_company_id"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.available_companies = Company.objects.none()
        request.company = None
        if request.user.is_authenticated:
            if request.user.is_superuser:
                companies = Company.objects.filter(is_active=True).order_by("name")
            else:
                companies = Company.objects.filter(
                    memberships__user=request.user,
                    memberships__is_active=True,
                    is_active=True,
                ).order_by("name")
            request.available_companies = companies
            selected_id = request.session.get(self.session_key)
            request.company = companies.filter(pk=selected_id).first() if selected_id else None
            if request.company is None:
                request.company = companies.first()
                if request.company:
                    request.session[self.session_key] = request.company.pk
        return self.get_response(request)
