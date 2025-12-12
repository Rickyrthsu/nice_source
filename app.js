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
            const response = await fetch('data.json', { cache: 'no-cache' });
            if (!response.ok) throw new Error(`無法讀取 data.json! 狀態: ${response.status}`);
            
            globalData = await response.json();
            console.log('成功讀取 data.json:', globalData);
            
            applyFilters();
            
        } catch (error) {
            console.error('初始化失敗:', error);
            resultsContainer.innerHTML = `<p style="color: red; text-align: center;">讀取資料庫失敗: ${error.message}</p>`;
        }
    }

    // === 【【【 核心邏輯：統一過濾函式 (已升級) 】】】 ===
    function applyFilters() {
        const filteredData = globalData.filter(item => {
            // 1. 檢查類別
            const matchCategory = (currentCategory === 'all') || (item.category === currentCategory);
            
            // 2. 檢查搜尋關鍵字 (忽略大小寫)
            const term = currentSearchTerm.toLowerCase().trim();
            
            // 【新增】檢查女優 (安全地讀取 details.actress)
            // 因為漫畫/動漫可能沒有 details，或者 details 裡沒有 actress，所以要用 ?. 和 || []
            const actressList = item.details?.actress || [];
            // 檢查女優列表裡，有沒有任何一個名字包含了搜尋關鍵字
            const matchActress = Array.isArray(actressList) && actressList.some(name => name.toLowerCase().includes(term));

            const matchSearch = 
                !term || // 如果沒輸入關鍵字，就當作符合
                item.title.toLowerCase().includes(term) || // 搜標題
                (item.code && item.code.toLowerCase().includes(term)) || // 搜番號
                (item.tags && item.tags.some(tag => tag.toLowerCase().includes(term))) || // 搜標籤
                matchActress; // 【【【 關鍵！加入搜女優 】】】

            // 兩個條件都要符合
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

    // === 渲染卡片 (保持不變) ===
    function renderCards(dataArray) {
        resultsContainer.innerHTML = '';
        if (dataArray.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center; width: 100%;">沒有找到符合的收藏。</p>';
            return;
        }
        dataArray.forEach(data => {
            addCardToPage(data);
        });
    }

    // === 建立單張卡片 (保持不變) ===
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.cursor = 'pointer'; 

        const imageUrl = data.imageUrl;

        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = imageUrl; 
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = (data.tags || []).join(','); 
        card.dataset.details = JSON.stringify(data.details || {});

        card.innerHTML = `
            <img src="${imageUrl}" alt="${data.title}" crossOrigin="anonymous">
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} </div>
        `;
        
        resultsContainer.insertAdjacentElement('afterbegin', card); 
    }

    // === Modal 邏輯 (保持不變) ===
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        const imageUrl = data.imageUrl;

        modalTitle.textContent = data.title;
        modalImage.src = imageUrl; 
        modalLink.href = data.targetUrl;

        modalDetailsContainer.innerHTML = ''; 
        const details = JSON.parse(data.details); 
        
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

        modalTagsContainer.innerHTML = ''; 
        if (data.tags && data.tags.length > 0) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
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

    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    init();
});