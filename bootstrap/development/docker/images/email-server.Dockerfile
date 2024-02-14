FROM coldfront-app-base

CMD ["python3", "-m", "smtpd", "-d", "-n", "-c", "DebuggingServer", "0.0.0.0:1025"]
