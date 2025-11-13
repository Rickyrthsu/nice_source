document.addEventListener('DOMContentLoaded', () => {

    // === 1. 抓取元素 (新增 modal-details-container) ===
    const resultsContainer = document.getElementById('results-container');
    const navButtons = document.querySelectorAll('.nav-btn');
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalLink = document.getElementById('modal-link');
    
    // (我們還是抓取它，只是不去用它)
    const modalDetailsContainer = document.getElementById('modal-details-container');

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
     * ===【【【 關鍵修正：儲存 details 】】】===
     */
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer'; 

        const imageUrl = data.imageUrl;

        // 儲存資料到 dataset 
        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = imageUrl; 
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = (data.tags || []).join(','); 
        
        // 【【【 關鍵！】】】 我們還是儲存「空的」 details
        card.dataset.details = JSON.stringify(data.details || {});

        // 填入卡片 HTML (不變)
        card.innerHTML = `
            <img src="${imageUrl}" alt="${data.title}" crossOrigin="anonymous">
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} </div>
        `;
        
        resultsContainer.insertAdjacentElement('afterbegin', card); 
    }

    // === 4. Modal 彈窗邏輯 ===
    // ===【【【 關鍵修正：移除 details 顯示 】】】===
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        const imageUrl = data.imageUrl;

        // 1. (不變) 填入基本資料
        modalTitle.textContent = data.title;
        modalImage.src = imageUrl; 
        modalLink.href = data.targetUrl;

        // 2. 【【【 移除！】】】 我們不再顯示「詳細資料」
        modalDetailsContainer.innerHTML = ''; // 永遠保持清空

        // 3. (不變) 處理「標籤」
        modalTagsContainer.innerHTML = ''; 
        if (data.tags && data.tags.length > 0) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
                // (我們把 "video" 這個內部標籤過濾掉，不用顯示)
                if (tagName && tagName !== 'video' && tagName !== 'not-found') {
                    const tagElement = document.createElement('span');
                    tagElement.className = 'tag';
                    tagElement.textContent = tagName;
                    modalTagsContainer.appendChild(tagElement);
                }
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