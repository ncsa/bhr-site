from django.http import HttpResponse
import csv
from cStringIO import StringIO
def respond_csv(lst, headers):
    f = StringIO()
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerows(lst)

    return HttpResponse(f.getvalue(), content_type="text/csv")

