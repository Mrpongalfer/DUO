FROM python:3.10-slim
WORKDIR /lcsaf
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV LCSAF_JWT_SECRET=changeme
ENV LCSAF_ARCHITECT_PASS=architectpass
USER nobody
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
