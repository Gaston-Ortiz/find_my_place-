# Third party imports
from unittest.mock import patch

import pytest
import scrapy

# Local imports
from web_scraper.spiders.house_spider import HouseSpider


@pytest.fixture
def spider():
    return HouseSpider()


def test_spider_attributes(spider):
    """Test basic spider attributes"""
    assert spider.name == "house_spider"
    assert "compraensanjuan.com" in spider.allowed_domains
    assert len(spider.start_urls) == 1
    assert "compraensanjuan.com" in spider.start_urls[0]


@pytest.fixture
def mock_response():
    """Create a mock response with sample house listings"""
    with open("tests/fixtures/sample_listing_page.html", "r", encoding="utf-8") as f:
        body = f.read()

    url = "https://www.compraensanjuan.com/b.php?cat=100&orden=0&pagina=1"
    request = scrapy.http.Request(url=url)
    return scrapy.http.HtmlResponse(
        url=url, body=body, encoding="utf-8", request=request
    )


@pytest.fixture
def mock_detail_response():
    """Create a mock response with a sample house detail page"""
    with open("tests/fixtures/sample_detail_page.html", "r", encoding="utf-8") as f:
        body = f.read()

    url = "https://www.compraensanjuan.com/aviso_12345.html"
    request = scrapy.http.Request(url=url)
    return scrapy.http.HtmlResponse(
        url=url, body=body, encoding="utf-8", request=request
    )


@patch("web_scraper.log.logger")
def test_parse_method(mock_logger, spider, mock_response):
    """Test the spider's parse method for listing pages"""
    results = list(spider.parse(mock_response))

    # Verify that we extracted house links and followed them
    assert len(results) > 0
    assert all(isinstance(r, scrapy.http.Request) for r in results)
    assert mock_logger.info.called


@patch("web_scraper.log.logger")
def test_parse_product_details(mock_logger, spider, mock_detail_response):
    """Test the spider's parse_product_details method"""
    results = list(spider.parse_product_details(mock_detail_response))

    # Verify that we extracted the house data correctly
    assert len(results) == 1
    item = results[0]
    assert "name" in item
    assert "price" in item
    assert "description" in item
    assert "url" in item
    assert mock_logger.info.called
