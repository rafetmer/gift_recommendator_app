const API_BASE = "http://localhost:8000/api";

const state = {
    questions: [],
    currentStep: 0,
    answers: {},
    budget: 0  // 0 = no limit
};

const dom = {
    hero: document.getElementById('hero-header'),
    progressBar: document.getElementById('progress-bar-container'),
    progressFill: document.getElementById('progress-fill'),
    progressLabel: document.getElementById('progress-label'),
    wizardSection: document.getElementById('wizard-section'),
    stepContainer: document.getElementById('step-container'),
    prevBtn: document.getElementById('prev-btn'),
    nextBtn: document.getElementById('next-btn'),
    budgetSection: document.getElementById('budget-section'),
    budgetSlider: document.getElementById('budget-slider'),
    budgetValue: document.getElementById('budget-value'),
    submitBtn: document.getElementById('submit-btn'),
    loader: document.getElementById('loader'),
    loaderDetail: document.getElementById('loader-detail'),
    resultsSection: document.getElementById('results-section'),
    resultsGrid: document.getElementById('results-grid'),
    resultsCount: document.getElementById('results-count'),
    restartBtn: document.getElementById('restart-btn')
};

// Strip "(Algoritma: ...)" from display text so users never see developer tags
function cleanDisplayText(raw) {
    return raw.replace(/\s*\(Algoritma:.*?\)/g, '').trim();
}

// INIT
async function init() {
    try {
        const res = await fetch(`${API_BASE}/questions`);
        state.questions = await res.json();
        showStep(0);
        dom.progressBar.classList.remove('hidden');
    } catch (err) {
        console.error("API not reachable:", err);
        dom.stepContainer.innerHTML = `
            <div class="empty-state">
                <span>⚠️</span>
                <p>API sunucusuna bağlanılamadı.<br>Lütfen terminalde <code>uvicorn api.main:app</code> komutunu çalıştırın.</p>
            </div>`;
    }
}

// STEP RENDERING
function showStep(idx) {
    state.currentStep = idx;
    const q = state.questions[idx];
    if (!q) return;

    const isMulti = q.title.toLowerCase().includes("temel ilgi alanları");
    const total = state.questions.length;

    // Progress
    const pct = ((idx + 1) / (total + 1)) * 100; // +1 for budget step
    dom.progressFill.style.width = pct + '%';
    dom.progressLabel.textContent = `Soru ${idx + 1} / ${total}`;

    // Render
    dom.stepContainer.innerHTML = `
        <h3 class="step-title">${cleanDisplayText(q.title)}</h3>
        <p class="step-subtitle">${isMulti ? 'Birden fazla seçebilirsin.' : 'Bir seçenek seç.'}</p>
        <div class="options-grid" id="current-grid">
            ${q.options.map(opt => {
                const display = cleanDisplayText(opt);
                const isSelected = (state.answers[q.id] || []).includes(opt);
                return `<div class="option-chip ${isSelected ? 'selected' : ''}" 
                             data-val="${opt}" data-multi="${isMulti}">${display}</div>`;
            }).join('')}
        </div>
    `;

    // Click handlers
    document.querySelectorAll('#current-grid .option-chip').forEach(chip => {
        chip.addEventListener('click', () => handleChipClick(chip, q.id));
    });

    // Nav state
    dom.prevBtn.disabled = idx === 0;
    updateNextBtn();

    // Show wizard, hide others
    dom.wizardSection.classList.remove('hidden');
    dom.budgetSection.classList.add('hidden');
}

function handleChipClick(chip, qid) {
    const val = chip.dataset.val;
    const isMulti = chip.dataset.multi === "true";
    const grid = document.getElementById('current-grid');

    if (isMulti) {
        chip.classList.toggle('selected');
        if (!state.answers[qid]) state.answers[qid] = [];
        if (chip.classList.contains('selected')) {
            state.answers[qid].push(val);
        } else {
            state.answers[qid] = state.answers[qid].filter(v => v !== val);
        }
    } else {
        grid.querySelectorAll('.option-chip').forEach(s => s.classList.remove('selected'));
        chip.classList.add('selected');
        state.answers[qid] = [val];
    }
    updateNextBtn();
}

function updateNextBtn() {
    const q = state.questions[state.currentStep];
    const answered = (state.answers[q.id] || []).length > 0;
    dom.nextBtn.disabled = !answered;
}

// NAVIGATION
dom.prevBtn.addEventListener('click', () => {
    if (state.currentStep > 0) showStep(state.currentStep - 1);
});

dom.nextBtn.addEventListener('click', () => {
    if (state.currentStep < state.questions.length - 1) {
        showStep(state.currentStep + 1);
    } else {
        // Last question → show budget
        dom.wizardSection.classList.add('hidden');
        dom.budgetSection.classList.remove('hidden');
        dom.progressFill.style.width = '100%';
        dom.progressLabel.textContent = 'Son adım — Bütçe';
    }
});

// BUDGET
dom.budgetSlider.addEventListener('input', () => {
    const val = parseInt(dom.budgetSlider.value);
    state.budget = val;
    dom.budgetValue.textContent = val === 0 ? 'Sınır Yok' : val.toLocaleString('tr-TR');
    document.querySelectorAll('.preset-chip').forEach(p => p.classList.remove('active'));
});

document.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
        const val = parseInt(chip.dataset.val);
        state.budget = val;
        dom.budgetSlider.value = val;
        dom.budgetValue.textContent = val === 0 ? 'Sınır Yok' : val.toLocaleString('tr-TR');
        document.querySelectorAll('.preset-chip').forEach(p => p.classList.remove('active'));
        chip.classList.add('active');
    });
});

// SUBMIT
dom.submitBtn.addEventListener('click', async () => {
    dom.budgetSection.classList.add('hidden');
    dom.progressBar.classList.add('hidden');
    dom.hero.classList.add('hidden');
    dom.loader.classList.remove('hidden');

    // Animated loader messages
    const messages = [
        "Kişilik profili oluşturuluyor...",
        "100.000+ üründe AI taraması yapılıyor...",
        "Kategori eşleştirme algoritması çalışıyor...",
        "En uygun hediyeler sıralanıyor..."
    ];
    let msgIdx = 0;
    const interval = setInterval(() => {
        msgIdx = (msgIdx + 1) % messages.length;
        dom.loaderDetail.textContent = messages[msgIdx];
    }, 1500);

    // Build payload (keep raw values with Algoritma tags for backend)
    const payloadAnswers = {};
    for (const [k, v] of Object.entries(state.answers)) {
        if (v.length === 1) payloadAnswers[k] = v[0];
        else if (v.length > 1) payloadAnswers[k] = v;
    }

    const payload = {
        answers: payloadAnswers,
        budget: state.budget > 0 ? state.budget : null
    };

    try {
        const res = await fetch(`${API_BASE}/recommend?limit=12`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        clearInterval(interval);

        dom.loader.classList.add('hidden');
        dom.resultsSection.classList.remove('hidden');

        const recs = data.recommendations || [];
        dom.resultsCount.textContent = `${recs.length} ürün bulundu`;
        renderResults(recs);
    } catch (err) {
        clearInterval(interval);
        console.error(err);
        dom.loader.classList.add('hidden');
        dom.budgetSection.classList.remove('hidden');
        alert("Bağlantı hatası. PostgreSQL ve API sunucusunun çalıştığından emin olun.");
    }
});

// RESTART
dom.restartBtn.addEventListener('click', () => {
    state.answers = {};
    state.currentStep = 0;
    state.budget = 0;
    dom.budgetSlider.value = 1000;
    dom.budgetValue.textContent = '1.000';

    dom.resultsSection.classList.add('hidden');
    dom.hero.classList.remove('hidden');
    dom.progressBar.classList.remove('hidden');
    showStep(0);
});

// RENDER RESULTS
function renderResults(products) {
    dom.resultsGrid.innerHTML = '';

    if (!products || products.length === 0) {
        dom.resultsGrid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <span>😔</span>
                <p>Bu kriterlere uygun hediye bulunamadı.<br>Bütçeni artırmayı veya farklı seçenekler denemeyi düşün.</p>
            </div>`;
        return;
    }

    products.forEach((p, idx) => {
        const imgUrl = p.photo_url && p.photo_url.length > 10
            ? p.photo_url
            : 'https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&q=80';

        const matchPct = typeof p.score === 'number' ? (p.score * 100).toFixed(0) : '—';

        const card = document.createElement('a');
        card.href = p.product_url || '#';
        card.target = "_blank";
        card.rel = "noopener";
        card.className = 'product-card';
        card.style.animationDelay = `${idx * 0.06}s`;

        card.innerHTML = `
            <img src="${imgUrl}" alt="${cleanDisplayText(p.title)}" class="product-img"
                 onerror="this.src='https://images.unsplash.com/photo-1549465220-1a8b9238cd48?w=400&q=80'" loading="lazy">
            <div class="product-info">
                <span class="product-brand">${p.brand || 'Premium'}</span>
                <h4 class="product-title">${cleanDisplayText(p.title)}</h4>
                <div class="product-footer">
                    <span class="product-price">${p.price.toLocaleString('tr-TR', {minimumFractionDigits: 2})} ₺</span>
                    <span class="product-score">${matchPct}% Eşleşme</span>
                </div>
                <div class="product-rationale">💡 ${p.rationale || ''}</div>
            </div>
        `;
        dom.resultsGrid.appendChild(card);
    });
}

// Boot
init();
