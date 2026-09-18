import os
import sys
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

thuMucGoc = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if thuMucGoc not in sys.path:
    sys.path.insert(0, thuMucGoc)

DAC_TRUNG_SO = [
    "diemToan",
    "diemVan",
    "diemNgoaiNgu",
    "diemVatLy",
    "diemHoaHoc",
    "diemSinhHoc",
    "diemTrungBinh",
    "mucKhopSoThich",
    "tiLeTaiChinh",
    "khopDiaBan",
    "diemChuanThamKhao",
    "soLuotTuongTacTruoc",
]

DAC_TRUNG_PHAN_LOAI = [
    "khoiTruong",
    "vungMien",
    "nhomNganh",
    "phuongThuc",
]

def taoPipelineTienXuLy():
    bienDoiSo = Pipeline([
        ("boSungThieu", SimpleImputer(strategy="median")),
        ("chuanHoa", StandardScaler()),
    ])

    bienDoiPhanLoai = Pipeline([
        ("boSungThieu", SimpleImputer(strategy="most_frequent")),
        ("maHoaOneHot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    boTienXuLy = ColumnTransformer(
        transformers=[
            ("so", bienDoiSo, DAC_TRUNG_SO),
            ("phanLoai", bienDoiPhanLoai, DAC_TRUNG_PHAN_LOAI),
        ],
        remainder="drop",
    )
    return boTienXuLy
