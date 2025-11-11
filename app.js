document.addEventListener('DOMContentLoaded', () => {

    // (抓取元素... 保持不變)
    const addForm = document.getElementById('add-form');
    const addCodeInput = document.getElementById('add-code-input');
    const searchForm = document.getElementById('search-form');
    const searchCodeInput = document.getElementById('search-code-input');
    const resultsContainer = document.getElementById('results-container');
    const navButtons = document.querySelectorAll('.nav-btn');
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalLink = document.getElementById('modal-link');
    let currentCategory = 'videos';

    // (導覽按鈕邏輯... 保持不變)
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            currentCategory = button.dataset.category;
            console.log(`切換到類別: ${currentCategory}`);
            resultsContainer.innerHTML = ''; 
            if (currentCategory === 'anime') {
                alert('「動漫」欄位的新增邏輯尚未實作');
            }
        });
    });

    // (新增按鈕邏輯... 保持不變)
    addForm.addEventListener('submit', async (event) => {
        event.preventDefault(); 
        const newCode = addCodeInput.value.trim();
        if (!newCode) { alert('請輸入要新增的番號'); return; }
        console.log(`使用者在 [${currentCategory}] 類別下，要求新增: ${newCode}`);
        addCodeInput.value = ''; 

        if (currentCategory === 'comics') {
            await fetchComicData(newCode); 
        } else if (currentCategory === 'videos') {
            alert('「影片」的新增邏輯尚未實作');
        } else if (currentCategory === 'anime') {
            alert('「動漫」的新增邏輯尚未實作');
        }
    });

    
    /**
     * [漫畫] 邏輯：抓取 nhentai 資料
     * * === 超級詳細偵錯版 ===
     */
    async function fetchComicData(code) {
        const rawApiUrl = `https://nhentai.net/api/gallery/${code}`;
        const proxyApiUrl = `https://api.allorigins.win/raw?url=${encodeURIComponent(rawApiUrl)}`;
        
        // 【偵錯 1】印出我們正要抓取的目標網址
        console.log(`[偵錯 1] 準備抓取: ${proxyApiUrl}`);
        
        let response; // 宣告 response 變數
        let dataText; // 宣告 dataText 變數

        try {
            // 【偵錯 2】執行網路請求
            console.log('[偵錯 2] 正在執行 fetch...');
            response = await fetch(proxyApiUrl);

            // 【偵錯 3】印出 HTTP 狀態
            console.log(`[偵錯 3] 收到回應! 狀態: ${response.status} (${response.statusText})`);

            // 【偵錯 4】檢查 HTTP 狀態是否 "ok" (200-299)
            if (!response.ok) {
                // 如果是 404, 500, 503... 就會在這裡出錯
                const errorText = await response.text(); // 試圖讀取錯誤頁面的內容
                console.error(`[偵錯 4.1 - 失敗] 伺服器回應錯誤:`, errorText);
                throw new Error(`HTTP 錯誤! 狀態: ${response.status}. 代理伺服器可能回傳: ${errorText.substring(0, 100)}...`);
            }
            console.log('[偵錯 4] HTTP 狀態 OK (200)');

            // 【偵錯 5】讀取回傳的「純文字」內容
            dataText = await response.text();
            console.log(`[偵錯 5] 收到原始資料 (前 200 字): ${dataText.substring(0, 200)}...`);

            // 【偵錯 6】檢查是否為 "not found"
            if (dataText.includes('does not exist') || response.status === 404) {
                 alert(`錯誤：找不到番號 ${code}`);
                 return;
            }
            console.log('[偵錯 6] 檢查通過，非 "not found"');

            // 【偵錯 7】嘗試把文字解析為 JSON (最容易失敗的地方)
            let data;
            try {
                data = JSON.parse(dataText);
            } catch (jsonError) {
                console.error('[偵錯 7.1 - 致命失敗] JSON 解析失敗!', jsonError);
                console.error('[偵錯 7.2] 導致失敗的原始資料:', dataText);
                throw new Error(`JSON 解析失敗。這代表代理伺服器傳回的不是 JSON，可能是 HTML 錯誤頁面 (例如 "Rate Limit Exceeded" 或 "Service Unavailable")。`);
            }
            console.log('[偵錯 7] JSON 解析成功!', data);

            // 【偵錯 8】解析 JSON 內的資料
            // (使用 ?. 可選串連，避免 data.title 不存在時香G)
            const title = data.title?.pretty || data.title?.english || data.title?.japanese;
            const mediaId = data.media_id;
            const tags = data.tags.map(tag => tag.name);
            const firstPage = data.images.pages[0];
            const pageType = firstPage.t === 'j' ? 'jpg' : 'png';
            const imageUrl = `https://i.nhentai.net/galleries/${mediaId}/1.${pageType}`;
            const targetUrl = `https://nhentai.net/g/${code}/`;
            console.log('[偵錯 8] 成功從 JSON 中取出所有資料');

            // 【偵錯 9】顯示卡片
            addCardToPage({
                title: title,
                code: code,
                imageUrl: imageUrl,
                targetUrl: targetUrl,
                tags: tags
            });
            console.log('[偵錯 9] 成功新增卡片到頁面');
            
            alert(`成功新增：\n${title}`);

        } catch (error) {
            // 【偵錯 10】最終的錯誤捕捉
            console.error('===== 抓取漫畫資料時發生了無法捕捉的錯誤 =====', error);
            
            // 彈出更詳細的錯誤提示
            let alertMessage = '抓取資料失敗，請打開 Console (F12) 查看詳細錯誤。\n\n';
            alertMessage += `錯誤類型: ${error.name}\n`;
            alertMessage += `錯誤訊息: ${error.message}\n\n`;

            if (error.message.includes('Failed to fetch')) {
                alertMessage += '👉 這通常是「網路連線問題」或「代理伺服器 (allorigins) 徹底掛了」。';
            } else if (error.message.includes('JSON 解析失敗')) {
                alertMessage += '👉 代理伺服器傳回了它無法理解的資料 (例如 HTML 錯誤頁)，它可能被 nhentai 封鎖或已過載。\n';
            } else if (error.message.includes('HTTP 錯誤')) {
                alertMessage += '👉 代理伺服器或 nhentai 傳回了 404/500/503 等錯誤狀態碼。\n';
            }

            alert(alertMessage);
        }
    }
    
    // (addCardToPage 函式... 保持不變)
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card'; 
        card.style.cursor = 'pointer'; 

        card.dataset.title = data.title;
        card.dataset.code = data.code;
        card.dataset.imageUrl = data.imageUrl;
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = data.tags.join(','); 

        card.innerHTML = `
            <img src="${data.imageUrl}" alt="${data.title}" crossOrigin="anonymous">
            <div class="card-info">
                <h3>${data.title}</h3>
                <p>${data.code}</p>
            </div>
        `;
        resultsContainer.insertAdjacentElement('afterbegin', card); 
    }

    // (Modal 彈窗邏輯... 保持不變)
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 
        const data = card.dataset;
        modalTitle.textContent = data.title;
        modalImage.src = data.imageUrl;
        modalLink.href = data.targetUrl;
        modalTagsContainer.innerHTML = ''; 
        const tags = data.tags.split(','); 
        tags.forEach(tagName => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.textContent = tagName;
            modalTagsContainer.appendChild(tagElement);
        });
        modal.classList.add('visible');
    });

    modalCloseBtn.addEventListener('click', () => {
        modal.classList.remove('visible');
    });

    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.classList.remove('visible');
        }
    });

    // (查詢邏輯... 保持不變)
    searchForm.addEventListener('submit', (event) => {
        event.preventDefault(); 
        const code = searchCodeInput.value.trim();
        if (!code) { alert('請輸入要查詢的番號'); return; }
        console.log(`使用者在 [${currentCategory}] 類別下查詢: ${code}`);
        addCardToPage({
            title: `[查詢結果] ${code}`,
            code: code,
            imageUrl: 'https://via.placeholder.com/200x200',
            targetUrl: '#',
            tags: ['test', 'search']
        });
        searchCodeInput.value = ''; 
    });
});