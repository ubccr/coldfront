from django.db.models import Q

from coldfront.core.allocation.models import (AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.resource.models import Resource

from django.shortcuts import render
from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from django.views import View
from xhtml2pdf import pisa



def set_allocation_user_status_to_error(allocation_user_pk):
    allocation_user_obj = AllocationUser.objects.get(pk=allocation_user_pk)
    error_status = AllocationUserStatusChoice.objects.get(name='Error')
    allocation_user_obj.status = error_status
    allocation_user_obj.save()


def generate_guauge_data_from_usage(name, value, usage):

    label = "%s: %.2f of %.2f" % (name, usage, value)

    try:
        percent = (usage/value)*100
    except ZeroDivisionError:
        percent = 100
    except ValueError:
        percent = 100

    if percent < 80:
        color = "#6da04b"
    elif percent >= 80 and percent < 90:
        color = "#ffc72c"
    else:
        color = "#e56a54"

    usage_data = {
        "columns": [
            [label, percent],
        ],
        "type": 'gauge',
        "colors": {
            label: color
        }
    }

    return usage_data


def get_user_resources(user_obj):

    if user_obj.is_superuser:
        resources = Resource.objects.filter(is_allocatable=True)
    else:
        resources = Resource.objects.filter(
            Q(is_allocatable=True) &
            Q(is_available=True) &
            (Q(is_public=True) | Q(allowed_groups__in=user_obj.groups.all()) | Q(allowed_users__in=[user_obj,]))
        ).distinct()

    return resources


def test_allocation_function(allocation_pk):
    print('test_allocation_function', allocation_pk)




# def render_to_pdf(template_src, context_dict={}):
# 	template = get_template(template_src)
# 	html  = template.render(context_dict)
# 	result = BytesIO()
# 	pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
# 	if not pdf.err:
# 		return HttpResponse(result.getvalue(), content_type='application/pdf')
# 	return None


# data = {
# 	"company": "FAS Research Computing",
# 	"address": "38 Oxford St",
# 	"city": "Cambridge",
# 	"state": "MA",
# 	"zipcode": "02138",


# 	"phone": "617-871-9977",
# 	"email": "test@harvard.edu",
# 	"website": "www.rc.fas.harvard.edu",
# 	}

# #Opens up page as PDF
# class ViewPDF(View):
# 	def get(self, request, *args, **kwargs):

# 		pdf = render_to_pdf('app/pdf_template.html', data)
# 		return HttpResponse(pdf, content_type='application/pdf')


# #Automaticly downloads to PDF file
# class DownloadPDF(View):
# 	def get(self, request, *args, **kwargs):
		
# 		pdf = render_to_pdf('app/pdf_template.html', data)

# 		response = HttpResponse(pdf, content_type='application/pdf')
# 		filename = "Invoice_%s.pdf" %("12341231")
# 		content = "attachment; filename='%s'" %(filename)
# 		response['Content-Disposition'] = content
# 		return response



# def index(request):
# 	context = {}
# 	return render(request, 'app/index.html', context)
