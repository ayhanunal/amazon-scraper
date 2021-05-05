from __future__ import absolute_import
from scrapy.spiders import Spider
from scrapy import Request, FormRequest
import json
import csv
import jsonlines
import random
import pandas as pd
import os
from datetime import datetime, timedelta
import sys
import re
import logging
import time
import traceback
from collections import OrderedDict
from w3lib.html import remove_tags
from lxml import html as lxhtml
from crawler.helper import missing_value_check


class My_Spider(Spider):
    handle_httpstatus_list = [404] 
    name = "amazon"
    #download_timeout = 30
    
    custom_settings = {
        "HTTPCACHE_ENABLED": False,
        "LOG_LEVEL":"INFO",
        "CONCURRENT_REQUESTS": 3,  
        "RETRY_TIMES": 3,           
        "DOWNLOAD_DELAY": 5,
        "RETRY_HTTP_CODES": [500, 503, 504, 400, 401, 403, 405, 407, 408, 416, 456, 502, 429, 307]
    }
    referrer = 'https://www.amazon.com/international-shipping-computers/b?ie=UTF8&node=16225007011'

    asin_array = []
    barcode_array = []
    def start_requests(self):
        processed = []
        data = []
        if os.path.exists('amazon.jl'):
            with jsonlines.open('amazon.jl') as reader:
                for obj in reader:
                    data.append(obj)
                    processed.append(obj['Id'])
        
        with open('input/products.csv','r') as file:
            reader = csv.reader(file)
            for row in reader:
                if row[2].strip() != "":
                    asin = row[2].strip()
                    if asin not in processed:
                        self.asin_array.append(asin)
                elif row[1].strip() != "":
                    barcode = row[1].strip()
                    if len(barcode) < 12 and barcode.isnumeric():
                        count = 12 - len(barcode)
                        added = ""
                        for i in range(count):
                            added += "0"
                        barcode = added + barcode
                    if barcode not in processed:
                        self.barcode_array.append(barcode)
                        
        random.shuffle(self.asin_array)
        random.shuffle(self.barcode_array)
                        
        for asin_index in range(0, len(self.asin_array)):  
            yield Request(
                self.referrer,
                dont_filter=True,
                callback=self.get_dp_page, meta={'asin_index': asin_index,'refresh_cache': True}
            )
        
        for barcode_index in range(0, len(self.barcode_array)):  
            yield Request(
                self.referrer,
                dont_filter=True,
                callback=self.get_search_page, meta={'barcode_index': barcode_index,'refresh_cache': True}
            )
            
        if len(self.asin_array) == 0 and len(self.barcode_array) == 0:
            df = pd.json_normalize(data)
            df.to_excel("amazon.xlsx", sheet_name='amazon') 
        
    def get_dp_page(self, response):
        asin_index = response.meta.get("asin_index", 0)
        retry = response.meta.get("retry", False)
        yield Request(
            f"https://www.amazon.com/dp/{self.asin_array[asin_index]}",
            callback=self.detail_page,
            #headers={'referrer': self.referrer},
            meta={"asin_index": asin_index, 'refresh_cache': retry, "request_info":"asin"},
        )
    
    def get_search_page(self, response):
        barcode_index = response.meta.get("barcode_index", 0)
        retry = response.meta.get("retry", False)
        yield Request(
            f"https://www.amazon.com/s?k={self.barcode_array[barcode_index]}&ref=nb_sb_noss",
            callback=self.listing_page,
            #headers={'referrer': self.referrer},
            meta={"barcode_index": barcode_index, 'refresh_cache': retry},
        )
    
    def listing_page(self, response):
        found_products = response.xpath("//h2[contains(@class,'a-size-mini a-spacing-none')]")
        for i in range(0, len(found_products)):
            sponsored = found_products[i].xpath("./../div//span[@class='s-label-popover-default']").get()
            if sponsored:
                continue
            f_url = response.urljoin(found_products[i].xpath("./a/@href").get())
            yield Request(
                f_url,
                callback=self.detail_page,
                meta={"barcode_index":response.meta["barcode_index"], 
                "request_info":"barcode",
                "found_order":i+1,
                'refresh_cache':response.meta["refresh_cache"]},
            )

    def detail_page(self, response):

        js = response.meta.get("js",{})
        sku = ""

        request_info = response.meta["request_info"]
        if request_info == "asin":
            asin_index = response.meta.get("asin_index")
            sku = self.asin_array[asin_index]
            js['Id'] = sku
            js["CheckColumn"] = "ASIN Code"
            js['URL'] = response.url
        elif request_info == "barcode":
            barcode_index = response.meta.get("barcode_index")
            js['Id'] = self.barcode_array[barcode_index]
            js["CheckColumn"] = "Barcode Search - " + str(response.meta.get("found_order"))

            sku = response.url.split("dp/")[1].split("/")[0]
            js['URL'] = f"https://www.amazon.com/dp/{sku}/"


        is404 = True if "Not Found" in response.xpath("//head/title/text()").get() else False

        if not is404:

            #------product name
            product_name = response.xpath("normalize-space(//span[@id='productTitle']/text())").get()
            if product_name:
                js["ProductName"] = product_name
            else:
                product_name = response.xpath("//span[@id='btAsinTitle']/span/text()").get()
                if product_name:
                    js["ProductName"] = product_name
            
            #------availability ??????????????
            availability = response.xpath("normalize-space(//div[@id='availability']/span/text())").get()
            if availability:
                js["Availability"] = availability
            else:
                availability = response.xpath("//div[@id='availability_feature_div']//text()[contains(.,'Available')]").get()
                if availability:
                    js["Availability"] = "In Stock"
                else:
                    js["Availability"] = "Out of Stock"

            #------product_weigth
            product_weigth = "".join(response.xpath("//th[contains(.,'Weight')]/following-sibling::*/text()").getall())
            if product_weigth:
                js["ProductWeight"] = product_weigth.strip()
            else:
                product_weigth = "".join(response.xpath("//td[contains(.,'Weight')]/following-sibling::*/p/text()").getall())
                if product_weigth:
                    js["ProductWeight"] = product_weigth.strip()

            #------product_dimensions
            product_dimensions = "".join(response.xpath("//th[contains(.,'Product Dimensions')]/following-sibling::*/text()").getall())
            if product_dimensions:
                js["ProductDimensions"] = product_dimensions.split("(")[0].strip()
            else:
                product_dimensions = response.xpath("//td[contains(.,'Product Dimensions') or contains(.,'Size')]/following-sibling::*/p/text()").get()
                if product_dimensions and "x" in product_dimensions.lower():
                    js["ProductDimensions"] = product_dimensions.split("(")[0].strip()
                else:
                    product_dimensions = response.xpath("//li/span[contains(.,'Dimensions')]//span[contains(text(),'x')]/text()").get()
                    if product_dimensions:
                        js["ProductDimensions"] = product_dimensions.split("(")[0].strip()

            #------price
            price = response.xpath("//div[@id='cerberus-data-metrics']/@data-asin-price").get()
            if price:
                js["Price"] = price
            else:
                price = response.xpath("normalize-space(//span[@id='price_inside_buybox']/text())").get()
                if price:
                    js["Price"] = price
                else:
                    price = response.xpath("normalize-space(//span[@id='priceblock_ourprice']/text())").get()
                    if price:
                        js["Price"] = price
            
            #------brand
            brand = "".join(response.xpath("//td[./span[.='Brand']]/following-sibling::*//text()").getall())
            if brand:
                js["Brand"] = brand
            else:
                brand = response.xpath("//a[@id='bylineInfo'][contains(.,'Brand')]/text()").get()
                if brand:
                    js["Brand"] = brand.split(":")[1].strip()
                else:
                    brand = response.xpath("//div[@id='bylineInfo_feature_div']/div/a/text()").get()
                    if brand:
                        js["Brand"] = brand.replace("Visit","").replace("the","").replace("Store","").strip()
            
            #------model
            model = "".join(response.xpath("//th[contains(.,'model number')]/following-sibling::*/text()").getall())
            if model:
                js["Model"] = model.strip()
            else:
                model = response.xpath("//text()[contains(.,'model number')]/../following-sibling::*/text()").get()
                if model:
                    js["Model"] = model.strip()
            
            #Vendor
            vendor = response.xpath("//div[@id='mbc-action-panel-wrapper']//span[contains(text(),'Sold') or contains(text(),'sold')]/following-sibling::span/text()").get()
            if vendor:
                js["Vendor"] = vendor.replace("✅", "").strip()
            else:
                vendor = response.xpath("//td[contains(.,'Sold')]/following-sibling::*//span[contains(@class,'a-truncate-full')]//text()").get()
                if vendor:
                    js["Vendor"] = vendor.replace("✅", "").strip()

            
            #--------description
            desc = "".join(response.xpath("//div[@id='productDescription']/p/text()").getall())
            if desc:
                js["ScrapedDescription"] = desc.strip()
            else:
                desc = "".join(response.xpath("//div[@id='feature-bullets']/ul/li//text()").getall())
                if desc:
                    js["ScrapedDescription"] = desc.strip()
        
            #--------ratings_number
            ratings_number = response.xpath("//span[@id='acrCustomerReviewText']/text()").get()
            if ratings_number:
                js["RatingsNumber"] = ratings_number.split(" ")[0].strip()
            
            #--------ratings_average
            ratings_average = response.xpath("//span[contains(@class,'reviewCountTextLinkedHistogram')]/@title").get()
            if ratings_average and "out" in ratings_average.lower():
                js["RatingsAverage"] = ratings_average.split("out")[0].strip()
            else:
                ratings_average = "".join(response.xpath("//th[.='Customer Reviews']/following-sibling::*/text()").getall())
                if ratings_average:
                    js["RatingsAverage"] = ratings_average.split("out")[0].strip()
                else:
                    ratings_average = response.xpath("//span[@data-hook='rating-out-of-text']/text()").get()
                    if ratings_average:
                        js["RatingsAverage"] = ratings_average.split("out")[0].strip()
                
            #--------amazon_sales_ranking
            amazon_sales_ranking = "".join(response.xpath("//th[contains(.,'Sellers Rank')]/following-sibling::*/span/span//text()[not(contains(.,'See'))]").getall())
            if amazon_sales_ranking:
                ranking_list = amazon_sales_ranking.replace("(","").replace(")","").split("#")
                amazon_sales_ranking = " #".join(x.strip() for x in ranking_list).strip()
                js["AmazonSalesRanking"] = amazon_sales_ranking
            else:
                amazon_sales_ranking = "".join(response.xpath("//text()[contains(.,'Sellers Rank')]/../..//text()").getall())
                if amazon_sales_ranking:
                    ranking_list = amazon_sales_ranking.replace("(","").replace(")","").split("#")
                    amazon_sales_ranking = " #".join(x.strip() for x in ranking_list).strip()
                    amazon_sales_ranking = amazon_sales_ranking.replace("See Top 100 in", "").replace("Best Sellers Rank:","").strip()
                    js["AmazonSalesRanking"] = amazon_sales_ranking
            

            #--------Images
            images = response.xpath("//div[@class='imgTagWrapper']/img/@data-old-hires").get()
            if images:
                js["Images"] = images
            else:
                images = response.xpath("//div[@class='imgTagWrapper']/img/@src").get()
                if images and ("base64" not in images or len(images) < 150):
                    js["Images"] = images

            #--------date_first
            date_first = "".join(response.xpath("//th[contains(.,'Date First Available')]/following-sibling::*/text()").getall())
            if date_first:
                datetime_object = datetime.strptime(date_first.replace("\n",""), '%B %d, %Y')
                newformat = datetime_object.strftime('%m-%d-%Y')
                js["DateFirstAvailable"] = newformat
            else:
                date_first = "".join(response.xpath("//h2[.='Product details']/..//text()[contains(.,'Date First')]/../following-sibling::*/text()").getall())
                if date_first:
                    datetime_object = datetime.strptime(date_first.replace("\n",""), '%B %d, %Y')
                    newformat = datetime_object.strftime('%m-%d-%Y')
                    js["DateFirstAvailable"] = newformat
            
            #--------sku
            if sku:
                js["RetailerSKU"] = sku
            else:
                sku = response.xpath("//th[contains(.,'ASIN')]/following-sibling::*/text()").get()
                if sku:
                    js["RetailerSKU"] = sku
                else:
                    sku = "".join(response.xpath("//h2[.='Product details']/..//text()[contains(.,'ASIN')]/../following-sibling::*/text()").getall())
                    if sku:
                        js["RetailerSKU"] = sku

            #--------quantity
            quantity = response.xpath("//select[@name='quantity']/option[last()]/@value").get()
            if quantity:
                js["Quantity"] = quantity.strip()
            
            #warranty
            warranty = "".join(response.xpath("//td[contains(.,'Warranty')]/following-sibling::*/p//text()").getall())
            if warranty:
                js["Warranty"] = warranty.strip()

            #--------item check---------
            title_check = "".join(response.xpath("//div[@id='comparison_title']//text()").getall())
            if title_check and product_name in title_check:
                warranty = "".join(response.xpath("//tr[contains(.,'Warranty')]/td[not(contains(@class,'-title'))][1]//text()").getall())
                if warranty:
                    js["Warranty"] = warranty.replace("Warranty and service","").replace("Warranty","").replace("service","").strip()
                if "Price" not in js:
                    price = "".join(response.xpath("//tr[contains(.,'Price')]/td[not(contains(@class,'-title'))][1]//text()").getall())
                    if price:
                        price = price.replace("From","").replace(":","").replace("$","").strip()
                        if price and price.isnumeric():
                            js["Price"] = price
                if "ProductWeight" not in js:
                    product_weigth = "".join(response.xpath("//tr[contains(.,'Weight')]/td[not(contains(@class,'-title'))][1]//text()").getall())
                    if product_weigth:
                        js["ProductWeight"] = product_weigth.replace("Weight","").replace("Item","").strip()
                if "ProductDimensions" not in js:
                    product_dimensions = "".join(response.xpath("//tr[contains(.,'Dimensions')]/td[not(contains(@class,'-title'))][1]//text()").getall())
                    if product_dimensions:
                        product_dimensions = product_dimensions.replace("Item","").replace("Dimensions","").replace("LxWxH","").strip()
                        if product_dimensions:
                            js["ProductDimensions"] = product_dimensions.strip()
                if "RatingsNumber" not in js:
                    ratings_number = "".join(response.xpath("//tr[contains(.,'Rating')]/td[not(contains(@class,'-title'))][1]//text()[contains(.,'(')]").getall())
                    if ratings_number:
                        js["RatingsNumber"] = ratings_number.replace("(","").replace(")","").strip()
                if "RatingsAverage" not in js:
                    ratings_average = "".join(response.xpath("//tr[contains(.,'Rating')]/td[not(contains(@class,'-title'))][1]//text()[contains(.,'out')]").getall())
                    if ratings_average:
                        js["RatingsAverage"] = ratings_average.split("out")[0].strip()
            

        else:
            #js["Active Status"] = "404 Not Fount"
            return
        
                    
        with jsonlines.open('amazon.jl', mode='a') as writer: writer.write(js)
        del js["Id"]
        del js["CheckColumn"]
        # missing_value_check(js)
        yield js
