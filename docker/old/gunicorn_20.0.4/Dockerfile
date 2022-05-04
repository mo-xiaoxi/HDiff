FROM python:3.6

COPY res/main.py /
RUN pip install gunicorn==20.0.4
EXPOSE 8080

CMD ["gunicorn", "--worker-class", "gthread", "-b", "0.0.0.0:8080", "main:app"]

# req_path: /
