from django.conf import settings
def lab(request):
    return {"LAB": settings.LAB, "CERT": settings.CERT,  "CERT_FF": settings.CERT_FF, "HYDRO": settings.HYDRO, "VDF": settings.VDF}
