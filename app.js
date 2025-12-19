document.addEventListener('DOMContentLoaded', () => {

    const resultsContainer = document.getElementById('results-container');
    const navButtons = document.querySelectorAll('.nav-btn');
    const searchInput = document.getElementById('search-input'); 

    // Modal 元素
    const modal = document.getElementById('modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalTitle = document.getElementById('modal-title');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalLink = document.getElementById('modal-link');
    const modalDetailsContainer = document.getElementById('modal-details-container');

    let globalData = []; 
    let currentCategory = 'all'; 
    let currentSearchTerm = '';

    // === 初始化 ===
    async function init() {
        console.log('初始化，準備讀取 data.json...');
        try {
            // 加上時間戳記 timestamp 防止 json 被快取
            const response = await fetch(`data.json?t=${new Date().getTime()}`);
            if (!response.ok) throw new Error(`無法讀取 data.json! 狀態: ${response.status}`);
            
            globalData = await response.json();
            console.log('成功讀取 data.json:', globalData);
            
            applyFilters();
            
        } catch (error) {
            console.error('初始化失敗:', error);
            resultsContainer.innerHTML = `<p style="color: red; text-align: center;">讀取資料庫失敗: ${error.message}</p>`;
        }
    }

    // === 核心邏輯：過濾 ===
    function applyFilters() {
        const term = currentSearchTerm.toLowerCase().trim();

        const filteredData = globalData.filter(item => {
            // 1. 檢查類別 (如果目前是 'actor'，這裡就會只篩選出 actor)
            const matchCategory = (currentCategory === 'all') || (item.category === currentCategory);
            
            if (!term) return matchCategory;

            // 2. 準備搜尋資料
            const title = (item.title || "").toLowerCase();
            const code = (item.code || "").toLowerCase();
            const tags = item.tags || [];
            const actressList = item.details?.actress || [];

            // 3. 開始比對
            const matchTitle = title.includes(term);
            const matchCode = code.includes(term);
            const matchTags = tags.some(tag => tag.toLowerCase().includes(term));
            const matchActress = Array.isArray(actressList) && actressList.some(name => name.toLowerCase().includes(term));

            const matchSearch = matchTitle || matchCode || matchTags || matchActress;

            return matchCategory && matchSearch;
        });

        renderCards(filteredData);
    }

    // === 事件監聽：類別按鈕 ===
    navButtons.forEach(button => {
        button.addEventListener('click', () => {
            navButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            currentCategory = button.dataset.category;
            applyFilters();
        });
    });

    // === 事件監聽：搜尋框 ===
    searchInput.addEventListener('input', (e) => {
        currentSearchTerm = e.target.value;
        applyFilters();
    });

    // === 渲染卡片 ===
    function renderCards(dataArray) {
        resultsContainer.innerHTML = '';
        if (dataArray.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center; width: 100%; padding: 20px;">沒有找到符合的收藏。</p>';
            return;
        }
        dataArray.forEach(data => {
            addCardToPage(data);
        });
    }

    // === 【關鍵修改】建立單張卡片 ===
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer'; 

        const imageUrl = data.imageUrl;

        // 設定 Dataset 供 Modal 使用
        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = imageUrl; 
        card.dataset.targetUrl = data.targetUrl;
        // 確保 tags 是陣列再 join，避免錯誤
        card.dataset.tags = Array.isArray(data.tags) ? data.tags.join(',') : ''; 
        card.dataset.details = JSON.stringify(data.details || {});

        // --- 這裡就是不同的地方！ ---
        if (data.category === 'actor') {
            // [A] 如果是「角色」：使用圓形頭像版型 (記得去 style.css 加我給你的樣式)
            card.innerHTML = `
                <img src="${imageUrl}" alt="${data.title}" class="actor-card-img" loading="lazy" crossOrigin="anonymous">
                <div class="actor-card-title">${data.title}</div>
                <div class="card-info" style="text-align: center;">
                   <small style="color: #aaa;">${data.code}</small>
                </div>
            `;
        } else {
            // [B] 如果是「漫畫/影片/動漫」：使用原本的長方形版型
            card.innerHTML = `
                <img src="${imageUrl}" alt="${data.title}" class="card-image" loading="lazy" crossOrigin="anonymous">
                <div class="card-info">
                    <h3>${data.title}</h3>
                    ${data.code ? `<p>${data.code}</p>` : ''} 
                </div>
            `;
        }
        
        // 改用 appendChild 確保順序是從新到舊 (依照 JSON 順序)
        resultsContainer.appendChild(card); 
    }

    // === Modal 邏輯 ===
    resultsContainer.addEventListener('click', (event) => {
        // 找到被點擊的卡片
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        
        modalTitle.textContent = data.title;
        modalImage.src = data.imageUrl; 
        modalLink.href = data.targetUrl;

        // 處理詳細資訊
        modalDetailsContainer.innerHTML = ''; 
        let details = {};
        try {
            details = JSON.parse(data.details); 
        } catch (e) {
            console.error("解析 details 失敗", e);
        }
        
        const detailMap = {
            'release_date': '發行日期',
            'series': '系列',
            'studio': '發行商',
            'actress': '女優',
            'male_actor': '男優',
            'director': '導演'
        };

        for (const [key, label] of Object.entries(detailMap)) {
            if (details[key] && details[key].length > 0) {
                const value = Array.isArray(details[key]) ? details[key].join(', ') : details[key];
                modalDetailsContainer.innerHTML += `<p><strong>${label}:</strong> ${value}</p>`;
            }
        }

        // 處理標籤
        modalTagsContainer.innerHTML = ''; 
        if (data.tags) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
                // 過濾掉一些系統用的標籤
                if (tagName && tagName !== 'video' && tagName !== 'not-found' && tagName !== 'actor' && tagName !== 'missav' && tagName !== 'pornhub') {
                    const tagElement = document.createElement('span');
                    tagElement.className = 'tag';
                    tagElement.textContent = tagName;
                    modalTagsContainer.appendChild(tagElement);
                }
            });
        }
        modal.classList.add('visible');
    });

    // 關閉 Modal
    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    init();
});