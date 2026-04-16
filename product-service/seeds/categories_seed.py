import os
import sys
import django

# Setup Django env
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from modules.catalog.infrastructure.models.category_model import CategoryModel

categories_info = [
    ("Book", "Kho sách với đủ các thể loại từ Sci-fi, phát triển bản thân đến văn học kinh điển."),
    ("Laptop", "Máy tính xách tay cấu hình cao đáp ứng mọi nhu cầu làm việc và giải trí."),
    ("Mobile", "Điện thoại thông minh đời mới nhất, pin trâu chụp hình sắc nét."),
    ("Shoes", "Giày dép thời trang thể thao êm ái, bền bỉ đến từ các thương hiệu hàng đầu."),
    ("Fashion", "Quần áo phong cách thiết kế hiện đại, định hình thời trang của bạn."),
    ("Watch", "Đồng hồ thông minh và cơ học, tôn lên vẻ thanh lịch và đẳng cấp."),
    ("Cosmetics", "Đồ trang điểm và bảo vệ da cao cấp cho nhan sắc của bạn."),
    ("Toys", "Đồ chơi tương tác phát triển trí não cho đủ lứa tuổi."),
    ("Furniture", "Nội thất gỗ và tiện ích giúp căn hộ của bạn trở thành tổ ấm hoàn hảo."),
    ("Home Appliances", "Trang thiết bị điện máy hỗ trợ công việc nội trợ hàng ngày."),
    ("Food", "Nhu yếu phẩm, đồ ăn đóng gói đảm bảo an toàn vệ sinh.")
]

def run():
    print("Seeding categories...")
    for name, desc in categories_info:
        obj, created = CategoryModel.objects.get_or_create(name=name, defaults={'description': desc})
        if created:
            print(f"Created category: {name}")
        else:
            print(f"Category already exists: {name}")
    print("Done seeding categories.")

if __name__ == "__main__":
    run()
