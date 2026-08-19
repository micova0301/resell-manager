from flask import Flask, Response

app = Flask(__name__)

HTML = r'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<title>리셀 매니저 AI</title>

<script src="https://cdn.jsdelivr.net/npm/tesseract.js@5/dist/tesseract.min.js"></script>

<style>
body{
    font-family:system-ui,sans-serif;
    background:#f5f6f8;
    margin:0;
}

.w{
    max-width:720px;
    margin:auto;
    padding:16px;
}

h1{
    font-size:32px;
}

.c{
    background:white;
    border-radius:16px;
    padding:16px;
    margin:12px 0;
    box-shadow:0 2px 12px #0001;
}

.g{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:10px;
}

button{
    font-size:17px;
    padding:14px;
    border-radius:12px;
    border:1px solid #ddd;
    background:white;
    font-weight:800;
}

.main{
    width:100%;
    margin-top:12px;
    background:#111;
    color:white;
    border:0;
}

.preview{
    display:none;
    margin-top:12px;
}

.preview img{
    width:100%;
    max-height:380px;
    object-fit:contain;
    border-radius:12px;
}

.status{
    background:#f1f3f5;
    padding:12px;
    border-radius:10px;
    margin-top:12px;
}

label{
    display:block;
    font-size:14px;
    font-weight:700;
    margin-top:14px;
    margin-bottom:6px;
}

input{
    width:100%;
    box-sizing:border-box;
    padding:12px;
    border:1px solid #ddd;
    border-radius:10px;
    font-size:17px;
}

.result{
    margin-top:15px;
    padding:15px;
    background:#f1f3f5;
    border-radius:12px;
}

.big{
    font-size:30px;
    font-weight:900;
}

.row{
    display:flex;
    justify-content:space-between;
    margin:8px 0;
}

.raw{
    display:none;
    white-space:pre-wrap;
    background:#eee;
    padding:12px;
    border-radius:10px;
    font-size:13px;
    margin-top:12px;
}
</style>
</head>

<body>

<div class="w">

<h1>리셀 매니저 AI</h1>

<div class="c">

<div class="g">

<button id="cameraBtn">📷 가격표 촬영</button>

<button id="galleryBtn">🖼️ 사진 불러오기</button>

</div>

<input
    id="cameraInput"
    type="file"
    accept="image/*"
    capture="environment"
    hidden
>

<input
    id="galleryInput"
    type="file"
    accept="image/*"
    hidden
>

<div class="preview" id="preview">
    <img id="previewImage">
</div>

<button class="main" id="ocrButton">
    ⚡ 빠른 OCR로 읽기
</button>

<div class="status" id="status">
    가격표 사진을 선택하세요.
</div>

<label>상품번호</label>
<input id="productNumber">

<label>상품명</label>
<input id="productName">

<label>정상가</label>
<input id="regularPrice" type="number">

<label>할인금액</label>
<input id="discount" type="number">

<label>현재 판매가</label>
<input id="salePrice" type="number">

<label>세일 시작일</label>
<input id="saleStart" type="date">

<label>세일 종료일</label>
<input id="saleEnd" type="date">

<button class="main" id="calculateButton">
    💰 권장 판매가 계산
</button>

<div id="result"></div>

<div class="raw" id="rawText"></div>

</div>

</div>

<script>

let selectedFile = null;

const cameraBtn = document.getElementById("cameraBtn");
const galleryBtn = document.getElementById("galleryBtn");

const cameraInput = document.getElementById("cameraInput");
const galleryInput = document.getElementById("galleryInput");

const preview = document.getElementById("preview");
const previewImage = document.getElementById("previewImage");

const ocrButton = document.getElementById("ocrButton");
const statusBox = document.getElementById("status");

const productNumber = document.getElementById("productNumber");
const productName = document.getElementById("productName");
const regularPrice = document.getElementById("regularPrice");
const discount = document.getElementById("discount");
const salePrice = document.getElementById("salePrice");

const saleStart = document.getElementById("saleStart");
const saleEnd = document.getElementById("saleEnd");

const resultBox = document.getElementById("result");
const rawText = document.getElementById("rawText");

cameraBtn.onclick = function(){
    cameraInput.click();
};

galleryBtn.onclick = function(){
    galleryInput.click();
};

cameraInput.onchange = function(){
    handleFile(this.files[0]);
};

galleryInput.onchange = function(){
    handleFile(this.files[0]);
};

function handleFile(file){

    if(!file){
        return;
    }

    selectedFile = file;

    previewImage.src = URL.createObjectURL(file);

    preview.style.display = "block";

    statusBox.textContent = "사진 준비 완료. OCR 버튼을 눌러주세요.";
}

function money(value){

    if(!value){
        return "";
    }

    const cleaned = String(value).replace(/[^\d]/g,"");

    if(!cleaned){
        return "";
    }

    return Number(cleaned);
}

function findPrices(text){

    const prices = [];

    const pattern =
        /(?:₩|￦)?\s*\d{1,3}(?:[,\s]\d{3})+(?:\s*원)?/g;

    let match;

    while((match = pattern.exec(text)) !== null){

        const start = match.index;

        const before =
            text.slice(Math.max(0, start - 5), start);

        /*
         -6,000원처럼 할인금액 앞에
         마이너스가 붙은 숫자는 가격에서 제외
        */

        if(/-\s*$/.test(before)){
            continue;
        }

        const number = money(match[0]);

        if(
            number >= 1000 &&
            number <= 10000000 &&
            !prices.includes(number)
        ){
            prices.push(number);
        }
    }

    return prices;
}

function findProductNumber(text){

    const match =
        text.match(/(?:^|\D)(\d{6})(?:\D|$)/);

    return match ? match[1] : "";
}

function findDates(text){

    const result = [];

    const matches =
        text.match(
            /20\d{2}\s*[\/.\-]\s*\d{1,2}\s*[\/.\-]\s*\d{1,2}/g
        ) || [];

    for(const item of matches){

        const cleaned =
            item
            .replace(/\s/g,"")
            .replace(/\./g,"-")
            .replace(/\//g,"-");

        const parts = cleaned.split("-");

        if(parts.length === 3){

            const date =
                parts[0] + "-" +
                String(parts[1]).padStart(2,"0") + "-" +
                String(parts[2]).padStart(2,"0");

            if(!result.includes(date)){
                result.push(date);
            }
        }
    }

    return result;
}

function findDiscount(text){

    const match =
        text.match(/-\s*([\d,]+)\s*원?/);

    return match ? money(match[1]) : "";
}

function findProductName(text){

    const lines = text
        .split(/\n/)
        .map(x => x.trim())
        .filter(x => x.length >= 2);

    const idx = lines.findIndex(
        x => /^\d{6}$/.test(x)
    );

    if(idx === -1){
        return "";
    }

    const candidates = [];

    for(let i = idx + 1; i < Math.min(idx + 8, lines.length); i++){

        const line = lines[i];

        // 가격, 날짜, 할인금액 등은 제외
        if(
            /원|할인|행사|20\d{2}|^\d+$|^\d+[,.]\d+$/
                .test(line)
        ){
            continue;
        }

        candidates.push(line);
    }

    // 한글이 포함된 상품명을 우선
    const koreanLines =
        candidates.filter(
            x => /[가-힣]/.test(x)
        );

    if(koreanLines.length >= 2){

        const first =
            candidates.find(
                x => /[가-힣]/.test(x)
            );

        const second =
            koreanLines.find(
                x => x !== first
            );

        return second
            ? first + " " + second
            : first;
    }

    if(koreanLines.length === 1){
        return koreanLines[0];
    }

    return candidates
        .slice(0, 2)
        .join(" ");
}
async function fileToJpeg(file){

    const bitmap = await createImageBitmap(file);

    const canvas = document.createElement("canvas");

    const scale = 2;

    canvas.width = bitmap.width * scale;
    canvas.height = bitmap.height * scale;

    const ctx = canvas.getContext("2d");

    ctx.drawImage(
        bitmap,
        0,
        0,
        canvas.width,
        canvas.height
    );

    const imageData =
        ctx.getImageData(
            0,
            0,
            canvas.width,
            canvas.height
        );

    const data = imageData.data;

    for(let i = 0; i < data.length; i += 4){

        const gray =
            0.299 * data[i] +
            0.587 * data[i + 1] +
            0.114 * data[i + 2];

        data[i] = gray;
        data[i + 1] = gray;
        data[i + 2] = gray;
    }

    ctx.putImageData(imageData, 0, 0);

    return canvas;
}
ocrButton.onclick = async function(){

    if(!selectedFile){

        alert("먼저 가격표 사진을 선택하세요.");

        return;
    }

    ocrButton.disabled = true;

    statusBox.textContent =
        "🔍 OCR 엔진을 준비하고 있습니다...";

    try{

        const result =
            await Tesseract.recognize(
                await fileToJpeg(selectedFile),
                "kor+eng",
                {
                    logger: function(message){

                        if(
                            message.status ===
                            "recognizing text"
                        ){

                            const percent =
                                Math.round(
                                    (message.progress || 0) * 100
                                );

                            statusBox.textContent =
                                "🔍 가격표 읽는 중... " +
                                percent + "%";
                        }
                    }
                }
            );

        const text =
            result.data.text || "";

        rawText.style.display = "block";

        rawText.textContent =
            "OCR 원문\n\n" + text;

        const number =
            findProductNumber(text);

const name = findProductName(text);

const dates = findDates(text);

const discountAmount = findDiscount(text);

/* 가격표 전용 가격 추출 */

const normalizedText =
    text
        .replace(/(\d{1,3})[,.]\s*\n?\s*(\d{3})/g, "$1,$2")
        .replace(/\n/g, " ");

const priceMatches =
    [...normalizedText.matchAll(/\d{1,3}(?:[,.]\d{3})+/g)];

const prices = [];

for(const match of priceMatches){

    const number = Number(
        match[0].replace(/,/g, "")
    );

    const before =
        normalizedText.slice(
            Math.max(0, match.index - 3),
            match.index
        );

    // 할인금액(-6,000원)은 제외
    if(/-\s*$/.test(before)){
        continue;
    }

    if(
        number >= 1000 &&
        number <= 10000000 &&
        !prices.includes(number)
    ){
        prices.push(number);
    }
}

prices.sort((a,b) => b-a);

productNumber.value = number;
productName.value = name;

if(prices.length >= 2){

    regularPrice.value = prices[0];
    salePrice.value = prices[1];

    if(discountAmount){
        discount.value = discountAmount;
    }

}else if(prices.length === 1){

    regularPrice.value = prices[0];
    salePrice.value = prices[0];
    discount.value = "";

}

        /*
         세일기간이 있는 경우만 날짜 입력
        */

        if(dates.length >= 2){

            saleStart.value =
                dates[0];

            saleEnd.value =
                dates[1];

        }else{

            saleStart.value = "";
            saleEnd.value = "";
        }

        statusBox.textContent =
            "✅ OCR 완료! 내용을 확인해주세요.";

    }
    catch(error){

        console.error(error);

        statusBox.textContent =
            "❌ OCR 오류: " +
            error.message;
    }

    ocrButton.disabled = false;
};

document
.getElementById("calculateButton")
.onclick = function(){

    const cost =
        Number(salePrice.value);

    if(!cost){

        alert("현재 판매가를 입력하세요.");

        return;
    }

    /*
     임시 테스트용 판매가 계산식.
     나중에 실제 판매 채널별 수수료를
     따로 설정할 수 있게 만들 수 있음.
    */

    const recommended =
        (cost + 2200) / 0.79;

    const fee =
        recommended * 0.11;

    const profit =
        recommended -
        fee -
        2200 -
        cost;

    resultBox.innerHTML = `

        <div class="result">

            <div>권장 판매가</div>

            <div class="big">
                ${Math.round(recommended).toLocaleString()}원
            </div>

            <div class="row">
                <span>매입/원가</span>
                <b>
                    ${cost.toLocaleString()}원
                </b>
            </div>

            <div class="row">
                <span>예상 수수료</span>
                <b>
                    ${Math.round(fee).toLocaleString()}원
                </b>
            </div>

            <div class="row">
                <span>배송·포장</span>
                <b>2,200원</b>
            </div>

            <div class="row">
                <span>예상 순이익</span>
                <b>
                    ${Math.round(profit).toLocaleString()}원
                </b>
            </div>

        </div>
    `;
};

</script>

</body>
</html>
'''

@app.get("/")
def home():
    return Response(HTML, mimetype="text/html")


if __name__ == "__main__":

    import os

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
