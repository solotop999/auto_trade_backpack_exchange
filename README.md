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

Nên chạy từ mã nguồn theo hướng dẫn dưới đây. Nếu dùng bản executable, hãy xác minh nguồn phát hành và đối chiếu với mã nguồn; repo không bảo đảm an toàn tuyệt đối cho file thực thi.

1. Tạo API  từ sàn Backpack: https://backpack.exchange/refer/TOP > Portfolio > Settings > API Key > New API Key
   
2. Copy `API KEY` và `API_SECRET` vào file `env_example`

_(**không để lộ thông tin 2 key này, không sử dụng nữa có thể xóa đi)_

   ![image](https://github.com/user-attachments/assets/96b6248d-e66e-4c2a-91bc-c09b3fc9d74c)
   
3. Đổi tên file: `env_example` thành `.env`
   
4. Mở file `settings.json` và điền các chiến lược trade vào. Có ghi chú chức năng trong file nha
(nếu bật tính năng thông báo qua telegram (TELEGRAM_ALERT=true), thì cài đặt thông tin telegram bot tại file .env, nếu không thi)
----------------------------

 <h3>Chạy code:</h3>
 
```
python start.py
```

### Kiểm thử và tương thích API

Đối chiếu với [tài liệu Backpack chính thức](https://docs.backpack.exchange/) ngày 21/10/2026.

- Request dùng ED25519, sắp xếp tham số theo tên và ký boolean dạng `true`/`false`.
- Các giá trị decimal (giá, số lượng, leverage) được gửi dạng chuỗi. Giá/số lượng được làm tròn xuống theo bội số tick/step thực tế.
- `clientId=0` được hỗ trợ; hủy lệnh phải truyền đúng một trong `clientId` hoặc `orderId`.
- `execute_order()` hỗ trợ `triggerBy`, `stopLossTriggerBy`, `takeProfitTriggerBy`, `slippageTolerance` và `slippageToleranceType`. Truyền cả giá trị và loại slippage nếu sử dụng.
- `autoRealizePnl` không còn được ghi vào account. Truyền tham số này sẽ báo lỗi cục bộ thay vì gửi request không hợp lệ.
- `/history/pnl` đã bị Backpack loại bỏ ngày 07/08/2025. `get_pnl_history()` báo lỗi rõ ràng; dùng `get_settlement_history()` để lấy các sự kiện settlement với schema riêng, không phải bản thay thế tương đương cho lịch sử PnL.
- Request HTTP có timeout 30 giây. Không tự động gửi lại lệnh khi lỗi mạng vì trạng thái thực thi có thể chưa xác định.
- Telegram chỉ cần cấu hình khi bật thông báo. Không tải và thực thi banner Python từ Internet khi khởi động.

Chạy kiểm thử offline (không cần API key và không đặt lệnh):

```powershell
python -m unittest discover -s tests -v
```

Kiểm thử dùng request giả lập, bao gồm xác minh chữ ký ED25519, payload API, precision và cấu hình Telegram tắt. Chưa xác nhận khớp lệnh thật bằng tài khoản giao dịch.

Lưu ý vận hành: vòng lặp hiện hủy tất cả lệnh và gửi lệnh đóng tất cả vị thế trong tài khoản trước mỗi lần đặt lệnh mới. Chỉ dùng tài khoản/subaccount dành riêng cho tool. Post-only không bảo đảm được khớp; TP/SL không bảo đảm mức lỗ/lãi thực tế do phí, funding, trượt giá và việc khớp lệnh. Không commit `.env` hoặc API secret.

_**Nếu hữu ích hãy Follow và thả Star cho mình nhé ❤️_
