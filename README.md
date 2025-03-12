# GenAI ALBUS
A comprehensive real estate platform featuring a robust web scraping system built with Scrapy and an intelligent chatbot assistant. The scraper runs in a Docker container with scheduled tasks via cron, while the chatbot leverages advanced AI to help users find and learn about properties.

## Project structure
Web Scraper - A Scrapy-based scraper for collecting real estate listings from compraensanjuan.com
AI Bot API - A FastAPI application providing an AI assistant to help users find properties and get information about the properties

## Features
- Containerized web scraping solution using Scrapy and Docker
- Automated scheduling with cron jobs
- AI-powered chatbot assistant for property search and information
- Retrieval augmented generation (RAG) for property information
- FastAPI backend for efficient API responses
- Comprehensive logging system with rotation and multiple handlers
- Conda environment and Poetry for dependency isolation and Python package management

## Environment Variables
- OPENAI_API_KEY: The API key for the OpenAI API
- CRON_SCHEDULE: The cron schedule for the web scraper

## Quick Start
1. **Run Docker Compose:**
   ```bash
   docker-compose up -d
   ```

2. **Api Docs**
   Go to http://localhost:8000/docs to interact with the API

3. **Application logs**
   You can find the logs in the logs_files folder. We have:
   * web_scraper.log for the web scraper
   * cron.log for the cron job
   * ai_bot_app.log for the ai bot app

4. **To stop the containers:**
   ```bash
   docker-compose down
   ```

## Key Components

- **Docker Configuration**: Utilizes `continuumio/miniconda3` as base image
- **Logging System**: Implements both console and file logging with rotation
- **Scheduling**: Cron-based task scheduling for automated scraping
- **Environment Management**: Combined use of Conda and Poetry

## Prerequisites

- Docker

## How the project works

**Web Scraper:**
   1. Scrapes real estate listings from the website 
   2. Create the embeddings of the data and stores them with the metadata in Elasticsearch
   3. Logs data to a file
   4. Schedules scraping tasks with cron (every hour at 0 minutes)

**AI Bot API:**
   1. Provides an AI assistant to help users find properties and get information about the properties
   2. Uses Elasticsearch for property information retrieval
   3. Logs data to a file
   4. Schedules scraping tasks with cron
   5. Swagger API documentation to interact with the API
