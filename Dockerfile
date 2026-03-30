FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      ca-certificates \
      curl \
      gnupg2 \
      fonts-liberation \
      libatk1.0-0 \
      libatk-bridge2.0-0 \
      libgtk-3-0 \
      libx11-xcb1 \
      libxcomposite1 \
      libxdamage1 \
      libxrandr2 \
      libgbm1 \
      libpango-1.0-0 \
      libpangocairo-1.0-0 \
      libxcb1 \
      libx11-6 \
      libxext6 \
      libxi6 \
      libnss3 \
      libxss1 \
      libasound2 \
      libappindicator3-1 \
      libcurl4 \
      cron && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
      > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*


ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/bin/chromium

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN printf "\
    @reboot    root   cd /app && /usr/local/bin/python main.py >> /proc/1/fd/1 2>&1\n\
    # run main.py every 4 hours, Mon–Fri\n\
    0 */4 * * 1-5 root cd /app && /usr/local/bin/python main.py >> /proc/1/fd/1 2>&1\n\
    " > /etc/cron.d/app-cron

RUN chmod 0644 /etc/cron.d/app-cron && \
    crontab /etc/cron.d/app-cron && \
    touch /var/log/cron.log

CMD ["cron", "-f"]