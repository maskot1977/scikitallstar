import time
import timeit

import matplotlib.pyplot as plt
import numpy as np
import optuna
import pandas as pd
from sklearn import metrics
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import (
    LinearDiscriminantAnalysis,
    QuadraticDiscriminantAnalysis,
)
from sklearn.ensemble import (
    AdaBoostClassifier,
    AdaBoostRegressor,
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
    StackingClassifier,
    StackingRegressor,
)

# from umap import UMAP
from sklearn.feature_selection import SelectFromModel
from sklearn.linear_model import (
    Lasso,
    LinearRegression,
    LogisticRegression,
    Ridge,
    RidgeClassifier,
)
from sklearn.metrics import (
    auc,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    r2_score,
    roc_curve,
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.preprocessing import MinMaxScaler, StandardScaler
from sklearn.svm import SVC, SVR

import scikitallstars.timeout_decorator as timeout_decorator
from scikitallstars.timeout import on_timeout


def handler_func(msg):
    print(msg)


class Objective:
    def __init__(
        self,
        x_train,
        y_train,
        x_test=None,
        y_test=None,
        support=None,
        classifier_names=[
            "GradientBoosting",
            "ExtraTrees",
            "RandomForest",
            "AdaBoost",
            "MLP",
            "SVC",
            "kNN",
            "Ridge",
            "QDA",
            "LDA",
            "LogisticRegression",
        ],
        regressor_names=[
            "GradientBoosting",
            "ExtraTrees",
            "RandomForest",
            "AdaBoost",
            "MLP",
            "SVR",
            "kNN",
            "Ridge",
            "Lasso",
            "PLS",
            "LinearRegression",
        ],
        classification_metrics="f1_score",
        test_size=0.1,
        split_random_state=None
    ):
        self.x_train = x_train
        self.x_test = x_test
        self.y_train = y_train
        self.y_test = y_test
        self.support = support
        self.best_scores = {}
        self.best_params = {}
        self.best_models = {}
        self.best_score = 0
        self.best_model = None
        self.test_size = test_size
        self.split_random_state = split_random_state
        self.classifier_names = classifier_names
        self.regressor_names = regressor_names
        self.classification_metrics = classification_metrics
        self.times = {}
        self.scores = {}
        self.debug = False
        self.scalers = ["StandardScaler", "MinMaxScaler"]
        self.is_regressor = True
        if len(set(y_train)) < 3:
            self.is_regressor = False

        self.gb_loss = ["deviance", "exponential"]
        self.gb_learning_rate_init = [0.001, 0.1]
        self.gb_n_estimators = [50, 200]
        self.gb_max_depth = [2, 32]
        self.gb_warm_start = [True, False]

        self.et_n_estimators = [50, 300]
        self.et_max_depth = [2, 32]
        self.et_warm_start = [True, False]

        self.ab_n_estimators = [50, 300]
        self.ab_loss = ["linear", "square", "exponential"]

        self.knn_n_neighbors = [2, 10]
        self.knn_weights = ["uniform", "distance"]
        self.knn_algorithm = ["auto", "ball_tree", "kd_tree", "brute"]
        self.knn_leaf_size = [20, 40]

        self.lr_C = [1e-5, 1e5]
        self.lr_max_iter = 530000
        self.lr_solver = ["newton-cg", "lbfgs", "liblinear", "sag", "saga"]

        self.mlp_max_iter = 530000
        self.mlp_n_layers = [1, 10]
        self.mlp_n_neurons = [4, 64]
        self.mlp_warm_start = [True, False]
        self.mlp_activation = ["identity", "logistic", "tanh", "relu"]

        self.pls_max_iter = 530000
        self.pls_scale = [True, False]
        self.pls_algorithm = ["nipals", "svd"]
        self.pls_tol = [1e-7, 1e-5]

        self.lasso_alpha = [1e-5, 1e5]
        self.lasso_max_iter = 530000
        self.lasso_warm_start = [True, False]
        self.lasso_normalize = [True, False]
        self.lasso_selection = ["cyclic", "random"]

        self.ridge_alpha = [1e-5, 1e5]
        self.ridge_max_iter = 530000
        self.ridge_solver = [
            "auto",
            "svd",
            "cholesky",
            "lsqr",
            "sparse_cg",
            "sag",
            "saga",
        ]
        self.ridge_normalize = [True, False]

        self.rf_max_depth = [2, 32]
        self.rf_max_features = ["auto", "sqrt", "log2"]
        self.rf_n_estimators = [100, 200]
        self.rf_warm_start = [True, False]

        self.svm_kernel = ["linear", "rbf"]
        self.svm_c = [1e-5, 1e5]
        self.svm_epsilon = [1e-5, 1e5]
        self.svm_max_iter = 530000

        self.linear_regression_fit_intercept = [True, False]
        self.linear_regression_normalize = [True, False]

    def get_model_names(self):
        if self.is_regressor:
            return self.regressor_names
        else:
            return self.classifier_names

    def set_model_names(self, model_names):
        if self.is_regressor:
            self.regressor_names = model_names
        else:
            self.classifier_names = model_names

    # @on_timeout(limit=5, handler=handler_func, hint=u'call')
    @timeout_decorator.timeout(10)
    def __call__(self, trial):
        if self.support is None:
            if self.y_test is None:
                x_train, x_test, y_train, y_test = train_test_split(
                    self.x_train, self.y_train, test_size=self.test_size
                )
            else:
                x_train = self.x_train
                x_test = self.x_test
                y_train = self.y_train
                y_test = self.y_test
        else:
            if self.y_test is None:
                x_train, x_test, y_train, y_test = train_test_split(
                    self.x_train.iloc[:, self.support], self.y_train, test_size=self.test_size, random_state=self.split_random_state
                )
            else:
                x_train = self.x_train.iloc[:, self.support]
                x_test = self.x_test.iloc[:, self.support]
                y_train = self.y_train
                y_test = self.y_test

        params = self.generate_params(trial, x_train)

        if len(set(y_train)) < 3:
            self.is_regressor = False
            model = Classifier(params, debug=self.debug)
            seconds = self.model_fit(model, x_train, y_train)
            if params["model_name"] not in self.times.keys():
                self.times[params["model_name"]] = []
            self.times[params["model_name"]].append(seconds)

            if self.classification_metrics == "f1_score":
                if self.support is None:
                    score = metrics.f1_score(model.predict(x_test), y_test)
                    # score = metrics.f1_score(model.predict(self.x_train), self.y_train)
                else:
                    # score = metrics.f1_score(model.predict(self.x_train.iloc[:, self.support]), self.y_train)
                    # score = metrics.f1_score(model.predict(x_test.iloc[:, self.support]), y_test)
                    score = metrics.f1_score(model.predict(x_test), y_test)
            else:
                if self.support is None:
                    score = model.model.score(x_test, y_test)
                    # score = model.model.score(self.x_train, self.y_train)
                else:
                    # score = model.model.score(self.x_train.iloc[:, self.support], self.y_train)
                    score = model.model.score(x_test, y_test)

            if params["model_name"] not in self.scores.keys():
                self.scores[params["model_name"]] = []
            self.scores[params["model_name"]].append(score)

            if self.best_score < score:
                self.best_score = score
                self.best_model = model
            if params["model_name"] not in self.best_scores.keys():
                self.best_scores[params["model_name"]] = 0
            if self.best_scores[params["model_name"]] < score:
                self.best_scores[params["model_name"]] = score
                self.best_models[params["model_name"]] = model

        else:
            self.is_regressor = True
            model = Regressor(params, debug=self.debug, support=self.support)
            seconds = self.model_fit(model, x_train, y_train)
            if params["model_name"] not in self.times.keys():
                self.times[params["model_name"]] = []
            self.times[params["model_name"]].append(seconds)

            if self.support is None:
                # score = model.model.score(self.x_train, self.y_train)
                score = model.model.score(x_test, y_test)
            else:
                # score = model.model.score(self.x_train.iloc[:, self.support], self.y_train)
                score = model.model.score(x_test, y_test)
            if params["model_name"] not in self.scores.keys():
                self.scores[params["model_name"]] = []
            self.scores[params["model_name"]].append(score)

            if self.best_score < score:
                self.best_score = score
                self.best_model = model
            if params["model_name"] not in self.best_scores.keys():
                self.best_scores[params["model_name"]] = 0
            if self.best_scores[params["model_name"]] < score:
                self.best_scores[params["model_name"]] = score
                self.best_models[params["model_name"]] = model

        return score

    @on_timeout(limit=10, handler=handler_func, hint=u"model_fit")
    def model_fit(self, model, x_train, y_train):
        return timeit.timeit(lambda: model.fit(x_train, y_train), number=1)

    def generate_params(self, trial, x):
        params = {}

        params["standardize"] = trial.suggest_categorical("standardize", self.scalers)
        if len(set(self.y_train)) < 3:
            params["model_name"] = trial.suggest_categorical(
                "model_name", self.classifier_names
            )
            model_params = {}

            if params["model_name"] == "SVC":
                model_params["kernel"] = trial.suggest_categorical(
                    "svc_kernel", ["linear", "rbf"]
                )
                model_params["C"] = trial.suggest_loguniform(
                    "svm_c", self.svm_c[0], self.svm_c[1]
                )
                # model_params["epsilon"] = trial.suggest_loguniform(
                #    "svm_epsilon", self.svm_epsilon[0], self.svm_epsilon[1]
                # )
                if model_params["kernel"] == "rbf":
                    model_params["gamma"] = trial.suggest_categorical(
                        "svc_gamma", ["auto", "scale"]
                    )
                else:
                    model_params["gamma"] = "auto"
                model_params["max_iter"] = self.svm_max_iter
                model_params["probability"] = True

            elif params["model_name"] == "RandomForest":
                model_params["n_estimators"] = trial.suggest_int(
                    "rf_n_estimators", self.rf_n_estimators[0], self.rf_n_estimators[1]
                )
                model_params["max_features"] = trial.suggest_categorical(
                    "rf_max_features", self.rf_max_features
                )
                model_params["n_jobs"] = -1
                model_params["max_depth"] = trial.suggest_int(
                    "rf_max_depth", self.rf_max_depth[0], self.rf_max_depth[1]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "rf_warm_start", self.rf_warm_start
                )

            elif params["model_name"] == "MLP":
                layers = []
                n_layers = trial.suggest_int(
                    "n_layers", self.mlp_n_layers[0], self.mlp_n_layers[1]
                )
                for i in range(n_layers):
                    layers.append(
                        trial.suggest_int(
                            str(i), self.mlp_n_neurons[0], self.mlp_n_neurons[1]
                        )
                    )
                model_params["hidden_layer_sizes"] = set(layers)
                model_params["max_iter"] = self.mlp_max_iter
                model_params["early_stopping"] = True
                model_params["warm_start"] = trial.suggest_categorical(
                    "mlp_warm_start", self.mlp_warm_start
                )
                model_params["activation"] = trial.suggest_categorical(
                    "mlp_activation", self.mlp_activation
                )

            elif params["model_name"] == "LogisticRegression":
                model_params["C"] = trial.suggest_loguniform(
                    "lr_C", self.lr_C[0], self.lr_C[0]
                )
                model_params["solver"] = trial.suggest_categorical(
                    "lr_solver", self.lr_solver
                )
                model_params["max_iter"] = self.lr_max_iter

            elif params["model_name"] == "GradientBoosting":
                model_params["loss"] = trial.suggest_categorical("loss", self.gb_loss)
                model_params["n_estimators"] = trial.suggest_int(
                    "gb_n_estimators", self.gb_n_estimators[0], self.gb_n_estimators[1]
                )
                model_params["max_depth"] = trial.suggest_int(
                    "gb_max_depth", self.gb_max_depth[0], self.gb_max_depth[1]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "gb_warm_start", self.gb_warm_start
                )

            elif params["model_name"] == "ExtraTrees":
                model_params["n_estimators"] = trial.suggest_int(
                    "et_n_estimators", self.et_n_estimators[0], self.et_n_estimators[1]
                )
                model_params["max_depth"] = trial.suggest_int(
                    "et_max_depth", self.et_max_depth[0], self.et_max_depth[1]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "et_warm_start", self.et_warm_start
                )

            elif params["model_name"] == "AdaBoost":
                model_params["n_estimators"] = trial.suggest_int(
                    "ab_n_estimators", self.ab_n_estimators[0], self.ab_n_estimators[1]
                )
                # model_params["loss"] = trial.suggest_categorical(
                #    "ab_loss", self.ab_loss
                # )

            elif params["model_name"] == "kNN":
                model_params["n_neighbors"] = trial.suggest_int(
                    "knn_n_neighbors", self.knn_n_neighbors[0], self.knn_n_neighbors[1]
                )
                model_params["weights"] = trial.suggest_categorical(
                    "knn_weights", self.knn_weights
                )
                model_params["algorithm"] = trial.suggest_categorical(
                    "knn_algorithm", self.knn_algorithm
                )
                model_params["leaf_size"] = trial.suggest_int(
                    "knn_leaf_size", self.knn_leaf_size[0], self.knn_leaf_size[1]
                )

            elif params["model_name"] == "Ridge":
                model_params["alpha"] = trial.suggest_loguniform(
                    "ridge_alpha", self.ridge_alpha[0], self.ridge_alpha[1]
                )
                model_params["max_iter"] = self.ridge_max_iter
                model_params["normalize"] = trial.suggest_categorical(
                    "ridge_normalize", self.ridge_normalize
                )
                model_params["solver"] = trial.suggest_categorical(
                    "ridge_solver", self.ridge_solver
                )

            elif params["model_name"] == "QDA":
                pass
            elif params["model_name"] == "LDA":
                pass
            else:
                raise RuntimeError("unspport classifier", params["model_name"])
            params["model_params"] = model_params

        else:
            params["model_name"] = trial.suggest_categorical(
                "model_name", self.regressor_names
            )
            model_params = {}

            if params["model_name"] == "GradientBoosting":
                # model_params["loss"] = trial.suggest_categorical(
                #    "gb_loss", ["ls", "lad", "huber", "quantile"]
                # )
                model_params["learning_rate"] = trial.suggest_loguniform(
                    "learning_rate_init",
                    self.gb_learning_rate_init[0],
                    self.gb_learning_rate_init[1],
                )
                model_params["n_estimators"] = trial.suggest_int(
                    "gb_n_estimators", self.gb_n_estimators[0], self.gb_n_estimators[1]
                )
                # model_params["criterion"] = trial.suggest_categorical(
                #    "gb_criterion", ["friedman_mse", "mse", "mae"]
                # )
                model_params["max_depth"] = trial.suggest_int(
                    "gb_max_depth", self.gb_max_depth[0], self.gb_max_depth[1]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "gb_warm_start", self.gb_warm_start
                )
                # model_params["max_features"] = trial.suggest_categorical(
                #    "gb_max_features", ["auto", "sqrt", "log2"]
                # )
                # model_params["tol"] = trial.suggest_loguniform(
                #    "gb_tol", 1e-5, 1e-3
                # )

            elif params["model_name"] == "ExtraTrees":
                model_params["n_estimators"] = trial.suggest_int(
                    "et_n_estimators", self.et_n_estimators[0], self.et_n_estimators[1]
                )
                model_params["criterion"] = trial.suggest_categorical(
                    "et_criterion", ["mse", "mae"]
                )
                model_params["max_depth"] = trial.suggest_int(
                    "et_max_depth", self.et_max_depth[0], self.et_max_depth[1]
                )
                model_params["max_features"] = trial.suggest_categorical(
                    "et_max_features", ["auto", "sqrt", "log2"]
                )
                model_params["bootstrap"] = True
                model_params["oob_score"] = trial.suggest_categorical(
                    "et_oob_score", [True]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "et_warm_start", self.et_warm_start
                )

            elif params["model_name"] == "RandomForest":
                model_params["n_estimators"] = trial.suggest_int(
                    "rf_n_estimators", self.rf_n_estimators[0], self.rf_n_estimators[1]
                )
                model_params["criterion"] = trial.suggest_categorical(
                    "rf_criterion", ["mse", "mae"]
                )
                model_params["max_depth"] = trial.suggest_int(
                    "rf_max_depth", self.rf_max_depth[0], self.rf_max_depth[1]
                )
                model_params["max_features"] = trial.suggest_categorical(
                    "rf_max_features", self.rf_max_features
                )
                model_params["bootstrap"] = True
                model_params["oob_score"] = trial.suggest_categorical(
                    "rf_oob_score", [True]
                )
                model_params["warm_start"] = trial.suggest_categorical(
                    "rf_warm_start", self.rf_warm_start
                )

            elif params["model_name"] == "AdaBoost":
                model_params["n_estimators"] = trial.suggest_int(
                    "ab_n_estimators", self.ab_n_estimators[0], self.ab_n_estimators[1]
                )
                model_params["learning_rate"] = trial.suggest_loguniform(
                    "ab_learning_rate", 0.1, 1.0
                )
                model_params["loss"] = trial.suggest_categorical(
                    "ab_loss", self.ab_loss
                )

            elif params["model_name"] == "MLP":
                layers = []
                n_layers = trial.suggest_int(
                    "n_layers", self.mlp_n_layers[0], self.mlp_n_layers[1]
                )
                for i in range(n_layers):
                    layers.append(
                        trial.suggest_int(
                            str(i), self.mlp_n_neurons[0], self.mlp_n_neurons[1]
                        )
                    )
                model_params["hidden_layer_sizes"] = set(layers)
                # model_params["activation"] = trial.suggest_categorical(
                #    "mlp_activation", self.mlp_activation
                # )
                # model_params["solver"] = trial.suggest_categorical(
                #    "mlp_solver", ["sgd", "adam"]
                # )
                model_params["solver"] = "adam"
                model_params["learning_rate"] = trial.suggest_categorical(
                    "mlp_learning_rate", ["constant", "invscaling", "adaptive"]
                )
                if model_params["solver"] in ["sgd", "adam"]:
                    model_params["learning_rate_init"] = trial.suggest_loguniform(
                        "mlp_learning_rate_init", 1e-4, 1e-2
                    )
                model_params["max_iter"] = self.mlp_max_iter
                model_params["early_stopping"] = True
                model_params["warm_start"] = trial.suggest_categorical(
                    "mlp_warm_start", self.mlp_warm_start
                )

            elif params["model_name"] == "SVR":
                model_params["kernel"] = trial.suggest_categorical(
                    "svm_kernel", self.svm_kernel
                )
                model_params["C"] = trial.suggest_loguniform(
                    "svm_c", self.svm_c[0], self.svm_c[1]
                )
                if model_params["kernel"] == "rbf":
                    model_params["gamma"] = trial.suggest_categorical(
                        "svc_gamma", ["auto", "scale"]
                    )
                else:
                    model_params["gamma"] = "auto"
                model_params["max_iter"] = self.svm_max_iter
                # model_params["epsilon"] = trial.suggest_loguniform(
                #    "svm_epsilon", self.svm_epsilon[0], self.svm_epsilon[1]
                # )

            elif params["model_name"] == "kNN":
                model_params["n_neighbors"] = trial.suggest_int(
                    "knn_n_neighbors", self.knn_n_neighbors[0], self.knn_n_neighbors[1]
                )
                model_params["weights"] = trial.suggest_categorical(
                    "knn_weights", self.knn_weights
                )
                model_params["algorithm"] = trial.suggest_categorical(
                    "knn_algorithm", self.knn_algorithm
                )

            elif params["model_name"] == "Ridge":
                model_params["alpha"] = trial.suggest_loguniform(
                    "ridge_alpha", self.ridge_alpha[0], self.ridge_alpha[1]
                )
                model_params["max_iter"] = self.ridge_max_iter
                model_params["normalize"] = trial.suggest_categorical(
                    "ridge_normalize", self.ridge_normalize
                )
                model_params["solver"] = trial.suggest_categorical(
                    "ridge_solver", self.ridge_solver
                )

            elif params["model_name"] == "Lasso":
                model_params["alpha"] = trial.suggest_loguniform(
                    "lasso_alpha", self.lasso_alpha[0], self.lasso_alpha[1]
                )
                model_params["max_iter"] = self.lasso_max_iter
                model_params["warm_start"] = trial.suggest_categorical(
                    "lasso_warm_start", self.lasso_warm_start
                )
                model_params["normalize"] = trial.suggest_categorical(
                    "lasso_normalize", self.lasso_normalize
                )
                model_params["selection"] = trial.suggest_categorical(
                    "lasso_selection", self.lasso_selection
                )

            elif params["model_name"] == "PLS":
                if self.support is None:
                    model_params["n_components"] = trial.suggest_int(
                        "n_components", 2, self.x_train.shape[1]
                    )
                else:
                    model_params["n_components"] = trial.suggest_int(
                        "n_components", 2, self.x_train.iloc[:, self.support].shape[1]
                    )
                model_params["max_iter"] = self.pls_max_iter
                model_params["scale"] = trial.suggest_categorical(
                    "pls_scale", self.pls_scale
                )
                # model_params["algorithm"] = trial.suggest_categorical(
                #    "pls_algorithm", self.pls_algorithm
                # )
                model_params["tol"] = trial.suggest_loguniform(
                    "pls_tol",
                    self.pls_tol[0],
                    self.pls_tol[1],
                )

            elif params["model_name"] == "LinearRegression":
                model_params["fit_intercept"] = trial.suggest_categorical(
                    "linear_regression_fit_intercept",
                    self.linear_regression_fit_intercept,
                )
                model_params["normalize"] = trial.suggest_categorical(
                    "linear_regression_normalize", self.linear_regression_normalize
                )

            else:
                raise RuntimeError("unspport regressor", params["model_name"])
            params["model_params"] = model_params

        return params

    def predict(self, x):
        return self.best_model.predict(pd.DataFrame(x), support=self.support)

    def score(self, x, y):
        if type(y) is not pd.core.series.Series:
            try:
                y = pd.DataFrame(y)[0]
            except:
                pass
        return self.best_model.score(pd.DataFrame(x), y, support=self.support)


class Classifier:
    def __init__(self, params, debug=False):
        self.params = params
        self.debug = debug
        if params["standardize"] == "StandardScaler":
            self.standardizer = StandardScaler()
        elif params["standardize"] == "MinMaxScaler":
            self.standardizer = MinMaxScaler()
        elif params["standardize"] == "NoScaler":
            self.standardizer = NullScaler()

        if params["model_name"] == "RandomForest":
            self.model = RandomForestClassifier(**params["model_params"])
        elif params["model_name"] == "SVC":
            self.model = SVC(**params["model_params"])
        elif params["model_name"] == "MLP":
            self.model = MLPClassifier(**params["model_params"])
        elif params["model_name"] == "LogisticRegression":
            self.model = LogisticRegression(**params["model_params"])
        elif params["model_name"] == "GradientBoosting":
            self.model = GradientBoostingClassifier(**params["model_params"])
        elif params["model_name"] == "kNN":
            self.model = KNeighborsClassifier(**params["model_params"])
        elif params["model_name"] == "Ridge":
            self.model = RidgeClassifier(**params["model_params"])
        elif params["model_name"] == "LDA":
            self.model = LinearDiscriminantAnalysis(**params["model_params"])
        elif params["model_name"] == "QDA":
            self.model = QuadraticDiscriminantAnalysis(**params["model_params"])
        elif params["model_name"] == "ExtraTrees":
            self.model = ExtraTreesClassifier(**params["model_params"])
        elif params["model_name"] == "AdaBoost":
            self.model = AdaBoostClassifier(**params["model_params"])
        if self.debug:
            print(self.model)

    def _fit_and_predict_core(
        self, x, y=None, fitting=False, proba=False, support=None, score=False
    ):
        if support is None:
            if fitting == True:
                self.standardizer.fit(x)

            self.standardizer.transform(x)
            if score:
                pred = np.array(self.model.predict(x))
                return f1_score(pred.flatten(), np.array(y).flatten())

            if fitting == True:
                self.model.fit(x, y)
            if y is None:
                if proba:
                    return self.model.predict_proba(x)
                else:
                    return self.model.predict(x)
        else:
            if fitting == True:
                self.standardizer.fit(x.iloc[:, support])

            self.standardizer.transform(x.iloc[:, support])
            if score:
                pred = np.array(self.model.predict(x.iloc[:, support]))
                return f1_score(pred.flatten(), np.array(y).flatten())

            if fitting == True:
                self.model.fit(x.iloc[:, support], y)

            if y is None:
                if proba and hasattr(self.model, "predict_proba"):
                    return self.model.predict_proba(x.iloc[:, support])
                else:
                    return self.model.predict(x.iloc[:, support])

        return None

    @on_timeout(limit=60, handler=handler_func, hint=u"classifier.fit")
    def fit(self, x, y, support=None):
        self._fit_and_predict_core(x, y, fitting=True, support=support)
        return self

    def predict(self, x, support=None):
        pred_y = self._fit_and_predict_core(x, support=support)
        return pred_y

    def predict_proba(self, x, support=None):
        pred_y = self._fit_and_predict_core(x, proba=True, support=support)
        return pred_y

    def score(self, x, y, support=None):
        return self._fit_and_predict_core(x, y, support=support, score=True)


class Regressor:
    def __init__(self, params, debug=False, support=None):
        self.params = params
        self.debug = debug
        self.support = support
        if params["standardize"] == "StandardScaler":
            self.standardizer = StandardScaler()
        elif params["standardize"] == "MinMaxScaler":
            self.standardizer = MinMaxScaler()
        elif params["standardize"] == "NoScaler":
            self.standardizer = NullScaler()

        if params["model_name"] == "RandomForest":
            self.model = RandomForestRegressor(**params["model_params"])
        elif params["model_name"] == "SVR":
            self.model = SVR(**params["model_params"])
        elif params["model_name"] == "MLP":
            self.model = MLPRegressor(**params["model_params"])
        elif params["model_name"] == "LinearRegression":
            self.model = LinearRegression(**params["model_params"])
        elif params["model_name"] == "PLS":
            self.model = PLSRegression(**params["model_params"])
        elif params["model_name"] == "GradientBoosting":
            self.model = GradientBoostingRegressor(**params["model_params"])
        elif params["model_name"] == "kNN":
            self.model = KNeighborsRegressor(**params["model_params"])
        elif params["model_name"] == "Ridge":
            self.model = Ridge(**params["model_params"])
        elif params["model_name"] == "Lasso":
            self.model = Lasso(**params["model_params"])
        elif params["model_name"] == "ExtraTrees":
            self.model = ExtraTreesRegressor(**params["model_params"])
        elif params["model_name"] == "AdaBoost":
            self.model = AdaBoostRegressor(**params["model_params"])
        else:
            self.model = None
            print(params)
            raise
        if self.debug:
            print(self.model)

    def _fit_and_predict_core(
        self, x, y=None, fitting=False, proba=False, support=None, score=False
    ):
        if support is None:
            if fitting == True:
                self.standardizer.fit(x)

            self.standardizer.transform(x)
            if score:
                pred = np.array(self.model.predict(x))
                return r2_score(pred.flatten(), np.array(y).flatten())

            if fitting == True:
                self.model.fit(x, y)
            if y is None:
                if proba:
                    return self.model.predict_proba(x)
                else:
                    return self.model.predict(x)
        else:
            if fitting == True:
                self.standardizer.fit(x.iloc[:, support])

            self.standardizer.transform(x.iloc[:, support])
            if score:
                pred = np.array(self.model.predict(x.iloc[:, support]))
                return r2_score(pred.flatten(), np.array(y).flatten())

            if fitting == True:
                self.model.fit(x.iloc[:, support], y)

            if y is None:
                if proba:
                    return self.model.predict_proba(x.iloc[:, support])
                else:
                    return self.model.predict(x.iloc[:, support])

        return None

    @on_timeout(limit=600, handler=handler_func, hint=u"regressor.fit")
    def fit(self, x, y, support=None):
        self._fit_and_predict_core(x, y, fitting=True, support=support)
        return self

    def predict(self, x, support=None):
        pred_y = self._fit_and_predict_core(x, support=support)
        return pred_y

    def predict_proba(self, x, support=None):
        pred_y = self._fit_and_predict_core(x, proba=True, support=support)
        return pred_y

    def score(self, x, y, support=None):
        return self._fit_and_predict_core(x, y, support=support, score=True)


class NullScaler(BaseEstimator, TransformerMixin):
    def __init__(self):
        pass

    def fit(self, x, y=None):
        return self

    def transform(self, x, y=None):
        return x


def random_forest_feature_selector(
    X_train, y_train, timeout=30, n_trials=20, show_progress_bar=False
):
    objective = Objective(X_train, y_train)
    objective.set_model_names(["RandomForest"])

    optuna.logging.set_verbosity(optuna.logging.WARN)
    study = optuna.create_study(direction="maximize")
    study.optimize(
        objective,
        timeout=timeout,
        n_trials=n_trials,
        show_progress_bar=show_progress_bar,
    )
    support = np.where(
        objective.best_model.model.feature_importances_ == 0, False, True
    )

    if sum([1 if x else 0 for x in support]) == len(support):
        selector = SelectFromModel(estimator=objective.best_model.model).fit(
            X_train, y_train
        )
        support = selector.get_support()

    return support


def fit(
    X_train,
    y_train,
    x_test=None,
    y_test=None
    feature_selection=True,
    verbose=True,
    timeout=100,
    n_trials=100,
    show_progress_bar=True,
):
    X_train = pd.DataFrame(X_train)
    if type(y_train) is not pd.core.series.Series:
        y_train = pd.DataFrame(y_train)[0]
    if feature_selection:
        support = random_forest_feature_selector(X_train, y_train)
        X_train_selected = X_train.iloc[:, support]
        if verbose:
            print(
                "feature selection: X_train",
                X_train.shape,
                "->",
                X_train_selected.shape,
            )
        # X_train = X_train_selected
    else:
        support = np.array([True] * X_train.shape[1])
        if verbose:
            print("X_train", X_train.shape)

    objective = Objective(X_train, y_train, x_train=x_train, y_train=y_train, support=support)
    optuna.logging.set_verbosity(optuna.logging.WARN)
    study = optuna.create_study(direction="maximize")

    model_names = objective.get_model_names()
    for model_name in model_names:
        if verbose:
            print(model_name)
        for _ in range(n_trials):
            study.enqueue_trial({"model_name": model_name})

        study.optimize(
            objective,
            timeout=timeout,
            n_trials=n_trials,
            show_progress_bar=show_progress_bar,
        )
        if verbose:
            if model_name in objective.best_scores.keys():
                if model_name in objective.best_models.keys():
                    print(
                        objective.best_scores[model_name],
                        objective.best_models[model_name].model,
                    )

    study.optimize(
        objective,
        timeout=timeout,
        n_trials=n_trials,
        show_progress_bar=show_progress_bar,
    )

    if verbose:
        print(objective.best_scores)

    return objective


class StackingObjective:
    def __init__(self, objective, X_train, y_train, test_size=0.1, verbose=True, train_random_state=None):
        self.x_train = X_train
        self.y_train = y_train
        self.verbose = verbose
        self.objective = objective
        self.best_score = None
        self.best_model = None
        self.already_tried = {}
        self.rf_max_depth = [2, 32]
        self.rf_max_features = ["auto", "sqrt", "log2"]
        self.rf_n_estimators = [50, 200]
        self.rf_warm_start = [True, False]
        self.rf_criterion = ["mse", "mae"]
        self.rf_oob_score = [True, False]
        self.n_trial = 0
        self.support = objective.support
        self.is_regressor = objective.is_regressor
        self.test_size = test_size,
        self.train_random_state = train_random_state

    def __call__(self, trial):
        self.n_trial += 1
        estimators = []
        key = ""
        for model_name in self.objective.get_model_names():
            if model_name in self.objective.best_models.keys():
                in_out = trial.suggest_int(model_name, 0, 1)
                key += str(in_out)
                if in_out == 1:
                    estimators.append(
                        (model_name, self.objective.best_models[model_name].model)
                    )

        params = {}
        params["n_estimators"] = trial.suggest_int(
            "rf_n_estimators", self.rf_n_estimators[0], self.rf_n_estimators[1]
        )
        # params["max_features"] = trial.suggest_categorical(
        #            "rf_max_features", self.rf_max_features
        #        )
        params["n_jobs"] = -1
        params["warm_start"] = trial.suggest_categorical(
            "rf_warm_start", self.rf_warm_start
        )
        params["max_depth"] = trial.suggest_int(
            "rf_max_depth", self.rf_max_depth[0], self.rf_max_depth[1]
        )
        # params["criterion"] = trial.suggest_categorical(
        #            "rf_criterion", self.rf_criterion
        #        )
        params["oob_score"] = trial.suggest_categorical(
            "rf_oob_score", self.rf_oob_score
        )

        if key in self.already_tried.keys():
            pass
            # return self.already_tried[key]

        if len(estimators) == 0:
            return 0 - 530000

        if True:  # self.support is None:
            x_train, x_test, y_train, y_test = train_test_split(
                self.x_train, self.y_train, test_size=self.test_size, random_state=self.train_random_state
            )
        else:
            x_train, x_test, y_train, y_test = train_test_split(
                self.x_train.iloc[:, self.support], self.y_train, test_size=self.test_size
            )
        stacking_model1 = stacking(
            self.objective, estimators=estimators, verbose=self.verbose, params=params
        )
        stacking_model1.support = self.objective.support
        stacking_model1.fit(x_train, y_train)
        score = stacking_model1.score(x_test, y_test)
        if self.verbose:
            print("Trial ", self.n_trial)
            print(score)
            print(stacking_model1.final_estimator_)

        if self.best_score is None:
            self.best_score = score
            self.best_model = stacking_model1
        elif self.best_score < score:
            self.best_score = score
            self.best_model = stacking_model1

        self.already_tried[key] = score

        return score

    def predict(self, X):
        return self.best_model.predict(X)

    def score(self, X, Y):
        return self.best_model.score(X, Y)


def get_best_stacking(
    objective,
    X_train,
    y_train,
    verbose=True,
    timeout=1000,
    n_trials=50,
    show_progress_bar=True,
):
    X_train = pd.DataFrame(X_train)
    if type(y_train) is not pd.core.series.Series:
        y_train = pd.DataFrame(y_train)[0]
    stacking_objective = StackingObjective(objective, X_train, y_train)
    study = optuna.create_study(direction="maximize")

    try_all = {}
    for model_name in objective.get_model_names():
        try_all[model_name] = 1
    study.enqueue_trial(try_all)

    threshold = sum(
        [objective.best_scores[name] for name, model in objective.best_models.items()]
    ) / len(objective.best_models.items())
    try_threshold = {}
    for model_name in objective.get_model_names():
        if model_name in objective.best_models.keys():
            model = objective.best_models[model_name]
            if objective.best_scores[model_name] >= threshold:
                try_threshold[model_name] = 1
            else:
                try_threshold[model_name] = 0
    study.enqueue_trial(try_threshold)

    study.optimize(
        stacking_objective,
        timeout=timeout,
        n_trials=n_trials,
        show_progress_bar=show_progress_bar,
    )
    return stacking_objective


class StackingRegressorS(StackingRegressor):
    def __init__(self, **args):
        super(StackingRegressor, self).__init__(**args)
        self.support = None
        self.x = None

    def fit(self, x, y):
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingRegressor, self).fit(x, y)
        else:
            return super(StackingRegressor, self).fit(x.iloc[:, self.support], y)

    def score(self, x, y):
        x = pd.DataFrame(x)
        if type(y) is not pd.core.series.Series:
            try:
                y = pd.DataFrame(y)[0]
            except:
                pass
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingRegressor, self).score(x, y)
        else:
            return super(StackingRegressor, self).score(x.iloc[:, self.support], y)

    def predict(self, x):
        x = pd.DataFrame(x)
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingRegressor, self).predict(x)
        else:
            return super(StackingRegressor, self).predict(x.iloc[:, self.support])


class StackingClassifierS(StackingClassifier):
    def __init__(self, **args):
        super(StackingClassifier, self).__init__(**args)
        self.support = None
        self.classes_ = [0, 1]

    # @property
    # def classes_(self):
    #   return self.classes_

    def fit(self, x, y):
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingClassifier, self).fit(x, y)
        else:
            return super(StackingClassifier, self).fit(x.iloc[:, self.support], y)

    def score(self, x, y):
        x = pd.DataFrame(x)
        y = pd.DataFrame(y)[0]
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingClassifier, self).score(x, y)
        else:
            return super(StackingClassifier, self).score(x.iloc[:, self.support], y)

    def predict(self, x):
        x = pd.DataFrame(x)
        if self.support is None or len(self.support) != x.shape[1]:
            return super(StackingClassifier, self).predict(x)
        else:
            return super(StackingClassifier, self).predict(x.iloc[:, self.support])


def stacking(
    objective,
    final_estimator=None,
    use_all=False,
    verbose=True,
    estimators=None,
    params=None,
):
    if estimators is None:
        if use_all:
            estimators = [
                (name, model.model) for name, model in objective.best_models.items()
            ]

        else:
            threshold = sum(
                [
                    objective.best_scores[name]
                    for name, model in objective.best_models.items()
                ]
            ) / len(objective.best_models.items())
            estimators = []
            for name, model in objective.best_models.items():
                if objective.best_scores[name] >= threshold:
                    estimators.append((name, model.model))

    if verbose:
        print([name for name, model in estimators])

    if objective.is_regressor:
        if final_estimator is None:
            if params is None:
                final_estimator = RandomForestRegressor()
            else:
                final_estimator = RandomForestRegressor(**params)

        model = StackingRegressorS(
            estimators=estimators,
            final_estimator=final_estimator,
        )
        model.support = objective.support
    else:
        if final_estimator is None:
            if params is None:
                final_estimator = RandomForestClassifier()
            else:
                final_estimator = RandomForestClassifier(**params)

        model = StackingClassifierS(
            estimators=estimators,
            final_estimator=final_estimator,
        )
        model.support = objective.support
    return model
