# Streamlit Web App - Hướng Dẫn Chạy Dự Án

## Giới thiệu
Đây là dự án web ứng dụng được xây dựng với [Streamlit](https://streamlit.io/), một framework Python giúp nhanh chóng xây dựng và chia sẻ ứng dụng web dữ liệu.

## Yêu cầu hệ thống
Trước khi bắt đầu, đảm bảo bạn đã cài đặt các công cụ sau trên máy tính:
- Python 3.8 trở lên (tải tại [python.org](https://www.python.org/))
- pip (trình quản lý gói của Python, thường được cài đặt sẵn cùng Python)
- Git (để clone dự án, tùy chọn nếu bạn tải file zip thay thế)

## Các bước cài đặt và chạy dự án

### 1. Clone hoặc tải mã nguồn dự án
Đầu tiên, lấy mã nguồn dự án về máy tính của bạn bằng một trong hai cách:
- Sử dụng Git để clone:
  ```bash
  git clone https://github.com/xuanhung215/CSDLPT.git
  pip install -r requirements.txt
  cd src
  python/python3 -m streamlit run app.py --server.headless true
  ```
- Hoặc tải file zip của dự án, giải nén và di chuyển vào thư mục dự án vừa giải nén.

### 2. Tạo môi trường ảo (khuyến nghị)
Để tránh xung đột giữa các gói của các dự án khác, bạn nên tạo một môi trường ảo riêng cho dự án này:
