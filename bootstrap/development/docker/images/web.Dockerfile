FROM coldfront-app-base

CMD ["python3", "manage.py", "runserver", "0.0.0.0:80"]
