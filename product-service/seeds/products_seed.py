import os
import sys
import django
import random
from decimal import Decimal

# Setup Django env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.catalog.infrastructure.models.category_model import CategoryModel
from modules.catalog.infrastructure.models.product_model import ProductModel

def get_realistic_data():
    return {
        "Book": {
            "desc": "Kho sách với đủ các thể loại từ Sci-fi, phát triển bản thân đến văn học kinh điển.",
            "items": [
                ("Sapiens", "Yuval Noah Harari", "Harper", 443),
                ("Dune", "Frank Herbert", "Chilton Books", 412),
                ("1984", "George Orwell", "Secker & Warburg", 328),
                ("Clean Code", "Robert C. Martin", "Prentice Hall", 464),
                ("The Great Gatsby", "F. Scott Fitzgerald", "Scribner", 218),
                ("Harry Potter", "J.K. Rowling", "Bloomsbury", 223),
                ("Lord of the Rings", "J.R.R. Tolkien", "Allen & Unwin", 1178),
                ("Atomic Habits", "James Clear", "Avery", 320),
                ("To Kill a Mockingbird", "Harper Lee", "J.B. Lippincott", 281),
                ("The Pragmatic Programmer", "Andrew Hunt", "Addison-Wesley", 352)
            ],
            "gen_attr": lambda i: {"author": i[1], "publisher": i[2], "isbn": f"{random.randint(1000000000, 9999999999)}", "language": random.choice(["English", "Vietnamese"]), "page_count": i[3], "format": random.choice(["Hardcover", "Paperback", "Kindle Edition"])}
        },
        "Laptop": {
            "desc": "Máy tính xách tay cấu hình cao đáp ứng mọi nhu cầu làm việc và giải trí.",
            "items": [
                ("MacBook Pro 16", "Apple", "16-core GPU, M2 Pro"),
                ("Dell XPS 13", "Dell", "Intel Iris Xe"),
                ("ThinkPad X1 Carbon", "Lenovo", "Intel UHD Graphics"),
                ("ASUS ROG Zephyrus", "ASUS", "RTX 3070 Ti"),
                ("MacBook Air M2", "Apple", "M2 Core GPU"),
                ("HP Spectre x360", "HP", "Intel Iris Xe"),
                ("Razer Blade 15", "Razer", "RTX 4080"),
                ("Lenovo Legion 5", "Lenovo", "RTX 3060"),
                ("Acer Swift 3", "Acer", "AMD Radeon"),
                ("Surface Laptop 5", "Microsoft", "Intel Iris Xe")
            ],
            "gen_attr": lambda i: {"brand": i[1], "cpu": random.choice(["Intel Core i5", "Intel Core i7", "Intel Core i9", "Apple M2", "AMD Ryzen 7"]), "ram": random.choice(["8GB", "16GB", "32GB"]), "storage": random.choice(["256GB SSD", "512GB SSD", "1TB SSD"]), "screen_size": random.choice(["13.3 inch", "14 inch", "15.6 inch", "16 inch", "17 inch"]), "gpu": i[2], "os": random.choice(["Windows 11", "macOS", "Ubuntu"]), "battery": f"{random.randint(40, 99)}Wh"}
        },
        "Mobile": {
            "desc": "Điện thoại thông minh đời mới nhất, pin trâu chụp hình sắc nét.",
            "items": [
                ("iPhone 15 Pro Max", "Apple"), ("Galaxy S24 Ultra", "Samsung"), ("Pixel 8 Pro", "Google"), 
                ("OnePlus 12", "OnePlus"), ("Xiaomi 14 Pro", "Xiaomi"), ("Xperia 1 V", "Sony"), 
                ("ROG Phone 8", "ASUS"), ("Nothing Phone (2)", "Nothing"), ("Motorola Edge+", "Motorola"), 
                ("Vivo X100 Pro", "Vivo")
            ],
            "gen_attr": lambda i: {"brand": i[1], "storage": random.choice(["128GB", "256GB", "512GB", "1TB"]), "ram": random.choice(["4GB", "8GB", "12GB", "16GB"]), "screen_size": f"{round(random.uniform(5.4, 6.8), 1)} inch", "battery_capacity": f"{random.randint(3000, 5000)}mAh", "camera": random.choice(["12MP", "48MP", "50MP", "200MP"])}
        },
        "Shoes": {
            "desc": "Giày dép thời trang thể thao êm ái, bền bỉ đến từ các thương hiệu hàng đầu.",
            "items": [
                ("Air Max 90", "Nike"), ("Ultraboost 22", "Adidas"), ("Puma Suede", "Puma"), 
                ("New Balance 574", "New Balance"), ("Vans Old Skool", "Vans"), ("Chuck Taylor", "Converse"), 
                ("Gel-Kayano 29", "Asics"), ("Reebok Classic", "Reebok"), ("Curry 10", "Under Armour"), 
                ("Speedcross 5", "Salomon")
            ],
            "gen_attr": lambda i: {"brand": i[1], "size": str(random.choice([38, 39, 40, 41, 42, 43, 44])), "color": random.choice(["Black", "White", "Red", "Blue", "Multi"]), "material": random.choice(["Leather", "Canvas", "Mesh", "Suede"]), "gender": random.choice(["Men", "Women", "Unisex"])}
        },
        "Fashion": {
            "desc": "Quần áo phong cách thiết kế hiện đại, định hình thời trang của bạn.",
            "items": [
                ("501 Original Jeans", "Levi's"), ("Bomber Jacket", "Zara"), ("Airism T-Shirt", "Uniqlo"), 
                ("Wool Blend Coat", "H&M"), ("GG Logo Hoodie", "Gucci"), ("Tech Fleece Set", "Nike"), 
                ("Modern Cotton Trunk", "Calvin Klein"), ("Classic Polo", "Tommy Hilfiger"), ("Oxford Shirt", "Ralph Lauren"), 
                ("Nuptse 1996", "The North Face")
            ],
            "gen_attr": lambda i: {"brand": i[1], "size": random.choice(["XS", "S", "M", "L", "XL", "XXL"]), "color": random.choice(["Navy", "Beige", "Black", "Grey", "Olive"]), "material": random.choice(["Cotton", "Polyester", "Wool", "Denim"]), "gender": random.choice(["Men", "Women", "Unisex"]), "care": "Machine wash cold"}
        },
        "Watch": {
            "desc": "Đồng hồ thông minh và cơ học, tôn lên vẻ thanh lịch và đẳng cấp.",
            "items": [
                ("Submariner", "Rolex"), ("Apple Watch Series 9", "Apple"), ("Galaxy Watch 6", "Samsung"), 
                ("Fenix 7X", "Garmin"), ("G-Shock DW5600", "Casio"), ("Alpinist SARB017", "Seiko"), 
                ("Speedmaster Moonwatch", "Omega"), ("Carrera Chronograph", "Tag Heuer"), ("PRX Powermatic", "Tissot"), 
                ("Nautilus 5711", "Patek Philippe")
            ],
            "gen_attr": lambda i: {"brand": i[1], "type": random.choice(["Analog", "Digital", "Smartwatch", "Chronograph", "Automatic"]), "case_material": random.choice(["Stainless Steel", "Titanium", "Gold", "Resin"]), "strap_material": random.choice(["Leather", "Steel Bracelet", "Silicone", "Nylon"]), "water_resistance": random.choice(["30m", "50m", "100m", "200m", "300m"])}
        },
        "Cosmetics": {
            "desc": "Đồ trang điểm và bảo vệ da cao cấp cho nhan sắc của bạn.",
            "items": [
                ("Revitalift Serum", "L'Oreal"), ("Advanced Night Repair", "Estee Lauder"), ("Ruby Woo Lipstick", "MAC"), 
                ("Moisture Surge", "Clinique"), ("Pro Filt'r Foundation", "Fenty Beauty"), ("Niacinamide 10%", "The Ordinary"), 
                ("Sauvage Eau de Toilette", "Dior"), ("No. 5 Eau de Parfum", "Chanel"), ("Ultra Facial Cream", "Kiehl's"), 
                ("Radiant Creamy Concealer", "NARS")
            ],
            "gen_attr": lambda i: {"brand": i[1], "volume_ml": random.choice([15, 30, 50, 100, 250]), "skin_type_target": random.choice(["Oily", "Dry", "Combination", "Sensitive", "All Types"]), "ingredients": random.choice(["Hyaluronic Acid", "Vitamin C", "Retinol", "Salicylic Acid", "Natural Extracts"]), "expiration_date": f"{random.randint(2025, 2028)}-12-31"}
        },
        "Toys": {
            "desc": "Đồ chơi tương tác phát triển trí não cho đủ lứa tuổi.",
            "items": [
                ("Millennium Falcon 75192", "LEGO"), ("Dreamhouse Playset", "Barbie"), ("Loop Star Track", "Hot Wheels"), 
                ("Elite 2.0 Commander", "Nerf"), ("Original 3x3 Cube", "Rubik's"), ("Fun Factory Set", "Play-Doh"), 
                ("Rock-a-Stack", "Fisher-Price"), ("Classic Monopoly", "Hasbro"), ("Wild Card Game", "Uno"), 
                ("Elite Trainer Box", "Pokemon")
            ],
            "gen_attr": lambda i: {"brand": i[1], "material": random.choice(["Plastic", "Wood", "Cardboard", "Die-Cast Metal", "Plush"]), "age_group_target": random.choice(["0-3 years", "4-7 years", "8-12 years", "13+ years", "Adults"]), "safety_warning": random.choice(["Choking Hazard - Small Parts", "Use under adult supervision", "Safe for all ages"])}
        },
        "Furniture": {
            "desc": "Nội thất gỗ và tiện ích giúp căn hộ của bạn trở thành tổ ấm hoàn hảo.",
            "items": [
                ("Klippan Loveseat", "IKEA"), ("Aeron Chair", "Herman Miller"), ("Mid-Century Bed", "West Elm"), 
                ("Rania Dining Table", "Wayfair"), ("Yandel Power Recliner", "Ashley Furniture"), ("Benchwright Bookshelf", "Pottery Barn"), 
                ("Lounge II Chair", "CB2"), ("Sven Leather Sofa", "Article"), ("Leap V2 Chair", "Steelcase"), 
                ("Lakin TV Stand", "Crate & Barrel")
            ],
            "gen_attr": lambda i: {"brand": i[1], "material": random.choice(["Wood", "Leather", "Fabric", "Metal", "Plastic"]), "dimensions_cm": f"{random.randint(50, 200)}x{random.randint(40, 100)}x{random.randint(40, 150)}", "weight_kg": round(random.uniform(5.0, 50.0), 1), "color": random.choice(["Walnut", "Black", "White", "Grey", "Tan"])}
        },
        "Home Appliances": {
            "desc": "Trang thiết bị điện máy hỗ trợ công việc nội trợ hàng ngày.",
            "items": [
                ("V15 Detect Vacuum", "Dyson"), ("Duo 7-in-1", "Instant Pot"), ("Premium Airfryer", "Philips"), 
                ("OLED C2 65 inch", "LG"), ("Family Hub Refrigerator", "Samsung"), ("Artisan Stand Mixer", "KitchenAid"), 
                ("Professional Blender", "Ninja"), ("Roomba j7+", "iRobot"), ("Bravia XR A80K", "Sony"), 
                ("VertuoPlus Coffee", "Nespresso")
            ],
            "gen_attr": lambda i: {"brand": i[1], "power_consumption_W": random.choice([200, 500, 1000, 1500, 2000, 2500]), "capacity": random.choice(["1.0L", "2.5L", "5.0L", "N/A", "9kg", "12 Place Settings"]), "warranty_months": random.choice([12, 24, 36, 60])}
        },
        "Food": {
            "desc": "Nhu yếu phẩm, đồ ăn đóng gói đảm bảo an toàn vệ sinh.",
            "items": [
                ("Chocolate Sandwich Cookies", "Oreo"), ("Classic Potato Chips", "Lays"), ("Diet Coke 12oz Cans", "Coca-Cola"), 
                ("Hazelnut Spread", "Nutella"), ("Corn Flakes Cereal", "Kellogg's"), ("Energy Drink 8oz", "Red Bull"), 
                ("Hazelnut Chocolate Bar", "Kinder"), ("Nacho Cheese Chips", "Doritos"), ("Peanut Chocolate Candies", "M&M's"), 
                ("Tomato Ketchup 20oz", "Heinz")
            ],
            "gen_attr": lambda i: {"brand": i[1], "origin": random.choice(["USA", "UK", "Vietnam", "Italy", "Switzerland", "Japan"]), "weight_g": random.choice([100, 250, 500, 1000, 150]), "expiration_date": f"{random.randint(2024, 2026)}-{random.randint(1,12):02d}-15", "calories_per_100g": random.choice([200, 350, 450, 500, 550])}
        }
    }


def run():
    print("Clearing old product data...")
    ProductModel.objects.all().delete()
    
    print("Seeding 11 categories x 10 items with HIGHLY REALISTIC DATA...")
    data_map = get_realistic_data()
    
    for cat_name, cat_data in data_map.items():
        # Get category (assumes categories_seed has run or creates it if missing)
        category, _ = CategoryModel.objects.get_or_create(
            name=cat_name, 
            defaults={"description": cat_data["desc"]}
        )
        
        for item_data in cat_data["items"]:
            # item_data: e.g. ("Sapiens", "Yuval Noah Harari", "Harper", 443)
            product_name = item_data[0]
            base_attr = cat_data["gen_attr"](item_data)
            
            # Base price according roughly to category
            min_price, max_price = 10, 50
            if cat_name in ["Laptop", "Mobile", "Home Appliances", "Furniture"]:
                min_price, max_price = 199, 2999
            elif cat_name in ["Watch"]:
                min_price, max_price = 50, 15000
            elif cat_name in ["Shoes", "Fashion", "Cosmetics", "Toys"]:
                min_price, max_price = 20, 250
            elif cat_name in ["Food", "Book"]:
                min_price, max_price = 5, 45
            
            price = round(random.uniform(min_price, max_price), 2)
            
            # Use unsplash image matching the category keyword
            search_query = product_name.replace(' ', ',') + "," + cat_name.lower().replace(' ', '')
            image_url = f"https://source.unsplash.com/random/400x400/?{search_query}"
            
            product_desc = f"{product_name} là một trong những sản phẩm {cat_name.lower()} tuyệt vời nhất từ {item_data[1]}. Mang đến trải nghiệm vượt trội cho người dùng."
            
            ProductModel.objects.create(
                category=category,
                name=product_name,
                description=product_desc,
                price=price,
                stock=random.randint(5, 500),
                image_url=image_url,
                attributes=base_attr
            )
            
    print(f"Done! Created {ProductModel.objects.count()} highly realistic products.")

if __name__ == "__main__":
    run()
