FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY environment.yml pyproject.toml poetry.lock .

# Create the conda environment
RUN conda env create -f environment.yml && conda clean -afy

# Activate the conda environment
SHELL ["conda", "run", "-n", "ai_bot_app", "/bin/bash", "-c"]

# Install the dependencies
RUN poetry install --no-root

# Create the ai_bot_app directory and move files there
RUN mkdir -p ai_bot_app

# Copy the rest of the application code into the container
COPY . ai_bot_app/

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["conda", "run", "-n", "ai_bot_app", "uvicorn", "ai_bot_app.main:app", "--host", "0.0.0.0", "--port", "8000"]