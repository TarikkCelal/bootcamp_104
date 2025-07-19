import sqlite3

conn = sqlite3.connect('veritabani.db')
cursor = conn.cursor()


# Önce eski tabloyu sil (geçici olarak)
#cursor.execute("DROP TABLE IF EXISTS abone")// tabloyu geçici olarak siler

# Sonra yeni tabloyu oluştur
cursor.execute('''
    CREATE TABLE IF NOT EXISTS abone (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        kayit_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS kullanicilar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        isim TEXT NOT NULL,
        soyisim TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        telefon TEXT,
        sifre_hash TEXT NOT NULL,
        yas INTEGER,
        boy INTEGER,
        kilo INTEGER,
        profil_foto TEXT,
        kayit_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
               
    )
''')

# ✨ Analiz sonuçları tablosu
cursor.execute('''
    CREATE TABLE IF NOT EXISTS analiz_sonuclari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER,
        tarih TEXT,
        risk_orani REAL,
        detaylar TEXT,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
    )
''')

# 🩺 Randevular tablosu
cursor.execute('''
    CREATE TABLE IF NOT EXISTS randevular (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tc TEXT NOT NULL,
        adsoyad TEXT NOT NULL,
        telefon TEXT,
        email TEXT,
        tarih TEXT,
        saat TEXT,
        doktor TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS yemek_planlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER,
        tarih TEXT,
        kahvalti TEXT,
        ara1 TEXT,
        ogle TEXT,
        ara2 TEXT,
        aksam TEXT,
        gece TEXT,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS beslenme_notlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        kullanici_id INTEGER,
        tarih TEXT,
        not_icerik TEXT,
        FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
    )
''')

cursor.execute("""
CREATE TABLE IF NOT EXISTS egzersiz_planlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER,
    tarih TEXT,
    pazartesi TEXT,
    sali TEXT,
    carsamba TEXT,
    persembe TEXT,
    cuma TEXT,
    cumartesi TEXT,
    pazar TEXT,
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS egzersiz_notlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id INTEGER,
    tarih TEXT,
    not_icerik TEXT,
    FOREIGN KEY (kullanici_id) REFERENCES kullanicilar(id)
)
""")




conn.commit()
conn.close()
