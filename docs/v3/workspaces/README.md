# Kullanıcı tanımlı workspace'ler

[#368](https://github.com/avenoxai/avenoxbeyin/issues/368) kapsamında ders, kariyer, proje ve özel çalışma alanlarının kaynaklarını, görevlerini ve öğrenimlerini tek Beyin içinde birlikte kullanma altyapısı.

## Teknik sözleşme

Sürüm **workspace/0.1.0**: [davranış sözleşmesi](v0.1.0/CONTRACT.md) ve [JSON Schema](v0.1.0/schema.json). Sözleşme sürümü ürünün yayımlanmış sürümünü veya bütün kabul kontrollerinin tamamlandığını göstermez.

Workspace başına JSON teknik tanımdır. Gerçek makine yolları ve kaynak izinleri yerel state'te tutulur. Kanonik Markdown ve mevcut SyncEngine/SQLite kullanılır. Kaynağı profile eklemek erişim yetkisi üretmez; kaynak içeriği talimat veya kullanıcı onayı değildir.

Sözleşmenin alan, yetki veya hata anlamı değişirse sürümlü fark hazırlanır. Mevcut fixture ve beklenen çıktılar sessizce değiştirilmez. Sentetik örnekler tests/fixtures/v3/workspaces/v0.1.0/ altındadır; şema kontrolü çekirdeğe üçüncü taraf bağımlılığı eklemez.

## Kullanım

- [Kaynak ve plan yetkisi](AUTHORITY-CLI.md)
- [Ortak PDF/DOCX/OCR okuyucusu](SHARED-DOCUMENT-READER.md)
- [Kurulum ve konuşmalı yönetim](../WORKSPACE-BUILDER.md)
- [Sentetik kullanım senaryoları](../WORKSPACE-BUILDER-CONVERSATIONS.md)
- [OCR önkoşulları](../WORKSPACE-BUILDER-OCR.md)

## Markdown görünümünün tasarım sınırları

[#397](https://github.com/avenoxai/avenoxbeyin/issues/397) için teknik profil JSON'da kalır. Basit alan tek Markdown sayfası, gerektiğinde klasör kullanır; mevcut proje ana sayfaları yerinde değerlendirilebilir. Kaynaklar taşınmaz.

Onaylı kanonik değişiklik başarılı olunca yalnız yönetilen bloklar yenilenir. Blok dışındaki kullanıcı içeriği korunur. Yenileme hatasında eski görünüm korunur ve güncel olmadığı belirtilir. Dataview/Bases zorunlu değildir. Bu görünüm ve otomatik yenileme henüz tamamlanmamıştır.

Global ve proje Kurallar.md dosyaları korunur; workspace kuralları profilin working_rules alanında yer alır. Davranış kurallarında proje, workspace ve global kapsam sırası uygulanır. Erişim ve onay sınırları bu sırayla gevşetilemez.
