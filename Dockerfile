FROM python:3.9-bullseye

# Install essential system dependencies + ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg \
      wget \
      curl \
      gnupg \
      libnss3 \
      libatk1.0-0 \
      libcups2 \
      libxcomposite1 \
      libxrandr2 \
      libxdamage1 \
      libxfixes3 \
      libxrender1 \
      libx11-xcb1 \
      libxcb1 \
      libdbus-1-3 \
      libxtst6 \
      libgtk-3-0 \
      libasound2 \
      libpangocairo-1.0-0 \
      libpango1.0-0 \
      libharfbuzz0b \
      libdrm2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (including playwright)
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers + dependencies
RUN playwright install --with-deps

# Copy app code
COPY . .

# Expose Flask port
EXPOSE 8080

# Entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
CMD ["/entrypoint.sh"]
