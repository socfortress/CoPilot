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

# Copy your application into the Docker image
WORKDIR /opt/copilot/backend
COPY . .

# Expose ports
EXPOSE 5000

# Run your application
#CMD ["sh", "-c", "cd backend && python copilot.py"]
# List the current directory
#CMD ["ls", "-l"]
#CMD ["sh", "-c", "/opt/venv/bin/python copilot.py"]
CMD ["sh", "-c", "ls -la && /opt/venv/bin/python copilot.py"]
