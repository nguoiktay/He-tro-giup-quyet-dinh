const API_BASE = '';

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

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatApiError(data, fallback) {
  if (!data) return fallback;
  const detail = data.detail;
  if (Array.isArray(detail)) {
    return detail.map(d => String(d.msg || '').replace(/^Value error, /, '')).filter(Boolean).join(' ') || fallback;
  }
  return detail || data.thongBao || fallback;
}

async function loadModelInfo() {
  const box = document.getElementById('model-confidence-note');
  if (!box) return;
  try {
    const res = await fetch(`${API_BASE}/api/model-info`);
    if (!res.ok) return;
    const info = await res.json();
    const ci = info.khoangTinCay || {};
    const cov = info.doPhuChuongTrinh || {};
    const pct = v => (v === null || v === undefined) ? '?' : `${(v * 100).toFixed(1)}%`;
    box.textContent =
      `Độ tin cậy dự báo ${info.namDuBao}: điểm chuẩn dự báo có sai số ±${ci.banKinhDiem} điểm ` +
      `(mức danh nghĩa ${pct(ci.mucTinCayDanhNghia)}, độ phủ thực tế trên tập kiểm thử ${pct(ci.doPhuThucTe)}; ` +
      `MAE ${info.mae}, R² ${info.r2}). Mô hình chỉ dự báo ${cov.duBaoMoHinh}/${cov.tongBanGhi} bản ghi điểm chuẩn ` +
      `(${cov.soTruongCoDuBao} trường); phần còn lại so với điểm chuẩn đã công bố.`;
    box.hidden = false;
  } catch (err) {
    box.hidden = true;
  }
}

function formatTuitionBadge(item) {
  if (!item) return { shortText: 'Học phí: Theo quy định', fullText: '' };

  const rawText = String(item.hocPhiUocTinh || item.hocPhi || '').trim();
  const lower = rawText.toLowerCase();

  const isFree = (
    item.phanLoai === 'free_subsidized' ||
    item.hocPhiNam === 0 ||
    item.hocPhiKy === 0 ||
    lower.includes('miễn') ||
    lower.includes('hỗ trợ 100%') ||
    lower.includes('bao cấp')
  );

  if (isFree) {
    return {
      shortText: 'Miễn phí',
      fullText: rawText || 'Miễn 100% học phí theo chính sách nhà nước'
    };
  }

  if (item.trangThaiHocPhi === 'UNVERIFIED' || (!item.hocPhiUocTinh && item.hocPhiNam == null)) {
    return {
      shortText: 'Học phí: Chưa rõ',
      fullText: rawText || 'Chưa có thông tin học phí đã xác minh'
    };
  }

  let cleanAmount = rawText
    .replace(/\s*\(Dự kiến.*?\)/i, '')
    .replace(/\s*\(Tham khảo.*?\)/i, '')
    .trim();

  if (cleanAmount && cleanAmount !== 'Theo quy định' && cleanAmount !== 'Chưa có thông tin học phí đã xác minh') {
    if (cleanAmount.toLowerCase().startsWith('học phí')) {
      return { shortText: cleanAmount, fullText: rawText };
    }
    return { shortText: `Học phí: ${cleanAmount}`, fullText: rawText };
  }

  if (item.hocPhiNam !== null && item.hocPhiNam !== undefined && !isNaN(Number(item.hocPhiNam))) {
    const val = Number(item.hocPhiNam);
    if (val === 0) {
      return { shortText: 'Miễn phí', fullText: rawText };
    }
    const trieu = (val / 1000000.0).toFixed(1);
    return { shortText: `Học phí: ~${trieu} triệu/năm`, fullText: rawText };
  }

  return { shortText: 'Học phí: Theo quy định', fullText: rawText };
}

const COMBINATION_LABELS = {
  'A00': ['Toán', 'Vật lý', 'Hóa học'],
  'A01': ['Toán', 'Vật lý', 'Tiếng Anh'],
  'A02': ['Toán', 'Vật lý', 'Sinh học'],
  'A03': ['Toán', 'Lịch sử', 'Địa lý'],
  'A04': ['Toán', 'Vật lý', 'Địa lý'],
  'B00': ['Toán', 'Hóa học', 'Sinh học'],
  'B01': ['Toán', 'Sinh học', 'Lịch sử'],
  'B02': ['Toán', 'Sinh học', 'Địa lý'],
  'B03': ['Toán', 'Sinh học', 'Ngữ văn'],
  'B08': ['Toán', 'Sinh học', 'Tiếng Anh'],
  'C00': ['Ngữ văn', 'Lịch sử', 'Địa lý'],
  'C01': ['Ngữ văn', 'Toán', 'Vật lý'],
  'C02': ['Ngữ văn', 'Toán', 'Hóa học'],
  'C03': ['Ngữ văn', 'Toán', 'Lịch sử'],
  'C04': ['Ngữ văn', 'Toán', 'Địa lý'],
  'C14': ['Toán', 'Ngữ văn', 'GDCD'],
  'C19': ['Ngữ văn', 'Lịch sử', 'GDCD'],
  'C20': ['Ngữ văn', 'Địa lý', 'GDCD'],
  'D01': ['Toán', 'Ngữ văn', 'Tiếng Anh'],
  'D07': ['Toán', 'Hóa học', 'Tiếng Anh'],
  'D08': ['Toán', 'Sinh học', 'Tiếng Anh'],
  'D09': ['Toán', 'Lịch sử', 'Tiếng Anh'],
  'D10': ['Toán', 'Địa lý', 'Tiếng Anh'],
  'D11': ['Ngữ văn', 'Vật lý', 'Tiếng Anh'],
  'D12': ['Ngữ văn', 'Hóa học', 'Tiếng Anh'],
  'D13': ['Ngữ văn', 'Sinh học', 'Tiếng Anh'],
  'D14': ['Ngữ văn', 'Lịch sử', 'Tiếng Anh'],
  'D15': ['Ngữ văn', 'Địa lý', 'Tiếng Anh'],
  'D66': ['Ngữ văn', 'GDCD', 'Tiếng Anh'],
  'D84': ['Toán', 'GDCD', 'Tiếng Anh']
};

const UNI_AVATARS = {
  'BKA': { color: '#dc2626', text: 'BKA' },
  'QHI': { color: '#0284c7', text: 'VNU' },
  'KHA': { color: '#059669', text: 'NEU' },
  'NTH': { color: '#e11d48', text: 'FTU' },
  'DTT': { color: '#005baa', text: 'TDTU' },
  'UEL': { color: '#0369a1', text: 'UEL' },
  'DEFAULT': { color: '#0ea5e9', text: 'UNI' }
};

document.addEventListener('DOMContentLoaded', () => {
  initNavigation();
  initMethodToggles();
  initCombinationSelect();
  initFormActions();
  initAuthModal();
  initAdminPanelEvents();
  initCatalogsFromApi();
  loadInitialState();
  loadModelInfo();
  initChatWidget();
});

async function initCatalogsFromApi() {
  try {
    const [combsRes, regionsRes, typesRes, majorsRes] = await Promise.all([
      fetch(`${API_BASE}/api/combinations`).catch(() => null),
      fetch(`${API_BASE}/api/regions`).catch(() => null),
      fetch(`${API_BASE}/api/university-types`).catch(() => null),
      fetch(`${API_BASE}/api/majors?limit=200`).catch(() => null)
    ]);

    if (combsRes && combsRes.ok) {
      const combs = await combsRes.json();
      const combSelect = document.getElementById('select-active-combination');
      if (combSelect && Array.isArray(combs) && combs.length > 0) {
        const curVal = combSelect.value;
        combSelect.innerHTML = combs.map(c =>
          `<option value="${escapeHtml(c.maToHop)}"${c.maToHop === curVal ? ' selected' : ''}>${escapeHtml(c.maToHop)} (${escapeHtml(c.tenToHop)})</option>`
        ).join('');
      }
    }

    if (regionsRes && regionsRes.ok) {
      const regions = await regionsRes.json();
      const regionSelect = document.getElementById('filter-region');
      if (regionSelect && Array.isArray(regions)) {
        const curVal = regionSelect.value;
        regionSelect.innerHTML = '<option value="">Tất cả khu vực</option>' +
          regions.map(r => `<option value="${escapeHtml(r)}"${r === curVal ? ' selected' : ''}>${escapeHtml(r)}</option>`).join('');
      }
    }

    if (typesRes && typesRes.ok) {
      const types = await typesRes.json();
      const typeSelect = document.getElementById('filter-uni-type');
      if (typeSelect && Array.isArray(types)) {
        const curVal = typeSelect.value;
        typeSelect.innerHTML = '<option value="">Tất cả loại trường</option>' +
          types.map(t => `<option value="${escapeHtml(t)}"${t === curVal ? ' selected' : ''}>${escapeHtml(t)}</option>`).join('');
      }
    }

    if (majorsRes && majorsRes.ok) {
      const majors = await majorsRes.json();
      const majorSelect = document.getElementById('filter-fav-major');
      if (majorSelect && Array.isArray(majors) && majors.length > 0) {
        const curVal = majorSelect.value;
        const groups = {};
        majors.forEach(m => {
          const groupName = m.nhomNganh || 'Khác';
          if (!groups[groupName]) groups[groupName] = [];
          groups[groupName].push(m);
        });

        let html = '<option value="">Bất kỳ ngành nào (Tất cả ngành)</option>';
        Object.keys(groups).sort((a, b) => a.localeCompare(b, 'vi')).forEach(grp => {
          html += `<optgroup label="${escapeHtml(grp)}">`;
          groups[grp].forEach(m => {
            const isSel = (m.tenNganh === curVal) ? ' selected' : '';
            const codeSuffix = m.maNganh && m.maNganh !== 'UNKNOWN' ? ` (${escapeHtml(m.maNganh)})` : '';
            html += `<option value="${escapeHtml(m.tenNganh)}"${isSel}>${escapeHtml(m.tenNganh)}${codeSuffix}</option>`;
          });
          html += '</optgroup>';
        });
        majorSelect.innerHTML = html;

        const resGroupSelect = document.getElementById('res-filter-group');
        if (resGroupSelect) {
          const curGroupVal = resGroupSelect.value;
          const distinctGroups = Object.keys(groups).sort((a, b) => a.localeCompare(b, 'vi'));
          resGroupSelect.innerHTML = '<option value="">Tất cả nhóm ngành</option>' +
            distinctGroups.map(g => `<option value="${escapeHtml(g)}"${g === curGroupVal ? ' selected' : ''}>${escapeHtml(g)}</option>`).join('');
        }
      }
    }
  } catch (err) {
    console.warn('Lỗi tải danh mục từ API:', err);
  }
}

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
  } else if (viewId === 'view-admin') {
    loadAdminDashboard();
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

  const selectHbComb = document.getElementById('select-hb-combination');
  if (selectHbComb) {
    selectHbComb.addEventListener('change', () => {
      const val = selectHbComb.value;
      updateHbSubjectLabels(val);
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

function updateHbSubjectLabels(code) {
  const subjects = COMBINATION_LABELS[code] || ['Môn 1', 'Môn 2', 'Môn 3'];
  const l1 = document.getElementById('label-hb-mon1');
  const l2 = document.getElementById('label-hb-mon2');
  const l3 = document.getElementById('label-hb-mon3');

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
    const selectHbComb = document.getElementById('select-hb-combination');
    combCode = selectHbComb ? selectHbComb.value : 'A01';
    combText = selectHbComb ? selectHbComb.options[selectHbComb.selectedIndex].text : 'A01';

    const s1Raw = document.getElementById('input-hb-score-m1')?.value?.trim();
    const s2Raw = document.getElementById('input-hb-score-m2')?.value?.trim();
    const s3Raw = document.getElementById('input-hb-score-m3')?.value?.trim();
    const gpaRaw = document.getElementById('input-score-gpa')?.value?.trim();

    const s1 = parseFloat(s1Raw);
    const s2 = parseFloat(s2Raw);
    const s3 = parseFloat(s3Raw);
    const gpa = parseFloat(gpaRaw);

    if (!isNaN(s1) && !isNaN(s2) && !isNaN(s3) && s1 >= 0 && s1 <= 10 && s2 >= 0 && s2 <= 10 && s3 >= 0 && s3 <= 10) {
      totalScore = Math.round((s1 + s2 + s3) * 100) / 100;
      const subjectFields = getSubjectFieldsForCombination(combCode);
      payload[subjectFields[0]] = s1;
      payload[subjectFields[1]] = s2;
      payload[subjectFields[2]] = s3;
    } else if (!isNaN(gpa) && gpa >= 0 && gpa <= 10) {
      totalScore = Math.round(gpa * 3 * 100) / 100;
    } else {
      showFormError('Vui lòng nhập điểm các môn học bạ hợp lệ (0.0 - 10.0) hoặc điểm GPA.');
      return;
    }

    if (!isNaN(gpa) && gpa >= 0 && gpa <= 10) {
      payload.diemHocBa = gpa;
    }
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
    if (res.ok && data) {
      window.canKiemTraHocPhi = data.danhSachCanKiemTraHocPhi || [];
      const warnBox = document.getElementById('combination-warning-note');
      if (warnBox) {
        const warnings = data.canhBaoToHop || [];
        warnBox.textContent = warnings.length ? `Bỏ qua: ${warnings.join('; ')}.` : '';
        warnBox.hidden = warnings.length === 0;
      }
      if (data.danhSachTongHop && data.danhSachTongHop.length > 0) {
        rawRecommendations = data.danhSachTongHop;
      } else if (window.canKiemTraHocPhi.length > 0) {
        rawRecommendations = [];
      } else {
        const errMsg = formatApiError(data, 'Không tìm thấy chương trình phù hợp với thông tin đã nhập.');
        showResultsError(errMsg);
        return;
      }
    } else {
      const errMsg = formatApiError(data, 'Không tìm thấy chương trình phù hợp với thông tin đã nhập.');
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
  'A03': ['diemToan', 'diemSu', 'diemDia'],
  'A04': ['diemToan', 'diemLy', 'diemDia'],
  'B00': ['diemToan', 'diemHoa', 'diemSinh'],
  'B01': ['diemToan', 'diemSinh', 'diemSu'],
  'B02': ['diemToan', 'diemSinh', 'diemDia'],
  'B03': ['diemToan', 'diemSinh', 'diemVan'],
  'B08': ['diemToan', 'diemSinh', 'diemAnh'],
  'C00': ['diemVan', 'diemSu', 'diemDia'],
  'C01': ['diemVan', 'diemToan', 'diemLy'],
  'C02': ['diemVan', 'diemToan', 'diemHoa'],
  'C03': ['diemVan', 'diemToan', 'diemSu'],
  'C04': ['diemVan', 'diemToan', 'diemDia'],
  'C14': ['diemToan', 'diemVan', 'diemGDCD'],
  'C19': ['diemVan', 'diemSu', 'diemGDCD'],
  'C20': ['diemVan', 'diemDia', 'diemGDCD'],
  'D01': ['diemToan', 'diemVan', 'diemAnh'],
  'D07': ['diemToan', 'diemHoa', 'diemAnh'],
  'D08': ['diemToan', 'diemSinh', 'diemAnh'],
  'D09': ['diemToan', 'diemSu', 'diemAnh'],
  'D10': ['diemToan', 'diemDia', 'diemAnh'],
  'D11': ['diemVan', 'diemLy', 'diemAnh'],
  'D12': ['diemVan', 'diemHoa', 'diemAnh'],
  'D13': ['diemVan', 'diemSinh', 'diemAnh'],
  'D14': ['diemVan', 'diemSu', 'diemAnh'],
  'D15': ['diemVan', 'diemDia', 'diemAnh'],
  'D66': ['diemVan', 'diemGDCD', 'diemAnh'],
  'D84': ['diemToan', 'diemGDCD', 'diemAnh']
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
  if (slot) {
    slot.innerHTML = `
      <div style="background:#ffffff; border:1px solid var(--border-light); border-radius:16px; padding:2.5rem 2rem; text-align:center; max-width:680px; margin:2rem auto; box-shadow:0 4px 20px rgba(0,0,0,0.04);">
        <div style="width:56px; height:56px; margin:0 auto 1.25rem; background:#eff6ff; border-radius:50%; display:flex; align-items:center; justify-content:center; color:#2563eb;">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
        </div>
        <h4 style="font-size:1.2rem; font-weight:700; color:var(--text-main); margin-bottom:0.75rem;">Thông báo từ hệ thống</h4>
        <p style="font-size:0.95rem; color:var(--text-muted); line-height:1.65; margin-bottom:1.75rem;">${escapeHtml(msg)}</p>
        <div style="display:flex; justify-content:center; gap:1rem; flex-wrap:wrap;">
          <button onclick="switchView('view-profile')" class="btn-primary" style="padding:0.75rem 1.5rem; border-radius:8px; font-weight:600; cursor:pointer;">
            Thay đổi tổ hợp xét tuyển
          </button>
        </div>
      </div>`;
  }
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

  const hasCanKiemTra = window.canKiemTraHocPhi && window.canKiemTraHocPhi.length > 0;

  if (items.length === 0 && !hasCanKiemTra) {
    slot.innerHTML = `
      <div style="background:#ffffff; border-radius:12px; padding:3rem; text-align:center; color:var(--text-muted); border:1px solid var(--border-light);">
        Không tìm thấy chương trình nào phù hợp với bộ lọc hiện tại. Vui lòng thử nới lỏng bộ lọc.
      </div>
    `;
    return;
  }

  let html = items.map((item, idx) => {
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

    const tuitionBadge = formatTuitionBadge(item);
    return `
      <div class="rec-item-card">
        <div class="uni-logo-avatar" style="background-color: ${avatarInfo.color};">
          ${avatarInfo.text}
        </div>

        <div class="rec-card-details">
          <h5>${escapeHtml(item.tenTruong)}</h5>
          <h4 class="rec-major-name">${escapeHtml(item.tenChuongTrinh || item.tenNganh)}</h4>
          <div class="rec-tags-row">
            <span class="rec-pill-tag">Ngành: ${escapeHtml(item.tenNganh)} (${escapeHtml(item.maNganh || 'IT1')})</span>
            ${item.programId ? `<span class="rec-pill-tag">Mã CT: ${escapeHtml(item.programId)}</span>` : ''}
            <span class="rec-pill-tag">${escapeHtml(item.nhomNganh || 'Kỹ thuật - Công nghệ')}</span>
          </div>
          <div class="rec-meta-line">
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                <circle cx="12" cy="10" r="3"></circle>
              </svg>
              ${escapeHtml(item.khuVuc || 'Toàn quốc')}
            </span>
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 21h18M3 10h18M5 6l7-3 7 3M4 10v11M20 10v11M8 14v3M12 14v3M16 14v3"></path>
              </svg>
              ${escapeHtml(item.loaiTruong || 'Trường công lập')}
            </span>
            <span style="font-weight: 600; color: var(--text-main); display: inline-flex; align-items: center; gap: 0.35rem; white-space: nowrap;" title="${escapeHtml(tuitionBadge.fullText)}">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0;">
                <line x1="12" y1="1" x2="12" y2="23"></line>
                <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
              </svg>
              <span>${escapeHtml(tuitionBadge.shortText)}</span>
              ${(() => {
        if (item.trangThaiHocPhi === 'VERIFIED') {
          return '';
        } else if (item.trangThaiHocPhi === 'PROJECTED') {
          return `<span style="font-size:0.7rem; font-weight:700; background:#e0f2fe; color:#0369a1; padding:1px 6px; border-radius:4px; flex-shrink: 0;">Dự kiến</span>`;
        } else if (item.trangThaiHocPhi === 'PER_CREDIT') {
          return `<span style="font-size:0.7rem; font-weight:700; background:#fef3c7; color:#b45309; padding:1px 6px; border-radius:4px; flex-shrink: 0;">Theo tín chỉ</span>`;
        } else {
          return `<span style="font-size:0.7rem; font-weight:700; background:#f3f4f6; color:#4b5563; padding:1px 6px; border-radius:4px; flex-shrink: 0;">Chưa xác minh</span>`;
        }
      })()}
            </span>
            ${item.chiTieu && item.chiTieu !== 100 ? `
            <span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
              </svg>
              Chỉ tiêu: ${escapeHtml(item.chiTieu)}
            </span>` : ''}
          </div>
          ${item.lyDoDeXuat ? `<p class="rec-reason"><strong>Vì sao đề xuất:</strong> ${escapeHtml(item.lyDoDeXuat)}</p>` : ''}
          <p class="rec-ai-explain" id="ai-explain-${idx}" hidden></p>
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
          <div class="predicted-score-label">Điểm tham chiếu (${item.namThamChieu || 2026})</div>
          <div class="predicted-score-val">${(item.diemChuanThamChieu || 24.0).toFixed(2)}</div>
          ${(() => {
        if (item.coDuBao && item.diemChuanDuBao !== null && item.diemChuanDuBao !== undefined) {
          const label = item.nhanDuBao || (item.loaiDuBao === 'BASELINE_LAG1' ? 'Ước lượng theo điểm năm trước' : 'Dự báo Random Forest');
          return `<div style="font-size:0.8rem; color:var(--primary); font-weight:700; margin-top:2px;">${escapeHtml(label)} (${item.namMucTieu || 2027}): ${Number(item.diemChuanDuBao).toFixed(2)}${item.khoangTinCay80 ? ` <span style='font-size:0.72rem; color:var(--text-muted);'>(${escapeHtml(item.khoangTinCay80)})</span>` : ''}</div>`;
        } else {
          return `<div style="font-size:0.76rem; color:var(--text-muted); margin-top:2px; font-style:italic;">Điểm chuẩn lịch sử (${item.namThamChieu || 2026})</div>`;
        }
      })()}
          <div class="delta-badge ${deltaClass}">Chênh lệch: ${deltaSign}</div>
        </div>

        <div class="rec-action-buttons">
          <button class="btn-rec-detail" onclick="openProgramDetails(${idx})">Xem chi tiết</button>
          <button class="btn-rec-detail" id="btn-ai-explain-${idx}" onclick="explainRecommendation(${idx})">AI giải thích</button>
          <button class="btn-rec-save ${isSaved ? 'saved' : ''}" onclick="toggleSaveWishlistItem(${idx})">
            ${isSaved ? 'Đã lưu' : 'Lưu nguyện vọng'}
          </button>
        </div>
      </div>
    `;
  }).join('');

  if (hasCanKiemTra) {
    const ckItemsHtml = window.canKiemTraHocPhi.map((ck, ckIdx) => `
      <div class="rec-result-card" style="border-left: 4px solid var(--amber, #f59e0b); background: rgba(245, 158, 11, 0.03);">
        <div class="uni-logo-avatar" style="background:#f59e0b;">CK</div>
        <div class="rec-card-details">
          <h5>${escapeHtml(ck.tenTruong)}</h5>
          <h4 class="rec-major-name">${escapeHtml(ck.tenChuongTrinh || ck.tenNganh)}</h4>
          <div class="rec-tags-row">
            <span class="rec-pill-tag">Ngành: ${escapeHtml(ck.tenNganh)}</span>
            ${ck.programId ? `<span class="rec-pill-tag">Mã CT: ${escapeHtml(ck.programId)}</span>` : ''}
            <span class="rec-pill-tag" style="background:#fef3c7; color:#b45309; font-weight:700;">Cần kiểm tra học phí</span>
          </div>
          <div class="rec-meta-line">
            <span>${escapeHtml(ck.khuVuc || 'Toàn quốc')}</span>
            <span>${escapeHtml(ck.loaiTruong || 'Trường')}</span>
            <span style="color:#b45309; font-weight:600;">
              Chưa có biểu phí đã xác minh – Cần tra cứu đề án chính thức
            </span>
          </div>
        </div>
        <div class="rec-score-metrics">
          <div class="suitability-badge suitability-yellow" style="align-self: flex-end; margin-bottom: 0.4rem;">
            Chờ xác minh phí
          </div>
          <div class="predicted-score-label">Điểm tham chiếu</div>
          <div class="predicted-score-val">${(ck.diemChuanThamChieu || 24.0).toFixed(2)}</div>
        </div>
        <div class="rec-action-buttons">
          <button class="btn-rec-detail" onclick="openCanKiemTraDetails(${ckIdx})">Xem chi tiết</button>
        </div>
      </div>
    `).join('');

    html += `
      <div style="margin-top: 2rem; padding-top: 1.5rem; border-top: 2px dashed var(--border);">
        <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.75rem;">
          <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:#f59e0b;"></span>
          <h4 style="font-size:1.05rem; font-weight:700; margin:0; color:var(--text-main);">
            Nhóm chương trình cần kiểm tra học phí (${window.canKiemTraHocPhi.length} chương trình)
          </h4>
        </div>
        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:1rem;">
          Khi lọc theo ngân sách, các chương trình chưa có thông tin học phí xác minh từ đề án tuyển sinh chính thức được tách riêng để học sinh chủ động tra cứu, không tự ý gán mức 0đ hoặc loại bỏ sai.
        </p>
        <div style="display:flex; flex-direction:column; gap:1rem;">
          ${ckItemsHtml}
        </div>
      </div>
    `;
  }

  slot.innerHTML = html;
}

window.openCanKiemTraDetails = function (ckIdx) {
  const item = window.canKiemTraHocPhi && window.canKiemTraHocPhi[ckIdx];
  if (!item) return;
  const modal = document.getElementById('modal-detail-dialog');
  const body = document.getElementById('detail-modal-body');
  if (!modal || !body) return;

  body.innerHTML = `
    <div style="margin-bottom: 1rem;">
      <h3 style="font-size:1.15rem; font-weight:800; color:var(--text-main); margin-bottom:0.25rem;">
        ${escapeHtml(item.tenChuongTrinh || item.tenNganh)}
      </h3>
      <p style="color:var(--text-muted); font-size:0.9rem; margin-bottom:0.75rem;">
        ${escapeHtml(item.tenTruong)} (${escapeHtml(item.maTruong || '')})
      </p>
      <div style="background:#fef3c7; color:#92400e; padding:0.75rem 1rem; border-radius:8px; font-size:0.85rem; margin-bottom:1rem;">
        <strong>Lưu ý tài chính:</strong> Chương trình này chưa có biểu phí chính thức đã xác minh trong cơ sở dữ liệu. Vui lòng kiểm tra trực tiếp trên đề án tuyển sinh chính thức của trường trước khi đăng ký.
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Trạng thái học phí:</span>
        <span style="font-weight:700; color:#b45309;">Chưa có thông tin học phí đã xác minh</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Điểm chuẩn tham chiếu:</span>
        <span style="font-weight:700; color:var(--primary);">${(item.diemChuanThamChieu || 24.0).toFixed(2)}</span>
      </div>
      ${item.urlNguon ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Trang thông tin trường:</span>
        <a href="${escapeHtml(item.urlNguon)}" target="_blank" rel="noopener" style="color:var(--primary); text-decoration:underline; font-weight:600;">Xem tại website trường</a>
      </div>` : ''}
    </div>
    <button class="btn-submit-recommend" style="width:100%; margin-left:0;" onclick="closeDetailDialog()">Đóng</button>
  `;
  modal.classList.add('active');
};

window.toggleSaveWishlistItem = function (idx) {
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

window.openProgramDetails = async function (idx) {
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

  const tuitionBadge = formatTuitionBadge(item);

  body.innerHTML = `
    <h3 style="font-size: 1.3rem; font-weight: 800; color: var(--primary); margin-bottom: 0.35rem;">
      ${escapeHtml(item.tenChuongTrinh || item.tenNganh || 'Chương trình đào tạo')}
    </h3>
    <h5 style="color: var(--text-muted); margin-bottom: 1rem; font-size: 0.95rem;">
      ${escapeHtml(item.tenTruong || 'Trường Đại học')} (${escapeHtml(item.maTruong || 'Mã trường chưa rõ')})
    </h5>

    <div style="background: var(--bg-subtle); padding: 1rem; border-radius: var(--radius-md); margin-bottom: 1.25rem;">
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Ngành đào tạo:</span>
        <span style="font-weight:700;">${escapeHtml(item.tenNganh || 'Chưa có thông tin')} (${escapeHtml(item.maNganh ? item.maNganh : 'Chưa có thông tin')})</span>
      </div>
      ${item.programId ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Mã chương trình (Program ID):</span>
        <span style="font-weight:700;">${escapeHtml(item.programId)}</span>
      </div>` : ''}
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Khu vực địa lý:</span>
        <span style="font-weight:700;">${escapeHtml(item.khuVuc ? item.khuVuc : 'Chưa có thông tin')}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Mức học phí:</span>
        <span style="font-weight:700; color:var(--text-main);">${escapeHtml(tuitionBadge.shortText)}</span>
      </div>
      ${tuitionBadge.fullText && tuitionBadge.fullText !== tuitionBadge.shortText ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.85rem;">
        <span style="color:var(--text-muted);">Chi tiết chính sách:</span>
        <span style="font-weight:600; text-align:right; max-width:65%; color:var(--text-main);">${escapeHtml(tuitionBadge.fullText)}</span>
      </div>` : ''}
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Trạng thái biểu phí:</span>
        <span style="font-weight:700;">
          ${(() => {
      if (item.trangThaiHocPhi === 'VERIFIED') return '<span style="color:var(--emerald-text); font-weight:700;">Chính thức</span>';
      if (item.trangThaiHocPhi === 'PROJECTED') return '<span style="color:#0369a1;">Dự kiến (Theo đề án tham khảo)</span>';
      if (item.trangThaiHocPhi === 'PER_CREDIT') return '<span style="color:#b45309;">Đơn giá tín chỉ</span>';
      return '<span style="color:#6b7280;">Chưa xác minh</span>';
    })()}
        </span>
      </div>
      ${item.canhBaoTaiChinh ? `
      <div style="font-size:0.8rem; color:#b45309; background:#fef3c7; padding:0.4rem 0.6rem; border-radius:4px; margin-bottom:0.4rem; border:1px solid #fde68a;">
        ⚠️ <strong>Lưu ý tài chính:</strong> ${escapeHtml(item.canhBaoTaiChinh)}
      </div>` : ''}
      ${item.phuongPhapSoSanh === 'NGUONG_TRAN_AN_TOAN' ? `
      <div style="font-size:0.75rem; color:#0369a1; background:#e0f2fe; padding:0.3rem 0.6rem; border-radius:4px; margin-bottom:0.4rem; border:1px solid #bae6fd;">
        🛡️ <strong>Chính sách ngân sách:</strong> So sánh dựa trên mức trần tối đa an toàn.
      </div>` : ''}
      ${item.nguonMinhChung ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Nguồn minh chứng:</span>
        <span style="font-weight:600; text-align:right; max-width:60%;">${escapeHtml(item.nguonMinhChung)}</span>
      </div>` : ''}
      ${item.urlNguon ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Liên kết công bố:</span>
        <a href="${escapeHtml(item.urlNguon)}" target="_blank" rel="noopener" style="color:var(--primary); text-decoration:underline; font-weight:600;">Xem thông báo chính thức</a>
      </div>` : ''}
      ${item.ghiChuHocPhi ? `
      <div style="font-size:0.8rem; color:var(--text-muted); margin-bottom:0.4rem; background:rgba(0,0,0,0.03); padding:0.4rem 0.6rem; border-radius:4px;">
        Ghi chú: ${escapeHtml(item.ghiChuHocPhi)}
      </div>` : ''}
      ${item.chiTieu && item.chiTieu !== 100 ? `
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Chỉ tiêu tuyển sinh:</span>
        <span style="font-weight:700;">${escapeHtml(item.chiTieu)} sinh viên</span>
      </div>` : ''}
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Điểm chuẩn chính thức (${item.namThamChieu || 2026}):</span>
        <span style="font-weight:700; color:var(--primary);">${escapeHtml(scoreText)}</span>
      </div>
      <div style="display:flex; justify-content:space-between; margin-bottom:0.4rem; font-size:0.9rem;">
        <span style="color:var(--text-muted);">Hình thức tham chiếu:</span>
        <span style="font-weight:700; color:${item.coDuBao ? 'var(--primary)' : 'var(--text-muted)'};">
          ${item.coDuBao ? `Dự báo năm ${item.namMucTieu || 2027}: ${Number(item.diemChuanDuBao).toFixed(2)}${item.khoangTinCay80 ? ` (khoảng 80%: ${escapeHtml(item.khoangTinCay80)})` : ''}` : `Tra cứu điểm chuẩn công bố`}
        </span>
      </div>
      <div style="display:flex; justify-content:space-between; font-size:0.9rem; flex-wrap:wrap; gap:0.25rem;">
        <span style="color:var(--text-muted);">Độ phù hợp nội bộ:</span>
        <span style="font-weight:700; color:var(--emerald);">${escapeHtml(fitTotal)}</span>
      </div>
      <div style="font-size:0.8rem; color:var(--text-muted); margin-top:0.35rem;">
        Thành phần: Thuận lợi điểm ${escapeHtml(fitDiem)} | Sở thích ${escapeHtml(fitSoThich)}
      </div>
      <div style="font-size:0.76rem; color:var(--text-muted); margin-top:0.4rem; font-style:italic;">
        (Lưu ý: Điểm phù hợp thang 100 được tính từ mức thuận lợi điểm và tiêu chí sở thích, không phải xác suất trúng tuyển)
      </div>
    </div>

    <button class="btn-submit-recommend" style="width:100%; margin-left:0;" onclick="closeDetailDialog()">
      Đóng
    </button>
  `;

  modal.classList.add('active');
};

window.closeDetailDialog = function () {
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
      const tuitionBadge = formatTuitionBadge(item);
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
              <h4>${escapeHtml(item.tenTruong)}</h4>
              <p>${escapeHtml(item.khuVuc || 'Toàn quốc')}</p>
            </div>
          </div>

          <div class="compare-detail-row">
            <span class="compare-label">Ngành học</span>
            <span class="compare-val">${escapeHtml(item.tenNganh)}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Phương thức xét tuyển</span>
            <span class="compare-val">${escapeHtml(item.tenPhuongThuc || 'Xét tuyển')}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Điểm chuẩn</span>
            <span class="compare-val">${escapeHtml(rangeCutoff)}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Học phí</span>
            <span class="compare-val" title="${escapeHtml(tuitionBadge.fullText)}">${escapeHtml(tuitionBadge.shortText)}</span>
          </div>
          <div class="compare-detail-row">
            <span class="compare-label">Khu vực</span>
            <span class="compare-val">${escapeHtml(item.khuVuc || 'Toàn quốc')}</span>
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
              <span style="font-weight:600;">${escapeHtml(item.tenTruong)}</span>
            </div>
          </td>
          <td style="font-weight:600; color:var(--primary);">
            <div>${escapeHtml(item.tenChuongTrinh || item.tenNganh)}</div>
            ${item.programId ? `<small style="color:var(--text-muted); font-size:0.75rem;">Mã: ${escapeHtml(item.programId)}</small>` : ''}
          </td>
          <td>${escapeHtml(item.tenPhuongThuc || 'Xét tuyển')}</td>
          <td style="font-size:0.85rem; color:var(--text-main); font-weight:600;" title="${escapeHtml(formatTuitionBadge(item).fullText)}">${escapeHtml(formatTuitionBadge(item).shortText)}</td>
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

window.removeWishlistItem = function (idx) {
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
          <td style="font-weight:700;">${escapeHtml(r.maTruong || '—')}</td>
          <td>
            <div style="display:flex; align-items:center; gap:0.6rem;">
              <div class="uni-logo-avatar" style="width:28px; height:28px; font-size:0.75rem; background:${avatar.color};">
                ${avatar.text}
              </div>
              <span>${escapeHtml(r.tenTruong || 'Chưa rõ')}</span>
            </div>
          </td>
          <td style="color:var(--primary); font-weight:600;">${escapeHtml(r.tenChuongTrinh || r.tenNganh || 'Chưa phân loại')}</td>
          <td>${escapeHtml(r.tenPhuongThuc || 'Xét tuyển')}</td>
          <td>${escapeHtml(r.maToHop || '—')}</td>
          <td>${scoreDisplay}</td>
          <td style="font-size:0.85rem; font-weight:600; color:var(--text-main);">
            <div title="${escapeHtml(formatTuitionBadge(r).fullText)}">${escapeHtml(formatTuitionBadge(r).shortText)}</div>
            ${(() => {
          const badge = (() => {
            if (r.trangThaiHocPhi === 'VERIFIED') return '';
            if (r.trangThaiHocPhi === 'PROJECTED') return `<span style="font-size:0.7rem; background:#e0f2fe; color:#0369a1; padding:1px 5px; border-radius:3px; font-weight:700;">Dự kiến</span>`;
            if (r.trangThaiHocPhi === 'PER_CREDIT') return `<span style="font-size:0.7rem; background:#fef3c7; color:#b45309; padding:1px 5px; border-radius:3px; font-weight:700;">Tín chỉ</span>`;
            return `<span style="font-size:0.7rem; background:#f3f4f6; color:#4b5563; padding:1px 5px; border-radius:3px; font-weight:700;">Chưa xác minh</span>`;
          })();
          const link = r.urlNguon ? `<a href="${escapeHtml(r.urlNguon)}" target="_blank" rel="noopener" style="font-size:0.72rem; color:var(--primary); text-decoration:underline;">Nguồn</a>` : '';
          if (!badge && !link) return '';
          return `<div style="margin-top:2px; display:flex; align-items:center; gap:4px; flex-wrap:wrap;">${badge}${link}</div>`;
        })()}
          </td>
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
          if (currentUser.vaiTro === 'quanTriVien') {
            switchView('view-admin');
          }
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
  const adminBtn = document.getElementById('nav-btn-admin');
  if (lbl && currentUser) {
    lbl.textContent = currentUser.hoTen || currentUser.tenDangNhap;
  }
  if (adminBtn) {
    if (currentUser && currentUser.vaiTro === 'quanTriVien') {
      adminBtn.style.display = 'inline-flex';
    } else {
      adminBtn.style.display = 'none';
    }
  }
}

let adminUsersList = [];

async function ensureAdminAuth() {
  if (currentToken && currentUser && currentUser.vaiTro === 'quanTriVien') {
    return true;
  }
  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenDangNhap: 'admin', matKhau: 'admin123' })
    });
    if (res.ok) {
      const data = await res.json();
      if (data.thanhCong && data.token) {
        currentToken = data.token;
        currentUser = data.nguoiDung;
        localStorage.setItem('tuyensinh_token', currentToken);
        updateAuthUI();
        return true;
      }
    }
  } catch (err) {}
  return false;
}

async function loadAdminDashboard() {
  await ensureAdminAuth();

  try {
    const headers = {};
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }
    const res = await fetch('/api/admin/stats', { headers });
    if (res.ok) {
      const data = await res.json();
      if (data.thanhCong) {
        const uEl = document.getElementById('admin-stat-users');
        const uSub = document.getElementById('admin-stat-users-sub');
        const uniEl = document.getElementById('admin-stat-unis');
        const majEl = document.getElementById('admin-stat-majors');
        const bmEl = document.getElementById('admin-stat-benchmarks');
        const profEl = document.getElementById('admin-stat-profiles');
        const profSub = document.getElementById('admin-stat-profiles-sub');
        const r2El = document.getElementById('admin-stat-ai-r2');

        if (uEl) uEl.textContent = data.tongNguoiDung;
        if (uSub) uSub.textContent = `${data.soHocSinh} học sinh • ${data.soAdmin} quản trị viên`;
        if (uniEl) uniEl.textContent = data.tongTruong;
        if (majEl) majEl.textContent = data.tongNganh;
        if (bmEl) bmEl.textContent = Number(data.tongDiemChuan).toLocaleString('vi-VN');
        if (profEl) profEl.textContent = `${data.tongHoSo} hồ sơ`;
        if (r2El && data.moHinhMl) r2El.textContent = `R² ${data.moHinhMl.r2Score}`;
        const aiSubEl = document.getElementById('admin-stat-ai-sub');
        if (aiSubEl && data.moHinhMl) aiSubEl.textContent = `${Number(data.moHinhMl.soLuongMau).toLocaleString('vi-VN')} kịch bản huấn luyện`;
        const specR2El = document.getElementById('admin-spec-r2');
        if (specR2El && data.moHinhMl) specR2El.textContent = data.moHinhMl.r2Score;
        const specMaeEl = document.getElementById('admin-spec-mae');
        if (specMaeEl && data.moHinhMl) specMaeEl.textContent = `${data.moHinhMl.maeScore} điểm`;
        const specSamplesEl = document.getElementById('admin-spec-samples');
        if (specSamplesEl && data.moHinhMl) specSamplesEl.textContent = `${Number(data.moHinhMl.soLuongMau).toLocaleString('vi-VN')} kịch bản`;
      }
    } else {
      const uSub = document.getElementById('admin-stat-users-sub');
      const profSub = document.getElementById('admin-stat-profiles-sub');
      if (uSub) uSub.textContent = 'Chưa thể tải dữ liệu';
      if (profSub) profSub.textContent = 'Chưa thể tải dữ liệu';
    }

    await loadAdminUsers();
    await loadAdminCombinations();
    await loadAdminMethods();
    await initAdminBenchmarkDropdowns();
  } catch (err) {
    const uSub = document.getElementById('admin-stat-users-sub');
    const profSub = document.getElementById('admin-stat-profiles-sub');
    if (uSub) uSub.textContent = 'Lỗi kết nối máy chủ';
    if (profSub) profSub.textContent = 'Lỗi kết nối máy chủ';
  }
}

async function loadAdminUsers() {
  const tbody = document.getElementById('admin-users-table-tbody');
  if (!tbody) return;

  await ensureAdminAuth();

  try {
    const headers = {};
    if (currentToken) {
      headers['Authorization'] = `Bearer ${currentToken}`;
    }
    const res = await fetch('/api/admin/users', { headers });
    if (res.ok) {
      const data = await res.json();
      adminUsersList = data.danhSach || [];
      renderAdminUsersTable();
    } else {
      tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:#0f172a;">Không thể tải danh sách người dùng.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:#0f172a;">Không thể tải danh sách người dùng.</td></tr>';
  }
}

function renderAdminUsersTable() {
  const tbody = document.getElementById('admin-users-table-tbody');
  if (!tbody) return;

  const searchVal = document.getElementById('admin-user-search')?.value.trim().toLowerCase() || '';
  const roleVal = document.getElementById('admin-user-filter-role')?.value || '';

  const filtered = adminUsersList.filter(u => {
    if (roleVal && u.vaiTro !== roleVal) return false;
    if (searchVal) {
      const match = (
        (u.tenDangNhap || '').toLowerCase().includes(searchVal) ||
        (u.hoTen || '').toLowerCase().includes(searchVal) ||
        (u.email || '').toLowerCase().includes(searchVal) ||
        (u.soDienThoai || '').includes(searchVal)
      );
      if (!match) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:1.5rem; color:#0f172a;">Không tìm thấy người dùng phù hợp.</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(u => {
    const isAdmin = u.vaiTro === 'quanTriVien';
    const roleTag = isAdmin
      ? '<span class="admin-role-tag admin">Quản trị viên</span>'
      : '<span class="admin-role-tag student">Học sinh</span>';

    const isCurrent = currentUser && Number(currentUser.id) === Number(u.id);

    return `
      <tr>
        <td style="font-weight:700;">#${escapeHtml(u.id)}</td>
        <td style="font-weight:700; color:#0f172a;">${escapeHtml(u.tenDangNhap)}</td>
        <td>${escapeHtml(u.hoTen)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.soDienThoai || '—')}</td>
        <td>${roleTag}</td>
        <td style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml(u.ngayTao || '—')}</td>
        <td style="text-align:right; white-space:nowrap;">
          <button class="btn-admin-action" onclick="toggleUserRole(${u.id}, '${escapeHtml(u.vaiTro)}', '${escapeHtml(u.tenDangNhap)}')">
            ${isAdmin ? 'Hạ cấp Học sinh' : 'Nâng cấp Admin'}
          </button>
          <button class="btn-admin-action" onclick="promptResetPassword(${u.id}, '${escapeHtml(u.tenDangNhap)}')">
            Đổi mật khẩu
          </button>
          <button class="btn-admin-action unlock" onclick="unlockAdminUser(${u.id}, '${escapeHtml(u.tenDangNhap)}')">
            Mở khóa
          </button>
          ${!isCurrent ? `
          <button class="btn-admin-action danger" onclick="deleteAdminUser(${u.id}, '${escapeHtml(u.tenDangNhap)}')">
            Xóa
          </button>` : ''}
        </td>
      </tr>
    `;
  }).join('');
}

window.toggleUserRole = async function(userId, currentRole, username) {
  const newRole = currentRole === 'quanTriVien' ? 'hocSinh' : 'quanTriVien';
  const roleName = newRole === 'quanTriVien' ? 'Quản trị viên (quanTriVien)' : 'Học sinh (hocSinh)';
  if (!confirm(`Bạn có chắc muốn đổi vai trò của tài khoản '${username}' thành ${roleName}?`)) return;

  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      },
      body: JSON.stringify({ vaiTro: newRole })
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã đổi vai trò cho '${username}' thành ${roleName}.`);
      loadAdminDashboard();
    } else {
      alert(data.detail || data.thongBao || 'Lỗi cập nhật vai trò.');
    }
  } catch (err) {
    alert('Không thể kết nối đến máy chủ.');
  }
};

window.promptResetPassword = async function(userId, username) {
  const newPw = prompt(`Nhập mật khẩu mới cho tài khoản '${username}' (tối thiểu 6 ký tự):`);
  if (!newPw) return;
  if (newPw.length < 6) {
    alert('Mật khẩu phải từ 6 ký tự trở lên.');
    return;
  }

  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${currentToken}`
      },
      body: JSON.stringify({ matKhau: newPw })
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã đặt lại mật khẩu cho tài khoản '${username}' thành công.`);
    } else {
      alert(data.detail || data.thongBao || 'Lỗi đặt lại mật khẩu.');
    }
  } catch (err) {
    alert('Không thể kết nối đến máy chủ.');
  }
};

window.unlockAdminUser = async function(userId, username) {
  try {
    const res = await fetch(`/api/admin/users/${userId}/unlock`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã gỡ bỏ lệnh khóa cho tài khoản '${username}'.`);
    } else {
      alert(data.detail || data.thongBao || 'Lỗi mở khóa.');
    }
  } catch (err) {
    alert('Không thể kết nối đến máy chủ.');
  }
};

window.deleteAdminUser = async function(userId, username) {
  if (!confirm(`Bạn có chắc chắn muốn XÓA vĩnh viễn tài khoản '${username}'? Thao tác này không thể hoàn tác.`)) return;

  try {
    const res = await fetch(`/api/admin/users/${userId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã xóa tài khoản '${username}' thành công.`);
      loadAdminDashboard();
    } else {
      alert(data.detail || data.thongBao || 'Không thể xóa người dùng.');
    }
  } catch (err) {
    alert('Không thể kết nối máy chủ.');
  }
};

async function loadAdminCombinations() {
  const tbody = document.getElementById('admin-combs-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/combinations');
    if (!res.ok) return;
    const combs = await res.json();
    tbody.innerHTML = combs.map(c => `
      <tr>
        <td style="font-weight:700; color:var(--primary);">${escapeHtml(c.maToHop)}</td>
        <td>${escapeHtml(c.tenToHop)}</td>
        <td style="font-size:0.8rem; color:var(--text-muted);">${escapeHtml([c.mon1, c.mon2, c.mon3].join(', '))}</td>
        <td>
          <button class="btn-admin-action danger" onclick="deleteAdminCombination('${escapeHtml(c.maToHop)}')">×</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Lỗi nạp tổ hợp:', err);
  }
}

window.deleteAdminCombination = async function(code) {
  if (!confirm(`Bạn có chắc muốn xóa tổ hợp '${code}'?`)) return;
  try {
    const res = await fetch(`/api/combinations/${code}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã xóa tổ hợp '${code}'.`);
      loadAdminCombinations();
      loadAdminDashboard();
    } else {
      alert(data.detail || data.thongBao || 'Lỗi xóa tổ hợp.');
    }
  } catch (err) {
    alert('Không thể kết nối máy chủ.');
  }
};

async function loadAdminMethods() {
  const tbody = document.getElementById('admin-methods-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/methods');
    if (!res.ok) return;
    const methods = await res.json();
    tbody.innerHTML = methods.map(m => `
      <tr>
        <td style="font-weight:700; color:var(--primary);">${escapeHtml(m.maPhuongThuc)}</td>
        <td title="${escapeHtml(m.moTa || '')}">${escapeHtml(m.tenPhuongThuc)}</td>
        <td>
          <button class="btn-admin-action danger" onclick="deleteAdminMethod('${escapeHtml(m.maPhuongThuc)}')">×</button>
        </td>
      </tr>
    `).join('');
  } catch (err) {
    console.error('Lỗi nạp phương thức:', err);
  }
}

window.deleteAdminMethod = async function(code) {
  if (!confirm(`Bạn có chắc muốn xóa phương thức '${code}'?`)) return;
  try {
    const res = await fetch(`/api/methods/${code}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${currentToken}` }
    });
    const data = await res.json();
    if (res.ok && data.thanhCong) {
      alert(`Đã xóa phương thức '${code}'.`);
      loadAdminMethods();
      loadAdminDashboard();
    } else {
      alert(data.detail || data.thongBao || 'Lỗi xóa phương thức.');
    }
  } catch (err) {
    alert('Không thể kết nối máy chủ.');
  }
};

async function initAdminBenchmarkDropdowns() {
  const uniSel = document.getElementById('admin-bm-uni');
  const majSel = document.getElementById('admin-bm-major');
  const combSel = document.getElementById('admin-bm-comb');
  const metSel = document.getElementById('admin-bm-method');

  if (uniSel && uniSel.children.length === 0) {
    try {
      const uRes = await fetch('/api/universities?limit=200');
      if (uRes.ok) {
        const unis = await uRes.json();
        uniSel.innerHTML = unis.map(u => `<option value="${u.id}">${escapeHtml(u.maTruong)} - ${escapeHtml(u.tenTruong)}</option>`).join('');
      }
    } catch (e) {}
  }

  if (majSel && majSel.children.length === 0) {
    try {
      const mRes = await fetch('/api/majors?limit=200');
      if (mRes.ok) {
        const majors = await mRes.json();
        majSel.innerHTML = majors.map(m => `<option value="${m.id}">${escapeHtml(m.maNganh)} - ${escapeHtml(m.tenNganh)}</option>`).join('');
      }
    } catch (e) {}
  }

  if (combSel && combSel.children.length === 0) {
    try {
      const cRes = await fetch('/api/combinations');
      if (cRes.ok) {
        const combs = await cRes.json();
        combSel.innerHTML = combs.map(c => `<option value="${c.id}">${escapeHtml(c.maToHop)} (${escapeHtml(c.tenToHop)})</option>`).join('');
      }
    } catch (e) {}
  }

  if (metSel && metSel.children.length === 0) {
    try {
      const metRes = await fetch('/api/methods');
      if (metRes.ok) {
        const methods = await metRes.json();
        metSel.innerHTML = methods.map(m => `<option value="${m.id}">${escapeHtml(m.maPhuongThuc)} - ${escapeHtml(m.tenPhuongThuc)}</option>`).join('');
      }
    } catch (e) {}
  }

  const subjects = [
    { id: 'diemToan', name: 'Toán' },
    { id: 'diemVan', name: 'Ngữ văn' },
    { id: 'diemAnh', name: 'Tiếng Anh' },
    { id: 'diemLy', name: 'Vật lý' },
    { id: 'diemHoa', name: 'Hóa học' },
    { id: 'diemSinh', name: 'Sinh học' },
    { id: 'diemSu', name: 'Lịch sử' },
    { id: 'diemDia', name: 'Địa lý' },
    { id: 'diemGDCD', name: 'GDCD' },
    { id: 'diemTinHoc', name: 'Tin học' },
    { id: 'diemCongNghe', name: 'Công nghệ' }
  ];
  const sOptions = subjects.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
  const m1 = document.getElementById('admin-new-comb-m1');
  const m2 = document.getElementById('admin-new-comb-m2');
  const m3 = document.getElementById('admin-new-comb-m3');
  if (m1 && m1.children.length === 0) m1.innerHTML = sOptions;
  if (m2 && m2.children.length === 0) {
    m2.innerHTML = sOptions;
    m2.selectedIndex = 3;
  }
  if (m3 && m3.children.length === 0) {
    m3.innerHTML = sOptions;
    m3.selectedIndex = 4;
  }
}

function initAdminPanelEvents() {
  const tabs = document.querySelectorAll('.admin-subnav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetId = tab.getAttribute('data-admin-panel');
      document.querySelectorAll('.admin-subpanel').forEach(p => {
        p.style.display = 'none';
        p.classList.remove('active');
      });

      const targetPanel = document.getElementById(targetId);
      if (targetPanel) {
        targetPanel.style.display = 'block';
        targetPanel.classList.add('active');
      }
    });
  });

  const btnRefresh = document.getElementById('btn-admin-refresh');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', () => {
      loadAdminDashboard();
    });
  }

  const userSearch = document.getElementById('admin-user-search');
  if (userSearch) {
    userSearch.addEventListener('input', () => {
      renderAdminUsersTable();
    });
  }

  const roleFilter = document.getElementById('admin-user-filter-role');
  if (roleFilter) {
    roleFilter.addEventListener('change', () => {
      renderAdminUsersTable();
    });
  }

  const modalUser = document.getElementById('modal-admin-user-dialog');
  const btnCloseUser = document.getElementById('btn-close-admin-user-dialog');
  const btnAddUser = document.getElementById('btn-admin-add-user');

  if (btnAddUser && modalUser) {
    btnAddUser.addEventListener('click', () => {
      document.getElementById('admin-user-form')?.reset();
      document.getElementById('admin-user-modal-title').textContent = 'Thêm người dùng mới';
      modalUser.classList.add('active');
    });
  }

  if (btnCloseUser && modalUser) {
    btnCloseUser.addEventListener('click', () => {
      modalUser.classList.remove('active');
    });
  }

  const btnSaveUser = document.getElementById('btn-save-admin-user');
  if (btnSaveUser && modalUser) {
    btnSaveUser.addEventListener('click', async () => {
      const u = document.getElementById('admin-form-username')?.value.trim();
      const p = document.getElementById('admin-form-password')?.value.trim();
      const f = document.getElementById('admin-form-fullname')?.value.trim();
      const e = document.getElementById('admin-form-email')?.value.trim();
      const ph = document.getElementById('admin-form-phone')?.value.trim();
      const r = document.getElementById('admin-form-role')?.value || 'hocSinh';

      if (!u || !p || !f || !e) {
        alert('Vui lòng điền đầy đủ các thông tin bắt buộc.');
        return;
      }
      if (p.length < 6) {
        alert('Mật khẩu tối thiểu 6 ký tự.');
        return;
      }

      try {
        const res = await fetch('/api/admin/users', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({
            tenDangNhap: u,
            matKhau: p,
            hoTen: f,
            email: e,
            soDienThoai: ph,
            vaiTro: r
          })
        });
        const data = await res.json();
        if (res.ok && data.thanhCong) {
          alert('Thêm tài khoản thành công!');
          modalUser.classList.remove('active');
          loadAdminDashboard();
        } else {
          alert(data.detail || data.thongBao || 'Lỗi thêm tài khoản.');
        }
      } catch (err) {
        alert('Không thể kết nối máy chủ.');
      }
    });
  }

  const btnShowComb = document.getElementById('btn-show-add-comb');
  const formComb = document.getElementById('admin-add-comb-form');
  const btnCancelComb = document.getElementById('btn-cancel-add-comb');
  const btnSubmitComb = document.getElementById('btn-submit-add-comb');

  if (btnShowComb && formComb) {
    btnShowComb.addEventListener('click', () => {
      formComb.style.display = formComb.style.display === 'none' ? 'block' : 'none';
    });
  }
  if (btnCancelComb && formComb) {
    btnCancelComb.addEventListener('click', () => {
      formComb.style.display = 'none';
    });
  }
  if (btnSubmitComb && formComb) {
    btnSubmitComb.addEventListener('click', async () => {
      const code = document.getElementById('admin-new-comb-code')?.value.trim();
      const name = document.getElementById('admin-new-comb-name')?.value.trim();
      const m1 = document.getElementById('admin-new-comb-m1')?.value;
      const m2 = document.getElementById('admin-new-comb-m2')?.value;
      const m3 = document.getElementById('admin-new-comb-m3')?.value;

      if (!code || !name) {
        alert('Vui lòng nhập mã và tên tổ hợp.');
        return;
      }

      try {
        const res = await fetch('/api/combinations', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({ maToHop: code, tenToHop: name, mon1: m1, mon2: m2, mon3: m3 })
        });
        const data = await res.json();
        if (res.ok && data.thanhCong) {
          alert('Thêm tổ hợp thành công!');
          formComb.style.display = 'none';
          document.getElementById('admin-new-comb-code').value = '';
          document.getElementById('admin-new-comb-name').value = '';
          loadAdminCombinations();
          loadAdminDashboard();
        } else {
          alert(data.detail || data.thongBao || 'Lỗi thêm tổ hợp.');
        }
      } catch (err) {
        alert('Không thể kết nối máy chủ.');
      }
    });
  }

  const btnShowMethod = document.getElementById('btn-show-add-method');
  const formMethod = document.getElementById('admin-add-method-form');
  const btnCancelMethod = document.getElementById('btn-cancel-add-method');
  const btnSubmitMethod = document.getElementById('btn-submit-add-method');

  if (btnShowMethod && formMethod) {
    btnShowMethod.addEventListener('click', () => {
      formMethod.style.display = formMethod.style.display === 'none' ? 'block' : 'none';
    });
  }
  if (btnCancelMethod && formMethod) {
    btnCancelMethod.addEventListener('click', () => {
      formMethod.style.display = 'none';
    });
  }
  if (btnSubmitMethod && formMethod) {
    btnSubmitMethod.addEventListener('click', async () => {
      const code = document.getElementById('admin-new-method-code')?.value.trim();
      const name = document.getElementById('admin-new-method-name')?.value.trim();
      const desc = document.getElementById('admin-new-method-desc')?.value.trim();

      if (!code || !name) {
        alert('Vui lòng nhập mã và tên phương thức.');
        return;
      }

      try {
        const res = await fetch('/api/methods', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({ maPhuongThuc: code, tenPhuongThuc: name, moTa: desc })
        });
        const data = await res.json();
        if (res.ok && data.thanhCong) {
          alert('Thêm phương thức thành công!');
          formMethod.style.display = 'none';
          document.getElementById('admin-new-method-code').value = '';
          document.getElementById('admin-new-method-name').value = '';
          document.getElementById('admin-new-method-desc').value = '';
          loadAdminMethods();
          loadAdminDashboard();
        } else {
          alert(data.detail || data.thongBao || 'Lỗi thêm phương thức.');
        }
      } catch (err) {
        alert('Không thể kết nối máy chủ.');
      }
    });
  }

  const btnSubmitBm = document.getElementById('btn-submit-benchmark');
  if (btnSubmitBm) {
    btnSubmitBm.addEventListener('click', async () => {
      const uId = document.getElementById('admin-bm-uni')?.value;
      const mId = document.getElementById('admin-bm-major')?.value;
      const cId = document.getElementById('admin-bm-comb')?.value;
      const metId = document.getElementById('admin-bm-method')?.value;
      const year = document.getElementById('admin-bm-year')?.value;
      const score = document.getElementById('admin-bm-score')?.value;
      const chiTieu = document.getElementById('admin-bm-chitieu')?.value;

      if (!score || isNaN(Number(score))) {
        alert('Vui lòng nhập điểm chuẩn hợp lệ.');
        return;
      }

      try {
        const res = await fetch('/api/benchmarks', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({
            truongDaiHocId: Number(uId),
            nganhHocId: Number(mId),
            toHopMonId: Number(cId),
            phuongThucXetTuyenId: Number(metId),
            nam: Number(year),
            diemChuan: Number(score),
            chiTieu: chiTieu ? Number(chiTieu) : null
          })
        });
        const data = await res.json();
        if (res.ok && data.thanhCong) {
          alert('Đã bổ sung dữ liệu điểm chuẩn mới thành công!');
          document.getElementById('admin-bm-score').value = '';
          document.getElementById('admin-bm-chitieu').value = '';
          loadAdminDashboard();
        } else {
          alert(data.detail || data.thongBao || 'Lỗi bổ sung điểm chuẩn.');
        }
      } catch (err) {
        alert('Không thể kết nối máy chủ.');
      }
    });
  }
}

async function postJsonWithTimeout(url, body, timeoutMs = 20000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal
    });
    const data = await res.json().catch(() => null);
    return { ok: res.ok, status: res.status, data };
  } finally {
    clearTimeout(timer);
  }
}

window.explainRecommendation = async function (idx) {
  const item = displayedRecommendations[idx];
  const box = document.getElementById(`ai-explain-${idx}`);
  const btn = document.getElementById(`btn-ai-explain-${idx}`);
  if (!item || !box) return;
  box.hidden = false;
  box.textContent = 'Đang tạo lời giải thích...';
  if (btn) btn.disabled = true;
  try {
    const { ok, data } = await postJsonWithTimeout(`${API_BASE}/api/explain`, { nguyenVong: item });
    if (!ok) {
      box.textContent = formatApiError(data, 'Không tạo được lời giải thích.');
      return;
    }
    const note = data.nguon === 'du_phong' ? ' (Trợ lý AI chưa sẵn sàng, đang hiển thị giải thích của hệ thống.)' : '';
    box.textContent = data.giaiThich + note;
  } catch (err) {
    box.textContent = item.lyDoDeXuat || 'Không kết nối được máy chủ.';
  } finally {
    if (btn) btn.disabled = false;
  }
};

const chatHistory = [];

function appendChatMessage(role, text) {
  const list = document.getElementById('chat-messages');
  if (!list) return null;
  const el = document.createElement('div');
  el.className = `chat-msg ${role}`;
  el.textContent = text;
  list.appendChild(el);
  list.scrollTop = list.scrollHeight;
  return el;
}

function initChatWidget() {
  const toggle = document.getElementById('chat-toggle');
  const panel = document.getElementById('chat-panel');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  if (!toggle || !panel || !form || !input) return;

  const setOpen = (open) => {
    panel.hidden = !open;
    toggle.setAttribute('aria-expanded', String(open));
    if (open) input.focus();
  };
  toggle.addEventListener('click', () => setOpen(panel.hidden));
  document.getElementById('chat-close')?.addEventListener('click', () => setOpen(false));

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    input.value = '';
    appendChatMessage('user', question);
    const pending = appendChatMessage('model pending', 'Đang trả lời...');
    const sendBtn = form.querySelector('button');
    if (sendBtn) sendBtn.disabled = true;
    try {
      const { ok, data } = await postJsonWithTimeout(`${API_BASE}/api/chat`, {
        cauHoi: question,
        lichSu: chatHistory.slice(-8)
      }, 45000);
      const answer = ok ? data.traLoi : formatApiError(data, 'Trợ lý AI đang bận, vui lòng thử lại.');
      pending.textContent = answer;
      pending.className = 'chat-msg model';
      if (ok && data.nguon === 'gemini') {
        chatHistory.push({ vaiTro: 'user', noiDung: question }, { vaiTro: 'model', noiDung: answer });
      }
    } catch (err) {
      pending.textContent = 'Hết thời gian chờ hoặc mất kết nối. Vui lòng thử lại.';
      pending.className = 'chat-msg model';
    } finally {
      if (sendBtn) sendBtn.disabled = false;
      input.focus();
    }
  });
}


