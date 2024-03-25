# build with `docker build -t python-backend -f Dockerfile.deb .`
# run with `docker run -p 5000:5000 -d python-backend`
# Start with the base Debian 11 image
# looking to split into 2 containers, one for the backend and one for the frontend
FROM debian:11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Update the package lists
RUN apt-get update

# Install necessary dependencies
RUN apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add the deadsnakes PPA
RUN echo "deb http://ppa.launchpad.net/deadsnakes/ppa/ubuntu focal main" | tee /etc/apt/sources.list.d/focal.list
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776

# Update the package lists
RUN apt-get update

# Install Python 3.11, pip and venv
RUN apt-get install -y python3.11 python3-pip python3.11-venv

# Create a Python virtual environment and activate it
RUN python3.11 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install setuptools
RUN /opt/venv/bin/pip install setuptools

# Install your application's dependencies
WORKDIR /opt/copilot/backend
COPY requirements.txt ./
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Install required browsers for playwright
RUN playwright install-deps
RUN playwright install

# Install wkhtmltopdf
RUN apt-get install -y wkhtmltopdf

# Copy your application into the Docker image
WORKDIR /opt/copilot/backend
COPY . .
# Create file-store folder
RUN mkdir file-store

# Expose ports
EXPOSE 5000

ENV SERVER_IP=0.0.0.0

# Connector Credentials
# ! SETTING UP YOUR CONNECTORS DEMOs https://www.youtube.com/@taylorwalton_socfortress/videos! #
ENV WAZUH_INDEXER_URL=https://1.1.1.1:9200
ENV WAZUH_INDEXER_USERNAME=admin
ENV WAZUH_INDEXER_PASSWORD=admin

ENV WAZUH_MANAGER_URL=https://1.1.1.1
ENV WAZUH_MANAGER_USERNAME=dummy
ENV WAZUH_MANAGER_PASSWORD=dummy

ENV GRAYLOG_URL=http://1.1.1.1
ENV GRAYLOG_USERNAME=dummy
ENV GRAYLOG_PASSWORD=dummy

ENV SHUFFLE_URL=https://1.1.1.1
ENV SHUFFLER_API_KEY=dummy

ENV DFIR_IRIS_URL=https://1.1.1.1
ENV DFIR_IRIS_API_KEY=dummy

ENV VELOCIRAPTOR_URL=https://1.1.1.1
ENV VELOCIRAPTOR_API_KEY_PATH=dummy

ENV SUBLIME_URL=http://1.1.1.1
ENV SUBLIME_API_KEY=dummy

ENV INFLUXDB_URL=http://1.1.1.1
ENV INFLUXDB_API_KEY=dummy
ENV INFLUXDB_ORG_AND_BUCKET=dummy,dummy

ENV ASKSOCFORTRESS_URL=https://knowledge.socfortress.co
ENV ASKSOCFORTRESS_API_KEY=dummy

ENV SOCFORTRESSTHREATINTEL_URL=https://intel.socfortress.co/search
ENV SOCFORTRESSTHREATINTEL_API_KEY=dummy

ENV CORTEX_URL=http://1.1.1.1
ENV CORTEX_API_KEY=dummy

ENV GRAFANA_URL=http://1.1.1.1
ENV GRAFANA_USERNAME=dummy
ENV GRAFANA_PASSWORD=dummy

ENV WAZUH_WORKER_PROVISIONING_URL=http://1.1.1.1

ENV EVENT_SHIPPER_URL=graylog_host
ENV GELF_INPUT_PORT=gelf_port

ENV ALERT_CREATION_PROVISIONING_URL=http://1.1.1.1

ARG CRYPTOLENS_AUTH
ENV CRYPTOLENS_AUTH=$CRYPTOLENS_AUTH

ARG RSA_PUBLIC_KEY
ENV RSA_PUBLIC_KEY=$RSA_PUBLIC_KEY

ARG PRODUCT_ID
ENV PRODUCT_ID=$PRODUCT_ID

# Run your application
CMD ["sh", "-c", "ls -la && /opt/venv/bin/python copilot.py"]
