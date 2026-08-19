import os, json
from flask import Flask, request, jsonify, Response
from openai import OpenAI

app = Flask(__name__)
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

HTML = r'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>리셀 매니저 AI</title>
<style>body{font-family:system-ui,sans-serif;background:#f5f6f8;margin:0}.w{max-width:720px;margin:auto;padding:16px}.c{background:#fff;border-radius:16px;padding:16px;margin:12px 0;box-shadow:0 2px 12px #0001}button,input{font-size:16px}button{padding:13px;border:1px solid #ddd;border-radius:10px;background:#fff;font-weight:800}.g{display:grid;grid-template-columns:1fr 1fr;gap:8px}.p{width:100%;background:#111;color:#fff;border:0;margin-top:12px}img{max-width:100%;max-height:300px;object-fit:contain}.prev{display:none;margin-top:10px}label{display:block;font-size:13px;font-weight:700;margin:12px 0 6px}input{width:100%;box-sizing:border-box;padding:11px;border:1px solid #ddd;border-radius:10px}.s{background:#f1f3f5;padding:11px;border-radius:10px;margin-top:10px}.big{font-size:28px;font-weight:900}.r{display:flex;justify-content:space-between;margin:7px 0}</style>
<div class=w><h1>리셀 매니저 AI</h1><div class=c><div class=g><button onclick="cam.click()">📷 가격표 촬영</button><button onclick="gal.click()">🖼️ 사진 불러오기</button></div><input id=cam type=file accept="image/*" capture=environment hidden><input id=gal type=file accept="image/*" hidden><div class=prev id=pr><img id=im></div><button class="p" onclick=go()>⚡ AI로 바로 읽기</button><div class=s id=st>가격표 사진을 선택하세요.</div><label>상품번호</label><input id=no><label>상품명</label><input id=nm><label>정상가</label><input id=rp type=number><label>할인금액</label><input id=dc type=number><label>현재 판매가</label><input id=sp type=number><label>세일 시작일</label><input id=sd type=date><label>세일 종료일</label><input id=ed type=date><button class=p onclick=calc()>💰 권장 쿠팡 판매가 계산</button><div id=res></div></div></div>
<script>let f=null;[cam,gal].forEach(x=>x.onchange=()=>{f=x.files[0];if(f){im.src=URL.createObjectURL(f);pr.style.display='block';st.textContent='사진 준비 완료.'}});async function go(){if(!f)return alert('가격표 사진을 선택하세요.');st.textContent='AI가 읽는 중…';let q=await new Promise(ok=>{let r=new FileReader;r.onload=()=>ok(r.result);r.readAsDataURL(f)});try{let a=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image:q})});let x=await a.json();if(!a.ok)throw Error(x.error||'분석 실패');no.value=x.product_number||'';nm.value=x.product_name||'';rp.value=x.regular_price??'';dc.value=x.sale_discount??'';sp.value=x.sale_price??'';sd.value=x.sale_start||'';ed.value=x.sale_end||'';st.textContent='완료!'}catch(e){st.textContent='오류: '+e.message}}function calc(){let c=+sp.value;if(!c)return alert('현재 판매가를 입력하세요.');let s=(c+2200)/.79,fee=s*.11,p=s-fee-2200-c;res.innerHTML='<div class=c><div>권장 쿠팡 판매가</div><div class=big>'+Math.round(s).toLocaleString()+'원</div><div class=r><span>원가</span><b>'+c.toLocaleString()+'원</b></div><div class=r><span>수수료 11%</span><b>'+Math.round(fee).toLocaleString()+'원</b></div><div class=r><span>배송·포장</span><b>2,200원</b></div><div class=r><span>예상 순이익</span><b>'+Math.round(p).toLocaleString()+'원</b></div></div>'}</script>'''

@app.get("/")
def home():
    return Response(HTML, mimetype="text/html")

@app.post("/analyze")
def analyze():
    try:
        d = request.get_json()
        prompt = """이 코스트코 가격표 사진을 읽어 JSON으로만 답하세요. 키: product_number, product_name, regular_price, sale_discount, sale_price, sale_start, sale_end, is_on_sale. 날짜는 YYYY-MM-DD. 보이지 않는 값은 null 또는 빈 문자열. 정상가, 할인금액, 할인 후 판매가를 정확히 구분하세요."""
        r = client.responses.create(model="gpt-5.6", input=[{"role":"user","content":[{"type":"input_text","text":prompt},{"type":"input_image","image_url":d["image"]}]}])
        text = r.output_text.replace("```json", "").replace("```", "").strip()
        return jsonify(json.loads(text))
    except Exception as e:
        return jsonify(error=str(e)), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
