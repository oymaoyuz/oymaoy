# Oymaoy — iPhone muddatli to'lov va savdo veb-sayti

Telegram kanali: [@oymaoyy](https://t.me/oymaoyy)  
Ushbu loyiha Apple minimalist uslubidagi bitta sahifali veb-sayt bo'lib, Telegram kanaldagi e'lonlar bilan **100% avtomatik sinxronlanadi**. Sotilgan telefonlar avtomatik yashiriladi.

---

## 🚀 GitHub'ga yuklash va avtomatlashtirishni yoqish (3 qadam)

### 1-qadam: GitHub'da yangi repozitoriy yarating
1. [github.com](https://github.com) ga kiring va yangi repozitoriy yarating (masalan: `oymaoy`).
2. Repozitoriyni **Public** qiling.

### 2-qadam: Kodni yuklang
Terminalda (PowerShell yoki Git Bash) ushbu papkaga kiring va buyruqlarni ketma-ket bajaring:

```bash
cd "C:\Users\user\Desktop\oymaoy-github"
git init
git add .
git commit -m "Oymaoy landing page and auto-sync"
git branch -M main
git remote add origin https://github.com/SIZNING_GITHUBINGIZ/oymaoy.git
git push -u origin main
```
*(Izoh: `SIZNING_GITHUBINGIZ` o'rniga o'zingizning GitHub username'ingizni yozing).*

---

### 3-qadam: GitHub Pages va Actions ruxsatlarini yoqish

1. **GitHub Pages (Saytni internetda bepul chiqarish):**
   - Repozitoriyingizga kiring -> **Settings** -> chap menyudan **Pages** bo'limiga o'ting.
   - **Build and deployment** bo'limida:
     - Source: `Deploy from a branch`
     - Branch: `main` va `/ (root)` ni tanlang -> **Save** tugmasini bosing.
   - 1-2 daqiqada saytingiz `https://SIZNING_GITHUBINGIZ.github.io/oymaoy/` manzilida ishga tushadi!

2. **GitHub Actions ruxsati (Avtomatik yangilab turishi uchun):**
   - **Settings** -> chap menyudan **Actions** -> **General** bo'limiga kiring.
   - Pastroqqa tushib, **Workflow permissions** bo'limida **"Read and write permissions"** ni belgilang va **Save** bosing.

---

## 🤖 Tizim qanday avtomatik ishlaydi?

1. **Har 30 daqiqada:** `.github/workflows/sync.yml` skripti GitHub serverlarida avtomatik ishga tushadi.
2. `@oymaoyy` kanalini tekshiradi:
   - Yangi qo'shilgan telefonlarni darhol saytga chiqaradi.
   - **"SOTILDI"** deb belgilangan telefonlarni saytdan butunlay o'chirib tashlaydi.
3. Agar o'zgarish bo'lsa, `index.html` yangilanadi va GitHub Pages saytni 10 soniyada yangi ko'rinishga keltiradi.
4. **Qo'lda darhol yangilash:** Istalgan vaqtda GitHub repozitoriyingizdagi **Actions** bo'limiga kirib, **"Run workflow"** tugmasini bossangiz, 1 daqiqada darhol yangilab beradi.
