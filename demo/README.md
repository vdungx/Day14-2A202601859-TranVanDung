# RAG Evaluation Lab — Demo

Giao diện demo đen–trắng cho Exercise 3.4, trực quan hóa dữ liệu đã được lưu
trong `artifacts/framework_comparison.json`.

## Luồng demo

1. **Overview:** kiểm tra coverage 151/160 trước khi xem averages.
2. **Metric cards:** so sánh bốn aggregate metrics và denominator của từng framework.
3. **Case matrix:** đổi metric, lọc failure/error/difficulty và chọn một case.
4. **Trace inspector:** theo dõi question → retrieved evidence → expected/actual answer → scores.
5. **Method notes:** giải thích provider errors, recovery pilots và embedding asymmetry.

## Chạy local

```powershell
cd demo
npm install
npm run dev
```

## Kiểm tra

```powershell
npm test
npm audit --omit=dev
```

Dashboard không gọi API, không đọc `.env` và không chứa secret. Dữ liệu demo là
snapshot đã kiểm chứng; muốn cập nhật số liệu cần chạy lại benchmark và đồng bộ
snapshot trong `app/page.tsx`.
