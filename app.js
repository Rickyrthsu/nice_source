document.addEventListener('DOMContentLoaded', () => {

    // === 1. 抓取元素 (已移除 add/search form) ===
    const resultsContainer = document.getElementById('results-container');
    const navButtons = document.querySelectorAll('.nav-btn');
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalLink = document.getElementById('modal-link');

    let globalData = []; // 用來儲存從 data.json 抓來的「所有」資料
    
    // === 2. 全新邏輯：初始化，讀取 data.json ===
    async function init() {
        console.log('初始化，準備讀取 data.json...');
        try {
            // fetch 我們的資料庫
            // cache: 'no-cache' 確保我們每次都抓到最新的，不會被瀏覽器快取
            const response = await fetch('data.json', { cache: 'no-cache' });
            
            if (!response.ok) {
                // 如果 fetch 失敗 (例如 404 Not Found)
                throw new Error(`無法讀取 data.json! 狀態: ${response.status}`);
            }
            
            globalData = await response.json();
            console.log('成功讀取 data.json:', globalData);
            
            // 預設顯示「全部」
            renderCards(globalData);

        } catch (error) {
            console.error('初始化失敗:', error);
            resultsContainer.innerHTML = `<p style="color: red; text-align: center;">讀取資料庫 (data.json) 失敗: ${error.message}<br>請檢查 data.json 檔案是否存在於專案根目錄。</p>`;
        }
    }

    // === 3. 全新邏輯：渲染卡片 (從 render 改成 filter) ===
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            // 處理按鈕 active 狀態
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            const category = button.dataset.category;
            console.log(`篩選類別: ${category}`);

            if (category === 'all') {
                // 顯示全部
                renderCards(globalData);
            } else {
                // 執行篩選
                const filteredData = globalData.filter(item => item.category === category);
                renderCards(filteredData);
            }
        });
    });

    /**
     * (輔助函式) 渲染一組卡片到畫面上
     */
    function renderCards(dataArray) {
        // 先清空
        resultsContainer.innerHTML = '';
        
        if (dataArray.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center;">這個分類目前沒有資料。</p>';
            return;
        }

        // 重新渲染 (注意：dataArray 可能是反的，所以我們用 forEach)
        // data.json 是新->舊，我們 insertAdjacentElement('afterbegin') 會變 舊->新
        // 沒關係，如果 data.json 本身就是新->舊，這樣顯示是正確的。
        dataArray.forEach(data => {
            addCardToPage(data);
        });
    }

    /**
     * (輔助函式) 建立單一張卡片
     */
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer'; 

        // 儲存資料到 dataset
        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; // code 可能不存在 (例如動漫)
        card.dataset.imageUrl = data.imageUrl;
        card.dataset.targetUrl = data.targetUrl;
        // 處理 tags: (動漫/影片 可能沒有 tags)
        card.dataset.tags = (data.tags || []).join(','); 

        // 填入卡片 HTML
        card.innerHTML = `
            <img src="${data.imageUrl}" alt="${data.title}" crossOrigin="anonymous">
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} </div>
        `;
        
        // 插入到最前面 (這樣新資料會顯示在最上面)
        resultsContainer.insertAdjacentElement('afterbegin', card); 
    }

    // === 4. Modal 彈窗邏輯 ===
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        modalTitle.textContent = data.title;
        modalImage.src = data.imageUrl;
        modalLink.href = data.targetUrl;

        // 處理標籤
        modalTagsContainer.innerHTML = ''; // 先清空
        if (data.tags && data.tags.length > 0) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.textContent = tagName;
                modalTagsContainer.appendChild(tagElement);
            });
        }
        // 顯示 Modal
        modal.classList.add('visible');
    });

    // 關閉 Modal (點擊 X)
    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));

    // 關閉 Modal (點擊黑色背景)
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    // === 5. 執行初始化 ===
    init();
});