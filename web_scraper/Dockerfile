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

# Install the cron job
RUN crontab web_scraper/scrapy_cron

# Apply migrations, start cron and tail its log to keep the container running
CMD ["conda", "run", "--no-capture-output", "-n", "web_scraper", "bash", "/app/web_scraper/docker_start.sh"]
