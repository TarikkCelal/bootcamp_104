from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.generativeai as genai
import markdown
import re

app = FastAPI()

# Statik dosyalar ve şablonlar
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Gemini API yapılandırması (kendi API anahtarınızı buraya koyun)
genai.configure(api_key="AIzaSyCmEx7txS_WTzR3eBBdaPbXAJ0va_mMs18")
model = genai.GenerativeModel("gemini-2.5-flash")

def extract_drugs(text: str) -> list[str]:
    words = re.findall(r'\b[a-zçğıöşü]+\b', text.lower())
    if len(words) == 0:
        return []
    elif len(words) == 1:
        return [words[0]]
    else:
        return words[:2]

def normalize_input(text: str) -> str:
    return " ".join(text.lower().strip().split())

# Bu fonksiyon, Markdown'ın eklediği ilk ve son <p> etiketlerini kaldırır.
def clean_markdown_output(html_string: str) -> str:
    if html_string is None:
        return None
    # `markdown` kütüphanesi tek satırlık metinleri bile <p></p> içine alır.
    # Bu yüzden sadece ilk ve son etiketleri siliyoruz.
    return html_string.removeprefix('<p>').removesuffix('</p>').strip()

@app.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "short_answer": None,
        "long_answer_html": None
    })

@app.post("/", response_class=HTMLResponse)
async def post_form(request: Request, user_input: str = Form(...)):
    normalized = normalize_input(user_input)
    drugs = extract_drugs(normalized)

    prompt = f"""
Sen tıbbi bilgi veren bir asistansın.

Kurallar:
- Kullanıcı sadece bir ilaç ismi yazarsa, önce kısa ve net bilgi ver.
- Parantez içinde hiçbir bilgi verme, tamamen atla.
- Teknik, bilimsel terimler, etken maddeler gibi detayları kullanma.
- Kullanıcı iki ilaç yazarsa, önce kısa ve net etkileşim bilgisini ver.
- Tehlikeli ya da kritik uyarıları içeren cümleleri kalın (**) yap.
- Sonra detaylı bilgi ver. (Kullanım alanları, yan etkiler, doz bilgisi...)
- Cevap markdown formatında olsun. Kısa cevap 2-3 cümle olsun.
- Cevabı şu formatta ver:

KISA CEVAP:
<kısa cevap>

DETAYLI CEVAP:
<detaylı cevap (markdown formatında)>

Soru:
{normalized}
"""

    try:
        response_text = model.generate_content(prompt).text.strip()

        short_resp = ""
        long_md = ""

        if "KISA CEVAP:" in response_text and "DETAYLI CEVAP:" in response_text:
            parts = response_text.split("DETAYLI CEVAP:")
            short_resp = parts[0].replace("KISA CEVAP:", "").strip()
            long_md = parts[1].strip()
        else:
            short_resp = response_text
            long_md = ""

        # Kısa cevabı işle ve ilk ve son <p> etiketlerini kaldır.
        short_html = clean_markdown_output(markdown.markdown(short_resp)) if short_resp else None
        
        # Detaylı cevabı işle, burada tüm markdown etiketleri korunur.
        long_html = markdown.markdown(long_md) if long_md else None

    except Exception as e:
        short_html = f"Hata oluştu: {str(e)}"
        long_html = None

    return templates.TemplateResponse("index.html", {
        "request": request,
        "short_answer": short_html,
        "long_answer_html": long_html
    })