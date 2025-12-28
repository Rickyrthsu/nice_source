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

    // === 【新增 1】初始化收藏清單 (從瀏覽器讀取) ===
    // 我們使用 Set 來儲存 targetUrl，確保不會重複
    let favorites = new Set(JSON.parse(localStorage.getItem('nice_source_favorites')) || []);

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
            // === 【新增 2】處理「收藏」類別 ===
            let matchCategory = false;
            if (currentCategory === 'all') {
                matchCategory = true;
            } else if (currentCategory === 'favorites') {
                // 如果目前選的是「收藏」，只顯示在 favorites 清單裡的項目
                matchCategory = favorites.has(item.targetUrl);
            } else {
                matchCategory = (item.category === currentCategory);
            }
            
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
        
        // 如果是收藏頁面且沒有資料
        if (currentCategory === 'favorites' && dataArray.length === 0) {
            resultsContainer.innerHTML = '<p style="text-align: center; width: 100%; padding: 20px; color: #777;">你還沒有加入任何收藏喔！點擊卡片右上角的愛心試試看。</p>';
            return;
        }

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
        card.className = `card ${data.category}`; 
        
        // 判斷是否已收藏
        const isLiked = favorites.has(data.targetUrl);
        const heartClass = isLiked ? 'active' : '';
        
        // 設定 Dataset
        const imageUrl = data.imageUrl;
        card.dataset.title = data.title;
        card.dataset.code = data.code || ''; 
        card.dataset.imageUrl = imageUrl; 
        card.dataset.targetUrl = data.targetUrl;
        card.dataset.tags = Array.isArray(data.tags) ? data.tags.join(',') : ''; 
        card.dataset.details = JSON.stringify(data.details || {});

        // === 【新增 3】插入愛心按鈕 HTML ===
        card.innerHTML = `
            <div class="img-container">
                <img src="${imageUrl}" alt="${data.title}" loading="lazy" crossOrigin="anonymous">
                <button class="like-btn ${heartClass}" aria-label="收藏">
                    <span class="like-icon">♥</span>
                </button>
            </div>
            <div class="card-info">
                <h3>${data.title}</h3>
                ${data.code ? `<p>${data.code}</p>` : ''} 
            </div>
        `;
        
        // === 【新增 4】愛心點擊事件 (必須在 card click 之前綁定) ===
        const likeBtn = card.querySelector('.like-btn');
        likeBtn.addEventListener('click', (e) => {
            e.stopPropagation(); // 【非常重要】阻止事件冒泡，這樣才不會觸發 Modal 打開
            
            toggleFavorite(data.targetUrl, likeBtn);
        });

        // 卡片點擊事件 (打開 Modal)
        card.addEventListener('click', () => openModal(data));
        
        resultsContainer.appendChild(card); 
    }

    // === 【新增 5】切換收藏狀態函式 ===
    function toggleFavorite(id, btnElement) {
        if (favorites.has(id)) {
            // 已經收藏 -> 取消收藏
            favorites.delete(id);
            btnElement.classList.remove('active');
            
            // 如果目前正在看「收藏」頁面，直接把這張卡片隱藏，體驗較好
            if (currentCategory === 'favorites') {
                const card = btnElement.closest('.card');
                card.style.display = 'none';
            }
        } else {
            // 沒收藏 -> 加入收藏
            favorites.add(id);
            btnElement.classList.add('active');
        }
        
        // 存回 LocalStorage
        localStorage.setItem('nice_source_favorites', JSON.stringify([...favorites]));
    }

    // === Modal 邏輯 (維持不變) ===
    function openModal(data) {
        modalTitle.textContent = data.title;
        modalImage.src = data.imageUrl; 
        modalLink.href = data.targetUrl;

        modalDetailsContainer.innerHTML = ''; 
        let details = {};
        try {
            details = JSON.parse(data.details); 
        } catch (e) {}
        
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
                if (tagName && !['video','not-found','actor','missav','pornhub'].includes(tagName)) {
                    const tagElement = document.createElement('span');
                    tagElement.className = 'tag';
                    tagElement.textContent = tagName;
                    modalTagsContainer.appendChild(tagElement);
                }
            });
        }
        modal.classList.add('visible');
    }

    modalCloseBtn.addEventListener('click', () => modal.classList.remove('visible'));
    modal.addEventListener('click', (event) => {
        if (event.target === modal) modal.classList.remove('visible');
    });

    // === 手機版左右滑動切換類別 (Swipe Logic) ===
    const categoryOrder = ['all', 'video', 'comic', 'anime', 'porn', 'actor', 'favorites']; // 把 favorites 也加進去
    
    let touchStartX = 0;
    let touchStartY = 0;
    let touchEndX = 0;
    let touchEndY = 0;
    const minSwipeDistance = 100; 

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        handleSwipe();
    }, { passive: true });

    function handleSwipe() {
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY; 

        if (Math.abs(diffY) > Math.abs(diffX)) return;
        if (Math.abs(diffX) < minSwipeDistance) return;

        const currentIndex = categoryOrder.indexOf(currentCategory);
        if (currentIndex === -1) return;

        let nextIndex = currentIndex;

        if (diffX < 0) { // 左滑 (Next)
            if (currentIndex < categoryOrder.length - 1) {
                nextIndex = currentIndex + 1;
            } else {
                nextIndex = 0; 
            }
        } else { // 右滑 (Prev)
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