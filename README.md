# Python code auto_trade_backpack_exchange_via_API


- Code python trade trên Backpack Exchange thông qua Backpack API

![zz](https://github.com/user-attachments/assets/f56819a3-700e-46da-9ef2-952bbafdbb19)

- Cài đặt các chiến lược trading:
  + Số lần muốn trade
  + thời gian chờ giữa các lần trade
  + Đặt TP và SL sau khi mở lệnh
  + Đặt các giá trị: Đòn bẩy, Số tiền muốn trade..
  + sử dụng lệnh Maker giúp tối ưu fee hơn

 
<h3>Cài đặt:</h3>

- Tải và cài đặt python: https://www.python.org/downloads/

- Cài phần mềm phụ thuộc để chạy code:

 ```
 pip install -r requirements.txt
 ```

**=> ae không rành có thể chạy file: `start.exe`, không cần cài python nha (Mình build từ code trên ra nên 100% an toàn nha, nhớ setting xong rồi chạy)**

1. Tạo API  từ sàn Backpack: https://backpack.exchange/refer/TOP > Portfolio > Settings > API Key > New API Key
   
2. Copy `API KEY` và `API_SECRET` vào file `env_example`

_(**không để lộ thông tin 2 key này, không sử dụng nữa có thể xóa đi)_

   ![image](https://github.com/user-attachments/assets/96b6248d-e66e-4c2a-91bc-c09b3fc9d74c)
   
3. Đổi tên file: `env_example` thành `.env`
   
4. Mở file `settings.json` và điền các chiến lược trade vào. Có ghi chú chức năng trong file nha

----------------------------

 <h3>Chạy code:</h3>
 
```
python start.py
```

hoặc

Chạy file: `start.exe`

_**Nếu hữu ích hãy Follow và thả Star cho mình nhé ❤️_
