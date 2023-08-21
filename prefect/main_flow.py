# Core
import numpy as np
import pandas as pd
import zipfile

# Workflow
from prefect import flow, task
import mlflow

# ML Libraries
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from catboost import CatBoostClassifier
import optuna

class MultiColumnLabelEncoder:
    def __init__(self, columns=None):
        self.columns = columns # array of column names to encode

    def fit(self, X, y=None):
        self.encoders = {}
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            self.encoders[col] = LabelEncoder().fit(X[col])
        return self

    def transform(self, X):
        output = X.copy()
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            output[col] = self.encoders[col].transform(X[col])
        return output

    def fit_transform(self, X: object, y: object = None) -> object:
        return self.fit(X,y).transform(X)

    def inverse_transform(self, X):
        output = X.copy()
        columns = X.columns if self.columns is None else self.columns
        for col in columns:
            output[col] = self.encoders[col].inverse_transform(X[col])
        return output



@task(name='data_preperation', retries=3, retry_delay_seconds=2, log_prints=True)
def data_preperation(DATASET, PATH):
    csvzip = f'{PATH}/{DATASET}.zip'
    with zipfile.ZipFile(csvzip, 'r') as zip:
        zip.printdir()
        zip.extractall(PATH)

    train = pd.read_csv(f'{PATH}/test.csv')
    test = pd.read_csv(f'{PATH}/test.csv')
    df = pd.concat([train, test])
    return df

@task(name='preprocess_data', retries=3, retry_delay_seconds=2, log_prints=True)
def preprocess_data(df):
    df = df.drop('Unnamed: 0', axis=1)
    df = df.drop('id', axis=1)
    df.columns = [col.replace(' ', '_') for col in df.columns]
    df['Arrival_Delay_in_Minutes'] = df['Arrival_Delay_in_Minutes'].fillna(df['Arrival_Delay_in_Minutes'].mean())
    df['Arrival_Delay_in_Minutes'] = df['Arrival_Delay_in_Minutes'].astype(int)
    return df

@task(name='embedding_text', retries=3, retry_delay_seconds=2, log_prints=True)
def prepare_embedding(df):
    list_to_encode = ['Gender',
                      'Customer_Type',
                      'Class',
                      'satisfaction',
                      'Type_of_Travel']

    multi: MultiColumnLabelEncoder = MultiColumnLabelEncoder(columns=list_to_encode)

    df_encoded = multi.fit_transform(df)

    inv = multi.inverse_transform(df_encoded)
    return df_encoded

@task(name='Assign_Xy_Scale', retries=3, retry_delay_seconds=2, log_prints=True)
def Assign_Xy_Scale(df, scaler_ind):
    X = df.drop('satisfaction', axis=1)
    y = df['satisfaction']
    categorical_features_indices = np.where(X.dtypes != float)[0]

    # Normalize features
    if scaler_ind == True:
        sc = StandardScaler()
        X = sc.fit_transform(X)

    return X, y, categorical_features_indices

@task(name='model_tuning', retries=3, retry_delay_seconds=2, log_prints=True)
def model_tuning(X, y, categorical_features_indices, log_prints=True):
    def objective(trial):
        with mlflow.start_run(nested=True):
            param = {
                "objective": trial.suggest_categorical("objective", ["Logloss", "CrossEntropy"]),
                "colsample_bylevel": trial.suggest_float("colsample_bylevel", 0.01, 0.1),
                "depth": trial.suggest_int("depth", 1, 12),
                "boosting_type": trial.suggest_categorical("boosting_type", ["Ordered", "Plain"]),
                "bootstrap_type": trial.suggest_categorical(
                    "bootstrap_type", ["Bayesian", "Bernoulli", "MVS"]
                ),
                "used_ram_limit": "5gb",
            }
            mlflow.set_tag("model", "catboost")
            mlflow.set_tag("stage", "model_tuning")
            mlflow.log_params(param)

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

            if param["bootstrap_type"] == "Bayesian":
                param["bagging_temperature"] = trial.suggest_float("bagging_temperature", 0, 10)
            elif param["bootstrap_type"] == "Bernoulli":
                param["subsample"] = trial.suggest_float("subsample", 0.1, 1)

            cat_cls = CatBoostClassifier(**param)

            cat_cls.fit(X_train, y_train, eval_set=[(X_test, y_test)], cat_features=categorical_features_indices,
                        verbose=0, early_stopping_rounds=10)
            mlflow.catboost.log_model(cat_cls, artifact_path="preprocessor")
            print(f"default artifacts URI: '{mlflow.get_artifact_uri()}'")

            pred = cat_cls.predict(X_test)
            pred_labels = np.array(pred, dtype=int)
            accuracy = round(accuracy_score(y_test, pred_labels), 4)
            mlflow.log_metric("accuracy", accuracy)
            return accuracy
        mlflow.end_run()

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50, timeout=600)
    print("Number of finished trials: {}".format(len(study.trials)))

    print("Best trial:")
    trial = study.best_trial

    print("  Value: {}".format(trial.value))

    print("  Params: ")
    for key, value in trial.params.items():
        print("    {}: {}".format(key, value))

    return trial.params

@task(name='final_model', retries=3, retry_delay_seconds=2, log_prints=True)
def final_model(X, y, categorical_features_indices, params, log_prints=True):
    with mlflow.start_run(nested=True):
        mlflow.set_tag("model", "catboost")
        mlflow.set_tag("stage", "final model")
        mlflow.log_params(params)

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

        cat_cls = CatBoostClassifier(**params)

        cat_cls.fit(X_train, y_train, eval_set=[(X_test, y_test)], cat_features=categorical_features_indices, verbose=0,
                    early_stopping_rounds=100)

        pred = cat_cls.predict(X_test)

        pred_labels = np.array(pred, dtype=int)
        accuracy = round(accuracy_score(y_test, pred_labels), 4)
        mlflow.log_metric("accuracy", accuracy)

        mlflow.log_artifact("prefect/models", artifact_path="preprocessor")
        mlflow.catboost.log_model(cat_cls, artifact_path="models")
        print(f"default artifacts URI: '{mlflow.get_artifact_uri()}'")
    mlflow.end_run()

@flow
def main(log_prints=True):
    mlflow.set_tracking_uri("http://127.0.0.1:5000/")
    mlflow.set_experiment("flight-satisfaction-prediction")
    print(f"default artifacts URI: '{mlflow.get_artifact_uri()}'")

    script_path = '/Users/evanhofmeister/PycharmProjects/mlops-zoomcamp-final-project/prefect'
    DATASET = 'airline-passenger-satisfaction'
    PATH = f'{script_path}/data'
    df = data_preperation(DATASET, PATH)
    df = preprocess_data(df)
    df = prepare_embedding(df)
    X, y, categorical_features_indices = Assign_Xy_Scale(df, False)

    params = model_tuning(X, y, categorical_features_indices)
    final_model(X, y, categorical_features_indices, params)


if __name__ == '__main__':
    main()