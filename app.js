document.addEventListener('DOMContentLoaded', () => {

    // === 1. 抓取元素 (不變) ===
    const resultsContainer = document.getElementById('results-container');
    const navButtons = document.querySelectorAll('.nav-btn');
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalLink = document.getElementById('modal-link');

    let globalData = []; 
    
    // === 2. 初始化 (不變) ===
    async function init() {
        console.log('初始化，準備讀取 data.json...');
        try {
            const response = await fetch('data.json', { cache: 'no-cache' });
            if (!response.ok) {
                throw new Error(`無法讀取 data.json! 狀態: ${response.status}`);
            }
            globalData = await response.json();
            console.log('成功讀取 data.json:', globalData);
            renderCards(globalData);
        } catch (error) {
            console.error('初始化失敗:', error);
            resultsContainer.innerHTML = `<p style="color: red; text-align: center;">讀取資料庫 (data.json) 失敗: ${error.message}<br>請檢查 data.json 檔案是否存在於專案根目錄。</p>`;
        }
    }

    // === 3. 篩選邏輯 (不變) ===
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const category = button.dataset.category;
            console.log(`篩選類別: ${category}`);
            if (category === 'all') {
                renderCards(globalData);
            } else {
                const filteredData = globalData.filter(item => item.category === category);
                renderCards(filteredData);
            }
        });
    });

    /**
     * (輔助函式) 渲染一組卡片 (不變)
     */
    function renderCards(dataArray) {
        resultsContainer.innerHTML = '';
        if (dataArray.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center;">這個分類目前沒有資料。</p>';
            return;
        }
        dataArray.forEach(data => {
            addCardToPage(data);
        });
    }

    /**
     * (輔助函式) 建立單一張卡片
     * ===【【【 關鍵修正！】】】===
     */
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer'; 

        // 1. 取得 nhentai 的原始圖片網址 (例如: https://i.nhentai.net/...)
        const originalImageUrl = data.imageUrl;
        
        // 2. 【關鍵！】我們把網址「包」一層圖片代理
        // 我們移除 'https://' 協議頭，因為 weserv 代理需要
        const cleanImageUrl = originalImageUrl.replace(/^https?:\/\//, '');
        const proxyImageUrl = `https://images.weserv.nl/?url=${cleanImageUrl}`;

        // 儲存資料到 dataset (我們還是存「原始」資料，Modal 再來處理)
        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = originalImageUrl; // 存原始的
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = (data.tags || []).join(','); 

        // 填入卡片 HTML
        card.innerHTML = `
            <img src="${proxyImageUrl}" alt="${data.title}" crossOrigin="anonymous">
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} </div>
        `;
        
        resultsContainer.insertAdjacentElement('afterbegin', card); 
    }

    // === 4. Modal 彈窗邏輯 ===
    // ===【【【 關鍵修正！】】】===
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        
        // 【關鍵！】Modal 裡的大圖「也需要」通過代理
        const originalImageUrl = data.imageUrl;
        const cleanImageUrl = originalImageUrl.replace(/^https?:\/\//, '');
        const proxyImageUrl = `https://images.weserv.nl/?url=${cleanImageUrl}`;

        modalTitle.textContent = data.title;
        modalImage.src = proxyImageUrl; // Modal 也使用代理網址
        modalLink.href = data.targetUrl;

        // 處理標籤
        modalTagsContainer.innerHTML = ''; 
        if (data.tags && data.tags.length > 0) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.textContent = tagName;
                modalTagsContainer.appendChild(tagElement);
            });
        }
        modal.classList.add('visible');
    });

    // 關閉 Modal (不變)
    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    // === 5. 執行初始化 (不變) ===
    init();
});
