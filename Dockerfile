FROM python:latest

WORKDIR /app
COPY api.py .
COPY requirement.txt .
RUN pip3 install -r requirement.txt
COPY . .
EXPOSE 8080
CMD ["python", "api.py"]