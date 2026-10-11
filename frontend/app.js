let currentMethod = 'PT01';
let currentProfile = {
  hoTen: 'Phạm Minh Anh',
  phuongThuc: 'PT01',
  maToHop: 'A01',
  tenToHop: 'A01 (Toán, Vật lý, Tiếng Anh)',
  tongDiem: 24.50,
  diemMon1: 8.5,
  diemMon2: 8.0,
  diemMon3: 8.0,
  gpaHocBa: 8.6
};

let rawRecommendations = [];
let displayedRecommendations = [];
let savedWishlist = [];
let currentToken = localStorage.getItem('tuyensinh_token') || '';
let currentUser = null;

const COMBINATION_LABELS = {
  'A00': ['Toán', 'Vật lý', 'Hóa học'],
  'A01': ['Toán', 'Vật lý', 'Tiếng Anh'],
  'A02': ['Toán', 'Vật lý', 'Sinh học'],
  'B00': ['Toán', 'Hóa học', 'Sinh học'],
  'B08': ['Toán', 'Sinh học', 'Tiếng Anh'],
  'C00': ['Ngữ văn', 'Lịch sử', 'Địa lý'],
  'C01': ['Ngữ văn', 'Toán', 'Vật lý'],
  'C02': ['Ngữ văn', 'Toán', 'Hóa học'],
  'C19': ['Ngữ văn', 'Lịch sử', 'GDCD'],
  'D01': ['Toán', 'Ngữ văn', 'Tiếng Anh'],
  'D07': ['Toán', 'Hóa học', 'Tiếng Anh'],
  'D09': ['Toán', 'Lịch sử', 'Tiếng Anh'],
  'D10': ['Toán', 'Địa lý', 'Tiếng Anh'],
  'D14': ['Ngữ văn', 'Lịch sử', 'Tiếng Anh']
};

const UNI_AVATARS = {
  'BKA': { color: '#dc2626', text: 'BKA' },
  'QHI': { color: '#0284c7', text: 'VNU' },
  'KHA': { color: '#059669', text: 'NEU' },
  'NTH': { color: '#e11d48', text: 'FTU' },
  'DTT': { color: '#0284c7', text: 'PTIT' },
  'UEL': { color: '#0369a1', text: 'UEL' },
  'DEFAULT': { color: '#0ea5e9', text: 'UNI' }
};

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initMethodToggles();
  initCombinationSelect();
  initFormActions();
  initAuthModal();
  loadInitialState();
});

function initNavigation() {
  const navBtns = document.querySelectorAll('.nav-item-btn[data-target]');
  navBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      const targetView = btn.getAttribute('data-target');
      switchView(targetView);
    });
  });

  const brandLink = document.getElementById('brand-home-link');
  if (brandLink) {
    brandLink.addEventListener('click', (e) => {
      e.preventDefault();
      switchView('view-home');
    });
  }

  const crumbHomes = document.querySelectorAll('.btn-crumb-home');
  crumbHomes.forEach(crumb => {
    crumb.addEventListener('click', (e) => {
      e.preventDefault();
      switchView('view-home');
    });
  });

  const heroThpt = document.getElementById('hero-btn-thpt');
  if (heroThpt) {
    heroThpt.addEventListener('click', () => {
      setMethodChoice('PT01');
      switchView('view-profile');
    });
  }

  const heroHocba = document.getElementById('hero-btn-hocba');
  if (heroHocba) {
    heroHocba.addEventListener('click', () => {
      setMethodChoice('PT02');
      switchView('view-profile');
    });
  }

  const cardFeatureExplore = document.getElementById('card-feature-explore');
  if (cardFeatureExplore) {
    cardFeatureExplore.addEventListener('click', () => {
      switchView('view-explore');
      loadExploreData();
    });
  }

  const cardFeaturePredict = document.getElementById('card-feature-predict');
  if (cardFeaturePredict) {
    cardFeaturePredict.addEventListener('click', () => {
      switchView('view-profile');
    });
  }

  const cardFeatureSort = document.getElementById('card-feature-sort');
  if (cardFeatureSort) {
    cardFeatureSort.addEventListener('click', async () => {
      if (currentToken && savedWishlist.length === 0) {
        await loadSavedWishlistFromServer();
      }
      switchView('view-wishlist');
      renderWishlistView();
    });
  }

  const btnEditProfile = document.getElementById('btn-edit-student-profile');
  if (btnEditProfile) {
    btnEditProfile.addEventListener('click', () => {
      switchView('view-profile');
    });
  }

  const btnBackResults = document.getElementById('btn-back-to-results');
  if (btnBackResults) {
    btnBackResults.addEventListener('click', () => {
      switchView('view-results');
    });
  }
}

function switchView(viewId) {
  const views = document.querySelectorAll('.page-view');
  views.forEach(v => v.classList.remove('active'));

  const activeView = document.getElementById(viewId);
  if (activeView) {
    activeView.classList.add('active');
  }

  const navBtns = document.querySelectorAll('.nav-item-btn[data-target]');
  navBtns.forEach(btn => {
    if (btn.getAttribute('data-target') === viewId) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  window.scrollTo({ top: 0, behavior: 'smooth' });

  if (viewId === 'view-explore') {
    loadExploreData();
  } else if (viewId === 'view-wishlist') {
    if (currentToken && savedWishlist.length === 0) {
      loadSavedWishlistFromServer();
    } else {
      renderWishlistView();
    }
  }
}

function initMethodToggles() {
  const radioThpt = document.getElementById('radio-method-thpt');
  const radioHocba = document.getElementById('radio-method-hocba');

  if (radioThpt) {
    radioThpt.addEventListener('click', () => {
      setMethodChoice('PT01');
    });
  }

  if (radioHocba) {
    radioHocba.addEventListener('click', () => {
      setMethodChoice('PT02');
    });
  }
}

function setMethodChoice(methodCode) {
  currentMethod = methodCode;
  const radioThpt = document.getElementById('radio-method-thpt');
  const radioHocba = document.getElementById('radio-method-hocba');
  const cThpt = document.getElementById('container-inputs-thpt');
  const cHocba = document.getElementById('container-inputs-hocba');
  const step2Title = document.getElementById('step2-title-label');
  const step2Desc = document.getElementById('step2-desc-label');

  if (methodCode === 'PT01') {
    if (radioThpt) radioThpt.classList.add('selected');
    if (radioHocba) radioHocba.classList.remove('selected');
    if (cThpt) cThpt.style.display = 'block';
    if (cHocba) cHocba.style.display = 'none';
    if (step2Title) step2Title.textContent = 'Nhập thông tin điểm thi THPT';
    if (step2Desc) step2Desc.textContent = 'Nhập điểm các môn trong tổ hợp xét tuyển của bạn.';
  } else {
    if (radioThpt) radioThpt.classList.remove('selected');
    if (radioHocba) radioHocba.classList.add('selected');
    if (cThpt) cThpt.style.display = 'none';
    if (cHocba) cHocba.style.display = 'block';
    if (step2Title) step2Title.textContent = 'Nhập thông tin điểm học bạ';
    if (step2Desc) step2Desc.textContent = 'Nhập điểm trung bình học bạ hoặc điểm tổ hợp xét tuyển theo học bạ.';
  }
}

function initCombinationSelect() {
  const selectComb = document.getElementById('select-active-combination');
  if (selectComb) {
    selectComb.addEventListener('change', () => {
      const val = selectComb.value;
      updateSubjectLabels(val);
    });
  }
}

function updateSubjectLabels(code) {
  const subjects = COMBINATION_LABELS[code] || ['Môn 1', 'Môn 2', 'Môn 3'];
  const l1 = document.getElementById('label-mon1');
  const l2 = document.getElementById('label-mon2');
  const l3 = document.getElementById('label-mon3');

  if (l1) l1.textContent = subjects[0];
  if (l2) l2.textContent = subjects[1];
  if (l3) l3.textContent = subjects[2];
}

function initFormActions() {
  const btnSubmit = document.getElementById('btn-submit-recommendation');
  if (btnSubmit) {
    btnSubmit.addEventListener('click', handleCalculateAndRecommend);
  }

  const sortSelect = document.getElementById('select-sort-recs');
  if (sortSelect) {
    sortSelect.addEventListener('change', () => {
      applySortingAndFilters();
    });
  }

  const btnApplyFilter = document.getElementById('btn-apply-results-filter');
  if (btnApplyFilter) {
    btnApplyFilter.addEventListener('click', () => {
      applySortingAndFilters();
    });
  }

  const btnSaveFinal = document.getElementById('btn-save-wishlist-final');
  if (btnSaveFinal) {
    btnSaveFinal.addEventListener('click', handleSaveWishlistOrder);
  }

  const btnExport = document.getElementById('btn-export-list');
  if (btnExport) {
    btnExport.addEventListener('click', handleExportWishlist);
  }

  const btnExploreSearch = document.getElementById('btn-do-explore-search');
  if (btnExploreSearch) {
    btnExploreSearch.addEventListener('click', () => {
      loadExploreData();
    });
  }
}

async function handleCalculateAndRecommend() {
  const isThpt = currentMethod === 'PT01';
  let totalScore = 0;
  let combCode = 'A01';
  let combText = 'A01 (Toán, Vật lý, Tiếng Anh)';

  const priorityKv = document.getElementById('select-priority-region')?.value || 'KV3';
  const priorityDt = document.getElementById('select-priority-target')?.value || 'NONE';
  const desiredRegion = document.getElementById('filter-region')?.value || '';
  const desiredMajor = document.getElementById('filter-fav-major')?.value?.trim() || '';
  const desiredTuition = document.getElementById('filter-tuition')?.value || '';

  const payload = {
    phuongThucMongMuon: [currentMethod],
    khuVucUuTien: priorityKv,
    doiTuongUuTien: priorityDt,
    khuVucMongMuon: desiredRegion,
    nganhMongMuon: desiredMajor,
    mucHocPhi: desiredTuition
  };

  if (isThpt) {
    const s1Raw = document.getElementById('input-score-m1')?.value?.trim();
    const s2Raw = document.getElementById('input-score-m2')?.value?.trim();
    const s3Raw = document.getElementById('input-score-m3')?.value?.trim();

    if (!s1Raw || !s2Raw || !s3Raw) {
      showFormError('Vui lòng nhập đầy đủ điểm cho cả 3 môn trong tổ hợp xét tuyển đã chọn.');
      return;
    }

    const s1 = parseFloat(s1Raw);
    const s2 = parseFloat(s2Raw);
    const s3 = parseFloat(s3Raw);

    if (isNaN(s1) || isNaN(s2) || isNaN(s3)) {
      showFormError('Điểm các môn phải là giá trị số hợp lệ.');
      return;
    }
    if (s1 < 0 || s1 > 10 || s2 < 0 || s2 > 10 || s3 < 0 || s3 > 10) {
      showFormError('Điểm mỗi môn phải nằm trong khoảng từ 0.0 đến 10.0.');
      return;
    }

    totalScore = Math.round((s1 + s2 + s3) * 100) / 100;

    const selectComb = document.getElementById('select-active-combination');
    combCode = selectComb ? selectComb.value : 'A01';
    combText = selectComb ? selectComb.options[selectComb.selectedIndex].text : 'A01';

    const subjectFields = getSubjectFieldsForCombination(combCode);
    payload[subjectFields[0]] = s1;
    payload[subjectFields[1]] = s2;
    payload[subjectFields[2]] = s3;
    payload.danhSachToHopDaChon = [combCode];
  } else {
    const gpaRaw = document.getElementById('input-score-gpa')?.value?.trim();
    if (!gpaRaw) {
      showFormError('Vui lòng nhập điểm trung bình học bạ (GPA).');
      return;
    }

    const gpa = parseFloat(gpaRaw);
    if (isNaN(gpa) || gpa < 0 || gpa > 10) {
      showFormError('Điểm trung bình học bạ phải nằm trong khoảng từ 0.0 đến 10.0.');
      return;
    }

    totalScore = Math.round(gpa * 3 * 100) / 100;
    const selectHbComb = document.getElementById('select-hb-combination');
    combCode = selectHbComb ? selectHbComb.value : 'A01';
    combText = selectHbComb ? selectHbComb.options[selectHbComb.selectedIndex].text : 'A01';

    payload.diemHocBa = gpa;
    payload.danhSachToHopDaChon = [combCode];
  }

  currentProfile = {
    hoTen: currentUser ? currentUser.hoTen : 'Học sinh',
    phuongThuc: currentMethod,
    maToHop: combCode,
    tenToHop: combText,
    tongDiem: totalScore
  };

  updateStudentInfoCard();
  showLoadingState();
  switchView('view-results');

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok && data && data.danhSachTongHop && data.danhSachTongHop.length > 0) {
      rawRecommendations = data.danhSachTongHop;
    } else {
      const errMsg = data.detail || data.thongBao || 'Không tìm thấy chương trình phù hợp với thông tin đã nhập.';
      showResultsError(errMsg);
      return;
    }
  } catch (err) {
    showResultsError('Không thể kết nối đến máy chủ. Vui lòng kiểm tra server đang chạy và thử lại.');
    return;
  }

  applySortingAndFilters();
}

function updateStudentInfoCard() {
  const nameEl = document.getElementById('res-student-name');
  const methodEl = document.getElementById('res-method-name');
  const totalEl = document.getElementById('res-total-score-val');
  const combEl = document.getElementById('res-combination-code');

  if (nameEl) nameEl.textContent = currentProfile.hoTen;
  if (methodEl) methodEl.textContent = currentProfile.phuongThuc === 'PT01' ? 'Điểm thi THPT' : 'Điểm học bạ';
  if (totalEl) totalEl.textContent = currentProfile.tongDiem.toFixed(2);
  if (combEl) combEl.textContent = currentProfile.tenToHop;
}

const COMBINATION_TO_FIELDS = {
  'A00': ['diemToan', 'diemLy', 'diemHoa'],
  'A01': ['diemToan', 'diemLy', 'diemAnh'],
  'A02': ['diemToan', 'diemLy', 'diemSinh'],
  'B00': ['diemToan', 'diemHoa', 'diemSinh'],
  'B08': ['diemToan', 'diemSinh', 'diemAnh'],
  'C00': ['diemVan', 'diemSu', 'diemDia'],
  'C01': ['diemVan', 'diemToan', 'diemLy'],
  'C02': ['diemVan', 'diemToan', 'diemHoa'],
  'C19': ['diemVan', 'diemSu', 'diemGDCD'],
  'D01': ['diemToan', 'diemVan', 'diemAnh'],
  'D07': ['diemToan', 'diemHoa', 'diemAnh'],
  'D09': ['diemToan', 'diemSu', 'diemAnh'],
  'D10': ['diemToan', 'diemDia', 'diemAnh'],
  'D14': ['diemVan', 'diemSu', 'diemAnh']
};

function getSubjectFieldsForCombination(code) {
  return COMBINATION_TO_FIELDS[code] || ['diemToan', 'diemLy', 'diemAnh'];
}

function showFormError(msg) {
  switchView('view-results');
  const slot = document.getElementById('recommendations-cards-slot');
  if (slot) slot.innerHTML = `<div style="background:#fff3f3;border:1px solid #fca5a5;border-radius:12px;padding:2rem;color:#dc2626;text-align:center;">${msg}</div>`;
  const cb = document.getElementById('rec-count-badge');
  if (cb) cb.textContent = '0 kết quả';
}

function showLoadingState() {
  const slot = document.getElementById('recommendations-cards-slot');
  if (slot) slot.innerHTML = `<div style="background:#fff;border:1px solid var(--border-light);border-radius:12px;padding:3rem;text-align:center;color:var(--text-muted);">Đang phân tích dữ liệu và tạo khuyến nghị...</div>`;
  const cb = document.getElementById('rec-count-badge');
  if (cb) cb.textContent = 'Đang tải...';
}

function showResultsError(msg) {
  const slot = document.getElementById('recommendations-cards-slot');
  if (slot) slot.innerHTML = `<div style="background:#fff3f3;border:1px solid #fca5a5;border-radius:12px;padding:2rem;color:#dc2626;text-align:center;">${msg}</div>`;
  const cb = document.getElementById('rec-count-badge');
  if (cb) cb.textContent = '0 kết quả';
}

function applySortingAndFilters() {
  const regionFilter = document.getElementById('res-filter-region')?.value || '';
  const typeFilter = document.getElementById('res-filter-type')?.value || '';
  const groupFilter = document.getElementById('res-filter-group')?.value || '';
  const sortMode = document.getElementById('select-sort-recs')?.value || 'portfolio';

  let list = [...rawRecommendations];

  if (regionFilter) {
    list = list.filter(item => (item.khuVuc || '').toLowerCase().includes(regionFilter.toLowerCase()));
  }
  if (typeFilter) {
    list = list.filter(item => (item.loaiTruong || '').toLowerCase().includes(typeFilter.toLowerCase()));
  }
  if (groupFilter) {
    list = list.filter(item => (item.nhomNganh || '').toLowerCase().includes(groupFilter.toLowerCase()));
  }

  if (sortMode === 'portfolio') {
    list.sort((a, b) => (a.stt || 0) - (b.stt || 0));
  } else if (sortMode === 'fit_desc') {
    list.sort((a, b) => (b.doPhuHop || 0) - (a.doPhuHop || 0));
  } else if (sortMode === 'score_asc') {
    list.sort((a, b) => (a.diemChuanThamChieu || 0) - (b.diemChuanThamChieu || 0));
  } else if (sortMode === 'score_desc') {
    list.sort((a, b) => (b.diemChuanThamChieu || 0) - (a.diemChuanThamChieu || 0));
  }

  displayedRecommendations = list;

  const countBadge = document.getElementById('rec-count-badge');
  if (countBadge) {
    countBadge.textContent = `${displayedRecommendations.length} kết quả phù hợp`;
  }

  renderRecommendationCards(displayedRecommendations);
}

function renderRecommendationCards(items) {
  const slot = document.getElementById('recommendations-cards-slot');
  if (!slot) return;

  if (items.length === 0) {
    slot.innerHTML = `
      <div style="background:#ffffff; border-radius:12px; padding:3rem; text-align:center; color:var(--text-muted); border:1px solid var(--border-light);">
        Không tìm thấy chương trình nào phù hợp với bộ lọc hiện tại. Vui lòng thử nới lỏng bộ lọc.
      </div>
    `;
    return;
  }

  slot.innerHTML = items.map((item, idx) => {
    const avatarInfo = UNI_AVATARS[item.maTruong] || UNI_AVATARS['DEFAULT'];
    const delta = item.delta !== undefined ? item.delta : Math.round((currentProfile.tongDiem - item.diemChuanThamChieu) * 100) / 100;
    
    const tier = item.nhomNguyenVong || (delta >= 1.5 ? 'An toàn' : (delta >= 0.0 ? 'Vừa sức' : 'Thử sức'));
    let statusClass = 'safe';
    let statusLabel = 'An toàn';
    if (tier === 'Thử sức') {
      statusClass = 'try';
      statusLabel = 'Thử sức';
    } else if (tier === 'Vừa sức') {
      statusClass = 'fit';
      statusLabel = 'Vừa sức';
    } else if (tier === 'Rủi ro cao') {
      statusClass = 'risk';
      statusLabel = 'Rủi ro cao';
    }

    const deltaSign = delta >= 0 ? `+${delta.toFixed(2)} (Cao hơn)` : `${delta.toFixed(2)} (Thấp hơn)`;
    const deltaClass = delta >= 0 ? 'positive' : 'negative';

    const isSaved = savedWishlist.some(w => {
      if (w.programId && item.programId) {
        return w.programId === item.programId && (w.maToHop === item.maToHop || w.toHopMonId === item.toHopMonId);
      }
      return w.truongDaiHocId === item.truongDaiHocId && w.nganhHocId === item.nganhHocId && (w.maToHop === item.maToHop || w.toHopMonId === item.toHopMonId);
    });

    return `
      <div class="rec-item-card">
        <div class="uni-logo-avatar" style="background-color: ${avatarInfo.color};">
          ${avatarInfo.text}
        </div>

        <div class="rec-card-details">
          <h5>${item.tenTruong}</h5>
          <h4 class="rec-major-name">${item.tenChuongTrinh || item.tenNganh}</h4>
          <div class="rec-tags-row">
            <span class="rec-pill-tag">Ngành: ${item.tenNganh} (${item.maNganh || 'IT1'})</span>
            ${item.programId ? `<span class="rec-pill-tag">Mã CT: ${item.programId}</span>` : ''}
            <span class="rec-pill-tag">${item.nhomNganh || 'Kỹ thuật - Công nghệ'}</span>
          </div>
          <div class="rec-meta-line">
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              ${item.khuVuc || 'Hà Nội'}
            </span>
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3"></path>
              </svg>
              ${item.loaiTruong || 'Trường công lập'}
            </span>
            <span style="font-weight: 600; color: var(--text-main);">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="1" x2="12" y2="23"></line>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
              </svg>
              ${item.hocPhiUocTinh || 'Học phí theo quy định'}
            </span>
            ${item.chiTieu ? `
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
              </svg>
              Chỉ tiêu: ${item.chiTieu}
            </span>` : ''}
          </div>
        </div>

        <div class="rec-score-metrics">
          <div class="suitability-badge ${statusClass}" style="align-self: flex-end; margin-bottom: 0.4rem;">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"></line>
              <line x1="12" y1="20" x2="12" y2="4"></line>
              <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            ${statusLabel}
          </div>
          <div class="predicted-score-label">Điểm tham chiếu (${item.namThamChieu || 2025})</div>
          <div class="predicted-score-val">${(item.diemChuanThamChieu || 24.0).toFixed(2)}</div>
          ${(() => {
            if (item.coDuBao && item.diemChuanDuBao !== null && item.diemChuanDuBao !== undefined) {
              const label = item.nhanDuBao || (item.loaiDuBao === 'BASELINE_LAG1' ? 'Ước lượng theo điểm năm trước' : 'Dự báo Random Forest');
              return `<div style="font-size:0.8rem; color:var(--primary); font-weight:700; margin-top:2px;">${label} (${item.namMucTieu || 2026}): ${Number(item.diemChuanDuBao).toFixed(2)}${item.khoangTinCay80 ? ` <span style='font-size:0.72rem; color:var(--text-muted);'>(${item.khoangTinCay80})</span>` : ''}</div>`;
            } else {
              return `<div style="font-size:0.76rem; color:var(--text-muted); margin-top:2px; font-style:italic;">Điểm chuẩn lịch sử (${item.namThamChieu || 2025})</div>`;
            }
          })()}
          <div class="delta-badge ${deltaClass}">Chênh lệch: ${deltaSign}</div>
        </div>

        <div class="rec-action-buttons">
          <button class="btn-rec-detail" onclick="openProgramDetails(${idx})">Xem chi tiết</button>
          <button class="btn-rec-save ${isSaved ? 'saved' : ''}" onclick="toggleSaveWishlistItem(${idx})">
            ${isSaved ? 'Đã lưu' : 'Lưu nguyện vọng'}
          </button>
        </div>
      </div>
    `;
  }).join('');
}

window.toggleSaveWishlistItem = function(idx) {
  const item = displayedRecommendations[idx];
  if (!item) return;

  const existingIdx = savedWishlist.findIndex(w => {
    if (w.programId && item.programId) {
      return w.programId === item.programId && (w.maToHop === item.maToHop || w.toHopMonId === item.toHopMonId);
    }
    return w.truongDaiHocId === item.truongDaiHocId && w.nganhHocId === item.nganhHocId && (w.maToHop === item.maToHop || w.toHopMonId === item.toHopMonId);
  });
  if (existingIdx >= 0) {
    savedWishlist.splice(existingIdx, 1);
  } else {
    savedWishlist.push({ ...item });
  }

  renderRecommendationCards(displayedRecommendations);
};

window.openProgramDetails = async function(idx) {
  const item = displayedRecommendations[idx];
  if (!item) return;

  const modal = document.getElementById('modal-detail-dialog');
  const body = document.getElementById('detail-modal-body');
  if (!modal || !body) return;

  const scoreText = (item.diemChuanThamChieu !== null && item.diemChuanThamChieu !== undefined)
    ? Number(item.diemChuanThamChieu).toFixed(2)
    : 'Chưa có điểm tham chiếu';

  const fitTotal = (item.doPhuHop !== null && item.doPhuHop !== undefined)
    ? `${Number(item.doPhuHop).toFixed(0)}/100 điểm phù hợp`
    : 'Chưa tính được';

  const fitDiem = (item.mucThuanLoiDiem !== null && item.mucThuanLoiDiem !== undefined)
    ? `${Number(item.mucThuanLoiDiem).toFixed(0)}/100`
    : ((item.doPhuHop !== null && item.doPhuHop !== undefined) ? `${Number(item.doPhuHop).toFixed(0)}/100` : 'Chưa tính được');

  const fitSoThich = (item.doPhuHopSoThich !== null && item.doPhuHopSoThich !== undefined)
    ? `${Number(item.doPhuHopSoThich).toFixed(0)}/100`
    : 'Chưa đánh giá';

  body.innerHTML = `
    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--primary); margin-bottom: 0.35rem;">
      ${item.tenChuongTrinh || item.tenNganh || 'Chương trình đào tạo'}
    </h3>
    <h5 style="color: var(--text-muted); margin-bottom: 1rem; font-size: 0.95rem;">
      ${item.tenTruong || 'Trường Đại học'} (${item.maTruong || 'Mã trường chưa rõ'})
    </h5>

    <div style="background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md); margin-bottom: 1.25rem;">
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Ngành đào tạo:</span>
        <span style="font-weight:700;">${item.tenNganh || 'Chưa có thông tin'} (${item.maNganh ? item.maNganh : 'Chưa có thông tin'})</span>
      </div>
      ${item.programId ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Mã chương trình (Program ID):</span>
        <span style="font-weight:700;">${item.programId}</span>
      </div>` : ''}
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Khu vực địa lý:</span>
        <span style="font-weight:700;">${item.khuVuc ? item.khuVuc : 'Chưa có thông tin'}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Mức học phí dự kiến:</span>
        <span style="font-weight:700; color:var(--text-main);">${item.hocPhiUocTinh || 'Theo quy định'}</span>
      </div>
      ${item.chiTieu ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Chỉ tiêu tuyển sinh:</span>
        <span style="font-weight:700;">${item.chiTieu} sinh viên</span>
      </div>` : ''}
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Điểm chuẩn chính thức (${item.namThamChieu || 2025}):</span>
        <span style="font-weight:700; color:var(--primary);">${scoreText}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Hình thức tham chiếu:</span>
        <span style="font-weight:700; color:${item.coDuBao ? 'var(--primary)' : 'var(--text-muted)'};">
          ${item.coDuBao ? `Dự báo năm ${item.namMucTieu || 2026}: ${Number(item.diemChuanDuBao).toFixed(2)}${item.khoangTinCay80 ? ` (±${item.khoangTinCay80})` : ''}` : `Tra cứu điểm chuẩn công bố`}
        </span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:0.9rem; flex-wrap:wrap; gap:0.25rem;">
        <span style="color:var(--text-muted);">Độ phù hợp nội bộ:</span>
        <span style="font-weight:700; color:var(--emerald);">${fitTotal}</span>
      </div>
      <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.35rem;">
        Thành phần: Thuận lợi điểm ${fitDiem} | Sở thích ${fitSoThich}
      </div>
      <div style="font-size:0.76rem; color:var(--text-muted); margin-top:0.4rem; font-style:italic;">
        * Điểm phù hợp (thang 100) được tính từ mức thuận lợi điểm và tiêu chí sở thích, không phải xác suất trúng tuyển.
      </div>
    </div>

    <button class="btn-submit-recommend" style="width:100%; margin-left:0;" onclick="closeDetailDialog()">
      Đóng
    </button>
  `;

  modal.classList.add('active');
};

window.closeDetailDialog = function() {
  const modal = document.getElementById('modal-detail-dialog');
  if (modal) modal.classList.remove('active');
};

const btnCloseDetail = document.getElementById('btn-close-detail-dialog');
if (btnCloseDetail) {
  btnCloseDetail.addEventListener('click', closeDetailDialog);
}

function renderWishlistView() {
  const compareSlot = document.getElementById('compare-cards-slot');
  const countLabel = document.getElementById('compare-count-label');
  const tableTbody = document.getElementById('wishlist-table-tbody');
  const wishCountBadge = document.getElementById('wishlist-count-badge');

  if (wishCountBadge) wishCountBadge.textContent = savedWishlist.length;

  if (savedWishlist.length === 0) {
    if (countLabel) countLabel.textContent = 0;
    if (compareSlot) {
      compareSlot.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 1rem; color: var(--text-muted); background: var(--bg-card); border-radius: var(--radius-lg); border: 1px dashed var(--border-color);">
          <p style="font-weight: 600; font-size: 1.05rem; margin-bottom: 0.5rem; color: var(--text-main);">Chưa có nguyện vọng nào được lưu</p>
          <p style="font-size: 0.9rem;">Hãy quay lại màn hình "Kết quả tư vấn" và nhấn nút <strong>"Lưu nguyện vọng"</strong> trên các chương trình bạn quan tâm.</p>
        </div>
      `;
    }
    if (tableTbody) {
      tableTbody.innerHTML = `
        <tr>
          <td colspan="8" style="text-align: center; padding: 2rem; color: var(--text-muted);">
            Danh sách nguyện vọng đang trống.
          </td>
        </tr>
      `;
    }
    return;
  }

  const top3 = savedWishlist.slice(0, 3);
  if (countLabel) countLabel.textContent = top3.length;

  if (compareSlot) {
    compareSlot.innerHTML = top3.map((item, i) => {
      const avatarInfo = UNI_AVATARS[item.maTruong] || UNI_AVATARS['DEFAULT'];
      const tuition = item.hocPhiUocTinh || item.hocPhi || 'Theo quy định';
      const rangeCutoff = item.diemChuanDuBao ? `${item.diemChuanDuBao.toFixed(2)} (Dự kiến)` : `${(item.diemChuanThamChieu || 24.0).toFixed(2)} (Tham chiếu)`;
      const fitLabel = item.doPhuHop >= 80 ? 'Rất phù hợp' : (item.doPhuHop >= 60 ? 'Phù hợp' : 'Khá phù hợp');
      const progressColor = item.doPhuHop >= 80 ? 'green' : (item.doPhuHop >= 60 ? 'blue' : 'amber');

      return `
        <div class="compare-program-card">
          <button class="btn-close-compare-col" onclick="removeWishlistItem(${i})">&times;</button>
          
          <div class="compare-card-head">
            <div class="uni-logo-avatar" style="width:42px; height:42px; font-size:0.9rem; background:${avatarInfo.color};">
              ${avatarInfo.text}
            </div>
            <div>
              <h4>${item.tenTruong}</h4>
              <p>${item.khuVuc || 'Toàn quốc'}</p>
            </div>
          </div>

          <div class="compare-detail-row">
            <span class="compare-label">Ngành học</span>
            <span class="compare-val">${item.tenNganh}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Phương thức xét tuyển</span>
            <span class="compare-val">${item.tenPhuongThuc || 'Xét tuyển'}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Điểm chuẩn</span>
            <span class="compare-val">${rangeCutoff}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Học phí (ước tính)</span>
            <span class="compare-val">${tuition}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Khu vực</span>
            <span class="compare-val">${item.khuVuc || 'Toàn quốc'}</span>
          </div>

          <div class="compare-progress-wrap">
            <div style="display:flex; justify-content:space-between; font-size:0.8rem; margin-bottom:0.25rem;">
              <span class="compare-label">Mức độ phù hợp</span>
              <span style="font-weight:700; color:var(--text-main);">${fitLabel} (${item.doPhuHop}%)</span>
            </div>
            <div class="progress-track">
              <div class="progress-fill ${progressColor}" style="width: ${item.doPhuHop || 75}%;"></div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  if (tableTbody) {
    tableTbody.innerHTML = savedWishlist.map((item, idx) => {
      const avatarInfo = UNI_AVATARS[item.maTruong] || UNI_AVATARS['DEFAULT'];
      const delta = item.delta !== undefined ? item.delta : Math.round((currentProfile.tongDiem - (item.diemChuanDuBao || item.diemChuanThamChieu || 24.0)) * 100) / 100;
      
      const tier = item.nhomNguyenVong || (delta >= 1.5 ? 'An toàn' : (delta >= 0.0 ? 'Vừa sức' : 'Thử sức'));
      let statusClass = 'safe';
      let statusLabel = 'An toàn';
      if (tier === 'Thử sức') {
        statusClass = 'try';
        statusLabel = 'Thử sức';
      } else if (tier === 'Vừa sức') {
        statusClass = 'fit';
        statusLabel = 'Vừa sức';
      } else if (tier === 'Rủi ro cao') {
        statusClass = 'risk';
        statusLabel = 'Rủi ro cao';
      }

      return `
        <tr>
          <td><span class="drag-handle-btn">:::</span></td>
          <td><span class="stt-circle-badge">${idx + 1}</span></td>
          <td>
            <div style="display:flex; align-items:center; gap:0.6rem;">
              <div class="uni-logo-avatar" style="width:30px; height:30px; font-size:0.75rem; background:${avatarInfo.color};">
                ${avatarInfo.text}
              </div>
              <span style="font-weight:600;">${item.tenTruong}</span>
            </div>
          </td>
          <td style="font-weight:600; color:var(--primary);">
            <div>${item.tenChuongTrinh || item.tenNganh}</div>
            ${item.programId ? `<small style="color:var(--text-muted); font-size:0.75rem;">Mã: ${item.programId}</small>` : ''}
          </td>
          <td>${item.tenPhuongThuc || 'Xét tuyển'}</td>
          <td style="font-size:0.85rem; color:var(--text-main); font-weight:600;">${item.hocPhiUocTinh || item.hocPhi || 'Theo quy định'}</td>
          <td style="font-weight:700;">${(item.diemChuanThamChieu || 24.0).toFixed(2)}</td>
          <td>
            <span class="suitability-badge ${statusClass}">
              ${statusLabel}
            </span>
          </td>
          <td style="text-align: center;">
            <button class="btn-delete-wish" onclick="removeWishlistItem(${idx})">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }
}

window.removeWishlistItem = function(idx) {
  savedWishlist.splice(idx, 1);
  renderWishlistView();
};

async function handleSaveWishlistOrder() {
  if (!currentToken) {
    alert('Vui lòng đăng nhập tài khoản để lưu thứ tự danh sách nguyện vọng vào hệ thống.');
    openAuthModal('login');
    return;
  }
  if (!savedWishlist || savedWishlist.length === 0) {
    alert('Danh sách nguyện vọng đang trống. Vui lòng thêm các nguyện vọng phù hợp trước khi lưu.');
    return;
  }

  try {
    const payload = {
      danhSachNguyenVong: savedWishlist.map((item, idx) => ({
        truongDaiHocId: item.truongDaiHocId,
        nganhHocId: item.nganhHocId,
        programId: item.programId || '',
        tenChuongTrinh: item.tenChuongTrinh || item.tenNganh || '',
        admissionCaseId: item.admissionCaseId || '',
        toHopMonId: item.toHopMonId,
        phuongThucXetTuyenId: item.phuongThucXetTuyenId,
        diemXetTuyen: item.diemXetTuyen,
        diemChuanThamChieu: item.diemChuanThamChieu,
        doPhuHop: item.doPhuHop,
        mucDoPhuHop: item.mucDoPhuHop,
        mucDoRuiRo: item.mucDoRuiRo,
        thuTuUuTien: `NV${idx + 1}`
      }))
    };

    const res = await fetch('/api/wishlist/save', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(data.thongBao || 'Đã lưu thứ tự nguyện vọng thành công vào hệ thống!');
    } else {
      alert(data.detail || data.thongBao || 'Không thể lưu nguyện vọng. Vui lòng thử lại.');
    }
  } catch (err) {
    alert('Lỗi kết nối khi lưu nguyện vọng: ' + err.message);
  }
}

async function loadSavedWishlistFromServer() {
  if (!currentToken) return;
  try {
    const res = await fetch('/api/wishlist-history', {
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        savedWishlist = data.map((item, idx) => ({
          ...item,
          thuTuUuTien: item.thuTuUuTien || `NV${idx + 1}`
        }));
        renderWishlistView();
      }
    }
  } catch (err) {
    console.error('Không thể nạp lịch sử nguyện vọng:', err);
  }
}

function handleExportWishlist() {
  if (savedWishlist.length === 0) {
    alert('Danh sách nguyện vọng đang trống!');
    return;
  }

  let textContent = "DANH SÁCH NGUYỆN VỌNG THAM KHẢO — TUYỂN SINH+\n";
  textContent += "Danh sách do hệ thống hỗ trợ tư vấn tạo.\n";
  textContent += "Không thay thế việc đăng ký trên hệ thống tuyển sinh chính thức.\n";
  textContent += `Họ và tên thí sinh: ${currentProfile.hoTen}\n`;
  textContent += `Tổ hợp: ${currentProfile.tenToHop} | Tổng điểm: ${currentProfile.tongDiem}\n`;
  textContent += "--------------------------------------------------------------------------\n";
  textContent += "STT | Mã trường | Tên trường | Ngành / Chương trình | Điểm chuẩn tham chiếu\n";
  textContent += "--------------------------------------------------------------------------\n";

  savedWishlist.forEach((w, i) => {
    const sc = (w.diemChuanThamChieu !== null && w.diemChuanThamChieu !== undefined)
      ? Number(w.diemChuanThamChieu).toFixed(2)
      : "Chưa có";
    textContent += `NV${i + 1} | ${w.maTruong || ''} | ${w.tenTruong || ''} | ${w.tenChuongTrinh || w.tenNganh || ''} | ${sc}\n`;
  });

  const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `DanhSachNguyenVong_ThamKhao_${currentProfile.hoTen.replace(/\s+/g, '_')}_2026.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

async function loadExploreData() {
  const query = document.getElementById('input-explore-search')?.value || '';
  const tbody = document.getElementById('explore-table-tbody');
  if (!tbody) return;

  try {
    const res = await fetch(`/api/explore-benchmarks?limit=50&query=${encodeURIComponent(query)}`);
    const records = await res.json();
    
    if (!Array.isArray(records) || records.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" style="text-align:center; padding:2rem; color:var(--text-muted);">
            Không tìm thấy chương trình đào tạo hoặc điểm chuẩn phù hợp với từ khóa "${query}".
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = records.map((r) => {
      const avatar = UNI_AVATARS[r.maTruong] || UNI_AVATARS['DEFAULT'];
      const scoreDisplay = (r.diemChuan !== null && r.diemChuan !== undefined)
        ? `<span style="font-weight:700; color:var(--text-main);">${Number(r.diemChuan).toFixed(2)}</span>`
        : `<span style="color:var(--text-muted); font-size:0.85rem; font-style:italic;">Chưa có điểm chuẩn</span>`;

      return `
        <tr>
          <td style="font-weight:700;">${r.maTruong || '—'}</td>
          <td>
            <div style="display:flex; align-items:center; gap:0.6rem;">
              <div class="uni-logo-avatar" style="width:28px; height:28px; font-size:0.75rem; background:${avatar.color};">
                ${avatar.text}
              </div>
              <span>${r.tenTruong || 'Chưa rõ'}</span>
            </div>
          </td>
          <td style="color:var(--primary); font-weight:600;">${r.tenChuongTrinh || r.tenNganh || 'Chưa phân loại'}</td>
          <td>${r.tenPhuongThuc || 'Xét tuyển'}</td>
          <td>${r.maToHop || '—'}</td>
          <td>${scoreDisplay}</td>
          <td style="font-size:0.85rem; font-weight:600; color:var(--text-main);">${r.hocPhiUocTinh || 'Theo quy định'}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('Explore load err:', err);
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align:center; padding:1.5rem; color:var(--rose);">
          Không thể nạp dữ liệu tra cứu từ máy chủ. Vui lòng thử lại.
        </td>
      </tr>
    `;
  }
}

function initAuthModal() {
  const btnOpen = document.getElementById('btn-open-auth-modal');
  const modal = document.getElementById('modal-auth-dialog');
  const btnClose = document.getElementById('btn-close-auth-dialog');

  if (btnOpen && modal) {
    btnOpen.addEventListener('click', () => {
      modal.classList.add('active');
    });
  }

  if (btnClose && modal) {
    btnClose.addEventListener('click', () => {
      modal.classList.remove('active');
    });
  }

  const tabLogin = document.getElementById('modal-tab-login');
  const tabReg = document.getElementById('modal-tab-register');
  const panelLogin = document.getElementById('auth-panel-login');
  const panelReg = document.getElementById('auth-panel-register');

  if (tabLogin && tabReg && panelLogin && panelReg) {
    tabLogin.addEventListener('click', () => {
      tabLogin.classList.add('active');
      tabReg.classList.remove('active');
      panelLogin.style.display = 'block';
      panelReg.style.display = 'none';
    });

    tabReg.addEventListener('click', () => {
      tabReg.classList.add('active');
      tabLogin.classList.remove('active');
      panelLogin.style.display = 'none';
      panelReg.style.display = 'block';
    });
  }

  const btnDoLogin = document.getElementById('btn-auth-do-login');
  if (btnDoLogin) {
    btnDoLogin.addEventListener('click', async () => {
      const u = document.getElementById('auth-username')?.value.trim();
      const p = document.getElementById('auth-password')?.value.trim();
      if (!u || !p) return;

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tenDangNhap: u, matKhau: p })
        });
        const data = await res.json();
        if (data && data.thanhCong) {
          currentToken = data.token;
          currentUser = data.nguoiDung;
          localStorage.setItem('tuyensinh_token', currentToken);
          updateAuthUI();
          if (modal) modal.classList.remove('active');
          alert(`Đăng nhập thành công! Xin chào ${currentUser.hoTen}`);
        } else {
          alert(data.detail || 'Đăng nhập không thành công.');
        }
      } catch (err) {
        alert('Có lỗi xảy ra khi kết nối máy chủ.');
      }
    });
  }

  const btnDoReg = document.getElementById('btn-auth-do-register');
  if (btnDoReg) {
    btnDoReg.addEventListener('click', async () => {
      const u = document.getElementById('reg-username')?.value.trim();
      const p = document.getElementById('reg-password')?.value.trim();
      const f = document.getElementById('reg-fullname')?.value.trim();
      const e = document.getElementById('reg-email')?.value.trim();
      if (!u || !p || !f) {
        alert('Vui lòng điền đủ thông tin đăng ký!');
        return;
      }

      try {
        const res = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ tenDangNhap: u, matKhau: p, hoTen: f, email: e })
        });
        const data = await res.json();
        if (data && data.thanhCong) {
          currentToken = data.token;
          currentUser = data.nguoiDung;
          localStorage.setItem('tuyensinh_token', currentToken);
          updateAuthUI();
          if (modal) modal.classList.remove('active');
          alert('Đăng ký tài khoản thành công!');
        } else {
          alert(data.detail || 'Đăng ký không thành công.');
        }
      } catch (err) {
        alert('Có lỗi xảy ra khi kết nối máy chủ.');
      }
    });
  }
}

async function loadInitialState() {
  if (currentToken) {
    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${currentToken}` }
      });
      if (res.ok) {
        currentUser = await res.json();
        updateAuthUI();
      }
    } catch (e) {
      console.log('Token check failed');
    }
  }
}

function updateAuthUI() {
  const lbl = document.getElementById('auth-btn-label');
  if (lbl && currentUser) {
    lbl.textContent = currentUser.hoTen || currentUser.tenDangNhap;
  }
}

