import numpy as np
import pandas as pd
from ml.forecasting.xgboost_model import predict_with_calibration, apply_sanity_bounds


def make_mock_model():
    import xgboost as xgb
    from sklearn.tree import DecisionTreeRegressor
    X = np.random.rand(100, 5).astype(np.float32)
    y = np.log1p(np.random.rand(100) * 10000)
    model = xgb.XGBRegressor(n_estimators=10, max_depth=3)
    model.fit(X, y)
    return model


def test_predict_with_calibration_applies_bias_correction():
    model = make_mock_model()
    features = ["f1", "f2", "f3", "f4", "f5"]
    input_df = pd.DataFrame(np.random.rand(5, 5), columns=features)

    calibration = {
        "site_bias": {1: 0.5, 2: -0.3},
        "site_std": {1: 0.2, 2: 0.15},
        "global_bias": 0.1,
        "global_std": 0.25,
        "median_site_std": 0.2,
        "log_transform": True,
    }

    pred_kwh, ci_lower, ci_upper = predict_with_calibration(
        model, features, input_df, calibration, site_id=1
    )

    assert len(pred_kwh) == 5
    assert len(ci_lower) == 5
    assert len(ci_upper) == 5
    assert np.all(pred_kwh >= 0)
    assert np.all(ci_lower <= ci_upper), "CI lower must be <= CI upper"
    assert np.all(ci_lower >= 0)


def test_predict_with_calibration_without_site_id():
    model = make_mock_model()
    features = ["f1", "f2", "f3", "f4", "f5"]
    input_df = pd.DataFrame(np.random.rand(3, 5), columns=features)

    calibration = {
        "site_bias": {},
        "site_std": {},
        "global_bias": 0.05,
        "global_std": 0.2,
        "median_site_std": 0.15,
        "log_transform": True,
    }

    pred_kwh, ci_lower, ci_upper = predict_with_calibration(
        model, features, input_df, calibration, site_id=None
    )

    assert len(pred_kwh) == 3
    assert np.all(pred_kwh >= 0)


def test_apply_sanity_bounds():
    predictions = np.array([100, 5000, 20000])
    site_mean = 1000.0
    bounded = apply_sanity_bounds(predictions, site_mean=site_mean)
    assert bounded[0] == 300.0  # 1000 * 0.3 (min multiplier)
    assert bounded[1] == 2000.0  # 1000 * 2.0 (max multiplier)
    assert bounded[2] == 2000.0
