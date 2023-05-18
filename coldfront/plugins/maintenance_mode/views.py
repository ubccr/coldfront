from django.shortcuts import render


def maintenance(request):
    return render(request, 'maintenance_mode/maintenance.html')
