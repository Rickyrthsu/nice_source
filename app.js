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
            const matchCategory = (currentCategory === 'all') || (item.category === currentCategory);
            
            if (!term) return matchCategory;

            const title = (item.title || "").toLowerCase();
            const code = (item.code || "").toLowerCase();
            const tags = item.tags || [];
            const actressList = item.details?.actress || [];

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
            
            window.scrollTo({ top: 0, behavior: 'smooth' });
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

    // === 建立單張卡片 ===
    function addCardToPage(data) {
        const card = document.createElement('div');
        card.className = `card ${data.category}`; 
        card.style.cursor = 'pointer'; 

        const imageUrl = data.imageUrl;

        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = imageUrl; 
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = Array.isArray(data.tags) ? data.tags.join(',') : ''; 
        card.dataset.details = JSON.stringify(data.details || {});

        card.innerHTML = `
            <div class="img-container">
                <img src="${imageUrl}" alt="${data.title}" loading="lazy" crossOrigin="anonymous">
            </div>
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} 
            </div>
        `;
        
        resultsContainer.appendChild(card); 
    }

    // === Modal 邏輯 ===
    resultsContainer.addEventListener('click', (event) => {
        const card = event.target.closest('.card');
        if (!card) return; 

        const data = card.dataset;
        
        modalTitle.textContent = data.title;
        modalImage.src = data.imageUrl; 
        modalLink.href = data.targetUrl;

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

        modalTagsContainer.innerHTML = ''; 
        if (data.tags) {
            const tags = data.tags.split(','); 
            tags.forEach(tagName => {
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

    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    // =========================================================
    // === 【改良版】手機版左右滑動切換類別 (Swipe Logic) ===
    // =========================================================
    
    const categoryOrder = ['all', 'video', 'comic', 'anime', 'porn', 'actor'];
    
    let touchStartX = 0;
    let touchStartY = 0; // 新增：紀錄垂直位置
    let touchEndX = 0;
    let touchEndY = 0;   // 新增：紀錄垂直位置
    
    // 【修改 1】提高門檻：從 50 改成 100 (需要滑比較長才算)
    const minSwipeDistance = 100; 

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY; // 記錄垂直起點
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY; // 記錄垂直終點
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY; // 計算垂直距離

        // 【修改 2】垂直檢測：如果你往下滑的距離 > 往左右滑的距離，就當作是捲動，忽略切換
        if (Math.abs(diffY) > Math.abs(diffX)) return;

        // 如果滑動距離太短，就不理會
        if (Math.abs(diffX) < minSwipeDistance) return;

        const currentIndex = categoryOrder.indexOf(currentCategory);
        if (currentIndex === -1) return;

        let nextIndex = currentIndex;

        if (diffX < 0) {
            // 左滑 (Next)
            if (currentIndex < categoryOrder.length - 1) {
                nextIndex = currentIndex + 1;
            } else {
                nextIndex = 0; 
            }
        } else {
            // 右滑 (Prev)
            if (currentIndex > 0) {
                nextIndex = currentIndex - 1;
            } else {
                nextIndex = categoryOrder.length - 1; 
            }
        }

        if (nextIndex !== currentIndex) {
            const nextCategory = categoryOrder[nextIndex];
            const targetBtn = document.querySelector(`.nav-btn[data-category="${nextCategory}"]`);
            if (targetBtn) {
                targetBtn.click();
            }
        }
    }

    init();
});