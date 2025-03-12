FROM continuumio/miniconda3

# Install cron in the base system
RUN apt-get update && apt-get install -y cron

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY environment.yml pyproject.toml poetry.lock .

# Create the conda environment
RUN conda env create -f environment.yml && conda clean -afy

# Activate the conda environment
SHELL ["conda", "run", "-n", "web_scraper", "/bin/bash", "-c"]

# Install the dependencies
RUN poetry install --no-root

# Create the web_scraper directory and move files there
COPY scrapy.cfg ./
RUN mkdir -p web_scraper
COPY . web_scraper/

# Copy the cron file into the container's cron.d directory
COPY scrapy_cron /etc/cron.d/scrapy_cron

# Set correct permissions for the cron job file and add it to crontab
RUN chmod 0644 /etc/cron.d/scrapy_cron && crontab /etc/cron.d/scrapy_cron

# Create a log file for cron output
RUN mkdir -p logs_files && touch logs_files/cron.log

# Print startup message to logs
RUN echo "Container started"

# Start cron and tail the log to keep the container running
CMD conda run -n web_scraper bash -c "cron -f & tail -f /app/logs_files/cron.log"