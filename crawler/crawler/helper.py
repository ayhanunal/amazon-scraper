def missing_value_check(js):
    item_list = ["UPC", "Brand", "Model", "Price", "ProductName", "RetailerSKU", "RatingsNumber", 
    "RatingsAverage", "Availability", "Quantity", "ProductWeight", "ProductDimensions", "ScrapedDescription",
     "Offer", "DateFirstAvailable", "Warranty", "Vendor", "Images", "URL", "AmazonSalesRanking"]
    
    print("***********************MISSING-VALUE***************************")
    missing_count = 0
    for i in item_list:
        if i not in js:
            missing_count += 1
            print(f"**************** -> {i}")
    
    print(f"Missing Count : {missing_count}")
    print(f"Product Url : {js['URL']}")
    print("***************************************************************")