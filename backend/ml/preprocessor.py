import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder


class DataPreprocessor:
    """
    Data preprocessor for student profile and university admission features.
    Handles missing values and encodes categorical features.
    """

    def __init__(self):
        self.numeric_columns = [
            "diemToan",
            "diemVan",
            "diemAnh",
            "diemLy",
            "diemHoa",
            "diemSinh",
            "diemSu",
            "diemDia",
            "diemGDCD",
            "diemTrungBinh",
            "diemHocBa",
            "diemDanhGiaNangLuc",
        ]
        self.categorical_columns = [
            "toHopMon",
            "phuongThucXetTuyen",
            "soThichNganh",
            "nhomNganh",
            "khuVuc",
            "mucHocPhi",
        ]
        self.encoders = {}
        self.target_encoder = LabelEncoder()

        # Vietnamese alias attributes for backwards compatibility
        self.danhSachCotSo = self.numeric_columns
        self.danhSachCotPhanLoai = self.categorical_columns
        self.cacBoMaHoa = self.encoders
        self.boMaHoaNhan = self.target_encoder

    def handle_missing_values(self, input_df: pd.DataFrame) -> pd.DataFrame:
        """Fills missing numeric values with mean and categoricals with 'Other'/'Khac'."""
        df = input_df.copy()
        for col in self.numeric_columns:
            if col in df.columns:
                mean_val = df[col].dropna().mean() if not df[col].dropna().empty else 0.0
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(mean_val)
            else:
                df[col] = 0.0

        for col in self.categorical_columns:
            if col in df.columns:
                df[col] = df[col].fillna("Khac").astype(str)
            else:
                df[col] = "Khac"
        return df

    def clean_and_encode_train(self, train_df: pd.DataFrame):
        """Preprocesses training dataset and encodes all categorical features."""
        df = self.handle_missing_values(train_df)

        for col in self.categorical_columns:
            encoder = LabelEncoder()
            df[col] = encoder.fit_transform(df[col])
            self.encoders[col] = encoder

        feature_columns = self.numeric_columns + self.categorical_columns
        features = df[feature_columns]

        if "nganhPhuHop" in df.columns:
            df["target"] = self.target_encoder.fit_transform(df["nganhPhuHop"])
            return features, df["target"]

        return features, None

    def encode_input_data(self, student_info):
        """Converts a student profile dictionary or single row into an encoded DataFrame."""
        if isinstance(student_info, dict):
            df = pd.DataFrame([student_info])
        else:
            df = student_info.copy()

        df = self.handle_missing_values(df)

        for col in self.categorical_columns:
            encoder = self.encoders.get(col)
            if encoder is not None:
                classes = list(encoder.classes_)
                df[col] = df[col].apply(lambda val: val if val in classes else classes[0])
                df[col] = encoder.transform(df[col])
            else:
                df[col] = 0

        feature_columns = self.numeric_columns + self.categorical_columns
        return df[feature_columns]

    # Vietnamese aliases
    xuLyDuLieuKhuyet = handle_missing_values
    lamSachVaMaHoaHuanLuyen = clean_and_encode_train
    maHoaDuLieuDauVao = encode_input_data


def preprocess_data(data: pd.DataFrame):
    """Utility function to preprocess data with DataPreprocessor."""
    preprocessor = DataPreprocessor()
    return preprocessor.clean_and_encode_train(data)


# Vietnamese backwards compatibility
BoTienXuLy = DataPreprocessor
tienXuLyDuLieu = preprocess_data
