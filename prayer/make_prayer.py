"""학생을 위한 오늘의 영어 기도 → 나레이션(voice.wav) + 자막 애니메이션 영상(mp4) + PDF.

사용: python3 make_prayer.py content.json OUTDIR
content.json 형식은 README.md 참고. 결과: OUTDIR/prayer_YYYYMMDD.mp4, prayer_YYYYMMDD.pdf, meta.json
필요: setup.sh 실행(음성 모델 + 한글 글꼴), ffmpeg, Playwright(Chromium).
"""
import sys, os, json, math, random, subprocess, html
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS = os.environ.get("PRAYER_ASSETS", "/home/claude/opic_assets")
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-%s.ttc"
SANS = "/usr/share/fonts/opentype/noto/NotoSansCJK-%s.ttc"
W, H, FPS, SR = 1280, 720, 24, 24000


def font(path, weight, size):
    return ImageFont.truetype(path % weight, size, index=1)  # index 1 = KR


# ---------------- 1. 나레이션 ----------------
def narrate(sc, wd):
    from kokoro_onnx import Kokoro
    k = Kokoro(f"{ASSETS}/kokoro-v1.0.onnx", f"{ASSETS}/voices-v1.0.bin")
    voice, speed = sc.get("voice", "af_heart"), sc.get("speed", 0.88)
    lines = [{"en": f"A prayer for students. {sc['title_en']}", "ko": sc["title_ko"], "intro": True}] + sc["sentences"]
    out, segs, t = [np.zeros(int(SR * 0.8), np.float32)], [], 0.8
    for i, s in enumerate(lines):
        a, _ = k.create(s["en"], voice=voice, speed=speed, lang="en-us")
        a = a.astype(np.float32); d = len(a) / SR
        if d < 0.3: raise SystemExit(f"문장 {i} 음성이 비었음(모델 파일 확인)")
        segs.append({"i": i, "start": round(t, 3), "end": round(t + d, 3), "en": s["en"], "ko": s["ko"], "intro": s.get("intro", False)})
        gap = 1.1 if i == 0 else 0.7
        out += [a, np.zeros(int(SR * gap), np.float32)]; t += d + gap
    out.append(np.zeros(int(SR * 2.0), np.float32)); t += 2.0
    sf.write(os.path.join(wd, "voice.wav"), np.concatenate(out), SR)
    return segs, t


# ---------------- 2. 애니메이션 ----------------
def lerp(a, b, u): return a + (b - a) * u
def mix(c1, c2, u): return tuple(int(lerp(x, y, u)) for x, y in zip(c1, c2))
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)


def gradient(top, bottom):
    y = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(top)[None, None, :] * (1 - y) + np.array(bottom)[None, None, :] * y)
    return Image.fromarray(np.repeat(arr, W, axis=1).astype(np.uint8), "RGB")


def radial(r, color, alpha):
    s = r * 2; y, x = np.ogrid[:s, :s]; d = np.sqrt((x - r) ** 2 + (y - r) ** 2) / r
    a = (np.clip(1 - d, 0, 1) ** 2 * alpha).astype(np.uint8)
    im = np.zeros((s, s, 4), np.uint8); im[..., :3] = color; im[..., 3] = a
    return Image.fromarray(im, "RGBA")


def rays_layer():
    im = Image.new("L", (1600, 1600), 0); d = ImageDraw.Draw(im); c = 800
    for k in range(18):
        a0 = k * 20; a1 = a0 + 7
        d.pieslice([0, 0, 1600, 1600], a0, a1, fill=34)
    return im.filter(ImageFilter.GaussianBlur(18))


def wrap(text, f, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def wrap_ko(text, f, maxw):
    lines, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if f.getlength(t) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines


def render_video(sc, segs, total, wd, out):
    fEN, fENb = font(SERIF, "Regular", 40), font(SERIF, "Bold", 40)
    fKO = font(SANS, "Regular", 25); fLab = font(SANS, "Bold", 20); fSm = font(SANS, "Regular", 18)
    fTitle = font(SERIF, "Bold", 54); fTitleKo = font(SANS, "Regular", 28)
    NIGHT = (gradient((18, 22, 58), (52, 46, 98)), gradient((44, 52, 112), (232, 150, 120)))
    glow = radial(380, (255, 214, 150), 150); halo = radial(120, (255, 240, 210), 120)
    rays = rays_layer()
    rnd = random.Random(7); stars = [(rnd.random() * W, rnd.random() * H * 0.6, rnd.random() * 1.6 + .6, rnd.random() * 6) for _ in range(70)]
    motes = [(rnd.random() * W, rnd.random() * H, rnd.random() * 14 + 6, rnd.random() * 2 + 1.5) for _ in range(26)]
    n = int(total * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", os.path.join(wd, "voice.wav"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    label = f"DAILY PRAYER FOR STUDENTS  ·  No.{sc.get('no', 1)}  ·  {sc['date']}"
    for fi in range(n):
        T = fi / FPS; prog = T / total
        img = Image.blend(NIGHT[0], NIGHT[1], ease(prog * 1.15)).convert("RGBA")
        d = ImageDraw.Draw(img)
        sa = 1 - ease(prog * 1.6)                                   # 별은 점점 사라짐
        for (x, y, r, ph) in stars:
            a = int(255 * sa * (0.5 + 0.5 * math.sin(T * 1.7 + ph)))
            if a > 8: d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 240, a))
        gy = int(lerp(H + 260, H * 0.62, ease(prog * 1.3)))            # 떠오르는 빛
        rl = rays.rotate(T * 3, resample=Image.BILINEAR)
        ray_rgba = Image.new("RGBA", rl.size, (255, 226, 170, 0)); ray_rgba.putalpha(rl.point(lambda v: int(v * ease(prog * 2))))
        img.alpha_composite(ray_rgba, (W // 2 - 800, gy - 800))
        img.alpha_composite(glow, (W // 2 - 380, gy - 380))
        for (x, y0, r, sp) in motes:                                   # 떠다니는 빛 알갱이
            y = (y0 - T * sp * 12) % (H + 40) - 20; xx = x + math.sin(T * 0.6 + y0) * 18
            img.alpha_composite(halo.resize((int(r * 2), int(r * 2))), (int(xx - r), int(y - r)))
        shade = Image.new("RGBA", (W, H), (0, 0, 0, 0)); sd = ImageDraw.Draw(shade)
        sd.rounded_rectangle([110, 168, W - 110, 548], 28, fill=(10, 12, 34, 120)); img.alpha_composite(shade)
        d = ImageDraw.Draw(img)
        d.text((40, 30), label, font=fLab, fill=(255, 236, 200, 230))
        cur = None
        for s in segs:
            if s["start"] - 0.25 <= T < (segs[s["i"] + 1]["start"] - 0.25 if s["i"] + 1 < len(segs) else total): cur = s
        if T < segs[0]["start"] - 0.25: cur = segs[0]
        if cur and cur["intro"]:
            u = ease((T - 0.2) / 1.0)
            t1 = sc["title_en"]; w1 = fTitle.getlength(t1)
            lines = wrap(t1, fTitle, W - 300)
            y = 250
            for ln in lines:
                d.text((W / 2 - fTitle.getlength(ln) / 2, y), ln, font=fTitle, fill=(255, 248, 232, int(255 * u))); y += 70
            d.text((W / 2 - fTitleKo.getlength(sc["title_ko"]) / 2, y + 14), sc["title_ko"], font=fTitleKo, fill=(255, 226, 190, int(230 * u)))
            th = "A prayer for students"; d.text((W / 2 - fSm.getlength(th) / 2, 205), th.upper(), font=fSm, fill=(255, 220, 170, int(200 * u)))
        elif cur:
            u = ease((T - cur["start"] + 0.25) / 0.5)
            k = max(0.0, min(1.0, (T - cur["start"]) / max(0.5, cur["end"] - cur["start"])))
            words = cur["en"].split(); lit = int(round(k * len(words)))
            lines = wrap(cur["en"], fEN, W - 300); klines = wrap_ko(cur["ko"], fKO, W - 320)
            y = 358 - (len(lines) * 58 + 16 + len(klines) * 36) / 2; wi = 0
            for ln in lines:
                x = W / 2 - fEN.getlength(ln) / 2
                for w in ln.split():
                    on = wi < lit
                    d.text((x, y), w, font=fEN, fill=(255, 226, 160, int(255 * u)) if on else (236, 236, 250, int(140 * u)))  # 읽은 단어는 색으로만 강조(폭 그대로)
                    x += fEN.getlength(w + " "); wi += 1
                y += 58
            for ln in klines:
                d.text((W / 2 - fKO.getlength(ln) / 2, y + 16), ln, font=fKO, fill=(220, 226, 255, int(225 * u))); y += 36
            body = [s for s in segs if not s["intro"]]; idx = cur["i"]
            cnt = f"{idx} / {len(body)}"; d.text((W - 40 - fSm.getlength(cnt), 34), cnt, font=fSm, fill=(255, 236, 200, 200))
        d.rectangle([0, H - 8, int(W * prog), H], fill=(255, 210, 140, 220))
        p.stdin.write(img.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise SystemExit("ffmpeg 실패")


# ---------------- 3. PDF ----------------
def render_pdf(sc, out_pdf, wd):
    e = html.escape
    rows = "".join(f'<div class="s"><span class="n">{i+1:02d}</span><div><p class="en">{e(s["en"])}</p><p class="ko">{e(s["ko"])}</p></div></div>' for i, s in enumerate(sc["sentences"]))
    ex = "".join(f'<tr><td class="ee">{e(a)}</td><td>{e(b)}</td><td class="tip">{e(c)}</td></tr>' for a, b, c in sc.get("exprs", []))
    key = sc.get("key_sentence") or sc["sentences"][0]["en"]
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>
@page{{size:A4;margin:18mm 17mm}}
body{{font-family:"Noto Sans CJK KR",sans-serif;color:#23263f;font-size:10pt;line-height:1.6}}
.top{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #e8a35f;padding-bottom:6px}}
.lab{{font-size:8.5pt;letter-spacing:.12em;color:#b8742f;font-weight:700}}
h1{{font-family:"Noto Serif CJK KR",serif;font-size:22pt;margin:14px 0 2px;color:#2a2f6e;line-height:1.25}}
.sub{{color:#6a6f94;margin:0 0 10px}}
.theme{{display:inline-block;background:#fff1de;color:#a5621f;border-radius:6px;padding:1px 9px;font-size:8.5pt;font-weight:700}}
.s{{display:grid;grid-template-columns:30px 1fr;gap:6px;padding:7px 0;border-bottom:1px solid #eceaf4;break-inside:avoid}}
.n{{font-family:"Noto Serif CJK KR",serif;color:#e09252;font-weight:700}}
.en{{font-family:"Noto Serif CJK KR",serif;font-size:11.5pt;margin:0;color:#1f2250}}
.ko{{margin:2px 0 0;color:#626786;font-size:9.5pt}}
h2{{font-family:"Noto Serif CJK KR",serif;font-size:13pt;color:#2a2f6e;margin:16px 0 6px}}
table{{width:100%;border-collapse:collapse}}td{{border-top:1px solid #eceaf4;padding:6px 8px;vertical-align:top}}
.ee{{font-family:"Noto Serif CJK KR",serif;font-weight:700;color:#1f2250;width:38%}}.tip{{color:#6a6f94;font-size:9pt}}
.key{{background:#f4f2ff;border-left:4px solid #6c6fd8;padding:10px 14px;border-radius:6px;font-family:"Noto Serif CJK KR",serif;font-size:12pt;color:#2a2f6e}}
.note{{color:#6a6f94;font-size:9pt;margin-top:12px}}
</style></head><body>
<div class="top"><span class="lab">DAILY PRAYER FOR STUDENTS · No.{sc.get('no',1)}</span><span class="lab">{e(sc['date'])}</span></div>
<h1>{e(sc['title_en'])}</h1><p class="sub">{e(sc['title_ko'])} <span class="theme">{e(sc.get('theme',''))}</span></p>
{rows}
<h2>오늘 마음에 새길 한 문장</h2><div class="key">{e(key)}</div>
<h2>기도 속 영어 표현</h2><table>{ex}</table>
<p class="note">{e(sc.get('note_ko',''))}</p>
</body></html>"""
    hp = os.path.join(wd, "prayer.html"); open(hp, "w", encoding="utf-8").write(doc)
    js = ("const {chromium}=require('playwright');(async()=>{const b=await chromium.launch();const p=await b.newPage();"
          "await p.goto('file://'+process.argv[1]);await p.waitForTimeout(300);"
          "await p.pdf({path:process.argv[2],format:'A4',preferCSSPageSize:true});await b.close()})()")
    subprocess.run(["node", "-e", js, os.path.abspath(hp), os.path.abspath(out_pdf)], check=True)  # 이 환경에는 Node용 Playwright가 기본 설치돼 있어요


def main():
    sp, od = sys.argv[1], sys.argv[2]; os.makedirs(od, exist_ok=True)
    sc = json.load(open(sp, encoding="utf-8")); tag = sc["date"].replace("-", "")
    segs, total = narrate(sc, od)
    vid = os.path.join(od, f"prayer_{tag}.mp4"); pdf = os.path.join(od, f"prayer_{tag}.pdf")
    render_video(sc, segs, total, od, vid); render_pdf(sc, pdf, od)
    meta = {"video": vid, "pdf": pdf, "dur": round(total), "segs": [{k: s[k] for k in ("start", "end", "en", "ko")} for s in segs]}
    json.dump(meta, open(os.path.join(od, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({"video": vid, "pdf": pdf, "dur": round(total)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
