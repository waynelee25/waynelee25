<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>匯率轉換計算機</title>
    <!--3.網頁中使用了 5 種不同的 CSS 語法所設計的特效，相關語法敘述皆須置於名稱為 "mystyle.css" 的檔案中-->
    <link rel="stylesheet" ref="C:\Users\user\Desktop\110403038\mystyle.css">
</head>
<body>
    <script>
      //1.使用 JS 設計一個匯率轉換計算機並在網頁中以文字說明運用方式，使用者可以在網頁中輸入台幣金額
      //按下執行計算的按鈕後，網頁上會顯示轉換成美金、歐元、日圓、韓元、澳幣的金額與幣別單位；計算結果呈現的數值至少要顯示到小數點下第 2 位 
      function convert() 
      {
        var sum= parseFloat(document.getElementById("sum").value);
        var exchangeRates = 
          {
          USD: 0.033,   
          EUR: 0.030,   
          JPY: 4.580,   
          KRW: 43.09,  
          AUD: 0.050    
          };
        //5.具備輸入檢查功能，若使用者輸入的內容非有效數值，按下執行計算的按鈕後會跳出警告，並觸發重新開始(reset)功能 
        if (isNaN(sum)) 
          {
            alert("請輸入有效數值！");
            resetForm();
            return;
          } 
        document.getElementById("result").innerHTML =
        "美金 (USD): "+(sum * exchangeRates.USD).toFixed(2)
        +"<br>" +"歐元 (EUR): "+(sum * exchangeRates.EUR).toFixed(2)
        +"<br>" +"日圓 (JPY): "+(sum * exchangeRates.JPY).toFixed(2)
        +"<br>" +"韓元 (KRW): "+(sum * exchangeRates.KRW).toFixed(2)
        +"<br>" +"澳幣 (AUD): "+(sum * exchangeRates.AUD).toFixed(2);
      }
      function resetForm() 
      {
        document.getElementById("sum").value = "";
        document.getElementById("result").innerHTML = "";
      }
    </script>
    <h1 class="line1">匯率轉換計算機</h1>

    <p>請輸入台幣金額：</p>
    <input id="sum" type="number">
    <button onclick="convert()">計算金額</button>
    <!--4.具備重新開始(reset)功能的按鈕，讓使用者可以進行全新一輪的計算-->
    <button onclick="resetForm()">重新開始</button>
    <h2>轉換結果：</h2>
    <div id="result"></div>
</body>
</html>
