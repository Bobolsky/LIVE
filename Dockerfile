FROM python:3.10
WORKDIR /livebotdiscord
COPY requirements.txt /bot/
RUN pip install -r requirements.txt
COPY . /livebotdiscord
CMD python app.py