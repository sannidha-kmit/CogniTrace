import sys
import pickle
import sklearn
import sklearn.linear_model
from sklearn.linear_model import LogisticRegression

# Map to sys.modules in case it was saved at top level
sys.modules['LogisticRegression'] = sklearn.linear_model.LogisticRegression

with open('models/adaptive_quiz_model.pkl', 'rb') as f:
    try:
        m = pickle.load(f)
        print("Successfully loaded model:")
        print("Type:", type(m))
        print("Object:", m)
        if hasattr(m, "coef_"):
            print("Coefficients:", m.coef_)
        if hasattr(m, "intercept_"):
            print("Intercept:", m.intercept_)
        if hasattr(m, "classes_"):
            print("Classes:", m.classes_)
        if hasattr(m, "feature_names_in_"):
            print("Feature names:", m.feature_names_in_)
        if hasattr(m, "n_features_in_"):
            print("N features in:", m.n_features_in_)
    except Exception as e:
        print("Error loading:", e)
