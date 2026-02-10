# QorSense Desktop - Proje Analiz Raporu

## 1. Uygulama Genel Bakışı ve Hedefler
**QorSense Desktop**, endüstriyel sensörlerden (pH, İletkenlik, Viskozite, Akış vb.) gelen verileri gerçek zamanlı olarak izleyen, analiz eden ve arıza teşhisi koyan, **donanım kilidi (hardware-lock)** ile korunan yüksek performanslı bir "Tahminleyici Bakım" (Predictive Maintenance) platformudur.

**Temel Hedefler:**
*   **Erken Arıza Tespiti:** Sensörlerdeki yaşlanma, kirlenme, donma veya elektronik arızaları henüz kritik seviyeye ulaşmadan tespit etmek.
*   **Gerçek Zamanlı İzleme:** Modbus TCP/RTU üzerinden saniyeler mertebesinde veri toplayıp görselleştirmek.
*   **Güvenlik:** Yazılımın sadece yetkilendirilmiş endüstriyel PC'lerde çalışmasını sağlamak (Licensing/Fingerprinting).

## 2. Hedef Kitle (Target Audience)
Uygulama, teknik bilgi düzeyi yüksek endüstriyel tesislere yöneliktir:
*   **Kontrol Odası Operatörleri:** "Fusion Dark Theme" ve büyük göstergeler, loş kontrol odalarında uzun süreli izleme için tasarlanmıştır.
*   **Bakım Mühendisleri:** Detaylı "Field Explorer" ve osiloskop görünümleri, teknik personelin kök neden analizi yapması içindir.
*   **Saha Teknisyenleri:** Otomatik bağlantı sihirbazı ve sensör profilleri, hızlı kurulum ve devreye alma sağlar.

## 3. Yapılması Gerekenler (Current Tasks & Roadmap)
Kod tabanı ve kullanıcı geçmişinden anlaşılan mevcut ve gelecek iş paketleri:
*   **Entegrasyon (Devam Ediyor):** `SensorDiagnosisDashboard`'un ana pencereye entegre edilmesi.
*   **Raporlama:** Analiz sonuçlarının CSV/PDF olarak dışa aktarılması (CSV export planlama aşamasında görünüyor).
*   **Zenginleştirme:** Teşhis motorunun sensör tiplerine göre özelleştirilmesi (Polimorfik yapı kurulmuş, genişletilebilir).

## 4. Kullanılan Sofistike Yöntemler ve Teknolojiler
Proje, sıradan bir veri izleme yazılımının ötesinde, **İleri Sinyal İşleme** ve **Makine Öğrenmesi** tekniklerini barındıran "Mission-Critical" bir mimariye sahiptir.

### A. Algoritmik Motor (The "Hard Math")
`backend/analysis.py` dosyası içerisinde tespit edilen ileri teknikler:

1.  **DFA (Detrended Fluctuation Analysis):**
    *   Sinyalin "fraktal" yapısını ve uzun dönemli hafızasını analiz eder.
    *   Vektörize edilmiş NumPy operasyonları ile döngülerden 10 kat daha hızlı çalışır.
2.  **Auto-Encoder (Yapay Sinir Ağı):**
    *   `sklearn.neural_network.MLPRegressor` kullanılarak oluşturulmuş bir anomali tespit modelidir.
    *   Sistemin "normal" davranışını öğrenir; sapma miktarı (`ae_error`) sensör yaşlanmasını veya bilinmeyen arızaları gösterir.
3.  **Spectral Centroid (Frekans Analizi):**
    *   Sinyalin frekans ağırlık merkezini hesaplar.
    *   Yüksek frekanslı gürültülerin (EMI, Ground Loop) mekanik arızalardan ayırt edilmesini sağlar.
4.  **Kaos Analizi (Lyapunov Exponent):**
    *   Sinyalin kaotik (öngörülemez) yapısını ölçer. Sistemin kararlılığını test eder.
5.  **Polimorfik Teşhis Motoru (Universal Decision Tree):**
    *   Tek bir "if-else" yığını yerine, sensör tipine (pH, Viskozite vb.) göre davranış değiştiren bir karar ağacıdır.
    *   Örneğin: "Yüksek Frekanslı Kaos" pH sensöründe "Çatlak Cam" anlamına gelirken, Viskozite sensöründe "Elektronik Kart Arızası" olarak yorumlanır.

### B. Yazılım Mimarisi
*   **Modular Monolith:** UI (`desktop_app`), İş Mantığı (`workers`) ve Çekirdek Hesaplama (`backend`) katmanları net bir şekilde ayrılmıştır.
*   **PyQt6 & QThread:** Arayüzün donmaması için tüm Modbus haberleşmesi ve ağır matematiksel hesaplamalar ayrı "Worker Thread"lerde çalıştırılır.
*   **NumPy Broadcasting:** Python'un yavaş döngüleri yerine C tabanlı vektör operasyonları kullanılarak gerçek zamanlı analiz performansı sağlanmıştır.
*   **Hardware Fingerprinting:** `backend/license_manager.py` içerisinde, cihazın MAC adresi ve CPU ID'si gibi özelliklerinden SHA-256 tabanlı benzersiz bir "Parmak İzi" oluşturulur. Bu, yazılımın kopyalanmasını engeller.

## 5. Sonuç
QorSense Desktop, basit bir SCADA ekranı değil, donanımın sağlığını matematiksel modellerle sürekli denetleyen bir **Yapay Zeka Destekli Mühendislik Aracıdır**.
