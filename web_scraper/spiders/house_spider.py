import scrapy

# Local import
from web_scraper.dependencies import items
from web_scraper.log import logger

scraped_data = []


class HouseSpider(scrapy.Spider):
    """A spider for scraping house listings from compraensanjuan.com.

    This spider crawls through house listing pages on compraensanjuan.com, extracting details
    about properties including names, prices, descriptions and other metadata.

    Attributes:
        name (str): Identifier for this spider, used by Scrapy
        allowed_domains (list): List of domains this spider is restricted to
        start_urls (list): Initial URLs to begin crawling from
        total_pages_to_scrape (int): Maximum number of listing pages to crawl
        current_page (int): Counter for number of pages crawled so far
    """
    name = "house_spider"
    allowed_domains = ["compraensanjuan.com"]
    start_urls = ["https://www.compraensanjuan.com/b.php?cat=100&orden=0&pagina=1"]
    total_pages_to_scrape = 10
    current_page = 0

    def parse(self, response: scrapy.http.Response):
        """Extract product links from the listings page."""
        logger.info("Parsing the listings page")
        list_houses = response.css("p.aviso-title")

        logger.info(f"Found {len(list_houses)} houses in the listings page")

        for house in list_houses:
            house_link = house.css("a.title.orange-link").attrib["href"]
            if house_link:
                full_url = response.urljoin(house_link)  # Convert to absolute URL
                yield response.follow(full_url, callback=self.parse_product_details)

        next_page = response.css("a.orange-link.next").attrib["href"]

        # Iterate over the next pages
        if next_page is not None and self.current_page < self.total_pages_to_scrape:
            logger.info(f"Scraping the next page: {next_page}")
            self.current_page += 1
            next_page_url = response.urljoin(next_page)
            yield response.follow(next_page_url, callback=self.parse)

        logger.info(f"Scraped {self.current_page} pages")

    def parse_product_details(self, response):
        """Extract laptop details from individual product pages."""

        logger.info("Parsing the individual product details")
        description = response.css(
            "p.comentario-caracteristicas-anuncio::text"
        ).getall()

        item = {
            "name": response.css("h2[class*='anuncio-title']::text").get(),
            "price": response.css("h3.text-center.precio::text").get(),
            "description": " ".join(description),
            "url": response.url,
            "code_number": response.css("p.codigo.m-0 span::text").get(),
            "number_visit": response.css("p.visitas.m-0 span::text").get(),
            "publish_date": response.css("p.publicado.m-0 span::text").get(),
            "last_update": response.css("p.actualizado.m-0 span::text").get(),
        }

        # Select all <p> elements with the class 'name-caracteristica' inside any container div.
        p_elements = response.css("div.mx-auto p.name-caracteristica")
        for p in p_elements:
            # The label (e.g., "Superficie total:") is the text node before the <span>
            label = p.xpath("text()").get()
            if label:
                # Remove any trailing spaces or colon characters
                label = label.strip(" :")
            # The value is inside the <span class="caracteristica">
            value = p.css("span.caracteristica::text").get(default="")

            # add to items
            item[label] = value

        # Validate and convert the scraped data to the defined model
        item = items.HouseAdvertisement(**item)

        # # Append the scraped data to the global list
        # scraped_data.append(item.model_dump())
        yield item
