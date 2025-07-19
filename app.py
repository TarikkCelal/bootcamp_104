from flask import Flask, request, render_template, redirect, url_for, session, flash
from flask import jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import pickle
import numpy as np
import pandas as pd
from functools import wraps
from werkzeug.utils import secure_filename
import os
import requests
import random



app = Flask(__name__)
app.secret_key = 'gizli-anahtar'

UPLOAD_FOLDER = 'static/uploads' # Yüklenen dosyaların kaydedileceği klasör
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'} # Dosya uzantıları

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER # Dosya yükleme klasörü


def allowed_file(filename): 
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS # Dosya uzantısını kontrol eder

# Giriş yapmadan erişilmesi gereken sayfalar için dekoratör
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'email' not in session:
            flash("Bu sayfaya erişmek için giriş yapmanız gerekiyor.", "warning")
            return redirect("/bize-katil")
        return f(*args, **kwargs)
    return decorated_function

# Model ve scaler yükleniyor.Veritabanı bağlantısı ve tablo oluşturma
model = pickle.load(open("model.pkl", "rb"))
scaler = pickle.load(open("scaler.pkl", "rb"))


# Ana Sayfa Route
@app.route('/')
def ana_sayfa():
    return render_template('anasayfa.html')

#Hakkımızda Route
@app.route('/hakkimizda')
def hakkimizda():
    return render_template('hakkimizda.html')

#Risk Analizi Route
@app.route('/risk-analizi')
@login_required
def risk_analizi():
    return render_template("riskAnalizi.html")

# Beslenme ve Diyet Önerileri Route
@app.route("/beslenme-onerisi")
@login_required
def beslenmeVeDiyet():
    kullanici_id = session.get("id")
    bugun = datetime.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    # Son yemek planını al
    cursor.execute("""
        SELECT kahvalti, ara1, ogle, ara2, aksam, gece
        FROM yemek_planlari
        WHERE kullanici_id = ?
        ORDER BY tarih DESC, id DESC
        LIMIT 1
    """, (kullanici_id,))
    plan = cursor.fetchone()

    if plan:
        plan_dict = {
            "kahvalti": plan[0],
            "ara1": plan[1],
            "ogle": plan[2],
            "ara2": plan[3],
            "aksam": plan[4],
            "gece": plan[5]
        }
    else:
        plan_dict = None

    # Son günlük notu al
    cursor.execute("""
        SELECT not_icerik FROM beslenme_notlari
        WHERE kullanici_id = ? AND tarih = ?
        LIMIT 1
    """, (kullanici_id, bugun))
    not_sonucu = cursor.fetchone()
    not_icerik = not_sonucu[0] if not_sonucu else ""

    conn.close()

    return render_template("beslenmeOnerileri.html", plan=plan_dict, not_icerik=not_icerik)




# Beslenme Planı Oluşturma Route
@app.route("/beslenme-oneri-generate", methods=["POST"])
@login_required
def yemek_plani_json():
    plan = yapay_beslenme_plani_uret()

    # Veritabanına kaydet
    if "id" in session:
        conn = sqlite3.connect("veritabani.db")
        cursor = conn.cursor()
        tarih = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO yemek_planlari (kullanici_id, tarih, kahvalti, ara1, ogle, ara2, aksam, gece)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["id"],
            tarih,
            plan["kahvalti"],
            plan["ara1"],
            plan["ogle"],
            plan["ara2"],
            plan["aksam"],
            plan["gece"]
        ))
        conn.commit()
        conn.close()

    return jsonify(plan)



# Yapay Beslenme Planı Üretme Route
def yapay_beslenme_plani_uret():
    plan = {
        "kahvalti": random.choice([
            "Yulaf ezmesi + muz + süt",
            "Haşlanmış yumurta + tam buğday ekmek",
            "Peynirli omlet + yeşil çay"
        ]),
        "ara1": random.choice([
            "1 adet elma", "1 avuç çiğ badem", "Yoğurt + keten tohumu"
        ]),
        "ogle": random.choice([
            "Izgara tavuk + bulgur + yoğurt",
            "Sebzeli kinoa salatası",
            "Mercimek çorbası + salata"
        ]),
        "ara2": random.choice([
            "2 kare bitter çikolata + kahve",
            "Portakal + yeşil çay",
            "1 adet muz"
        ]),
        "aksam": random.choice([
            "Somon + haşlanmış brokoli",
            "Zeytinyağlı sebze + tam buğday ekmek",
            "Kıymalı kabak yemeği"
        ]),
        "gece": random.choice([
            "1 bardak ılık süt", "2 adet kuru kayısı", "Yarım avokado"
        ])
    }
    return plan

@app.route("/beslenme-notu-kaydet", methods=["POST"])
@login_required
def beslenme_notu_kaydet():
    data = request.get_json()
    not_text = data.get("not", "").strip()
    kullanici_id = session["id"]
    bugun = datetime.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    # Günlük not varsa güncelle, yoksa ekle
    cursor.execute("""
        SELECT id FROM beslenme_notlari WHERE kullanici_id = ? AND tarih = ?
    """, (kullanici_id, bugun))
    mevcut = cursor.fetchone()

    if mevcut:
        cursor.execute("""
            UPDATE beslenme_notlari SET not_icerik = ? WHERE id = ?
        """, (not_text, mevcut[0]))
    else:
        cursor.execute("""
            INSERT INTO beslenme_notlari (kullanici_id, tarih, not_icerik)
            VALUES (?, ?, ?)
        """, (kullanici_id, bugun, not_text))

    conn.commit()
    conn.close()

    return jsonify({"message": "Not başarıyla kaydedildi!"})


# Egzersiz Önerileri Route
@app.route("/egzersiz-onerisi")
@login_required
def egzersiz_onerisi():
    egzersiz_not = ""
    plan = None
    kullanici_id = session["id"]

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    # Son planı çek
    cursor.execute("""
        SELECT pazartesi, sali, carsamba, persembe, cuma, cumartesi, pazar
        FROM egzersiz_planlari
        WHERE kullanici_id = ?
        ORDER BY tarih DESC
        LIMIT 1
    """, (kullanici_id,))
    row = cursor.fetchone()
    if row:
        plan = {
            "Pazartesi": row[0],
            "Salı": row[1],
            "Çarşamba": row[2],
            "Perşembe": row[3],
            "Cuma": row[4],
            "Cumartesi": row[5],
            "Pazar": row[6]
        }

    # Son egzersiz notu
    cursor.execute("""
        SELECT not_icerik FROM egzersiz_notlari
        WHERE kullanici_id = ?
        ORDER BY tarih DESC
        LIMIT 1
    """, (kullanici_id,))
    not_row = cursor.fetchone()
    if not_row:
        egzersiz_not = not_row[0]

    conn.close()

    return render_template("egzersizOnerisi.html", egzersiz_not=egzersiz_not, plan=plan)


@app.route("/egzersiz-oneri-generate", methods=["POST"])
@login_required
def egzersiz_plani_json():
    plan = yapay_egzersiz_plani_uret()
    tarih = datetime.today().strftime("%Y-%m-%d")
    kullanici_id = session["id"]

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO egzersiz_planlari (
            kullanici_id, tarih, pazartesi, sali, carsamba,
            persembe, cuma, cumartesi, pazar
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        kullanici_id, tarih,
        plan["Pazartesi"], plan["Salı"], plan["Çarşamba"],
        plan["Perşembe"], plan["Cuma"], plan["Cumartesi"], plan["Pazar"]
    ))

    conn.commit()
    conn.close()

    return jsonify(plan)



# Egzersiz Planı Oluşturma Route
def yapay_egzersiz_plani_uret():
    kardiyo = ["Yürüyüş", "Koşu", "Bisiklet"]
    kuvvet = ["Direnç", "Squat", "Plank", "Şınav"]
    esneme = ["Yoga", "Pilates", "Esneme"]
    dinlenme = ["Dinlenme"]

    plan = {
        "Pazartesi": random.choice(kardiyo),
        "Salı": random.choice(kuvvet),
        "Çarşamba": random.choice(kardiyo),
        "Perşembe": random.choice(kuvvet),
        "Cuma": random.choice(esneme),
        "Cumartesi": random.choice(kardiyo + kuvvet),
        "Pazar": random.choice(dinlenme)
    }

    return plan


#Egzersiz Not Kaydetme Route
@app.route("/egzersiz-notu-kaydet", methods=["POST"])
@login_required
def egzersiz_notu_kaydet():
    data = request.get_json()
    not_text = data.get("not", "").strip()
    kullanici_id = session["id"]
    bugun = datetime.today().strftime("%Y-%m-%d")

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    # Aynı gün daha önce not eklendiyse güncelle, yoksa ekle
    cursor.execute("""
        SELECT id FROM egzersiz_notlari WHERE kullanici_id = ? AND DATE(tarih) = ?
    """, (kullanici_id, bugun))
    mevcut = cursor.fetchone()

    if mevcut:
        cursor.execute("""
            UPDATE egzersiz_notlari SET not_icerik = ? WHERE id = ?
        """, (not_text, mevcut[0]))
    else:
        cursor.execute("""
            INSERT INTO egzersiz_notlari (kullanici_id, tarih, not_icerik)
            VALUES (?, ?, ?)
        """, (kullanici_id, bugun, not_text))

    conn.commit()
    conn.close()

    return jsonify({"message": "Egzersiz notun başarıyla kaydedildi."})




#Geçmiş Sonuçlarım Route
@app.route("/gecmis-sonuclarim")
@login_required
def gecmis_sayfasi():
    if "id" not in session:
        return redirect(url_for("giris"))

    sayfa = int(request.args.get('sayfa', 1))
    limit = 4
    offset = (sayfa - 1) * limit

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, tarih, risk_orani FROM analiz_sonuclari
        WHERE kullanici_id = ?
        ORDER BY tarih DESC
        LIMIT ? OFFSET ?
    """, (session["id"], limit, offset))

    sonuclar = cursor.fetchall()
    conn.close()

    return render_template("gecmisSonuclarim.html", sonuclar=sonuclar, sayfa=sayfa)

# hekimlerRandevu Route
@app.route("/hekimlerRandevu")
@login_required
def hekimlerRandevu():
    return render_template("hekimlerRandevu.html")

# Randevu Alma Route
@app.route("/randevu_al", methods=["POST"])
@login_required
def randevu_al():
    data = request.get_json()
    tc = data.get("tc")
    adsoyad = data.get("adsoyad")
    telefon = data.get("telefon")
    email = data.get("email")
    tarih = data.get("tarih")
    saat = data.get("saat")
    doktor = data.get("doktor")  # 👈 yeni alan eklendi

    try:
        conn = sqlite3.connect("veritabani.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO randevular (tc, adsoyad, telefon, email, tarih, saat, doktor)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tc, adsoyad, telefon, email, tarih, saat, doktor))  # 👈 doktor da eklendi
        conn.commit()
        conn.close()

        return jsonify({"message": "Randevunuz başarıyla kaydedildi!"})
    except Exception as e:
        return jsonify({"message": f"Hata oluştu: {str(e)}"}), 500




#Bize Katıl Route
@app.route('/bize-katil')
def bize_katil():
    return render_template('bizekatil.html')

# Abonelik işlemi - Tüm sayfalar için ortak
@app.route('/abone', methods=['POST'])
def abone():
    email = request.form.get('email', '').strip().lower()


    if not email:
        flash("E-posta boş olamaz.")
        return redirect(request.referrer)

    try:
        conn = sqlite3.connect('veritabani.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM abone WHERE email = ?", (email,))
        if cursor.fetchone():
            flash("Bu e-posta zaten kayıtlı!")
        else:
            tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("INSERT INTO abone (email, kayit_tarihi) VALUES (?, ?)", (email, tarih))
            conn.commit()
            flash("Başarıyla abone oldunuz!")
        conn.close()
    except Exception as e:
        flash(f"Hata oluştu: {e}")

    return redirect(request.referrer)  # Geldiği sayfaya geri yönlendir

@app.route('/admin/sil/<email>')
def abone_sil(email):
    try:
        conn = sqlite3.connect('veritabani.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM abone WHERE email = ?", (email,))
        conn.commit()
        conn.close()
        flash("Abone başarıyla silindi.")
    except Exception as e:
        flash(f"Hata: {e}")
    return redirect('/admin')


# Abonelik Listesi,# Veritabanı bağlantısı ve tablo oluşturma
@app.route('/admin')
def admin_panel():
    try:
        conn = sqlite3.connect('veritabani.db')
        cursor = conn.cursor()
        cursor.execute("SELECT email, kayit_tarihi FROM abone")
        aboneler = cursor.fetchall()
        conn.close()
        return render_template('admin.html', aboneler=aboneler)
    except Exception as e:
        return f"Hata oluştu: {e}"
    
#Kayıt Route (POST ile formdan veri alır ve veritabanına kaydeder):
@app.route('/kayit', methods=['POST'])
def kayit():
    try:
        isim = request.form['isim']
        soyisim = request.form['soyisim']
        email = request.form['email']
        telefon = request.form['telefon']
        parola = request.form['parola']
        yas = request.form['yas']
        boy = request.form['boy']
        kilo = request.form['kilo']
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        sifre_hash = generate_password_hash(parola)

        conn = sqlite3.connect("veritabani.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO kullanicilar (isim, soyisim, email, telefon, sifre_hash, yas, boy, kilo, kayit_tarihi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (isim, soyisim, email, telefon, sifre_hash, yas, boy, kilo, tarih))
        conn.commit()
        conn.close()
        
        flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
        return redirect("/bize-katil")

    except sqlite3.IntegrityError:
        flash("Bu e-posta ile daha önce kayıt yapılmış!", "danger")
        return redirect("/bize-katil")

    except Exception as e:
        flash(f"Hata oluştu: {e}", "danger")
        return redirect("/bize-katil")

#Giriş Route (POST ile kullanıcı kontrolü yapar):
@app.route('/giris', methods=['GET', 'POST'])
def giris():
    email = request.form.get('email')
    parola = request.form.get('parola')

    if not email or not parola:
        flash("E-posta veya parola alanı boş bırakılamaz.", "warning")
        return redirect("/bize-katil")

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, isim, soyisim, email, telefon, sifre_hash, profil_foto FROM kullanicilar WHERE email=?", (email,))
    kullanici = cursor.fetchone()
    conn.close()

    if kullanici and check_password_hash(kullanici[5], parola):
        session.permanent = False # Oturumun kalıcı olmasını istemiyorsanız False yapın
        session['id'] = kullanici[0]
        session['isim'] = kullanici[1]
        session['soyisim'] = kullanici[2]
        session['email'] = kullanici[3]
        session['telefon'] = kullanici[4]
        session['profil_foto'] = kullanici[6] if kullanici[6] else "img/user.png" # PROFİL FOTOĞRAFINI DA OTURUMA EKLE,Eğer veri tabanındaki profil_foto değeri boşsa default ikon kullanacak

        flash("Giriş başarılı!", "success")
        return redirect("/")
    else:
        flash("E-posta veya parola hatalı!", "danger")
        return redirect("/bize-katil")
    

    
#Profil Route
@app.route("/profil")
@login_required
def profil():

    email = session["email"]
    kullanici_id = session["id"] # Oturumdan kullanıcı ID'sini al

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT isim, soyisim, email, telefon, yas, boy, kilo, profil_foto 
        FROM kullanicilar 
        WHERE email = ?
    ''', (email,))
    kullanici = cursor.fetchone()

    # Geçmiş analiz tarihlerini al
    cursor.execute('''
        SELECT tarih 
        FROM analiz_sonuclari 
        WHERE kullanici_id = ? 
        ORDER BY tarih DESC 
        LIMIT 4
    ''', (kullanici_id,))
    analiz_tarihleri = [row[0] for row in cursor.fetchall()]

    # Randevu verilerini çek
    cursor.execute('''
        SELECT tarih, saat, doktor 
        FROM randevular 
        WHERE email = ? 
        ORDER BY tarih DESC 
    ''', (email,))
    randevular = cursor.fetchall()

    conn.close()

    if kullanici:
        return render_template("profil.html",
            isim=kullanici[0],
            soyisim=kullanici[1],
            email=kullanici[2],
            telefon=kullanici[3],
            yas=kullanici[4],
            boy=kullanici[5],
            kilo=kullanici[6],
            profil_foto=kullanici[7] or "img/profilFotosu.png",  # eğer hiç yüklememişse default göster
            analiz_tarihleri=analiz_tarihleri,
            randevular=randevular  # Template'e randevu listesini gönder
        )
    else:
        flash("Kullanıcı bilgileri bulunamadı.", "danger")
        return redirect(url_for("giris"))


#Profil Güncelleme Route
@app.route('/profil-guncelle', methods=['POST'])
def profil_guncelle():
    if 'email' not in session:
        return redirect('/bize-katil')

    email = session['email']
    ad_soyad = request.form['adSoyad']
    telefon = request.form['telefon']
    yas = request.form['yas']
    boy = request.form['boy']
    kilo = request.form['kilo']

    # Ad ve soyadı ayır
    ad_soyad = ad_soyad.strip()
    isim = ad_soyad.split()[0]
    soyisim = ' '.join(ad_soyad.split()[1:]) if len(ad_soyad.split()) > 1 else ''

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE kullanicilar
        SET isim = ?, soyisim = ?, telefon = ?, yas = ?, boy = ?, kilo = ?
        WHERE email = ?
    ''', (isim, soyisim, telefon, yas, boy, kilo, email))

    conn.commit()
    conn.close()

    flash("Profil bilgileri başarıyla güncellendi.", "success")
    return redirect('/profil')



# profil_fotograf_yukle Route
@app.route('/profil_fotograf_yukle', methods=['POST'])
@login_required
def profil_fotograf_yukle():
    if 'profil_foto' not in request.files or 'email' not in session:
        flash('Dosya veya kullanıcı bilgisi eksik.', 'warning')
        return redirect('/profil')

    dosya = request.files['profil_foto']
    if dosya.filename == '':
        flash('Dosya seçilmedi.', 'warning')
        return redirect('/profil')

    if dosya and allowed_file(dosya.filename):
        filename = secure_filename(session['email'] + '_' + dosya.filename)
        yol = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        dosya.save(yol)

        # Veritabanına yolunu kaydet
        conn = sqlite3.connect("veritabani.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE kullanicilar SET profil_foto = ? WHERE email = ?", (f"uploads/{filename}", session['email']))
        conn.commit()
        conn.close()

        flash('Profil fotoğrafı başarıyla yüklendi.', 'success')
        return redirect('/profil')
    else:
        flash('Geçersiz dosya formatı.', 'danger')
        return redirect('/profil')
    
#Profil Fotoğrafı Silme Route
@app.route("/profil/fotograf-sil", methods=["POST"])

def profil_fotograf_sil():
    if "email" not in session:
        return redirect(url_for("giris"))

    email = session["email"]
    varsayilan_foto = "img/profilFotosu.png"

    # Veritabanında profil_foto'yu varsayılanla değiştir
    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE kullanicilar SET profil_foto = ? WHERE email = ?", (varsayilan_foto, email))
    conn.commit()
    conn.close()

    # Oturum bilgisini de güncelle
    session["profil_foto"] = varsayilan_foto

    flash("Profil fotoğrafı kaldırıldı.", "info")
    return redirect(url_for("profil"))



    
# Risk Analizi İşlemi
@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()

        yas = float(data['yas'])
        vki = float(data['vki'])
        hba1c = float(data['hba1c'])
        glikoz = float(data['kanGlikoz'])
        cinsiyet = data['cinsiyet']
        hipertansiyon = 1 if data['hipertansiyon'] == 'Var' else 0
        kalp_hastaligi = 1 if data['kalpHastaligi'] == 'Var' else 0
        sigara = data['sigara']

        input_dict = {
            'age': yas,
            'hypertension': hipertansiyon,
            'heart_disease': kalp_hastaligi,
            'bmi': vki,
            'HbA1c_level': hba1c,
            'blood_glucose_level': glikoz,
            'gender_Female': 0,
            'gender_Male': 0,
            'gender_Other': 0,
            'smoking_history_No Info': 0,
            'smoking_history_current': 0,
            'smoking_history_ever': 0,
            'smoking_history_former': 0,
            'smoking_history_never': 0,
            'smoking_history_not current': 0
        }

        if cinsiyet == 'Erkek':
            input_dict['gender_Male'] = 1
        elif cinsiyet == 'Kadın':
            input_dict['gender_Female'] = 1
        else:
            input_dict['gender_Other'] = 1

        sigara_key = f"smoking_history_{sigara}"
        if sigara_key in input_dict:
            input_dict[sigara_key] = 1

        input_df = pd.DataFrame([input_dict])
        input_scaled = scaler.transform(input_df)
        risk_yuzdesi = model.predict_proba(input_scaled)[0][1] * 100

        if "id" in session:
            conn = sqlite3.connect("veritabani.db")
            cursor = conn.cursor()

            tarih = datetime.today().strftime("%Y-%m-%d")
            kullanici_id = session["id"]
            detaylar = f"Yaş: {yas}, VKİ: {vki}, HbA1c: {hba1c}, Glikoz: {glikoz}, Cinsiyet: {cinsiyet}, Sigara: {sigara}"

            cursor.execute("""
                INSERT INTO analiz_sonuclari (kullanici_id, tarih, risk_orani, detaylar)
                VALUES (?, ?, ?, ?)
                """, (kullanici_id, tarih, float(round(risk_yuzdesi, 2)), detaylar))
            
            conn.commit()
            conn.close()

        return jsonify({'risk': float(round(risk_yuzdesi, 2))})
    
    except Exception as e:
        print("Tahmin hatası:", e)  # 👈 BU SATIRI EKLE
        return jsonify({'error': str(e)}), 500
    

@app.route("/analiz-detay/<int:analiz_id>")
def analiz_detay(analiz_id):
    if "id" not in session:
        return redirect(url_for("giris"))

    conn = sqlite3.connect("veritabani.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT tarih, risk_orani, detaylar 
        FROM analiz_sonuclari 
        WHERE id = ? AND kullanici_id = ?
    """, (analiz_id, session["id"]))
    analiz = cursor.fetchone()
    conn.close()

    if analiz:
        return render_template("analizDetay.html", analiz=analiz)
    else:
        flash("Analiz detayı bulunamadı.", "danger")
        return redirect(url_for("gecmis_sayfasi"))

@app.route('/cikis', methods=['GET', 'POST'])
def cikis():
    session.clear()

    if request.method == 'POST':
        # JS'ten gelen sendBeacon isteği
        return '', 204  # sessizce çık
    else:
        # Kullanıcı manuel olarak tıkladıysa (GET ile geldiyse)
        flash("Başarıyla çıkış yaptınız.", "info")
        return redirect('/bize-katil')




# Uygulamayı başlat
if __name__ == '__main__':
    app.run(debug=True)
