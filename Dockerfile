FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY diftar2energyid.py diftar2energyid.py
CMD [ "python", "diftar2energyid.py" ]
