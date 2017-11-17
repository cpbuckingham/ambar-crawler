FROM python:3.6
MAINTAINER Ambar "http://ambar.cloud"

# Set a timezone
ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD python ./crawler.py -name $AMBAR_CRAWLER_NAME -api_url $AMBAR_API_URL -api_token $AMBAR_API_TOKEN -rabbit_host $AMBAR_RABBIT_HOST

HEALTHCHECK --interval=5s --timeout=30s --retries=50 \
  CMD if (pidof -x python > /dev/null) then (exit 0) else (exit 1) fi